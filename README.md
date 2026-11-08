# Practo (Healthcare) — Final Capstone

**Track completed: Practo (Healthcare). Mode: deterministic `MOCK_LLM`. Zero API keys and zero external network access during application execution after one-time installation/model download.**

**Dataset design:** `dataset.py` generates 60 synthetic appointments using seed **20261108**. Category weights are **30/15/20/20/15** for General Medicine/Cardiology/Dermatology/Pediatrics/Orthopedics; status weights are **30/35/10/10/15** for Scheduled/Completed/Cancelled/No-Show/Rescheduled. Fees are uniformly drawn from **INR 400–2000 in INR 100 increments**, a plausible educational range for general and specialist outpatient visits with promotional/tier variation. Creation age is uniformly 0–30 days; the follow-up flag uses probability **0.20**. No individual record is edited to force the distribution.

An original, synthetic clinic-support application for **IITR-AS-260313**. It answers written clinic-policy questions, reads appointment status, retains session context, and reviews drafts before responding. It performs no diagnosis, prescribing, booking changes, or real patient-data processing. Policies are fictional and are not actual Practo policies.

## Run it

Tested with **Python 3.12.14**, CPU-only PyTorch, on Linux. Use Python 3.12 for the closest reproduction. Run commands from this repository's root.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
# Linux CPU build (skip this line on macOS; the next command installs its native torch):
python -m pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e '.[dev]'
python scripts/download_model.py
```

On Windows, use `py -3.12 -m venv .venv` and `.venv\Scripts\activate`; use double quotes for `".[dev]"`. Setup downloads dependencies and the free embedding model, approximately 90 MB for its weights. Setup needs internet; **graded execution does not**. No provider account, API key, credit card, or `.env` file is needed. A restrictive proxy using SOCKS may require `python -m pip install socksio` during setup.

```bash
python dataset.py
python -m pytest -q
python scripts/run_evidence.py
python scripts/live_smoke.py
python -m uvicorn practo.api:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000/** for **CareDesk**, the presentation-ready chat interface. It includes suggested questions, appointment cards, clickable original policies, fresh conversations, safeguard demos and a project overview. The execution panel uses actual per-request agent/tool metadata and explicitly marks cached answers as not re-executed. All HTML, CSS and JavaScript are served locally without a CDN.

Open **http://127.0.0.1:8000/docs** for the interactive API. `POST /ask`, `POST /add-document`, `GET /health`, and `WS /chat` are implemented. Start **one worker** because memory, cache and Chroma indexes are intentionally in-process. Close the server with Ctrl+C.

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is the status of APT-001?","session_id":"demo"}'
curl -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is its fee?","session_id":"demo"}'
```

Change the second session to `fresh` to demonstrate missing context. See [API examples](docs/API.md) and the [explanation/demo guide](docs/EXPLAIN_AND_DEMO.md).

## What runs under MOCK_LLM

| Component | Actual implementation |
|---|---|
| Embeddings | Local `SentenceTransformer`, all-MiniLM-L6-v2, real 384-dimensional vectors |
| Vector search | Actual Chroma collections with `upsert`, cosine distance, top four chunks |
| Generation | Deterministic extractive composition using only retrieved text |
| CrewAI | Three actual `Agent` objects, three `Task` objects, `Crew.kickoff()` |
| Tool dispatch | Custom `BaseLLM` emits ReAct actions; CrewAI executes declared tools |
| Memory | LangChain `InMemoryChatMessageHistory`, session-specific reference resolution |
| Output schema | Pydantic `CrewResponse`, validated by the crew and orchestrator |
| Review | Actual AutoGen two-agent `RoundRobinGroupChat`, `max_turns=2`, typed editor output |
| Judge | Published rubric prompt plus deterministic reference/rule scoring |
| Deployment | FastAPI + real loopback Uvicorn HTTP/WebSocket test |

`src/practo/__init__.py` sets **`CREWAI_DISABLE_TELEMETRY=true` and `OTEL_SDK_DISABLED=true` before importing the frameworks**. Crew tracing and Chroma telemetry are also disabled; Hugging Face and Transformers are forced offline at runtime. The model loader uses `local_files_only=True`. `run_evidence.py` additionally blocks external Python socket connections/DNS and records any attempt; the recorded run has **zero attempts**. It permits loopback for local API tests; this tripwire is not an OS firewall.

There is no paid-model fallback. `MOCK_LLM` controls decisions without pretending that the frameworks, tools, embeddings or network tests are mocked. Crew tool arguments are selected by the tool's **argument schema**, so the name `rag_lookup` cannot be mistaken for the appointment lookup. The adapter does not search CrewAI's system prompt for `Observation:`.

## Measured dataset and retrieval

The generated dataset contains **60 appointments and 12 follow-up flags (20%)**.

| Category | Count | Status | Count |
|---|---:|---|---:|
| General Medicine | 14 | Scheduled | 20 |
| Cardiology | 10 | Completed | 22 |
| Dermatology | 13 | Cancelled | 4 |
| Pediatrics | 16 | No-Show | 7 |
| Orthopedics | 7 | Rescheduled | 7 |

Twelve original policy files contain three sentences each. Fixed windows use **48 words with 12-word overlap**; sentence windows use **two sentences with one-sentence overlap**. Each strategy is embedded and stored separately. Both collections use the same model, cosine similarity and retrieval `k=4`.

Calibration uses three in-scope and two deliberately unrelated questions, separate from the fifteen evaluation cases. The threshold is the midpoint between the maximum out-of-scope and minimum in-scope top-1 similarity; calibration aborts if these clusters overlap.

| Calibration question | Fixed similarity | Sentence similarity |
|---|---:|---:|
| How do I book an appointment? | 0.711693 | 0.700898 |
| What is the cancellation and rescheduling window? | 0.527769 | 0.507679 |
| What is the turnaround time for laboratory blood test results? | 0.827591 | 0.820397 |
| How do I repair a bicycle chain? | 0.127240 | 0.083488 |
| Who won the football world cup in 1998? | 0.040493 | 0.031406 |
| **Chosen midpoint threshold** | **0.327505** | **0.295583** |

| Strategy | Document-level macro precision | Document-level macro recall |
|---|---:|---:|
| Fixed windows | 0.361111 | 1.000000 |
| Sentence windows | **0.416667** | **1.000000** |

I select **sentence windows**: measured precision is 0.416667 versus 0.361111 for fixed windows, with identical recall of 1.0 on the same twelve in-scope questions. Sentence boundaries also preserve complete policy statements. These small-corpus measurements support this choice for this project; they do not establish general superiority.

Metrics map retrieved chunks to parent documents and deduplicate **before** scoring. Precision is relevant retrieved documents / all retrieved unique documents; recall is relevant retrieved documents / all known relevant documents. [Raw metrics](evidence/retrieval_metrics.json) show each numerator, denominator, source chunk and document set; they include the same queries used in [grounded generation](evidence/grounded_generation.json). Precision is measured on the full top-four retrieval result, before generation keeps the best matching document, so the figures honestly include distractor documents.

## Escalation design

`score = 0.65 × int(follow_up_required) + 0.35 × days_since_created / 30`.

The flag is the dominant administrative signal; age contributes a continuous, normalized overdue-follow-up signal. Escalate only when `score > 0.65 + 0.35 × age_P80 / 30`, where `age_P80` uses the nearest-rank 80th percentile of this generated dataset: **24 days**, giving a strict **0.93** threshold and **three** qualifying records. [Measured escalation evidence](evidence/escalation.json) reports the exact percentile, threshold and qualifying records. An unflagged record cannot cross this threshold. This is a transparent support-prioritization rule, **not clinical triage**.

## Acceptance map — all 16 tasks

| Task | Implementation | Demonstration / verification |
|---|---|---|
| 1 Dataset | `dataset.py` | `evidence/dataset_report.json`, `appointments.json` |
| 2 Knowledge base | `knowledge_base/*.md` | 12 topic documents; tests check sentence counts |
| 3 Dual chunking/indexing | `src/practo/retrieval.py` | `retrieval_metrics.json`, actual 384-dimensional index test |
| 4 Grounded generation | `retrieval.py`, `guardrails.py` | `calibration.json`, `grounded_generation.json` |
| 5 Comparison | `evaluation.py` | `retrieval_metrics.json`, `RESULTS.md` |
| 6 Lookup and score | `lookup.py` | `escalation.json`; tests verify all 60 records |
| 7 Actual CrewAI | `crew.py` | `crew_lookup_trace.json`, `crew_combined_trace.json`, per-query request traces |
| 8 LangChain memory | `service.py` | `memory_conversation.json`, separate `fresh_conversation.json` |
| 9 Structured response | `schemas.py`, `crew.py` | Typed outputs throughout; invalid-schema negative test |
| 10 Guardrails | `guardrails.py`, `service.py` | `guardrails.json`, rejected unsupported draft in `review_revision.json` |
| 11 FastAPI/WebSocket | `api.py` | `api_transcript.json`, `live_deployment.json` |
| 12 JSONL logs | `service.py`, API middleware | `requests.jsonl`, masked-phone and one-entry HTTP test |
| 13 Fifteen-query judge | `config/evaluation_cases.json`, `evaluation.py` | `evaluation.json`, `judge_negative_control.json` |
| 14 AutoGen review | `review.py` | `review_approval.json`, `review_revision.json` |
| 15 Governance/budget | `governance.py`, [governance](docs/GOVERNANCE.md) | `least_autonomy.json`, `budget.json` |
| 16 Caching | `retrieval.py`, `service.py` | `cache.json` with before/after counters |

## Evaluation and honest limits

The fifteen-case deterministic judge reports means of **1.0 Accuracy, 1.0 Grounding, 1.0 Completeness and 1.0 Safety** on the explicit reference set. Twelve questions cover the twelve required policy topics, two are unrelated, and one attempts prompt injection. A deliberately false/unsafe answer scores zero on all four criteria, demonstrating that the evaluator does not automatically award full marks. These are reproducible engineering checks, not independent clinical validation or a guarantee of a capstone grade.

The mock extracts policy sentences rather than reasoning like a general LLM. Similarity is not entailment: closely related but unsupported questions can retrieve a policy, and multi-topic synthesis is limited to the best matching policy document plus an optional record lookup. Pattern-based injection detection is demonstrative, not an exhaustive defense. The fixed-format masker covers Indian phone-number examples; names, diagnoses and insurance IDs are deliberately out of scope, and the dataset contains none. No actual patient information belongs in this demo.

Memory and indexes reset on restart; session IDs are supplied by the client and are **not authentication**. `/add-document` is a local demonstration endpoint, not an authenticated production admin API. Run on loopback only. Real deployment would require identity/access controls, approved policy ownership, stronger safety evaluation, durable secure storage and operational monitoring; see the four-layer governance document.

## Repository layout

- `dataset.py`: seeded data and validation.
- `knowledge_base/`: original policy source text.
- `src/practo/`: retrieval, tools, crew, review, schemas, memory/API, guardrails, governance and evaluation.
- `config/evaluation_cases.json`: explicit fifteen-question reference suite.
- `scripts/`: model setup, evidence regeneration, real deployment test.
- `tests/`: offline acceptance and failure-path tests.
- `evidence/`: actual run outputs, raw JSONL logs, metrics and pytest report.
- `docs/`: architecture, governance, API examples, explanation guide, source references.
- `requirements-lock.txt`: tested environment package versions; `pyproject.toml` is the portable install entry point.

Model binaries, runtime logs, caches, credentials and virtual environments are excluded from the submission. All committed deliverables are code or text; no images, PDFs, videos or slides are included.

## Submission

Publish this repository as **public**, with `README.md`, `dataset.py`, `src/`, `knowledge_base/`, `tests/`, `docs/`, `config/` and `evidence/` visible at the repository root. In the LMS, enter the domain exactly as **`Healthcare`**, then the public GitHub repository URL. Review the explanation guide and run the demo before submitting. The project does not submit anything to the LMS automatically.

## Teaching-resource alignment

See [resource review and six-box design contract](docs/RESOURCE_REVIEW.md) for the session sources, access limitations and mapping from the teaching example to this package. Basic greetings and capability questions use explicit static application help; policy questions still use the actual retrieval/CrewAI/AutoGen pipeline. Help responses correctly report no agent execution or policy review.
