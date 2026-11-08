# Architecture and data flow

## Boundaries

The repository follows the four parts of the capstone brief. `dataset.py` and `knowledge_base/` are source data; retrieval supplies evidence; CrewAI assembles a draft; AutoGen independently checks that draft against the original evidence; FastAPI exposes the same orchestrator tested by the suite.

An incoming `AskRequest` is validated, normalized and phone-masked before it reaches memory, embeddings, agents or disk. Obvious instruction-override patterns are blocked. The orchestrator then checks its request budget, resolves an explicit appointment reference or a reference from this session's LangChain human messages, and checks the final-response cache.

On a cache miss, three actual CrewAI tasks run sequentially. The Retrieval Agent invokes `rag_lookup`, which embeds the query, searches the selected sentence collection and applies its empirically measured fallback threshold. The Lookup Agent invokes `check_appointment_status` only when an explicit or remembered record reference exists. The Composer uses those resulting per-request objects and emits a validated `CrewResponse`.

The actual AutoGen reviewer receives the draft plus the original chunks and lookup result. Its mock client reconstructs the allowed answer from evidence rather than treating the draft as truth. The FinalEditor consumes that review and returns a `ReviewVerdict` through `output_content_type`; the team registers `StructuredMessage[ReviewVerdict]` and stops after two agent turns. An additional output check verifies the reviewed answer against evidence before release. Unsupported retrieval produces the explicit fallback.

The final response is cached and appended to session memory. A JSONL event includes the trace ID, timing, sanitized input, tool events, per-stage budget charges and result. HTTP middleware records one entry per request; a successful `/ask` supplies its detailed inference event to that middleware rather than writing a duplicate. WebSocket messages are individually logged; connection disconnects are additional lifecycle events.

## State and concurrency

`ClinicService` uses an async lock to serialize inference and document updates for this small local demonstration. Embedding/crew execution runs in a worker thread; `RagCore` separately protects index/cache operations using an `RLock`. These prevent a simultaneous update from changing the evidence between a draft and its review. This is correctness-first behavior, not high-throughput serving.

LangChain histories are capped at 200 sessions and 20 messages per session, evicting least-recently-used sessions. Two caches are capped at 256 entries. The generation cache is keyed by normalized/casefolded query, strategy and corpus revision. The final-response cache also includes the resolved appointment reference and intent flags, preventing a repeated pronoun from returning another session's record.

The dataset is immutable for this demo. Chroma and memory are ephemeral. A document update upserts the candidate corpus into two new collections and recalibrates both thresholds before committing the swap, incrementing the corpus revision and invalidating both caches. Calibration inspects the complete small collection and uses its highest similarity, avoiding approximate top-one search misses. If calibration fails, the candidate indexes are deleted and the prior document/index state is retained. API updates do not rewrite the original Markdown files and do not survive restart.

## Framework authenticity

The custom Crew model subclasses `crewai.llms.base_llm.BaseLLM`; it does not bypass `.kickoff()`. Tool results are produced by CrewAI's real tool executor with `result_as_answer=True`. Choosing arguments from `args_schema` avoids the brief's `rag_lookup` name-collision pitfall. The model does not parse example observations in system messages.

AutoGen uses its official replay-client extension base, with `create()` overridden to make evidence-dependent decisions. It is not a fixed list of approval responses: altering a draft changes the review verdict. The reviewer and editor are separate framework agents; the editor reads the reviewer's actual message. Their deterministic rules are independently testable but are not independent learned medical reasoning.

## Determinism

The dataset seed, policy text, model revision, explicit retrieval threshold procedure, mock composition and judge references are fixed. Equivalent requests yield the same substantive answers. Trace IDs, measured timings, ephemeral collection namespaces, platform versions and last-bit floating-point differences are operational metadata and can vary; they are not claimed to be byte-for-byte deterministic.

## Application help

After masking, injection checks and the input budget, narrowly recognized whole-input greetings/help requests return static application capabilities. These are not policy answers and have no citations, review or agent execution. Mixed substantive requests continue through the normal crew and review pipeline. This route still updates bounded session history and audit logs. See RESOURCE_REVIEW.md for the teaching-resource mapping.
