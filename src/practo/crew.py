"""Tasks 7,9,15: genuine CrewAI execution with a deterministic BaseLLM adapter.

The mock emits a ReAct action using the tool's declared argument schema. CrewAI,
not the adapter, executes the tool. result_as_answer returns that real tool result.
The composer reads only the resulting per-request evidence, never canned answers.
"""
import json
from typing import Any
from crewai import Agent, Crew, Process, Task
from crewai.llms.base_llm import BaseLLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from .schemas import CrewResponse, LookupResult
from .lookup import check_appointment_status, render_lookup
from .guardrails import FALLBACK
from .governance import enforce_tool_ownership


class RagArgs(BaseModel):
    query: str = Field(description="Sanitized policy question")


class LookupArgs(BaseModel):
    record_id: str = Field(description="Synthetic appointment reference such as APT-001")


class RagTool(BaseTool):
    name: str = "rag_lookup"
    description: str = "Retrieve clinic policy evidence from local ChromaDB and answer only from that evidence."
    args_schema: type[BaseModel] = RagArgs
    result_as_answer: bool = True
    _rag: Any = PrivateAttr()
    _state: dict = PrivateAttr()

    def __init__(self, rag, state):
        super().__init__()
        self._rag, self._state = rag, state

    def _run(self, query: str):
        result = self._rag.answer(query)
        self._state["rag"] = result
        self._state["tool_events"].append({"agent":"Retrieval Agent","tool":self.name,"arguments":{"query":query},"cache_hit":result["cache_hit"]})
        return json.dumps(result)


class AppointmentTool(BaseTool):
    name: str = "check_appointment_status"
    description: str = "Read one synthetic appointment status and administrative escalation score."
    args_schema: type[BaseModel] = LookupArgs
    result_as_answer: bool = True
    _state: dict = PrivateAttr()

    def __init__(self, state):
        super().__init__()
        self._state = state

    def _run(self, record_id: str):
        result = check_appointment_status(record_id)
        self._state["lookup"] = result
        self._state["tool_events"].append({"agent":"Lookup Agent","tool":self.name,"arguments":{"record_id":record_id},"result":result})
        return json.dumps(result)


def compose_response(state):
    rag, lookup = state.get("rag"), state.get("lookup")
    # Record-only requests do not inherit irrelevant policy snippets.
    if lookup and state["record_only"]:
        return CrewResponse(answer=render_lookup(lookup),lookup=LookupResult(**lookup),fallback=not lookup["found"])
    if state["missing_reference"]:
        return CrewResponse(answer="Please provide an appointment reference such as APT-001. This session has no appointment reference.",fallback=True)
    if not rag:
        raise RuntimeError("Composer has no retrieval evidence")
    answer = rag["answer"]
    if lookup:
        answer = render_lookup(lookup) + " " + answer
    return CrewResponse(answer=answer,citations=rag["citations"],
                        lookup=LookupResult(**lookup) if lookup else None, fallback=rag["fallback"])


class MockCrewLLM(BaseLLM):
    """Mock model decisions; framework and tools remain real and observable."""
    def __init__(self, role, state, budget, tool=None):
        super().__init__(model="MOCK_LLM", temperature=0)
        self.role, self.state, self.budget, self.tool = role, state, budget, tool

    def supports_function_calling(self):
        return False  # ReAct text is parsed by CrewAI; no provider or LiteLLM call.

    def get_context_window_size(self):
        return 32768

    def call(self, messages, tools=None, callbacks=None, available_functions=None, **kwargs):
        # Charge every call including retries; never inspect system-prompt Observation examples.
        self.budget.consume(self.role, json.dumps(messages,default=str),output_reserve=1024)
        self.state["model_calls"].append(self.role)
        if self.role == "Response Composer":
            result = compose_response(self.state)
            return "Final Answer: " + result.model_dump_json()
        if self.tool is None or (self.role == "Lookup Agent" and not self.state["record_id"]):
            return "Final Answer: No appointment lookup requested."
        properties = self.tool.args_schema.model_json_schema()["properties"]
        if "record_id" in properties:
            args = {"record_id":self.state["record_id"]}
        elif "query" in properties:
            args = {"query":self.state["query"]}
        else:
            raise ValueError("Unsupported tool argument schema")
        return f"Thought: Use my authorized evidence tool.\nAction: {self.tool.name}\nAction Input: {json.dumps(args)}"


def run_crew(query, record_id, rag, budget, *, record_only=False, missing_reference=False):
    state = {"query":query,"record_id":record_id,"record_only":record_only,
             "missing_reference":missing_reference,"tool_events":[],"model_calls":[]}
    rag_tool, lookup_tool = RagTool(rag,state), AppointmentTool(state)
    retrieval = Agent(role="Retrieval Agent", goal="Retrieve policy evidence", backstory="Read-only clinic policy retrieval.",
        llm=MockCrewLLM("Retrieval Agent",state,budget,rag_tool),tools=[rag_tool],allow_delegation=False,max_iter=3,verbose=False)
    lookup = Agent(role="Lookup Agent",goal="Read synthetic appointment records",backstory="Only authorized appointment lookup owner.",
        llm=MockCrewLLM("Lookup Agent",state,budget,lookup_tool),tools=[lookup_tool],allow_delegation=False,max_iter=3,verbose=False)
    composer = Agent(role="Response Composer",goal="Compose evidence-only structured response",backstory="No tools or independent facts.",
        llm=MockCrewLLM("Response Composer",state,budget),tools=[],allow_delegation=False,max_iter=3,verbose=False)
    agents = [retrieval,lookup,composer]
    enforce_tool_ownership(agents,lookup_tool.name)
    task_rag = Task(description=f"Retrieve policy evidence for the sanitized query: {query}",expected_output="Evidence JSON from the RAG tool",agent=retrieval)
    task_lookup = Task(description=f"Look up reference {record_id or '(none supplied: skip lookup)'}. Never invent a reference.",expected_output="Lookup JSON or no lookup requested",agent=lookup)
    task_compose = Task(description="Combine the tool evidence. Return only JSON conforming to CrewResponse.",
        expected_output="Validated CrewResponse JSON",agent=composer,context=[task_rag,task_lookup],output_pydantic=CrewResponse)
    crew = Crew(agents=agents,tasks=[task_rag,task_lookup,task_compose],process=Process.sequential,
                memory=False,cache=False,verbose=False,tracing=False)
    result = crew.kickoff()
    response = result.pydantic or CrewResponse.model_validate_json(result.raw)
    response = CrewResponse.model_validate(response)
    state["task_outputs"] = [{"agent":a.role,"raw":t.output.raw} for a,t in zip(agents,[task_rag,task_lookup,task_compose])]
    state["tool_ownership"] = {a.role:[t.name for t in a.tools] for a in agents}
    return response, state

