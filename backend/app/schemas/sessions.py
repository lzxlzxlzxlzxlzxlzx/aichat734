from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    mode: str = Field(pattern="^(play|chat|creation)$")
    name: str = Field(min_length=1, max_length=200)
    status: str = Field(default="active")
    card_id: str | None = None
    card_version_id: str | None = None
    worldbook_id: str | None = None
    project_id: str | None = None
    persona_id: str | None = None
    preset_version_id: str | None = None
    origin_session_id: str | None = None
    origin_snapshot_id: str | None = None
    model_name: str | None = None


class SessionResponse(BaseModel):
    id: str
    mode: str
    name: str
    status: str
    card_id: str | None = None
    card_version_id: str | None = None
    worldbook_id: str | None = None
    project_id: str | None = None
    persona_id: str | None = None
    preset_version_id: str | None = None
    origin_session_id: str | None = None
    origin_snapshot_id: str | None = None
    message_count: int
    last_message_id: str | None = None
    last_message_at: datetime | None = None
    current_state_snapshot_id: str | None = None
    model_name: str | None = None
    created_at: datetime
    updated_at: datetime
