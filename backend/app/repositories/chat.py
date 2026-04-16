import sqlite3


class ChatRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_recent_cards(self, limit: int = 8) -> list[sqlite3.Row]:
        query = """
        WITH ranked AS (
            SELECT
                c.id,
                c.name,
                c.description,
                c.tags_json,
                c.cover_asset_id,
                c.avatar_asset_id,
                c.latest_session_id,
                MAX(s.updated_at) AS last_interaction_at
            FROM character_cards AS c
            INNER JOIN sessions AS s
              ON s.card_id = c.id
            WHERE s.mode = 'play'
              AND c.status = 'published'
            GROUP BY
                c.id,
                c.name,
                c.description,
                c.tags_json,
                c.cover_asset_id,
                c.avatar_asset_id,
                c.latest_session_id
        )
        SELECT
            id,
            name,
            description,
            tags_json,
            cover_asset_id,
            avatar_asset_id,
            latest_session_id,
            last_interaction_at
        FROM ranked
        ORDER BY last_interaction_at DESC, name ASC
        LIMIT ?
        """
        return self.connection.execute(query, (limit,)).fetchall()
