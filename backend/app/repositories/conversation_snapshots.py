import sqlite3
from typing import Any


class ConversationSnapshotRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create_snapshot(self, values: dict[str, Any]) -> None:
        query = """
        INSERT INTO conversation_snapshots (
            id,
            session_id,
            snapshot_type,
            message_id,
            message_sequence,
            inclusive,
            state_snapshot_id,
            memory_summary_ids,
            label,
            summary,
            created_by,
            created_at
        ) VALUES (
            :id,
            :session_id,
            :snapshot_type,
            :message_id,
            :message_sequence,
            :inclusive,
            :state_snapshot_id,
            :memory_summary_ids,
            :label,
            :summary,
            :created_by,
            :created_at
        )
        """
        self.connection.execute(query, values)

    def get_snapshot(self, snapshot_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            cs.id,
            cs.session_id,
            cs.snapshot_type,
            cs.message_id,
            cs.message_sequence,
            cs.inclusive,
            cs.state_snapshot_id,
            cs.memory_summary_ids,
            cs.label,
            cs.summary,
            cs.created_by,
            cs.created_at
        FROM conversation_snapshots AS cs
        WHERE cs.id = ?
        """
        return self.connection.execute(query, (snapshot_id,)).fetchone()

    def list_snapshots(self, session_id: str) -> list[sqlite3.Row]:
        query = """
        SELECT
            cs.id,
            cs.session_id,
            cs.snapshot_type,
            cs.message_id,
            cs.message_sequence,
            cs.inclusive,
            cs.state_snapshot_id,
            cs.memory_summary_ids,
            cs.label,
            cs.summary,
            cs.created_by,
            cs.created_at
        FROM conversation_snapshots AS cs
        WHERE cs.session_id = ?
        ORDER BY cs.created_at DESC, cs.message_sequence DESC
        """
        return self.connection.execute(query, (session_id,)).fetchall()
