# Four-layer AI governance

## Risk classification: High

The domain involves medical data and patient-facing support, which puts it in the brief's **High** risk category even though this implementation contains only synthetic appointment metadata and fictional policies. Wrong routing, misleading coverage promises or mistaken medication advice could harm a patient in a real deployment. This prototype deliberately limits itself to policy retrieval and read-only administrative lookup, does not make clinical decisions, and requires human review for actual healthcare deployment. Its escalation score prioritizes administrative follow-up, not medical urgency.

## 1. Data layer

All 60 records are generated from a documented seed; there are no patient names, diagnoses, phone numbers or insurance IDs in the dataset. Twelve original policies are marked fictional. A pinned local embedding model produces actual vectors; model revision and calibration outputs make the retrieval input reproducible. Inbound Indian-format phone numbers are masked before processing, memory and logs. Names, diagnoses and insurance IDs cannot be reliably recognized by this fixed-format keyless masker and are explicitly out of scope; never supply real patient data.

The mutable policy endpoint rejects detected injection patterns and phone-number-bearing text, updates both indexes and recalibrates thresholds. Rollback preserves the old corpus on failed calibration. This is a local demonstration, not a policy-publishing authorization system; a deployed version would need authenticated policy owners, signed/approved revisions, retention rules, audit controls and deletion processes.

## 2. Model layer

The supported mode is `MOCK_LLM`: no hosted provider calls, credentials or hidden real-model fallback. Generation is extractive and context-only. Similarity thresholds come from observed in/out-of-scope clusters; changing the corpus recalibrates them. Pydantic validates drafts and final review verdicts. The AutoGen reviewer and editor inspect original evidence rather than trusting the composer, and the suite contains a deliberate unsupported-claim revision.

Similarity is not proof of answer relevance, exact matching is not semantic entailment, and regex injection detection can be bypassed. The fifteen-question reference suite and negative controls demonstrate bounded behavior, not clinical certification. Real deployment requires broader paraphrase, adversarial, multilingual, demographic and clinical-safety evaluation by qualified reviewers.

## 3. Application layer — least autonomy

Only the agent whose role is `Lookup Agent` is given `check_appointment_status`. The Retrieval Agent receives only `rag_lookup`; the Response Composer has no tools; delegation is disabled. Before `.kickoff()`, `enforce_tool_ownership()` inspects every agent and rejects any wiring that gives the lookup tool to another role. The negative test deliberately tries to give it to the Composer and receives `PermissionError`; the actual ownership map is recorded in `evidence/least_autonomy.json`. This is an application construction invariant, not an OS sandbox against malicious Python code, and it prevents unintended agent autonomy within this configured crew.

Lookup is read-only; no agent can modify appointments, prescribe, approve insurance claims or contact anyone. Client-selected session IDs partition local memory but are not authentication. A production system would authorize the logged-in patient against each record, bind sessions to identity, and restrict policy updates to verified staff. The API must remain on loopback for this demonstration.

## 4. Runtime layer

Every uncached request has a **32,000 simulated-token-unit / USD 0.032 simulated-cost cap**, at **USD 0.000001 per unit**. Units are conservatively counted as UTF-8 input bytes plus reserved output (512 for ingress, 1024 for each mock model call); these are documented budget units rather than actual provider billing tokens. Each CrewAI and AutoGen call is charged before it executes, including retries. AutoGen charges its entire actual message list. Requests above **6,000 input bytes** are rejected before any crew, tool, embedding or review work. Both token and cost limits are separately tested. No money is actually spent by inference.

`evidence/budget.json` proves an oversized request is rejected without changing model/tool/generation counters, and separately proves the monetary cap rejects a simulated overrun. Cache hits avoid generation and agents and consume only the ingress allowance. The model constructors limit CrewAI iterations and AutoGen turns; memory/cache size caps bound retained state. Dependency/model downloads are installation steps, separate from offline graded runs.

CrewAI telemetry, OpenTelemetry, tracing and Chroma telemetry are disabled before framework use. The embedding loader is local-only. Evidence and tests run inside an external-socket/DNS tripwire; the real deployment smoke test permits only loopback. For stronger isolation, run after setup in an OS/container environment with outbound networking disabled. JSONL entries contain trace IDs, timing, masked input and bounded execution evidence; do not use the unencrypted local log as a production medical-data store.

## Human responsibility and release gate

A human approves real clinical policies and any future access to patient records. For this submission, release checks are the offline tests, generated evidence, live loopback API/WebSocket smoke test, code/text-only package check, and public-repository visibility. The student reviews the code and explanation guide before submitting; no grade is guaranteed by a passing local suite.
