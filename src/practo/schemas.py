"""Typed trust boundaries: tools, crew output, independent review and public API."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LookupResult(StrictModel):
    record_id: str
    found: bool
    status: str | None = None
    consultation_fee_inr: int | None = None
    escalation_score: float = Field(default=0, ge=0, le=1)
    recommend_escalation: bool = False


class CrewResponse(StrictModel):
    answer: str
    citations: list[str] = Field(default_factory=list)
    lookup: LookupResult | None = None
    fallback: bool = False


class ReviewVerdict(StrictModel):
    approved: bool
    final_answer: str
    reason: str


class AskRequest(StrictModel):
    query: str = Field(min_length=1, max_length=20000)
    session_id: str = Field(default="demo", pattern=r"^[A-Za-z0-9_-]{1,64}$")


class AskResponse(StrictModel):
    trace_id: str
    session_id: str
    response_format: CrewResponse
    review: ReviewVerdict | None = None
    outcome: Literal["answered", "fallback", "blocked", "budget_exceeded"]
    cache_hit: bool = False
    masked_input: str
    elapsed_ms: float = 0
    executed_agents: list[str] = Field(default_factory=list)
    executed_tools: list[str] = Field(default_factory=list)
    budget_units: int = 0


class DocumentRequest(StrictModel):
    document_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{2,63}$")
    title: str = Field(min_length=3, max_length=150)
    text: str = Field(min_length=30, max_length=3000)


class DocumentResponse(StrictModel):
    document_id: str
    revision: int
    collections: list[str]

