import sqlite3
from typing import Any


class MemorySummaryRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_by_session(
        self, session_id: str, *, limit: int = 20, include_frozen: bool = True
    ) -> list[sqlite3.Row]:
        frozen_clause = ""
        parameters: list[Any] = [session_id]
        if not include_frozen:
            frozen_clause = "AND ms.frozen = 0"
        parameters.append(limit)
        query = f"""
        SELECT
            ms.id,
            ms.session_id,
            ms.segment_start,
            ms.segment_end,
            ms.summary,
            ms.key_events,
            ms.state_snapshot_id,
            ms.frozen,
            ms.created_at
        FROM memory_summaries AS ms
        WHERE ms.session_id = ?
          {frozen_clause}
        ORDER BY ms.segment_end DESC, ms.created_at DESC
        LIMIT ?
        """
        return self.connection.execute(query, tuple(parameters)).fetchall()

    def list_before_sequence(
        self, session_id: str, *, before_sequence: int, limit: int = 3
    ) -> list[sqlite3.Row]:
        query = """
        SELECT
            ms.id,
            ms.session_id,
            ms.segment_start,
            ms.segment_end,
            ms.summary,
            ms.key_events,
            ms.state_snapshot_id,
            ms.frozen,
            ms.created_at
        FROM memory_summaries AS ms
        WHERE ms.session_id = ?
          AND ms.segment_end < ?
        ORDER BY ms.segment_end DESC, ms.created_at DESC
        LIMIT ?
        """
        return self.connection.execute(
            query, (session_id, before_sequence, limit)
        ).fetchall()

    def get_latest_summary(self, session_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            ms.id,
            ms.session_id,
            ms.segment_start,
            ms.segment_end,
            ms.summary,
            ms.key_events,
            ms.state_snapshot_id,
            ms.frozen,
            ms.created_at
        FROM memory_summaries AS ms
        WHERE ms.session_id = ?
        ORDER BY ms.segment_end DESC, ms.created_at DESC
        LIMIT 1
        """
        return self.connection.execute(query, (session_id,)).fetchone()

    def get_summary(self, summary_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            ms.id,
            ms.session_id,
            ms.segment_start,
            ms.segment_end,
            ms.summary,
            ms.key_events,
            ms.state_snapshot_id,
            ms.frozen,
            ms.created_at
        FROM memory_summaries AS ms
        WHERE ms.id = ?
        """
        return self.connection.execute(query, (summary_id,)).fetchone()

    def create_summary(self, values: dict[str, Any]) -> None:
        query = """
        INSERT INTO memory_summaries (
            id,
            session_id,
            segment_start,
            segment_end,
            summary,
            key_events,
            state_snapshot_id,
            frozen,
            created_at
        ) VALUES (
            :id,
            :session_id,
            :segment_start,
            :segment_end,
            :summary,
            :key_events,
            :state_snapshot_id,
            :frozen,
            :created_at
        )
        """
        self.connection.execute(query, values)
