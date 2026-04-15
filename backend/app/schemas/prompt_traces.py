from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PromptTraceSummaryResponse(BaseModel):
    id: str
    session_id: str
    message_id: str
    swipe_id: str | None = None
    mode: str
    created_at: datetime


class PromptTraceInputSection(BaseModel):
    raw_user_input: str | None = None
    normalized_input: str | None = None
    raw_length: int = 0
    normalized_length: int = 0


class PromptTracePresetSection(BaseModel):
    global_core: list[dict[str, Any]] = Field(default_factory=list)
    mode_specific: list[dict[str, Any]] = Field(default_factory=list)
    izumi_persona: list[dict[str, Any]] = Field(default_factory=list)
    st_compat_legacy: list[dict[str, Any]] = Field(default_factory=list)
    total_items: int = 0


class PromptTraceInjectionSection(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    by_stage: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    by_source_type: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    total_items: int = 0
    total_token_estimate: int = 0


class PromptTraceFinalMessagesSection(BaseModel):
    messages: list[dict[str, Any]] = Field(default_factory=list)
    role_counts: dict[str, int] = Field(default_factory=dict)
    total_messages: int = 0


class PromptTraceResponseSection(BaseModel):
    raw_response: Any = None
    cleaned_response: str | None = None
    display_response: str | None = None
    cleaned_length: int = 0
    display_length: int = 0


class PromptTraceTokenSection(BaseModel):
    stats: dict[str, Any] = Field(default_factory=dict)
    estimated_input: int | None = None
    estimated_output: int | None = None
    estimated_total: int | None = None


class PromptTraceOverviewSection(BaseModel):
    has_tool_calls: bool = False
    has_regex_hits: bool = False
    has_state_update: bool = False
    tool_call_count: int = 0
    regex_hit_count: int = 0


class PromptTraceInspectorResponse(BaseModel):
    id: str
    session_id: str
    message_id: str
    swipe_id: str | None = None
    mode: str
    raw_user_input: str | None = None
    normalized_input: str | None = None
    preset_layers: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    injection_items: list[dict[str, Any]] = Field(default_factory=list)
    final_messages: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    token_stats: dict[str, Any] = Field(default_factory=dict)
    raw_response: Any = None
    cleaned_response: str | None = None
    display_response: str | None = None
    regex_hits: list[dict[str, Any]] | list[Any] = Field(default_factory=list)
    state_update: dict[str, Any] = Field(default_factory=dict)
    injection_count: int = 0
    final_message_count: int = 0
    input_section: PromptTraceInputSection
    preset_section: PromptTracePresetSection
    injection_section: PromptTraceInjectionSection
    final_messages_section: PromptTraceFinalMessagesSection
    response_section: PromptTraceResponseSection
    token_section: PromptTraceTokenSection
    overview: PromptTraceOverviewSection
    created_at: datetime
