"""Task 14: actual two-turn AutoGen team with evidence-dependent mock model clients."""
import json
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import StructuredMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core.models import CreateResult, RequestUsage
from autogen_ext.models.replay import ReplayChatCompletionClient

from .schemas import ReviewVerdict
from .guardrails import FALLBACK, grounded
from .retrieval import compose_context
from .lookup import render_lookup


def evidence_answer(payload):
    """Reconstruct support from retrieved chunks and lookup; never trust the draft."""
    if payload["missing_reference"]:
        return "Please provide an appointment reference such as APT-001. This session has no appointment reference."
    lookup = payload.get("lookup")
    if lookup and payload["record_only"]:
        return render_lookup(lookup)
    policy = compose_context(payload["chunks"]) if payload["chunks"] else FALLBACK
    return (render_lookup(lookup) + " " if lookup else "") + policy


class EvidenceReviewClient(ReplayChatCompletionClient):
    """Use AutoGen's official local client base, but derive results from live inputs.

    Unlike fixed response replay, unseen draft changes produce new verdicts.
    The reviewer checks evidence; the editor consumes the reviewer's report.
    """
    def __init__(self, role, budget):
        super().__init__([],model_info={"vision":False,"function_calling":False,"json_output":True,
                                      "family":"unknown","structured_output":True})
        self.role, self.budget = role, budget

    async def create(self, messages, **kwargs):
        task = next(m.content for m in messages if getattr(m,"source",None)=="user" and isinstance(m.content,str) and m.content.startswith("REVIEW_INPUT:"))
        payload = json.loads(task.removeprefix("REVIEW_INPUT:"))
        serialized_messages = json.dumps([m.model_dump() for m in messages],default=str)
        self.budget.consume(self.role, serialized_messages, output_reserve=1024)
        if self.role == "PolicyComplianceReviewer":
            allowed = evidence_answer(payload)
            approved = grounded(payload["draft"],allowed)
            result = {"approved":approved,"final_answer":payload["draft"] if approved else allowed,
                      "reason":"Draft is supported by retrieved policy/lookup evidence." if approved else "Removed unsupported or altered claims; reconstructed answer from original evidence."}
        else:
            report = next(m.content for m in reversed(messages) if getattr(m,"source",None)=="PolicyComplianceReviewer")
            result = ReviewVerdict.model_validate_json(report).model_dump()
        content = json.dumps(result)
        return CreateResult(finish_reason="stop",content=content,
                            usage=RequestUsage(prompt_tokens=len(serialized_messages.encode()),completion_tokens=len(content.encode())),cached=False)


async def review_draft(draft, state, budget):
    payload = {"draft":draft,"chunks":state.get("rag",{}).get("chunks",[]),
               "lookup":state.get("lookup"),"record_only":state["record_only"],
               "missing_reference":state["missing_reference"]}
    reviewer = AssistantAgent("PolicyComplianceReviewer",model_client=EvidenceReviewClient("PolicyComplianceReviewer",budget),
        system_message="Check every claim against the original retrieved context and lookup. Return a JSON review.")
    editor = AssistantAgent("FinalEditor",model_client=EvidenceReviewClient("FinalEditor",budget),
        system_message="Apply the review and return the final structured verdict.",output_content_type=ReviewVerdict)
    team = RoundRobinGroupChat([reviewer,editor],max_turns=2,
                              custom_message_types=[StructuredMessage[ReviewVerdict]])
    result = await team.run(task="REVIEW_INPUT:"+json.dumps(payload))
    verdict = result.messages[-1].content
    if not isinstance(verdict,ReviewVerdict):
        verdict = ReviewVerdict.model_validate_json(verdict)
    transcript = [{"source":m.source,"content":m.content.model_dump() if hasattr(m.content,"model_dump") else m.content} for m in result.messages]
    return verdict, transcript

