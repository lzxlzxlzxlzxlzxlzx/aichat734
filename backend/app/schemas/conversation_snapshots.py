from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConversationSnapshotResponse(BaseModel):
    id: str
    session_id: str
    snapshot_type: str
    message_id: str | None = None
    message_sequence: int
    inclusive: bool
    state_snapshot_id: str | None = None
    memory_summary_ids: list[str] = Field(default_factory=list)
    label: str | None = None
    summary: dict[str, Any] | None = None
    created_by: str
    created_at: datetime


class RestoreConversationSnapshotResponse(BaseModel):
    session_id: str
    snapshot_id: str
    restored_message_count: int
    last_message_id: str | None = None
    rollback_to_message_id: str | None = None
    state_snapshot_id: str | None = None
