import json

from app.core.ids import new_id
from app.repositories.cards import CardRepository
from app.repositories.worldbooks import WorldBookRepository
from app.schemas.prompt_pipeline import PromptBuildResult, PromptInjectionItem


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


class PromptPipelineService:
    def build(
        self,
        *,
        session_row,
        history_rows: list,
        current_user_input: str,
        cards: CardRepository,
        worldbooks: WorldBookRepository,
    ) -> PromptBuildResult:
        mode = session_row["mode"]
        normalized_input = current_user_input.strip()

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

        sorted_items = _sort_items([item for item in injection_items if item.content])

        final_messages: list[dict] = []
        for item in sorted_items:
            if item.stage in {"system_head", "before_history", "after_history"}:
                final_messages.append({"role": "system", "content": item.content})

        for history_row in history_rows:
            final_messages.append(
                {"role": history_row["role"], "content": history_row["content"]}
            )

        final_messages.append({"role": "user", "content": normalized_input})

        return PromptBuildResult(
            raw_user_input=current_user_input,
            normalized_input=normalized_input,
            preset_layers=preset_layers,
            injection_items=sorted_items,
            final_messages=final_messages,
        )
