"""Request-scoped, conservatively metered simulated token/cost allowance."""
from dataclasses import dataclass, field
import math


class BudgetExceeded(ValueError):
    pass


@dataclass
class Budget:
    max_tokens: int = 32000
    max_cost_usd: float = 0.032
    rate_per_token: float = 0.000001
    used_tokens: int = 0
    events: list = field(default_factory=list)

    def consume(self, stage, text, output_reserve=512):
        # UTF-8 byte count is an intentionally conservative upper-bound proxy.
        # No paid inference occurs; this meters a hypothetical deployment budget.
        units = len(text.encode("utf-8")) + output_reserve
        projected = self.used_tokens + units
        cost = projected * self.rate_per_token
        if projected > self.max_tokens or cost > self.max_cost_usd:
            self.events.append({"stage": stage, "rejected": True, "projected_tokens": projected})
            raise BudgetExceeded("Request exceeds the configured simulated token/cost budget.")
        self.used_tokens = projected
        self.events.append({"stage": stage, "charged_tokens": units, "total_tokens": projected,
                            "simulated_cost_usd": round(cost, 6)})


def enforce_tool_ownership(agents, lookup_name):
    for agent in agents:
        if any(t.name == lookup_name for t in agent.tools) and agent.role != "Lookup Agent":
            raise PermissionError("Only Lookup Agent may possess the appointment lookup tool")

