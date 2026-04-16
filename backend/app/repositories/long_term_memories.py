import sqlite3
from typing import Any


class LongTermMemoryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_by_scope(
        self, scope_type: str, scope_id: str, *, limit: int = 50
    ) -> list[sqlite3.Row]:
        query = """
        SELECT
            ltm.id,
            ltm.scope_type,
            ltm.scope_id,
            ltm.content,
            ltm.type,
            ltm.importance,
            ltm.source_message_id,
            ltm.created_at
        FROM long_term_memories AS ltm
        WHERE ltm.scope_type = ?
          AND ltm.scope_id = ?
        ORDER BY
          CASE ltm.importance
            WHEN 'high' THEN 3
            WHEN 'medium' THEN 2
            ELSE 1
          END DESC,
          ltm.created_at DESC
        LIMIT ?
        """
        return self.connection.execute(query, (scope_type, scope_id, limit)).fetchall()

    def list_for_scopes(
        self, scopes: list[tuple[str, str]], *, limit: int = 12
    ) -> list[sqlite3.Row]:
        if not scopes:
            return []

        conditions: list[str] = []
        parameters: list[Any] = []
        for scope_type, scope_id in scopes:
            conditions.append("(ltm.scope_type = ? AND ltm.scope_id = ?)")
            parameters.extend([scope_type, scope_id])
        parameters.append(limit)

        query = f"""
        SELECT
            ltm.id,
            ltm.scope_type,
            ltm.scope_id,
            ltm.content,
            ltm.type,
            ltm.importance,
            ltm.source_message_id,
            ltm.created_at
        FROM long_term_memories AS ltm
        WHERE {" OR ".join(conditions)}
        ORDER BY
          CASE ltm.importance
            WHEN 'high' THEN 3
            WHEN 'medium' THEN 2
            ELSE 1
          END DESC,
          ltm.created_at DESC
        LIMIT ?
        """
        return self.connection.execute(query, tuple(parameters)).fetchall()

    def get_memory(self, memory_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            ltm.id,
            ltm.scope_type,
            ltm.scope_id,
            ltm.content,
            ltm.type,
            ltm.importance,
            ltm.source_message_id,
            ltm.created_at
        FROM long_term_memories AS ltm
        WHERE ltm.id = ?
        """
        return self.connection.execute(query, (memory_id,)).fetchone()

    def get_by_source_message_id(self, source_message_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            ltm.id,
            ltm.scope_type,
            ltm.scope_id,
            ltm.content,
            ltm.type,
            ltm.importance,
            ltm.source_message_id,
            ltm.created_at
        FROM long_term_memories AS ltm
        WHERE ltm.source_message_id = ?
        ORDER BY ltm.created_at DESC
        LIMIT 1
        """
        return self.connection.execute(query, (source_message_id,)).fetchone()

    def find_exact_match(
        self, *, scope_type: str, scope_id: str, content: str
    ) -> sqlite3.Row | None:
        query = """
        SELECT
            ltm.id,
            ltm.scope_type,
            ltm.scope_id,
            ltm.content,
            ltm.type,
            ltm.importance,
            ltm.source_message_id,
            ltm.created_at
        FROM long_term_memories AS ltm
        WHERE ltm.scope_type = ?
          AND ltm.scope_id = ?
          AND ltm.content = ?
        LIMIT 1
        """
        return self.connection.execute(
            query, (scope_type, scope_id, content)
        ).fetchone()

    def create_memory(self, values: dict[str, Any]) -> None:
        query = """
        INSERT INTO long_term_memories (
            id,
            scope_type,
            scope_id,
            content,
            type,
            importance,
            source_message_id,
            created_at
        ) VALUES (
            :id,
            :scope_type,
            :scope_id,
            :content,
            :type,
            :importance,
            :source_message_id,
            :created_at
        )
        """
        self.connection.execute(query, values)

    def update_memory(self, memory_id: str, values: dict[str, Any]) -> None:
        payload = dict(values)
        payload["id"] = memory_id
        query = """
        UPDATE long_term_memories
        SET
            content = :content,
            importance = :importance
        WHERE id = :id
        """
        self.connection.execute(query, payload)

    def delete_memory(self, memory_id: str) -> None:
        query = """
        DELETE FROM long_term_memories
        WHERE id = ?
        """
        self.connection.execute(query, (memory_id,))

    def list_auto_memory_ids_from_sequence(
        self, *, session_id: str, sequence: int
    ) -> list[str]:
        query = """
        SELECT ltm.id
        FROM long_term_memories AS ltm
        INNER JOIN messages AS m
          ON m.id = ltm.source_message_id
        WHERE ltm.type = 'auto'
          AND m.session_id = ?
          AND m.sequence >= ?
        """
        rows = self.connection.execute(query, (session_id, sequence)).fetchall()
        return [str(row[0]) for row in rows]
