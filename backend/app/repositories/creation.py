import sqlite3


class CreationRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_creation_cards(self) -> list[sqlite3.Row]:
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

    def list_creation_sessions_by_card(self, card_id: str) -> list[sqlite3.Row]:
        query = """
        SELECT
            s.id,
            s.mode,
            s.name,
            s.status,
            s.card_id,
            s.project_id,
            s.message_count,
            s.last_message_id,
            s.last_message_at,
            s.model_name,
            s.created_at,
            s.updated_at
        FROM sessions AS s
        WHERE s.mode = 'creation'
          AND s.card_id = ?
          AND s.status != 'deleted'
        ORDER BY s.updated_at DESC
        """
        return self.connection.execute(query, (card_id,)).fetchall()

    def list_cards_by_project(self, project_id: str) -> list[sqlite3.Row]:
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
        WHERE c.project_id = ?
        ORDER BY c.updated_at DESC
        """
        return self.connection.execute(query, (project_id,)).fetchall()

    def list_creation_sessions_by_project(self, project_id: str) -> list[sqlite3.Row]:
        query = """
        SELECT
            s.id,
            s.mode,
            s.name,
            s.status,
            s.card_id,
            s.project_id,
            s.message_count,
            s.last_message_id,
            s.last_message_at,
            s.model_name,
            s.created_at,
            s.updated_at
        FROM sessions AS s
        WHERE s.mode = 'creation'
          AND s.project_id = ?
          AND s.status != 'deleted'
        ORDER BY s.updated_at DESC
        """
        return self.connection.execute(query, (project_id,)).fetchall()

    def list_linked_sessions_by_card(self, card_id: str) -> list[sqlite3.Row]:
        query = """
        SELECT
            s.id,
            s.mode,
            s.name,
            s.status,
            s.last_message_at,
            s.updated_at
        FROM sessions AS s
        WHERE s.card_id = ?
          AND s.status != 'deleted'
        ORDER BY
            CASE
                WHEN s.mode = 'creation' THEN 0
                WHEN s.mode = 'play' THEN 1
                WHEN s.mode = 'chat' THEN 2
                ELSE 99
            END,
            s.updated_at DESC
        LIMIT 20
        """
        return self.connection.execute(query, (card_id,)).fetchall()

    def list_recent_creation_cards(self, limit: int = 12) -> list[sqlite3.Row]:
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
        LIMIT ?
        """
        return self.connection.execute(query, (limit,)).fetchall()

    def list_recent_creation_edits(self, limit: int = 20) -> list[sqlite3.Row]:
        query = """
        SELECT
            'project' AS item_type,
            p.id AS item_id,
            p.name AS title,
            COALESCE(p.description, '') AS subtitle,
            p.id AS project_id,
            NULL AS card_id,
            NULL AS session_id,
            p.updated_at AS updated_at
        FROM creation_projects AS p

        UNION ALL

        SELECT
            'card' AS item_type,
            c.id AS item_id,
            c.name AS title,
            COALESCE(c.description, '') AS subtitle,
            c.project_id AS project_id,
            c.id AS card_id,
            NULL AS session_id,
            c.updated_at AS updated_at
        FROM character_cards AS c

        UNION ALL

        SELECT
            'session' AS item_type,
            s.id AS item_id,
            s.name AS title,
            ('mode=' || s.mode) AS subtitle,
            s.project_id AS project_id,
            s.card_id AS card_id,
            s.id AS session_id,
            s.updated_at AS updated_at
        FROM sessions AS s
        WHERE s.mode = 'creation'
          AND s.status != 'deleted'

        ORDER BY updated_at DESC
        LIMIT ?
        """
        return self.connection.execute(query, (limit,)).fetchall()
