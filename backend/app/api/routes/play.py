from fastapi import APIRouter

from app.schemas.play import (
    PlayCardDetailResponse,
    PlayCardSummaryResponse,
    PlaySnapshotListResponse,
    PlayQuickReplyGroup,
    PlaySessionCopyRequest,
    PlaySessionCreateRequest,
    PlaySessionCreateResponse,
    PlaySessionExportResponse,
    PlaySessionOverviewResponse,
    PlaySessionRenameRequest,
    PlayStateBundleResponse,
    PlaySessionStatusRequest,
    PlayTraceListResponse,
    PlaySessionSummaryResponse,
)
from app.schemas.conversation_snapshots import RestoreConversationSnapshotResponse
from app.schemas.prompt_traces import PromptTraceInspectorResponse
from app.schemas.sessions import SessionCopyResponse, SessionResponse
from app.services.play import PlayService

router = APIRouter(prefix="/play", tags=["play"])

service = PlayService()


@router.get("/cards", response_model=list[PlayCardSummaryResponse])
async def list_play_cards() -> list[PlayCardSummaryResponse]:
    return service.list_play_cards()


@router.get("/cards/{card_id}", response_model=PlayCardDetailResponse)
async def get_play_card_detail(card_id: str) -> PlayCardDetailResponse:
    return service.get_play_card_detail(card_id)


@router.get(
    "/cards/{card_id}/sessions",
    response_model=list[PlaySessionSummaryResponse],
)
async def list_play_sessions_by_card(card_id: str) -> list[PlaySessionSummaryResponse]:
    return service.list_play_sessions_by_card(card_id)


@router.get(
    "/sessions/{session_id}/overview",
    response_model=PlaySessionOverviewResponse,
)
async def get_play_session_overview(session_id: str) -> PlaySessionOverviewResponse:
    return service.get_play_session_overview(session_id)


@router.patch("/sessions/{session_id}/rename", response_model=SessionResponse)
async def rename_play_session(
    session_id: str, payload: PlaySessionRenameRequest
) -> SessionResponse:
    return service.rename_play_session(session_id, payload)


@router.patch("/sessions/{session_id}/status", response_model=SessionResponse)
async def update_play_session_status(
    session_id: str, payload: PlaySessionStatusRequest
) -> SessionResponse:
    return service.update_play_session_status(session_id, payload)


@router.post("/sessions/{session_id}/copy", response_model=SessionCopyResponse, status_code=201)
async def copy_play_session(
    session_id: str,
    payload: PlaySessionCopyRequest,
) -> SessionCopyResponse:
    return service.copy_play_session(session_id, payload)


@router.get("/sessions/{session_id}/quick-replies", response_model=list[PlayQuickReplyGroup])
async def list_play_quick_replies(session_id: str) -> list[PlayQuickReplyGroup]:
    return service.list_quick_replies(session_id)


@router.get("/sessions/{session_id}/export", response_model=PlaySessionExportResponse)
async def export_play_session(
    session_id: str,
    export_format: str,
    export_scope: str,
) -> PlaySessionExportResponse:
    return service.export_play_session(
        session_id,
        export_format=export_format,
        export_scope=export_scope,
    )


@router.get("/sessions/{session_id}/snapshots", response_model=PlaySnapshotListResponse)
async def list_play_snapshots(session_id: str) -> PlaySnapshotListResponse:
    return service.list_play_snapshots(session_id)


@router.post(
    "/sessions/{session_id}/snapshots/{snapshot_id}/restore",
    response_model=RestoreConversationSnapshotResponse,
)
async def restore_play_snapshot(
    session_id: str, snapshot_id: str
) -> RestoreConversationSnapshotResponse:
    return service.restore_play_snapshot(session_id, snapshot_id)


@router.get("/sessions/{session_id}/state", response_model=PlayStateBundleResponse)
async def get_play_state_bundle(session_id: str) -> PlayStateBundleResponse:
    return service.get_play_state_bundle(session_id)


@router.get("/sessions/{session_id}/traces", response_model=PlayTraceListResponse)
async def list_play_traces(session_id: str) -> PlayTraceListResponse:
    return service.list_play_traces(session_id)


@router.get(
    "/sessions/{session_id}/traces/latest",
    response_model=PromptTraceInspectorResponse,
)
async def get_latest_play_trace(session_id: str) -> PromptTraceInspectorResponse:
    return service.get_latest_play_trace(session_id)


@router.get(
    "/sessions/{session_id}/traces/{trace_id}",
    response_model=PromptTraceInspectorResponse,
)
async def get_play_trace(
    session_id: str, trace_id: str
) -> PromptTraceInspectorResponse:
    return service.get_play_trace(session_id, trace_id)


@router.get(
    "/sessions/{session_id}/messages/{message_id}/trace",
    response_model=PromptTraceInspectorResponse,
)
async def get_play_trace_by_message(
    session_id: str, message_id: str
) -> PromptTraceInspectorResponse:
    return service.get_play_trace_by_message(session_id, message_id)


@router.post(
    "/cards/{card_id}/sessions",
    response_model=PlaySessionCreateResponse,
    status_code=201,
)
async def create_play_session(
    card_id: str, payload: PlaySessionCreateRequest
) -> PlaySessionCreateResponse:
    return service.create_play_session(card_id, payload)
