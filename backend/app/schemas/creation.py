from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.cards import (
    CharacterCardCreateRequest,
    CharacterCardResponse,
    CharacterCardUpdateRequest,
)
from app.schemas.prompt_traces import (
    PromptTraceInspectorResponse,
    PromptTraceSummaryResponse,
)
from app.schemas.sessions import SessionCopyResponse, SessionResponse


class CreationProjectSummaryResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    project_type: str
    ip_name: str | None = None
    status: str
    default_model: str | None = None
    card_count: int = 0
    worldbook_count: int = 0
    updated_at: datetime


class CreationProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    project_type: str = Field(default="original", pattern="^(original|adaptation)$")
    ip_name: str | None = Field(default=None, max_length=200)
    status: str = Field(default="draft", pattern="^(draft|active|archived)$")
    default_model: str | None = None


class CreationProjectUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    project_type: str = Field(default="original", pattern="^(original|adaptation)$")
    ip_name: str | None = Field(default=None, max_length=200)
    status: str = Field(default="draft", pattern="^(draft|active|archived)$")
    default_model: str | None = None


class CreationProjectDetailResponse(BaseModel):
    project: CreationProjectSummaryResponse
    cards: list["CreationCardSummaryResponse"] = Field(default_factory=list)
    sessions: list["CreationSessionSummaryResponse"] = Field(default_factory=list)


class CreationRecentEditResponse(BaseModel):
    item_type: str
    id: str
    title: str
    subtitle: str = ""
    project_id: str | None = None
    card_id: str | None = None
    session_id: str | None = None
    updated_at: datetime


class CreationHomeResponse(BaseModel):
    projects: list[CreationProjectSummaryResponse] = Field(default_factory=list)
    cards: list["CreationCardSummaryResponse"] = Field(default_factory=list)
    recent_edits: list[CreationRecentEditResponse] = Field(default_factory=list)


class CreationCardSummaryResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    cover_asset_id: str | None = None
    avatar_asset_id: str | None = None
    worldbook_id: str | None = None
    project_id: str | None = None
    status: str
    source_type: str
    current_draft_version_id: str | None = None
    current_published_version_id: str | None = None
    latest_session_id: str | None = None
    updated_at: datetime


class CreationSessionSummaryResponse(BaseModel):
    id: str
    name: str
    status: str
    card_id: str | None = None
    project_id: str | None = None
    message_count: int = 0
    last_message_id: str | None = None
    last_message_at: datetime | None = None
    model_name: str | None = None
    created_at: datetime
    updated_at: datetime


class CreationLinkedSessionSummary(BaseModel):
    id: str
    mode: str
    name: str
    status: str
    last_message_at: datetime | None = None
    updated_at: datetime


class CreationCardDetailResponse(BaseModel):
    card: CharacterCardResponse
    creation_sessions: list[CreationSessionSummaryResponse] = Field(default_factory=list)
    linked_sessions: list[CreationLinkedSessionSummary] = Field(default_factory=list)


class CreationSessionOverviewResponse(BaseModel):
    session: SessionResponse
    card: CharacterCardResponse
    linked_sessions: list[CreationLinkedSessionSummary] = Field(default_factory=list)
    latest_trace: PromptTraceSummaryResponse | None = None


class CreationSessionCreateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    model_name: str | None = None
    use_latest_existing_session: bool = False


class CreationSessionRenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class CreationSessionStatusRequest(BaseModel):
    status: str = Field(pattern="^(active|archived|deleted)$")


class CreationSessionModelRequest(BaseModel):
    model_name: str = Field(min_length=1, max_length=200)


class CreationSessionCopyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_message_id: str | None = None


class CreationQuickReplyItem(BaseModel):
    id: str
    label: str
    content: str
    mode: str = "fill"
    order: int = 0


class CreationQuickReplyGroup(BaseModel):
    id: str
    name: str
    scope_type: str
    items: list[CreationQuickReplyItem] = Field(default_factory=list)


class CreationTraceListResponse(BaseModel):
    items: list[PromptTraceSummaryResponse] = Field(default_factory=list)


class CreationSessionExportResponse(BaseModel):
    session_id: str
    export_format: str
    export_scope: str
    file_name: str
    content: str


__all__ = [
    "CharacterCardCreateRequest",
    "CharacterCardUpdateRequest",
    "CreationCardDetailResponse",
    "CreationHomeResponse",
    "CreationCardSummaryResponse",
    "CreationLinkedSessionSummary",
    "CreationProjectCreateRequest",
    "CreationProjectDetailResponse",
    "CreationProjectSummaryResponse",
    "CreationProjectUpdateRequest",
    "CreationQuickReplyGroup",
    "CreationQuickReplyItem",
    "CreationRecentEditResponse",
    "CreationSessionCopyRequest",
    "CreationSessionCreateRequest",
    "CreationSessionExportResponse",
    "CreationSessionModelRequest",
    "CreationSessionOverviewResponse",
    "CreationSessionRenameRequest",
    "CreationSessionStatusRequest",
    "CreationSessionSummaryResponse",
    "CreationTraceListResponse",
    "PromptTraceInspectorResponse",
    "SessionCopyResponse",
]
