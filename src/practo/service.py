"""Orchestrator: masked input → memory → budget → CrewAI → AutoGen → audit."""
import asyncio
from collections import OrderedDict
import json
from pathlib import Path
import re
from threading import Lock
from time import perf_counter
import uuid

from langchain_core.chat_history import InMemoryChatMessageHistory
from .crew import run_crew
from .governance import Budget, BudgetExceeded
from .guardrails import FALLBACK, grounded, injection_detected, mask_pii, normalize
from .retrieval import RagCore
from .review import evidence_answer, review_draft
from .schemas import AskRequest, AskResponse, CrewResponse

REFERENCE = re.compile(r"\bAPT-\d{3}\b", re.I)
POLICY = re.compile(r"cancel|reschedul|book|insurance|refill|lab|telemedicine|emergen|privacy|discount|second opinion|home visit|specialt", re.I)
STATUS = re.compile(r"status|my appointment|its fee|its cost|escalat|what about it", re.I)


CAPABILITIES = (
    "I’m CareDesk, a fictional clinic support demo. I can explain booking, cancellation, "
    "fees, insurance, refills, lab reports, telemedicine, emergency routing, privacy, "
    "follow-ups, second opinions and home-visit policies. I can also read a synthetic "
    "appointment’s status and fee when you provide a reference such as APT-001. "
    "Try: What is the cancellation policy? I cannot diagnose, prescribe, or change bookings."
)


def conversation_help(query):
    # Whole-input matching prevents a greeting from swallowing a substantive request.
    text = query.casefold().strip(" .!?，")
    if re.fullmatch(r"(?:hi|hello|hey|good morning|good evening)(?: caredesk)?", text):
        return "Hello! " + CAPABILITIES
    if re.fullmatch(r"(?:please )?(?:help(?: me)?|what can you (?:help(?: me)? with|do)|how can you help(?: me)?|what do you do|who are you|what are your capabilities)", text):
        return CAPABILITIES
    if text in {"what do you say", "what do you mean", "i don't understand"}:
        return "Please tell me which clinic policy or appointment you mean. " + CAPABILITIES
    if text in {"thanks", "thank you", "thank you so much"}:
        return "You’re welcome. Ask another clinic-policy question or provide an appointment reference when you need it."
    return None


class AuditLog:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()

    def write(self, event):
        # Serialize first so deeply nested strings receive the same masking.
        line = mask_pii(json.dumps(event, ensure_ascii=False, default=str))
        with self.lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")


class ClinicService:
    def __init__(self, rag=None, log_path=".runtime/requests.jsonl"):
        self.rag = rag or RagCore()
        self.audit = AuditLog(log_path)
        self.histories = OrderedDict()
        self.cache = OrderedDict()
        self.lock = asyncio.Lock()
        self.crew_calls = 0
        self.review_calls = 0
        self.tool_calls = 0
        self.last_trace = {}

    def history(self, session_id):
        if session_id not in self.histories:
            self.histories[session_id] = InMemoryChatMessageHistory()
        self.histories.move_to_end(session_id)
        while len(self.histories) > 200:
            self.histories.popitem(last=False)
        return self.histories[session_id]

    def resolve(self, query, history):
        explicit = REFERENCE.search(query)
        record_id = explicit.group().upper() if explicit else None
        wants_record = bool(explicit or STATUS.search(query))
        if wants_record and not record_id:
            for message in reversed(history.messages):
                if message.type == "human" and (match := REFERENCE.search(message.content)):
                    record_id = match.group().upper()
                    break
        record_only = wants_record and not POLICY.search(query)
        return record_id, bool(record_only), wants_record and not record_id

    async def ask(self, request: AskRequest, trace_id=None, *, emit_log=True):
        async with self.lock:  # bounded single-worker demo: model, cache and history are atomic
            started = perf_counter()
            trace_id = trace_id or uuid.uuid4().hex
            query = normalize(mask_pii(request.query))
            budget = Budget()
            trace = {"event":"inference","trace_id":trace_id,"session_id":request.session_id,
                     "query":query,"mode":"MOCK_LLM","tool_events":[]}
            cache_hit, verdict = False, None
            try:
                if injection_detected(query):
                    response = CrewResponse(answer="Request blocked: instructions attempting to override system rules are not accepted.",fallback=True)
                    outcome = "blocked"
                else:
                    if len(query.encode()) > 6000:
                        budget.events.append({"stage":"input","rejected":True,"reason":"6000-byte input limit"})
                        raise BudgetExceeded("Input budget exceeded")
                    budget.consume("input", query)
                    history = self.history(request.session_id)
                    record_id, record_only, missing = self.resolve(query,history)
                    key = (query.casefold(),record_id,record_only,missing,self.rag.revision,self.rag.strategy)
                    help_answer = conversation_help(query)
                    if help_answer is not None:
                        response = CrewResponse(answer=help_answer)
                        trace["route"] = "static_application_help"
                    elif key in self.cache:
                        response, verdict = self.cache[key]
                        response, verdict = response.model_copy(deep=True), verdict.model_copy(deep=True)
                        self.cache.move_to_end(key)
                        cache_hit = True
                    else:
                        self.crew_calls += 1
                        response, state = await asyncio.to_thread(run_crew,query,record_id,self.rag,budget,
                            record_only=record_only,missing_reference=missing)
                        self.tool_calls += len(state["tool_events"])
                        trace.update(state)
                        self.review_calls += 1
                        verdict, transcript = await review_draft(response.answer,state,budget)
                        trace["review_transcript"] = transcript
                        allowed = evidence_answer({"chunks":state.get("rag",{}).get("chunks",[]),
                            "lookup":state.get("lookup"),"record_only":record_only,"missing_reference":missing})
                        if not grounded(verdict.final_answer,allowed):
                            response = CrewResponse(answer=FALLBACK,fallback=True)
                            trace["grounding_refusal"] = True
                        else:
                            response.answer = mask_pii(verdict.final_answer)
                        # Validate again after all post-processing.
                        response = CrewResponse.model_validate(response.model_dump())
                        self.cache[key] = (response.model_copy(deep=True),verdict.model_copy(deep=True))
                        while len(self.cache) > 256:
                            self.cache.popitem(last=False)
                    outcome = "fallback" if response.fallback else "answered"
                    history.add_user_message(query)
                    history.add_ai_message(response.model_dump_json())
                    history.messages = history.messages[-20:]
            except BudgetExceeded:
                response = CrewResponse(answer="Request rejected: the configured input or simulated token/cost budget was exceeded. Please shorten the request.",fallback=True)
                outcome = "budget_exceeded"
            except Exception as exc:
                trace.update(error_type=type(exc).__name__,elapsed_ms=round((perf_counter()-started)*1000,3))
                if emit_log:
                    self.audit.write(trace)
                self.last_trace = trace
                raise
            result = AskResponse(trace_id=trace_id,session_id=request.session_id,response_format=response,
                review=verdict,outcome=outcome,cache_hit=cache_hit,masked_input=query,
                elapsed_ms=round((perf_counter()-started)*1000,3),
                executed_agents=trace.get("model_calls",[]) + [m["source"] for m in trace.get("review_transcript",[]) if m["source"] != "user"],
                executed_tools=[e["tool"] for e in trace.get("tool_events",[])],budget_units=budget.used_tokens)
            trace.update(result=result.model_dump(),cache_hit=cache_hit,budget=budget.events,
                         elapsed_ms=round((perf_counter()-started)*1000,3),
                         counters={"crew_calls":self.crew_calls,"review_calls":self.review_calls,
                                   "tool_calls":self.tool_calls,"generation_calls":self.rag.generation_calls})
            if emit_log:
                self.audit.write(trace)
            self.last_trace = trace
            return result
