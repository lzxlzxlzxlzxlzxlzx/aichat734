import sqlite3
from typing import Any


class StateRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get_latest_state_snapshot(self, session_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            s.id,
            s.session_id,
            s.message_id,
            s.variables,
            s.created_at
        FROM state_snapshots AS s
        WHERE s.session_id = ?
        ORDER BY s.created_at DESC
        LIMIT 1
        """
        return self.connection.execute(query, (session_id,)).fetchone()

    def get_latest_state_snapshot_before_sequence(
        self, session_id: str, sequence: int
    ) -> sqlite3.Row | None:
        query = """
        SELECT
            s.id,
            s.session_id,
            s.message_id,
            s.variables,
            s.created_at
        FROM state_snapshots AS s
        LEFT JOIN messages AS m
          ON m.id = s.message_id
        WHERE s.session_id = ?
          AND (
            s.message_id IS NULL
            OR m.sequence < ?
          )
        ORDER BY
          CASE WHEN s.message_id IS NULL THEN -1 ELSE m.sequence END DESC,
          s.created_at DESC
        LIMIT 1
        """
        return self.connection.execute(query, (session_id, sequence)).fetchone()

    def get_state_snapshot(self, snapshot_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            s.id,
            s.session_id,
            s.message_id,
            s.variables,
            s.created_at
        FROM state_snapshots AS s
        WHERE s.id = ?
        """
        return self.connection.execute(query, (snapshot_id,)).fetchone()

    def list_state_snapshots(self, session_id: str, limit: int = 20) -> list[sqlite3.Row]:
        query = """
        SELECT
            s.id,
            s.session_id,
            s.message_id,
            s.variables,
            s.created_at
        FROM state_snapshots AS s
        WHERE s.session_id = ?
        ORDER BY s.created_at DESC
        LIMIT ?
        """
        return self.connection.execute(query, (session_id, limit)).fetchall()

    def create_state_snapshot(self, values: dict[str, Any]) -> None:
        query = """
        INSERT INTO state_snapshots (
            id,
            session_id,
            message_id,
            variables,
            created_at
        ) VALUES (
            :id,
            :session_id,
            :message_id,
            :variables,
            :created_at
        )
        """
        self.connection.execute(query, values)

    def list_state_change_logs(self, session_id: str, limit: int = 50) -> list[sqlite3.Row]:
        query = """
        SELECT
            l.id,
            l.session_id,
            l.message_id,
            l.changes,
            l.raw_block,
            l.source_type,
            l.created_at
        FROM state_change_logs AS l
        WHERE l.session_id = ?
        ORDER BY l.created_at DESC
        LIMIT ?
        """
        return self.connection.execute(query, (session_id, limit)).fetchall()

    def get_state_change_log_by_message(self, message_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            l.id,
            l.session_id,
            l.message_id,
            l.changes,
            l.raw_block,
            l.source_type,
            l.created_at
        FROM state_change_logs AS l
        WHERE l.message_id = ?
        ORDER BY l.created_at DESC
        LIMIT 1
        """
        return self.connection.execute(query, (message_id,)).fetchone()

    def create_state_change_log(self, values: dict[str, Any]) -> None:
        query = """
        INSERT INTO state_change_logs (
            id,
            session_id,
            message_id,
            changes,
            raw_block,
            source_type,
            created_at
        ) VALUES (
            :id,
            :session_id,
            :message_id,
            :changes,
            :raw_block,
            :source_type,
            :created_at
        )
        """
        self.connection.execute(query, values)
