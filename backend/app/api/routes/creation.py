from fastapi import APIRouter

from app.schemas.creation import (
    CharacterCardCreateRequest,
    CharacterCardUpdateRequest,
    CreationCardDetailResponse,
    CreationHomeResponse,
    CreationCardSummaryResponse,
    CreationProjectCreateRequest,
    CreationProjectDetailResponse,
    CreationProjectSummaryResponse,
    CreationProjectUpdateRequest,
    CreationQuickReplyGroup,
    CreationSessionCopyRequest,
    CreationSessionCreateRequest,
    CreationSessionExportResponse,
    CreationSessionModelRequest,
    CreationSessionOverviewResponse,
    CreationSessionRenameRequest,
    CreationSessionStatusRequest,
    CreationSessionSummaryResponse,
    CreationTraceListResponse,
)
from app.schemas.cards import CharacterCardResponse
from app.schemas.prompt_traces import PromptTraceInspectorResponse
from app.schemas.sessions import SessionCopyResponse, SessionResponse
from app.services.creation import CreationService

router = APIRouter(prefix="/creation", tags=["creation"])

service = CreationService()


@router.get("/home", response_model=CreationHomeResponse)
async def get_creation_home() -> CreationHomeResponse:
    return service.get_home()


@router.get("/projects", response_model=list[CreationProjectSummaryResponse])
async def list_creation_projects() -> list[CreationProjectSummaryResponse]:
    return service.list_projects()


@router.post("/projects", response_model=CreationProjectSummaryResponse, status_code=201)
async def create_creation_project(
    payload: CreationProjectCreateRequest,
) -> CreationProjectSummaryResponse:
    return service.create_project(payload)


@router.get("/projects/{project_id}", response_model=CreationProjectDetailResponse)
async def get_creation_project_detail(
    project_id: str,
) -> CreationProjectDetailResponse:
    return service.get_project_detail(project_id)


@router.put("/projects/{project_id}", response_model=CreationProjectSummaryResponse)
async def update_creation_project(
    project_id: str, payload: CreationProjectUpdateRequest
) -> CreationProjectSummaryResponse:
    return service.update_project(project_id, payload)


@router.get("/cards", response_model=list[CreationCardSummaryResponse])
async def list_creation_cards() -> list[CreationCardSummaryResponse]:
    return service.list_creation_cards()


@router.get("/cards/{card_id}", response_model=CreationCardDetailResponse)
async def get_creation_card_detail(card_id: str) -> CreationCardDetailResponse:
    return service.get_creation_card_detail(card_id)


@router.post("/cards", response_model=CharacterCardResponse, status_code=201)
async def create_creation_card(
    payload: CharacterCardCreateRequest,
) -> CharacterCardResponse:
    return service.create_card(payload)


@router.put("/cards/{card_id}", response_model=CharacterCardResponse)
async def update_creation_card(
    card_id: str, payload: CharacterCardUpdateRequest
) -> CharacterCardResponse:
    return service.update_card(card_id, payload)


@router.get(
    "/cards/{card_id}/sessions",
    response_model=list[CreationSessionSummaryResponse],
)
async def list_creation_sessions_by_card(
    card_id: str,
) -> list[CreationSessionSummaryResponse]:
    return service.list_creation_sessions_by_card(card_id)


@router.post(
    "/cards/{card_id}/sessions",
    response_model=SessionResponse,
    status_code=201,
)
async def create_creation_session(
    card_id: str, payload: CreationSessionCreateRequest
) -> SessionResponse:
    return service.create_creation_session(card_id, payload)


@router.get(
    "/sessions/{session_id}/overview",
    response_model=CreationSessionOverviewResponse,
)
async def get_creation_session_overview(
    session_id: str,
) -> CreationSessionOverviewResponse:
    return service.get_creation_session_overview(session_id)


@router.patch("/sessions/{session_id}/rename", response_model=SessionResponse)
async def rename_creation_session(
    session_id: str, payload: CreationSessionRenameRequest
) -> SessionResponse:
    return service.rename_creation_session(session_id, payload)


@router.patch("/sessions/{session_id}/status", response_model=SessionResponse)
async def update_creation_session_status(
    session_id: str, payload: CreationSessionStatusRequest
) -> SessionResponse:
    return service.update_creation_session_status(session_id, payload)


@router.patch("/sessions/{session_id}/model", response_model=SessionResponse)
async def update_creation_session_model(
    session_id: str, payload: CreationSessionModelRequest
) -> SessionResponse:
    return service.update_creation_session_model(session_id, payload)


@router.post("/sessions/{session_id}/copy", response_model=SessionCopyResponse, status_code=201)
async def copy_creation_session(
    session_id: str, payload: CreationSessionCopyRequest
) -> SessionCopyResponse:
    return service.copy_creation_session(session_id, payload)


@router.get("/sessions/{session_id}/export", response_model=CreationSessionExportResponse)
async def export_creation_session(
    session_id: str,
    export_format: str,
    export_scope: str,
) -> CreationSessionExportResponse:
    return service.export_creation_session(
        session_id,
        export_format=export_format,
        export_scope=export_scope,
    )


@router.get(
    "/sessions/{session_id}/quick-replies",
    response_model=list[CreationQuickReplyGroup],
)
async def list_creation_quick_replies(
    session_id: str,
) -> list[CreationQuickReplyGroup]:
    return service.list_quick_replies(session_id)


@router.get("/sessions/{session_id}/traces", response_model=CreationTraceListResponse)
async def list_creation_traces(session_id: str) -> CreationTraceListResponse:
    return service.list_creation_traces(session_id)


@router.get(
    "/sessions/{session_id}/traces/latest",
    response_model=PromptTraceInspectorResponse,
)
async def get_latest_creation_trace(
    session_id: str,
) -> PromptTraceInspectorResponse:
    return service.get_latest_creation_trace(session_id)


@router.get(
    "/sessions/{session_id}/traces/{trace_id}",
    response_model=PromptTraceInspectorResponse,
)
async def get_creation_trace(
    session_id: str, trace_id: str
) -> PromptTraceInspectorResponse:
    return service.get_creation_trace(session_id, trace_id)


@router.get(
    "/sessions/{session_id}/messages/{message_id}/trace",
    response_model=PromptTraceInspectorResponse,
)
async def get_creation_trace_by_message(
    session_id: str, message_id: str
) -> PromptTraceInspectorResponse:
    return service.get_creation_trace_by_message(session_id, message_id)
