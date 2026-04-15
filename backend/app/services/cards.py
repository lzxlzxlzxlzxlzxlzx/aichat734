import json
from datetime import datetime, timezone

from app.core.database import get_connection
from app.core.exceptions import NotFoundError
from app.core.ids import new_id
from app.repositories.cards import CardRepository
from app.schemas.cards import (
    CharacterCardBase,
    CharacterCardCreateRequest,
    CharacterCardResponse,
    CharacterCardUpdateRequest,
    CharacterCardVersionResponse,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_name(name: str) -> str:
    return "-".join(name.strip().lower().split())


def _build_base_info(payload: CharacterCardBase) -> dict:
    return {
        "name": payload.name,
        "description": payload.description or "",
        "tags": payload.tags,
    }


def _row_to_version_response(row) -> CharacterCardVersionResponse:
    return CharacterCardVersionResponse(
        id=row["id"],
        card_id=row["card_id"],
        version=row["version"],
        version_label=row["version_label"],
        is_published=bool(row["is_published"]),
        spec=row["spec"],
        source_type=row["source_type"],
        base_info=json.loads(row["base_info"]),
        prompt_blocks=json.loads(row["prompt_blocks"]),
        play_config=json.loads(row["play_config"]),
        extension_blocks=json.loads(row["extension_blocks"]),
        import_meta=json.loads(row["import_meta"]),
        created_at=row["created_at"],
    )


def _row_to_card_response(row, version_row=None) -> CharacterCardResponse:
    version = _row_to_version_response(version_row) if version_row else None
    return CharacterCardResponse(
        id=row["id"],
        project_id=row["project_id"],
        name=row["name"],
        name_normalized=row["name_normalized"],
        description=row["description"],
        tags=json.loads(row["tags_json"]),
        cover_asset_id=row["cover_asset_id"],
        avatar_asset_id=row["avatar_asset_id"],
        worldbook_id=row["worldbook_id"],
        default_preset_id=row["default_preset_id"],
        status=row["status"],
        source_type=row["source_type"],
        current_draft_version_id=row["current_draft_version_id"],
        current_published_version_id=row["current_published_version_id"],
        latest_session_id=row["latest_session_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        published_at=row["published_at"],
        current_version=version,
    )


class CardService:
    def list_cards(self) -> list[CharacterCardResponse]:
        with get_connection() as connection:
            repository = CardRepository(connection)
            rows = repository.list_cards()
            return [_row_to_card_response(row) for row in rows]

    def get_card(self, card_id: str) -> CharacterCardResponse:
        with get_connection() as connection:
            repository = CardRepository(connection)
            card_row = repository.get_card(card_id)
            if card_row is None:
                raise NotFoundError(f"Character card not found: {card_id}")
            version_id = (
                card_row["current_published_version_id"]
                or card_row["current_draft_version_id"]
            )
            version_row = repository.get_card_version(version_id) if version_id else None
            return _row_to_card_response(card_row, version_row)

    def create_card(self, payload: CharacterCardCreateRequest) -> CharacterCardResponse:
        now = _utc_now()
        card_id = new_id()
        version_id = new_id()
        is_published = 1 if payload.is_published else 0

        card_values = {
            "id": card_id,
            "project_id": payload.project_id,
            "name": payload.name,
            "name_normalized": _normalize_name(payload.name),
            "description": payload.description,
            "tags_json": json.dumps(payload.tags, ensure_ascii=False),
            "cover_asset_id": payload.cover_asset_id,
            "avatar_asset_id": payload.avatar_asset_id,
            "worldbook_id": payload.worldbook_id,
            "default_preset_id": payload.default_preset_id,
            "status": payload.status,
            "source_type": payload.source_type,
            "current_draft_version_id": version_id,
            "current_published_version_id": version_id if payload.is_published else None,
            "latest_session_id": None,
            "created_at": now,
            "updated_at": now,
            "published_at": now if payload.is_published else None,
        }

        version_values = {
            "id": version_id,
            "card_id": card_id,
            "version": 1,
            "version_label": payload.version_label,
            "is_published": is_published,
            "spec": payload.spec,
            "source_type": payload.source_type,
            "base_info": json.dumps(_build_base_info(payload), ensure_ascii=False),
            "prompt_blocks": payload.content.model_dump_json(),
            "play_config": payload.play_config.model_dump_json(),
            "extension_blocks": payload.extension_blocks.model_dump_json(),
            "import_meta": payload.import_meta.model_dump_json(),
            "created_at": now,
        }

        with get_connection() as connection:
            repository = CardRepository(connection)
            repository.create_card(card_values)
            repository.create_card_version(version_values)
            created_card = repository.get_card(card_id)
            created_version = repository.get_card_version(version_id)

        return _row_to_card_response(created_card, created_version)

    def update_card(self, card_id: str, payload: CharacterCardUpdateRequest) -> CharacterCardResponse:
        now = _utc_now()
        with get_connection() as connection:
            repository = CardRepository(connection)
            existing_card = repository.get_card(card_id)
            if existing_card is None:
                raise NotFoundError(f"Character card not found: {card_id}")

            next_version = repository.get_latest_version_number(card_id) + 1
            version_id = new_id()
            is_published = 1 if payload.is_published else 0

            version_values = {
                "id": version_id,
                "card_id": card_id,
                "version": next_version,
                "version_label": payload.version_label,
                "is_published": is_published,
                "spec": payload.spec,
                "source_type": payload.source_type,
                "base_info": json.dumps(_build_base_info(payload), ensure_ascii=False),
                "prompt_blocks": payload.content.model_dump_json(),
                "play_config": payload.play_config.model_dump_json(),
                "extension_blocks": payload.extension_blocks.model_dump_json(),
                "import_meta": payload.import_meta.model_dump_json(),
                "created_at": now,
            }
            repository.create_card_version(version_values)

            current_published_version_id = existing_card["current_published_version_id"]
            if payload.is_published:
                current_published_version_id = version_id

            card_values = {
                "project_id": payload.project_id,
                "name": payload.name,
                "name_normalized": _normalize_name(payload.name),
                "description": payload.description,
                "tags_json": json.dumps(payload.tags, ensure_ascii=False),
                "cover_asset_id": payload.cover_asset_id,
                "avatar_asset_id": payload.avatar_asset_id,
                "worldbook_id": payload.worldbook_id,
                "default_preset_id": payload.default_preset_id,
                "status": payload.status,
                "source_type": payload.source_type,
                "current_draft_version_id": version_id,
                "current_published_version_id": current_published_version_id,
                "latest_session_id": existing_card["latest_session_id"],
                "updated_at": now,
                "published_at": now if payload.is_published else existing_card["published_at"],
            }
            repository.update_card(card_id, card_values)

            updated_card = repository.get_card(card_id)
            current_version_id = (
                updated_card["current_published_version_id"]
                or updated_card["current_draft_version_id"]
            )
            updated_version = repository.get_card_version(current_version_id)

        return _row_to_card_response(updated_card, updated_version)
