# Sources and originality

This implementation, seeded synthetic dataset, policy documents, tests and analysis were created specifically for the IITR-AS-260313 Healthcare brief. No actual Practo dataset or clinic policy is used. AI assistance was used in implementation; the student should review, run and understand the work before submission.

## Assignment source

- [Official cohort Healthcare problem statement](https://github.com/ABVenu/capstone-projects/blob/main/content/iitr-as-260313/problem_statement_healthcare.md).
- Retrieved file SHA: `1e4147a4370618e64b221c9cdcdc07325882fb05`.
- [Cohort capstone resource site](https://abvenu.github.io/capstone-projects/index.html#/iitr-as-260313/03healthcare).
- LMS assignment 84578 supplies the authoritative submission deadline and exact domain/repository fields; no private LMS links or login credentials are included here.

The source names required frameworks and acceptance criteria but does not prescribe a single repository scaffold. This repository separates the four brief parts into data/KB, retrieval/orchestration, API/evaluation and governance modules while retaining the required root `dataset.py` and `APPOINTMENTS` list.

## Primary implementation references

- [CrewAI custom BaseLLM extension](https://docs.crewai.com/en/learn/custom-llm).
- [AutoGen teams / RoundRobinGroupChat](https://microsoft.github.io/autogen/stable/reference/python/autogen_agentchat.teams.html).
- [AutoGen replay client extension](https://microsoft.github.io/autogen/stable/reference/python/autogen_ext.models.replay.html).
- [LangChain chat history API](https://reference.langchain.com/python/langchain-core/chat_history/).
- [SentenceTransformers model](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), pinned revision `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`.
- [Chroma documentation](https://docs.trychroma.com/).
- [FastAPI WebSocket documentation](https://fastapi.tiangolo.com/advanced/websockets/).
- [Pydantic documentation](https://docs.pydantic.dev/latest/).

Framework constructor signatures and behavior were also verified against the installed source and actual executions. `evidence/environment.json` records the exact tested versions. LangChain's in-memory-history deprecation warning is expected and explicitly permitted by the brief; framework deprecation warnings remain visible in the test report.
