import sqlite3


class WorldBookRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get_worldbook(self, worldbook_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            w.id,
            w.project_id,
            w.name,
            w.description,
            w.source_type,
            w.ui_schema,
            w.state_schema,
            w.status,
            w.version,
            w.created_at,
            w.updated_at
        FROM worldbooks AS w
        WHERE w.id = ?
        """
        return self.connection.execute(query, (worldbook_id,)).fetchone()

    def list_constant_entries(self, worldbook_id: str) -> list[sqlite3.Row]:
        query = """
        SELECT
            e.id,
            e.worldbook_id,
            e.title,
            e.comment,
            e.keys_json,
            e.secondary_keys_json,
            e.content,
            e.constant,
            e.enabled,
            e.position,
            e.insertion_order,
            e.priority,
            e.extensions,
            e.created_at,
            e.updated_at
        FROM worldbook_entries AS e
        WHERE e.worldbook_id = ?
          AND e.enabled = 1
          AND e.constant = 1
        ORDER BY e.position ASC, e.priority DESC, e.insertion_order ASC
        """
        return self.connection.execute(query, (worldbook_id,)).fetchall()
