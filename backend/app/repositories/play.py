import sqlite3


class PlayRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_published_cards(self) -> list[sqlite3.Row]:
        query = """
        SELECT
            c.id,
            c.name,
            c.description,
            c.tags_json,
            c.cover_asset_id,
            c.avatar_asset_id,
            c.latest_session_id,
            c.published_at,
            c.current_published_version_id
        FROM character_cards AS c
        WHERE c.current_published_version_id IS NOT NULL
        ORDER BY c.updated_at DESC
        """
        return self.connection.execute(query).fetchall()

    def get_published_card(self, card_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            c.id,
            c.name,
            c.description,
            c.tags_json,
            c.cover_asset_id,
            c.avatar_asset_id,
            c.latest_session_id,
            c.published_at,
            c.current_published_version_id
        FROM character_cards AS c
        WHERE c.id = ?
          AND c.current_published_version_id IS NOT NULL
        """
        return self.connection.execute(query, (card_id,)).fetchone()

    def list_play_sessions_by_card(self, card_id: str) -> list[sqlite3.Row]:
        query = """
        SELECT
            s.id,
            s.name,
            s.status,
            s.card_id,
            s.message_count,
            s.last_message_id,
            s.last_message_at,
            s.current_state_snapshot_id,
            s.model_name,
            s.created_at,
            s.updated_at
        FROM sessions AS s
        WHERE s.mode = 'play'
          AND s.card_id = ?
          AND s.status != 'deleted'
        ORDER BY s.updated_at DESC
        """
        return self.connection.execute(query, (card_id,)).fetchall()
