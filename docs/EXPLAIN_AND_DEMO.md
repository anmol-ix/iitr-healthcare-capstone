# Understand and present the project

## A simple explanation

“I built a synthetic clinic-support assistant for the Healthcare track. It answers only from twelve written clinic policies and reads appointment details from a reproducible sixty-record dataset. CrewAI handles retrieval, lookup and composition; an independent two-agent AutoGen stage checks the draft. The service remembers appointment references within a session, masks phone numbers, rejects obvious prompt injections, enforces a request budget and exposes HTTP and WebSocket APIs. The graded mode is completely local after setup.”

Read the code before using that explanation. AI assistance is permitted by the course, but you should be able to describe every important decision accurately.

## Ten-minute demo

1. Run `python dataset.py`. Explain the seed, category/status weights, 20% observed flags and realistic synthetic fee range.
2. Open `knowledge_base/booking.md` and `src/practo/retrieval.py`. Show both chunking methods and separate real Chroma collections. Explain that embeddings are actual model output, even though language generation is a deterministic mock.
3. Open `evidence/calibration.json` and `retrieval_metrics.json`. Explain empirical thresholds, cosine similarity, parent-document deduplication and the precision/recall fractions. Sentence precision is 0.416667 versus 0.361111; both recalls are 1.0.
4. Run the server and open `/` for the CareDesk chat interface (or `/docs` for raw API exploration). Ask “Check APT-003 and explain the cancellation window.” Show lookup, policy citations and AutoGen approval in the response. Open the corresponding crew trace to show both tool events.
5. Ask “What is its fee?” in the same session, then in a new session. Explain LangChain message history and why sessions must not share appointment context.
6. Demonstrate a synthetic contact number, an instruction-override prompt, and an unrelated recipe question. Show masking, blocking and fallback respectively. Do not use your own or any patient's actual phone number.
7. Open `evidence/review_revision.json`. Explain that the test deliberately appended a false insurance guarantee; the reviewer rejected it and the editor reconstructed the evidence-supported answer. This injection is a test-only alteration, not a public API feature.
8. Repeat one query. Open `cache.json` to show unchanged model/tool/generation counters. Show `budget.json` for pre-execution rejection and `least_autonomy.json` for forbidden tool wiring.
9. Run `python scripts/live_smoke.py`. Explain real HTTP and WebSocket requests, session continuity and successful HTTP health after disconnect.
10. Open `evidence/evaluation.json` and `pytest.txt`. Explain the four score definitions, fifteen cases, negative judge control and limitations. Never describe those scores as independent clinical validation.

## Questions you should be able to answer

**Why both CrewAI and AutoGen?** The brief requires both. CrewAI is the operational team producing the draft; AutoGen is a bounded review team receiving the draft and original evidence.

**What is actually mocked?** Language-model decisions, extractive wording and judge scoring. The dataset, embeddings, vector search, agent framework execution, tool calls, session memory, Pydantic validation and API transports are real.

**What stops hallucinations?** The answer is constructed from retrieved text, low similarity triggers fallback, typed output restricts shape, and evidence-based review checks unsupported additions. This is conservative extraction; it is not a general proof that all questions are semantically answerable.

**Why is precision below one if the answers are correct?** Four chunks can include multiple parent documents. Recall measures whether the intended policy is present; precision penalizes extra documents before generation narrows to the best-matching document. We report the honest full retrieval set.

**How does escalation work?** A follow-up flag contributes 0.65; normalized age contributes up to 0.35. Age's nearest-rank 80th percentile is 24 days, so the strict threshold is 0.93. Three generated records exceed it. Older flagged appointments receive administrative follow-up; this is not medical triage.

**How can the mock reviewer revise?** It receives the original chunks/lookup and reconstructs the allowed answer. When the supplied draft contains an extra guarantee, it marks approval false and returns the reconstruction. The FinalEditor consumes the reviewer's actual message; the team has exactly two agent turns.

**Why is the system High risk?** The intended domain involves healthcare and potential medical data. Synthetic inputs reduce prototype exposure, but don't change the domain classification in the brief.

**Does zero network include installation?** No. Installation downloads packages and the free model once. Model inference, retrieval, agents, review, evaluation and graded transcripts then use zero external network requests and no keys. The local API uses loopback by design.

**Why can sessions reset?** Memory is explicitly in-process per the brief. New session IDs have no history; a process restart also resets memory, caches and document updates.

**What would you improve for production?** Authentication and per-patient authorization, clinician-approved policy updates, durable encrypted storage, stronger masking/injection defenses, broader independent evaluation and reliable operational monitoring. Do not claim this local prototype is safe for real patients.

## Before submission

- Confirm the repo is public by opening it without being logged in.
- Ensure project files are at the repository root, not hidden inside an uploaded ZIP.
- Confirm `evidence/pytest.txt` shows a passing run and the JSON evidence is committed.
- Use the exact LMS domain string `Healthcare` and the public repository URL.
- Do not upload model weights, virtual environments, credentials, screenshots, PDFs, videos or slides.
- Submit yourself; the application does not interact with LMS submission controls.
