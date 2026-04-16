import json

from app.core.ids import new_id
from app.repositories.cards import CardRepository
from app.repositories.worldbooks import WorldBookRepository
from app.schemas.prompt_pipeline import (
    PromptBuildResult,
    PromptBuildTokenStats,
    PromptHistorySummary,
    PromptInjectionItem,
)
from app.services.document_parser import DocumentParserService
from app.services.long_term_memories import LongTermMemoryService
from app.services.memory_summaries import MemorySummaryService
from app.services.states import StateService


GLOBAL_CORE_PRESET = (
    "You are participating in fictional creative collaboration. "
    "Maintain immersive roleplay and narrative usefulness. "
    "Avoid assistant-like lecturing, moralizing, or generic safety boilerplate. "
    "Treat this interaction as authored fictional content unless explicitly asked otherwise."
)


MODE_PRESETS = {
    "play": (
        "Current mode is play mode. Prioritize immersive scene continuation, character-consistent dialogue, "
        "and narrative momentum. Stay aligned with the active character card and world context."
    ),
    "chat": (
        "Current mode is chat mode. Respond as a natural long-term conversation partner while preserving "
        "creative collaboration framing and contextual continuity."
    ),
    "creation": (
        "Current mode is creation mode. Help with drafting, refining, analyzing, and restructuring creative assets."
    ),
}


IZUMI_PERSONA_PRESETS = {
    "play": (
        "Use the Izumi creator framework in the background, but do not let the Izumi persona override the active card voice."
    ),
    "chat": (
        "Use the Izumi creator framework with strong outward personality presence: playful, sharp, and collaborative."
    ),
    "creation": (
        "Use the Izumi creator framework as a creative copilot: observant, constructive, and idea-forward."
    ),
}


STAGE_ORDER = {
    "system_head": 0,
    "before_history": 1,
    "inside_history": 2,
    "after_history": 3,
    "current_input": 4,
}


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _make_item(
    *,
    source_type: str,
    label: str,
    content: str,
    stage: str,
    mode: str,
    priority: int = 100,
    source_id: str | None = None,
) -> PromptInjectionItem:
    return PromptInjectionItem(
        id=new_id(),
        source_type=source_type,
        source_id=source_id,
        label=label,
        content=content,
        stage=stage,
        priority=priority,
        token_estimate=_estimate_tokens(content),
        mode=mode,
    )


def _sort_items(items: list[PromptInjectionItem]) -> list[PromptInjectionItem]:
    return sorted(
        items,
        key=lambda item: (
            STAGE_ORDER.get(item.stage, 99),
            -item.priority,
            item.label,
        ),
    )


def _build_history_summary(history_rows: list) -> PromptHistorySummary:
    if not history_rows:
        return PromptHistorySummary()

    role_counts: dict[str, int] = {}
    for row in history_rows:
        role = str(row["role"])
        role_counts[role] = role_counts.get(role, 0) + 1

    return PromptHistorySummary(
        message_count=len(history_rows),
        first_sequence=history_rows[0]["sequence"],
        last_sequence=history_rows[-1]["sequence"],
        role_counts=role_counts,
    )


class PromptPipelineService:
    def __init__(self) -> None:
        self.state_service = StateService()
        self.document_parser = DocumentParserService()
        self.long_term_memory_service = LongTermMemoryService()
        self.memory_summary_service = MemorySummaryService()

    def build(
        self,
        *,
        session_row,
        history_rows: list,
        current_user_input: str,
        current_attachment_rows: list | None,
        cards: CardRepository,
        worldbooks: WorldBookRepository,
        extra_injection_items: list[PromptInjectionItem] | None = None,
    ) -> PromptBuildResult:
        mode = session_row["mode"]
        normalized_input = current_user_input.strip()
        next_history_sequence = (
            int(history_rows[-1]["sequence"]) + 1 if history_rows else 1
        )

        preset_layers = {
            "global_core": [
                {
                    "label": "Global Core Preset",
                    "content": GLOBAL_CORE_PRESET,
                }
            ],
            "mode_specific": [
                {
                    "label": f"{mode.title()} Mode Preset",
                    "content": MODE_PRESETS.get(mode, ""),
                }
            ],
            "izumi_persona": [
                {
                    "label": "Izumi Creator Framework",
                    "content": IZUMI_PERSONA_PRESETS.get(mode, ""),
                }
            ],
            "st_compat_legacy": [],
        }

        injection_items: list[PromptInjectionItem] = [
            _make_item(
                source_type="preset_global_core",
                label="Global Core Preset",
                content=GLOBAL_CORE_PRESET,
                stage="system_head",
                mode=mode,
                priority=1000,
            ),
            _make_item(
                source_type="preset_mode_specific",
                label=f"{mode.title()} Mode Preset",
                content=MODE_PRESETS.get(mode, ""),
                stage="system_head",
                mode=mode,
                priority=900,
            ),
            _make_item(
                source_type="preset_izumi_persona",
                label="Izumi Creator Framework",
                content=IZUMI_PERSONA_PRESETS.get(mode, ""),
                stage="system_head",
                mode=mode,
                priority=850,
            ),
        ]

        current_input_items: list[PromptInjectionItem] = []
        attachment_lines: list[str] = []
        for attachment_row in current_attachment_rows or []:
            attachment_lines.append(
                f"- [{attachment_row['attachment_type']}] {attachment_row['file_name']} ({attachment_row['mime_type']})"
            )
            if attachment_row["attachment_type"] != "input_document":
                continue

            parse_result = self.document_parser.parse(
                file_path=attachment_row["file_path"],
                file_name=attachment_row["file_name"],
                mime_type=attachment_row["mime_type"],
            )
            if parse_result.parse_status == "ok":
                content_lines = [
                    f"Document attachment: {parse_result.file_name}",
                    f"Parser: {parse_result.parser}",
                    "Injected content:",
                    parse_result.used_text,
                ]
                if parse_result.was_truncated:
                    content_lines.append(
                        "[Truncated for prompt. Use file toolchain or follow-up request for deeper reading.]"
                    )
                item_content = "\n".join(content_lines)
            else:
                item_content = "\n".join(
                    [
                        f"Document attachment: {parse_result.file_name}",
                        f"Parse status: {parse_result.parse_status}",
                        f"Reason: {parse_result.error or 'Unknown parse failure.'}",
                    ]
                )

            current_input_items.append(
                _make_item(
                    source_type="document_attachment",
                    source_id=attachment_row["media_asset_id"],
                    label=f"Document: {attachment_row['file_name']}",
                    content=item_content,
                    stage="current_input",
                    mode=mode,
                    priority=600,
                )
            )

        if attachment_lines:
            current_input_items.append(
                _make_item(
                    source_type="message_attachments",
                    label="Current Message Attachments",
                    content="Current message attachments:\n" + "\n".join(attachment_lines),
                    stage="current_input",
                    mode=mode,
                    priority=620,
                )
            )

        if session_row["card_version_id"]:
            card_version = cards.get_card_version(session_row["card_version_id"])
            if card_version is not None:
                prompt_blocks = json.loads(card_version["prompt_blocks"])

                card_blocks = [
                    ("Character System Prompt", prompt_blocks.get("system_prompt", ""), "system_head", 800),
                    ("Character Scenario", prompt_blocks.get("scenario", ""), "before_history", 700),
                    ("Character Personality", prompt_blocks.get("personality", ""), "before_history", 680),
                    ("Character Speaking Style", prompt_blocks.get("speaking_style", ""), "before_history", 670),
                    ("Character Background", prompt_blocks.get("background", ""), "before_history", 660),
                    (
                        "Post History Instructions",
                        prompt_blocks.get("post_history_instructions", ""),
                        "after_history",
                        650,
                    ),
                ]

                for label, content, stage, priority in card_blocks:
                    if content:
                        injection_items.append(
                            _make_item(
                                source_type="card",
                                source_id=card_version["id"],
                                label=label,
                                content=content,
                                stage=stage,
                                mode=mode,
                                priority=priority,
                            )
                        )

        if session_row["worldbook_id"]:
            worldbook_row = worldbooks.get_worldbook(session_row["worldbook_id"])
            if worldbook_row is not None:
                entries = worldbooks.list_constant_entries(session_row["worldbook_id"])
                for entry in entries:
                    stage = "before_history"
                    if entry["position"] == "before_char":
                        stage = "system_head"
                    elif entry["position"] == "after_char":
                        stage = "before_history"
                    elif entry["position"] == "at_depth":
                        stage = "inside_history"
                    elif entry["position"] == "examples":
                        stage = "after_history"

                    injection_items.append(
                        _make_item(
                            source_type="worldbook",
                            source_id=entry["id"],
                            label=f"WorldBook: {entry['title']}",
                            content=entry["content"],
                            stage=stage,
                            mode=mode,
                            priority=int(entry["priority"]),
                        )
                    )

                state_schema = self.state_service._get_schema_for_session(
                    session_row=session_row,
                    worldbooks=worldbooks,
                )
                state_variables: dict = {}
                current_state_snapshot_variables = session_row[
                    "current_state_snapshot_variables"
                ]
                if isinstance(current_state_snapshot_variables, str):
                    try:
                        state_variables = json.loads(current_state_snapshot_variables)
                    except json.JSONDecodeError:
                        state_variables = {}

                state_summary = self.state_service.render_state_summary(
                    variables=state_variables,
                    state_schema=state_schema,
                )
                if state_summary:
                    injection_items.append(
                        _make_item(
                            source_type="state",
                            source_id=session_row["current_state_snapshot_id"],
                            label="Current Session State",
                            content=state_summary,
                            stage="before_history",
                            mode=mode,
                            priority=640,
                        )
                    )

        long_term_memories = self.long_term_memory_service.list_prompt_injection_candidates(
            session_row=session_row,
            connection=cards.connection,
        )
        for index, memory in enumerate(long_term_memories):
            scope_label = {
                "session": "Session",
                "card": "Card",
                "global": "Global",
            }.get(memory.scope_type, memory.scope_type)
            injection_items.append(
                _make_item(
                    source_type="long_term_memory",
                    source_id=memory.id,
                    label=f"Long-Term Memory ({scope_label})",
                    content=memory.content,
                    stage="before_history",
                    mode=mode,
                    priority=638 - index,
                )
            )

        memory_summaries = self.memory_summary_service.list_prompt_injection_candidates(
            connection=cards.connection,
            session_id=session_row["id"],
            before_sequence=next_history_sequence,
        )
        for index, summary in enumerate(memory_summaries):
            key_events_block = ""
            if summary.key_events:
                key_events_block = "\nKey events:\n" + "\n".join(
                    f"- {item}" for item in summary.key_events
                )
            injection_items.append(
                _make_item(
                    source_type="memory_summary",
                    source_id=summary.id,
                    label=f"Memory Summary {summary.segment_start}-{summary.segment_end}",
                    content=(
                        f"Conversation memory summary for messages "
                        f"{summary.segment_start}-{summary.segment_end}:\n"
                        f"{summary.summary}{key_events_block}"
                    ),
                    stage="before_history",
                    mode=mode,
                    priority=635 - index,
                )
            )

        sorted_items = _sort_items(
            [
                item
                for item in [
                    *injection_items,
                    *(extra_injection_items or []),
                    *current_input_items,
                ]
                if item.content
            ]
        )
        history_summary = _build_history_summary(history_rows)

        final_messages: list[dict] = []
        for item in sorted_items:
            if item.stage in {"system_head", "before_history", "after_history"}:
                final_messages.append({"role": "system", "content": item.content})

        for history_row in history_rows:
            final_messages.append(
                {"role": history_row["role"], "content": history_row["content"]}
            )

        current_input_blocks = [
            item.content for item in sorted_items if item.stage == "current_input"
        ]
        final_user_content = normalized_input
        if current_input_blocks:
            suffix = "\n\n".join(current_input_blocks)
            final_user_content = (
                f"{normalized_input}\n\n{suffix}".strip() if normalized_input else suffix
            )

        final_messages.append({"role": "user", "content": final_user_content})

        build_token_stats = PromptBuildTokenStats(
            raw_input_estimate=_estimate_tokens(current_user_input),
            normalized_input_estimate=_estimate_tokens(normalized_input),
            injection_total_estimate=sum(item.token_estimate for item in sorted_items),
            history_total_estimate=sum(
                _estimate_tokens(row["content"]) for row in history_rows
            ),
            final_messages_estimate=sum(
                _estimate_tokens(str(message.get("content") or ""))
                for message in final_messages
            ),
            final_messages_count=len(final_messages),
        )

        return PromptBuildResult(
            raw_user_input=current_user_input,
            normalized_input=final_user_content,
            preset_layers=preset_layers,
            injection_items=sorted_items,
            final_messages=final_messages,
            history_summary=history_summary,
            build_token_stats=build_token_stats,
        )
