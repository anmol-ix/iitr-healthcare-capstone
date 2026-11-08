# API examples

Start `python -m uvicorn practo.api:app --host 127.0.0.1 --port 8000` and open `/` for CareDesk or `/docs` for the API explorer. All data and policies are synthetic. API inputs are validated using Pydantic; extra fields are rejected.

| Endpoint | Request | Response |
|---|---|---|
| `GET /` | none | Locally served CareDesk chat interface |
| `GET /policies` | none | Original fictional policy text for citation inspection |
| `GET /health` | none | status, mode, document count |
| `POST /ask` | `AskRequest` | `AskResponse` containing typed `response_format`, review, trace ID, outcome and cache flag |
| `POST /add-document` | `DocumentRequest` | document ID, revision, both collection strategies |
| `WS /chat` | one `AskRequest` JSON object per text message | one `AskResponse` per valid message; safe error for malformed message |

## Ask examples

```json
{"query":"Check APT-003 and explain the cancellation window.","session_id":"demo"}
```

```json
{"query":"What is its fee?","session_id":"demo"}
```

```json
{"query":"What is its fee?","session_id":"fresh"}
```

The first request combines two real tools. The second resolves the remembered appointment. The third does not inherit it. Session IDs accept 1–64 letters, digits, underscores or hyphens.

## Add a fictional policy

```json
{
  "document_id":"accessibility",
  "title":"Wheelchair access",
  "text":"A wheelchair-accessible ramp is available at the clinic entrance. Reception staff can arrange entry assistance on request."
}
```

Ask `Is wheelchair access available at the entrance?` afterwards. The endpoint upserts both collections and invalidates caches; changes are ephemeral. It is deliberately local-only and has no production admin authentication. HTTP 400 indicates blocked policy content or failed calibration; HTTP 422 indicates an invalid request schema.

## WebSocket client

```python
import asyncio, json
from websockets.asyncio.client import connect

async def main():
    async with connect("ws://127.0.0.1:8000/chat", proxy=None) as ws:
        for query in ["Status of APT-001", "What is its fee?"]:
            await ws.send(json.dumps({"query": query, "session_id": "socket-demo"}))
            print(json.loads(await ws.recv()))

asyncio.run(main())
```

Closing this connection is handled with `WebSocketDisconnect`; other clients and HTTP endpoints remain available. `scripts/live_smoke.py` proves this against an actual Uvicorn TCP listener, rather than only an in-process test client.

## Logs and failures

Successful HTTP `/ask` has one complete JSONL request entry; middleware records validation errors and other HTTP routes too. The trace ID is also returned as `X-Trace-ID`. WebSocket messages have per-message IDs; disconnects are separate connection events. Input phone numbers are masked before the response, memory, tools and logger see them. Raw request bodies are not logged by middleware. `blocked`, `fallback` and `budget_exceeded` are valid typed application outcomes, not server crashes.

Presentation metadata in `AskResponse` includes `elapsed_ms`, `executed_agents`, `executed_tools` and `budget_units`. These fields come from the current request, not a simulated UI timeline. Cache hits have empty execution lists and retain the previously produced review verdict.
