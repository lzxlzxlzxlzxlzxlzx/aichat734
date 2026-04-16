from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StateFieldSchema(BaseModel):
    type: str = "string"
    default: Any = None
    min: int | float | None = None
    max: int | float | None = None
    options: list[Any] = Field(default_factory=list)


class SessionStateResponse(BaseModel):
    session_id: str
    snapshot_id: str | None = None
    state_schema: dict[str, dict[str, Any]] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class StateSnapshotResponse(BaseModel):
    id: str
    session_id: str
    message_id: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class StateChangeItemResponse(BaseModel):
    key: str
    old: Any = None
    new: Any = None
    operation: str = "set"


class StateChangeLogResponse(BaseModel):
    id: str
    session_id: str
    message_id: str
    changes: list[StateChangeItemResponse] = Field(default_factory=list)
    raw_block: str | None = None
    source_type: str
    created_at: datetime


class StateParseResult(BaseModel):
    raw_block: str | None = None
    parsed_updates: dict[str, Any] = Field(default_factory=dict)
    delta_updates: dict[str, int | float] = Field(default_factory=dict)
    applied_changes: list[StateChangeItemResponse] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    ignored_fields: list[str] = Field(default_factory=list)
    has_update: bool = False
