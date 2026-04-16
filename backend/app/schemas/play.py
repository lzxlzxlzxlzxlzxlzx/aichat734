from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.sessions import SessionResponse
from app.schemas.conversation_snapshots import (
    ConversationSnapshotResponse,
    RestoreConversationSnapshotResponse,
)
from app.schemas.prompt_traces import (
    PromptTraceInspectorResponse,
    PromptTraceSummaryResponse,
)
from app.schemas.states import (
    SessionStateResponse,
    StateChangeLogResponse,
    StateSnapshotResponse,
)


class PlayOpeningOption(BaseModel):
    index: int
    title: str
    content: str
    is_default: bool = False


class PlayCardSummaryResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    cover_asset_id: str | None = None
    avatar_asset_id: str | None = None
    latest_session_id: str | None = None
    published_at: datetime | None = None
    opening_count: int = 0


class PlaySessionSummaryResponse(BaseModel):
    id: str
    name: str
    status: str
    card_id: str | None = None
    message_count: int = 0
    last_message_id: str | None = None
    last_message_at: datetime | None = None
    current_state_snapshot_id: str | None = None
    model_name: str | None = None
    created_at: datetime
    updated_at: datetime


class PlayCardDetailResponse(BaseModel):
    card: PlayCardSummaryResponse
    openings: list[PlayOpeningOption] = Field(default_factory=list)
    sessions: list[PlaySessionSummaryResponse] = Field(default_factory=list)


class PlaySessionOverviewResponse(BaseModel):
    session: SessionResponse
    card: PlayCardSummaryResponse
    openings: list[PlayOpeningOption] = Field(default_factory=list)
    state_summary: str = ""


class PlaySessionRenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class PlaySessionStatusRequest(BaseModel):
    status: str = Field(pattern="^(active|archived|deleted)$")


class PlayQuickReplyItem(BaseModel):
    id: str
    label: str
    content: str
    mode: str = "fill"
    order: int = 0


class PlayQuickReplyGroup(BaseModel):
    id: str
    name: str
    scope_type: str
    items: list[PlayQuickReplyItem] = Field(default_factory=list)


class PlaySessionExportResponse(BaseModel):
    session_id: str
    export_format: str
    export_scope: str
    file_name: str
    content: str


class PlaySnapshotListResponse(BaseModel):
    items: list[ConversationSnapshotResponse] = Field(default_factory=list)


class PlayTraceListResponse(BaseModel):
    items: list[PromptTraceSummaryResponse] = Field(default_factory=list)


class PlayStateBundleResponse(BaseModel):
    current: SessionStateResponse
    snapshots: list[StateSnapshotResponse] = Field(default_factory=list)
    changes: list[StateChangeLogResponse] = Field(default_factory=list)


class PlaySessionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    opening_index: int | None = None
    model_name: str | None = None
    use_latest_existing_session: bool = False


class PlaySessionCopyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_message_id: str | None = None


class PlaySessionCreateResponse(BaseModel):
    session: SessionResponse
    opening_message_id: str | None = None
    opening_selected: PlayOpeningOption | None = None
