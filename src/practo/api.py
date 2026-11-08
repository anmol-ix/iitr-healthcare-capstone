"""Local demo HTTP + WebSocket API. Run on 127.0.0.1, never with real patient data."""
from contextlib import asynccontextmanager
import asyncio
from time import perf_counter
import uuid
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .guardrails import injection_detected, mask_pii
from .retrieval import Document
from .schemas import AskRequest, AskResponse, DocumentRequest, DocumentResponse
from .service import ClinicService


def create_app(service=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.service = service or ClinicService()
        yield

    app = FastAPI(title="Practo Policy & Appointment Assistant",version="1.0.0",lifespan=lifespan)

    ui = Path(__file__).parent / "web"
    app.mount("/assets", StaticFiles(directory=ui), name="assets")

    @app.get("/", include_in_schema=False)
    async def interface():
        return FileResponse(ui / "index.html")

    @app.get("/policies")
    async def policies():
        return [{"id":d.document_id,"title":d.title,"text":d.text}
                for d in app.state.service.rag.documents.values()]

    @app.middleware("http")
    async def audit_http(request: Request, call_next):
        started, trace_id = perf_counter(), uuid.uuid4().hex
        request.state.trace_id = trace_id
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Trace-ID"] = trace_id
            return response
        finally:
            app.state.service.audit.write({**getattr(request.state,"audit_event",{}),"event":"http_request","trace_id":trace_id,
                "method":request.method,"path":mask_pii(request.url.path),"status":status,
                "elapsed_ms":round((perf_counter()-started)*1000,3)})

    @app.get("/health")
    async def health():
        return {"status":"ok","mode":"MOCK_LLM","network_required":False,
                "documents":len(app.state.service.rag.documents)}

    @app.post("/ask",response_model=AskResponse)
    async def ask(body: AskRequest, request: Request):
        result = await app.state.service.ask(body,request.state.trace_id,emit_log=False)
        request.state.audit_event = app.state.service.last_trace.copy()
        return result

    @app.post("/add-document",response_model=DocumentResponse)
    async def add_document(body: DocumentRequest):
        # Local demonstration only. A production deployment needs authenticated policy owners.
        if injection_detected(body.title + " " + body.text):
            raise HTTPException(400,"Policy contains blocked instruction patterns")
        if mask_pii(body.title + body.text) != body.title + body.text:
            raise HTTPException(400,"Policy documents must not contain phone numbers")
        doc = Document(body.document_id,body.title,body.text)
        service = app.state.service
        async with service.lock:
            try:
                revision = await asyncio.to_thread(service.rag.add_document,doc)
            except ValueError:
                raise HTTPException(400,"Document update failed calibration; previous corpus restored")
            service.cache.clear()
        return DocumentResponse(document_id=doc.document_id,revision=revision,collections=["fixed","sentence"])

    @app.websocket("/chat")
    async def chat(websocket: WebSocket):
        await websocket.accept()
        connection_id = uuid.uuid4().hex
        started = perf_counter()
        try:
            while True:
                trace_id, message_started = uuid.uuid4().hex, perf_counter()
                try:
                    body = AskRequest.model_validate_json(await websocket.receive_text())
                    result = await app.state.service.ask(body,trace_id)
                    await websocket.send_json(result.model_dump())
                except ValidationError:
                    app.state.service.audit.write({"event":"websocket_invalid_message","trace_id":trace_id,
                        "elapsed_ms":round((perf_counter()-message_started)*1000,3)})
                    await websocket.send_json({"error":"Invalid AskRequest","trace_id":trace_id})
        except WebSocketDisconnect:
            app.state.service.audit.write({"event":"websocket_disconnect","trace_id":connection_id,
                "elapsed_ms":round((perf_counter()-started)*1000,3)})

    return app


app = create_app()
