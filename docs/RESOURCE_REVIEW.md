# Teaching-resource review — 8 November 2026

The Healthcare problem statement remains the grading authority. Examples from other tracks are architectural references, not healthcare requirements or code to copy.

## Sources reviewed

- Support Session 1 (15 October), https://students.masaischool.com/lectures/172321: attached Capstone note explicitly requires deterministic MOCK_LLM, zero keys and offline graded transcripts. Optional real APIs do not replace this requirement. The note's financial PII examples belong to another track; Healthcare requires phone masking.
- Support Session 2 (22 October), https://students.masaischool.com/lectures/172322: linked https://github.com/sahil1998237/naukri-domain-support-agent. Reviewed README, capstone_strategy.md, RUNTIME_ARCHITECTURE.md and agent integration examples. This is a Recruitment/HR reference, not an additional Healthcare rubric. Its measured thresholds, policy text and results must not be copied into this project.
- Support Session 3 (27 October), https://students.masaischool.com/lectures/173274: no attached description/resources. Portal summary reports an unusable transcript.
- Support Session 4 (3 November), https://students.masaischool.com/lectures/174000: no attached description/resources. Portal summary reports an unusable transcript. We do not infer that no teaching occurred and do not claim the full recording was reviewed.
- Architecture and Planning (1 October), https://students.masaischool.com/lectures/170659: read the attached Capstone_Project.pptx text from the shared teaching folder. Its invoice example teaches a six-box design canvas; invoice/payment requirements are not Healthcare requirements.

## Six-box design contract applied to CareDesk

| Box | Project contract |
|---|---|
| Problem | Help a user find fictional clinic policies and synthetic appointment status without inventing medical advice. No measured real-world business improvement is claimed. |
| Roles | Retrieval reads policies; Lookup reads appointment records; Composer produces structured answers; Reviewer checks original evidence; Editor applies the review. No role can prescribe or alter bookings. |
| Handoffs | RAG chunks/citations and LookupResult become CrewResponse; the original evidence plus draft becomes ReviewVerdict; AskResponse carries the final response and trace. |
| Tools and truth | Markdown policies and seeded APPOINTMENTS are authoritative within this fictional demo. LangChain history resolves references but does not establish policy facts. |
| Human boundaries | Clinical advice, prescription decisions, insurance approval and actual appointment changes require an appropriate human/service outside this read-only application. Administrative escalation is a recommendation; it does not contact staff or create a real work queue. |
| Risks and metrics | Wrong retrieval, privacy leakage, unsupported claims, tool failures and excess work are addressed by thresholds, masking, evidence review, error propagation and budgets. Retrieval precision/recall, four separate judge dimensions, traces and negative tests provide bounded evidence. |

## Reference-to-project structure

| Teaching reference responsibility | This project's module |
|---|---|
| rag/chunking, indexer, retriever | src/practo/retrieval.py |
| agents/mock_llm, crew, tools | src/practo/crew.py and lookup.py |
| agents/memory, schemas, guardrails | service.py, schemas.py, guardrails.py |
| review/autogen_review | review.py |
| governance/autonomy, cost_budget | governance.py and docs/GOVERNANCE.md |
| api/main, logging, cache | api.py, service.py and retrieval.py |
| evaluation and transcripts | evaluation.py, config/, scripts/run_evidence.py and evidence/ |

The package layout groups the same responsibilities under an installable src/practo package. The examples do not establish mandatory identical folder names. Dataset, policy corpus, thresholds and evaluation results remain original.

## Gaps and disposition

Basic greetings/capability questions previously entered policy search and could return an unhelpful fallback. Whole-input application-help routing now handles those narrow cases after injection and budget checks. It provides static capability information, not policy evidence, and reports zero agent/tool execution and no review. Mixed requests still enter the normal pipeline. This does not turn MOCK_LLM into a general conversational model.

Acceptance tests now also exercise natural help phrasing, a greeting mixed with a policy question, a greeting mixed with an injection and an unrelated question. Broader language understanding remains limited; the original evaluation is not a general-accuracy claim.

Public GitHub publishing and LMS submission are still external release steps. The student must understand the code and submit the verified public repository URL. No grade is guaranteed.
