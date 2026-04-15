import sqlite3
from typing import Any


class CardRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_cards(self) -> list[sqlite3.Row]:
        query = """
        SELECT
            c.id,
            c.project_id,
            c.name,
            c.name_normalized,
            c.description,
            c.tags_json,
            c.cover_asset_id,
            c.avatar_asset_id,
            c.worldbook_id,
            c.default_preset_id,
            c.status,
            c.source_type,
            c.current_draft_version_id,
            c.current_published_version_id,
            c.latest_session_id,
            c.created_at,
            c.updated_at,
            c.published_at
        FROM character_cards AS c
        ORDER BY c.updated_at DESC
        """
        return self.connection.execute(query).fetchall()

    def get_card(self, card_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            c.id,
            c.project_id,
            c.name,
            c.name_normalized,
            c.description,
            c.tags_json,
            c.cover_asset_id,
            c.avatar_asset_id,
            c.worldbook_id,
            c.default_preset_id,
            c.status,
            c.source_type,
            c.current_draft_version_id,
            c.current_published_version_id,
            c.latest_session_id,
            c.created_at,
            c.updated_at,
            c.published_at
        FROM character_cards AS c
        WHERE c.id = ?
        """
        return self.connection.execute(query, (card_id,)).fetchone()

    def get_card_version(self, version_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            v.id,
            v.card_id,
            v.version,
            v.version_label,
            v.is_published,
            v.spec,
            v.source_type,
            v.base_info,
            v.prompt_blocks,
            v.play_config,
            v.extension_blocks,
            v.import_meta,
            v.created_at
        FROM character_card_versions AS v
        WHERE v.id = ?
        """
        return self.connection.execute(query, (version_id,)).fetchone()

    def get_latest_version_number(self, card_id: str) -> int:
        query = """
        SELECT COALESCE(MAX(version), 0)
        FROM character_card_versions
        WHERE card_id = ?
        """
        row = self.connection.execute(query, (card_id,)).fetchone()
        if row is None:
            return 0
        return int(row[0])

    def create_card(self, values: dict[str, Any]) -> None:
        query = """
        INSERT INTO character_cards (
            id,
            project_id,
            name,
            name_normalized,
            description,
            tags_json,
            cover_asset_id,
            avatar_asset_id,
            worldbook_id,
            default_preset_id,
            status,
            source_type,
            current_draft_version_id,
            current_published_version_id,
            latest_session_id,
            created_at,
            updated_at,
            published_at
        ) VALUES (
            :id,
            :project_id,
            :name,
            :name_normalized,
            :description,
            :tags_json,
            :cover_asset_id,
            :avatar_asset_id,
            :worldbook_id,
            :default_preset_id,
            :status,
            :source_type,
            :current_draft_version_id,
            :current_published_version_id,
            :latest_session_id,
            :created_at,
            :updated_at,
            :published_at
        )
        """
        self.connection.execute(query, values)

    def create_card_version(self, values: dict[str, Any]) -> None:
        query = """
        INSERT INTO character_card_versions (
            id,
            card_id,
            version,
            version_label,
            is_published,
            spec,
            source_type,
            base_info,
            prompt_blocks,
            play_config,
            extension_blocks,
            import_meta,
            created_at
        ) VALUES (
            :id,
            :card_id,
            :version,
            :version_label,
            :is_published,
            :spec,
            :source_type,
            :base_info,
            :prompt_blocks,
            :play_config,
            :extension_blocks,
            :import_meta,
            :created_at
        )
        """
        self.connection.execute(query, values)

    def update_card(self, card_id: str, values: dict[str, Any]) -> None:
        payload = dict(values)
        payload["id"] = card_id
        query = """
        UPDATE character_cards
        SET
            project_id = :project_id,
            name = :name,
            name_normalized = :name_normalized,
            description = :description,
            tags_json = :tags_json,
            cover_asset_id = :cover_asset_id,
            avatar_asset_id = :avatar_asset_id,
            worldbook_id = :worldbook_id,
            default_preset_id = :default_preset_id,
            status = :status,
            source_type = :source_type,
            current_draft_version_id = :current_draft_version_id,
            current_published_version_id = :current_published_version_id,
            latest_session_id = :latest_session_id,
            updated_at = :updated_at,
            published_at = :published_at
        WHERE id = :id
        """
        self.connection.execute(query, payload)
