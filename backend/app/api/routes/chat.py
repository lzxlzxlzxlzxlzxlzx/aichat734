from fastapi import APIRouter

from app.schemas.chat import (
    ChatQuickReplyGroup,
    ChatRecentCardSummaryResponse,
    ChatSessionCreateRequest,
    ChatSessionModelRequest,
    ChatSessionOverviewResponse,
    ChatSessionRenameRequest,
    ChatSessionStatusRequest,
    ChatSessionSummaryResponse,
    ChatTraceListResponse,
)
from app.schemas.prompt_traces import PromptTraceInspectorResponse
from app.schemas.sessions import SessionResponse
from app.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])

service = ChatService()


@router.get("/sessions", response_model=list[ChatSessionSummaryResponse])
async def list_chat_sessions() -> list[ChatSessionSummaryResponse]:
    return service.list_chat_sessions()


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_chat_session(payload: ChatSessionCreateRequest) -> SessionResponse:
    return service.create_chat_session(payload)


@router.get(
    "/sessions/{session_id}/overview",
    response_model=ChatSessionOverviewResponse,
)
async def get_chat_session_overview(session_id: str) -> ChatSessionOverviewResponse:
    return service.get_chat_session_overview(session_id)


@router.patch("/sessions/{session_id}/rename", response_model=SessionResponse)
async def rename_chat_session(
    session_id: str, payload: ChatSessionRenameRequest
) -> SessionResponse:
    return service.rename_chat_session(session_id, payload)


@router.patch("/sessions/{session_id}/status", response_model=SessionResponse)
async def update_chat_session_status(
    session_id: str, payload: ChatSessionStatusRequest
) -> SessionResponse:
    return service.update_chat_session_status(session_id, payload)


@router.patch("/sessions/{session_id}/model", response_model=SessionResponse)
async def update_chat_session_model(
    session_id: str, payload: ChatSessionModelRequest
) -> SessionResponse:
    return service.update_chat_session_model(session_id, payload)


@router.get(
    "/sessions/{session_id}/quick-replies",
    response_model=list[ChatQuickReplyGroup],
)
async def list_chat_quick_replies(
    session_id: str,
) -> list[ChatQuickReplyGroup]:
    return service.list_quick_replies(session_id)


@router.get("/recent-cards", response_model=list[ChatRecentCardSummaryResponse])
async def list_recent_cards(limit: int = 8) -> list[ChatRecentCardSummaryResponse]:
    return service.list_recent_cards(limit=limit)


@router.get("/sessions/{session_id}/traces", response_model=ChatTraceListResponse)
async def list_chat_traces(session_id: str) -> ChatTraceListResponse:
    return service.list_chat_traces(session_id)


@router.get(
    "/sessions/{session_id}/traces/latest",
    response_model=PromptTraceInspectorResponse,
)
async def get_latest_chat_trace(session_id: str) -> PromptTraceInspectorResponse:
    return service.get_latest_chat_trace(session_id)


@router.get(
    "/sessions/{session_id}/traces/{trace_id}",
    response_model=PromptTraceInspectorResponse,
)
async def get_chat_trace(
    session_id: str, trace_id: str
) -> PromptTraceInspectorResponse:
    return service.get_chat_trace(session_id, trace_id)


@router.get(
    "/sessions/{session_id}/messages/{message_id}/trace",
    response_model=PromptTraceInspectorResponse,
)
async def get_chat_trace_by_message(
    session_id: str, message_id: str
) -> PromptTraceInspectorResponse:
    return service.get_chat_trace_by_message(session_id, message_id)
