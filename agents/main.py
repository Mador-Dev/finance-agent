from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from agents.app.chat_service import ChatService
from agents.app.jobs_service import JobsService
from agents.app.schemas import (
    BootstrapJobResult,
    BootstrapStartRequest,
    BootstrapStartResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationCreateRequest,
    ConversationHistory,
    ConversationRenameRequest,
    JobsResponse,
    SavedConversationListResponse,
    SavedConversationResponse,
    TriggerJobRequest,
    TriggerResponse,
)
from agents.app.service import BootstrapService


bootstrap_service = BootstrapService()
jobs_service = JobsService()
chat_service = ChatService(jobs_service)

app = FastAPI(
    title="Agents Service",
    version="0.2.0",
    description="Direct-client bootstrap, jobs, and chat orchestration service.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_user_id(x_user_id: str | None = Header(default=None)) -> str:
    user_id = (x_user_id or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return user_id


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/bootstrap/start", response_model=BootstrapStartResponse)
async def start_bootstrap(payload: BootstrapStartRequest) -> BootstrapStartResponse:
    job = await bootstrap_service.start_bootstrap(payload)
    return BootstrapStartResponse(jobId=job.jobId, status=job.status, totalTickers=job.totalTickers)


@app.get("/api/bootstrap/jobs/{user_id}/{job_id}")
async def get_bootstrap_job(user_id: str, job_id: str) -> dict:
    try:
        return bootstrap_service.get_job(user_id, job_id).model_dump()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/bootstrap/jobs/{user_id}/{job_id}/result", response_model=BootstrapJobResult)
async def get_bootstrap_result(user_id: str, job_id: str) -> BootstrapJobResult:
    try:
        return bootstrap_service.get_result(user_id, job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/bootstrap/strategies/{user_id}")
async def list_bootstrap_strategies(user_id: str) -> dict:
    ws = bootstrap_service.store.workspace(user_id)
    strategies = []
    for strategy_path in ws.tickers_dir.glob("*/strategy.json"):
        strategies.append(bootstrap_service.store.read_json(strategy_path, default={}))
    return {"userId": user_id, "strategies": strategies}


@app.get("/api/jobs", response_model=JobsResponse)
async def list_jobs(user_id: str = Depends(require_user_id)) -> JobsResponse:
    try:
        return jobs_service.list_jobs(user_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str, user_id: str = Depends(require_user_id)) -> dict:
    try:
        return jobs_service.get_job(user_id, job_id).model_dump()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/jobs/trigger", response_model=TriggerResponse, status_code=201)
async def trigger_job(payload: TriggerJobRequest, user_id: str = Depends(require_user_id)) -> TriggerResponse:
    try:
        job = await jobs_service.trigger(user_id, payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TriggerResponse(jobId=job.id, job=job)


@app.delete("/api/jobs/{job_id}")
async def cancel_job(job_id: str, user_id: str = Depends(require_user_id)) -> dict:
    try:
        job = await jobs_service.cancel(user_id, job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"cancelled": True, "job": job.model_dump()}


@app.post("/api/jobs/{job_id}/resume")
async def resume_job(job_id: str, user_id: str = Depends(require_user_id)) -> dict:
    try:
        job = await jobs_service.resume(user_id, job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"resumed": True, "job": job.model_dump()}


@app.post("/api/chat/messages", response_model=ChatMessageResponse)
async def send_chat_message(payload: ChatMessageRequest, user_id: str = Depends(require_user_id)) -> ChatMessageResponse:
    try:
        conversation_id = payload.conversationId or chat_service.create_conversation(user_id, None).id
        return await chat_service.send_message(user_id, payload.text, conversation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/chat/conversations", response_model=SavedConversationListResponse)
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(require_user_id),
) -> SavedConversationListResponse:
    try:
        return chat_service.list_conversations(user_id, limit, offset)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/chat/conversations", response_model=SavedConversationResponse, status_code=201)
async def create_conversation(payload: ConversationCreateRequest, user_id: str = Depends(require_user_id)) -> SavedConversationResponse:
    conversation = chat_service.create_conversation(user_id, payload.title)
    return SavedConversationResponse(conversation=conversation)


@app.get("/api/chat/conversations/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(conversation_id: str, user_id: str = Depends(require_user_id)) -> ConversationHistory:
    try:
        return chat_service.get_conversation(user_id, conversation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/api/chat/conversations/{conversation_id}", response_model=SavedConversationResponse)
async def rename_conversation(
    conversation_id: str,
    payload: ConversationRenameRequest,
    user_id: str = Depends(require_user_id),
) -> SavedConversationResponse:
    try:
        conversation = chat_service.rename_conversation(user_id, conversation_id, payload.title)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SavedConversationResponse(conversation=conversation)


@app.delete("/api/chat/conversations/{conversation_id}", response_model=SavedConversationResponse)
async def archive_conversation(conversation_id: str, user_id: str = Depends(require_user_id)) -> SavedConversationResponse:
    try:
        conversation = chat_service.archive_conversation(user_id, conversation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SavedConversationResponse(conversation=conversation)


__all__ = ["app"]
