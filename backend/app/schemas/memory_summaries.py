from pydantic import BaseModel, Field


class MemorySummaryResponse(BaseModel):
    id: str
    session_id: str
    segment_start: int
    segment_end: int
    summary: str
    key_events: list[str] = Field(default_factory=list)
    state_snapshot_id: str | None = None
    frozen: bool = False
    created_at: str


class MemorySummaryGenerateResponse(BaseModel):
    created: bool
    summary: MemorySummaryResponse | None = None
