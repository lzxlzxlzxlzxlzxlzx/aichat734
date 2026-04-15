import sqlite3
from typing import Any


class MessageRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_messages_by_session(self, session_id: str) -> list[sqlite3.Row]:
        query = """
        SELECT
            m.id,
            m.session_id,
            m.role,
            m.sequence,
            m.reply_to_message_id,
            m.content,
            m.raw_content,
            m.structured_content,
            m.active_swipe_id,
            m.token_count,
            m.is_hidden,
            m.is_locked,
            m.is_edited,
            m.source_type,
            m.created_at,
            m.updated_at
        FROM messages AS m
        WHERE m.session_id = ?
        ORDER BY m.sequence ASC
        """
        return self.connection.execute(query, (session_id,)).fetchall()

    def get_message(self, message_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            m.id,
            m.session_id,
            m.role,
            m.sequence,
            m.reply_to_message_id,
            m.content,
            m.raw_content,
            m.structured_content,
            m.active_swipe_id,
            m.token_count,
            m.is_hidden,
            m.is_locked,
            m.is_edited,
            m.source_type,
            m.created_at,
            m.updated_at
        FROM messages AS m
        WHERE m.id = ?
        """
        return self.connection.execute(query, (message_id,)).fetchone()

    def get_last_sequence(self, session_id: str) -> int:
        query = "SELECT COALESCE(MAX(sequence), 0) FROM messages WHERE session_id = ?"
        row = self.connection.execute(query, (session_id,)).fetchone()
        if row is None:
            return 0
        return int(row[0])

    def create_message(self, values: dict[str, Any]) -> None:
        query = """
        INSERT INTO messages (
            id,
            session_id,
            role,
            sequence,
            reply_to_message_id,
            content,
            raw_content,
            structured_content,
            active_swipe_id,
            token_count,
            is_hidden,
            is_locked,
            is_edited,
            source_type,
            created_at,
            updated_at
        ) VALUES (
            :id,
            :session_id,
            :role,
            :sequence,
            :reply_to_message_id,
            :content,
            :raw_content,
            :structured_content,
            :active_swipe_id,
            :token_count,
            :is_hidden,
            :is_locked,
            :is_edited,
            :source_type,
            :created_at,
            :updated_at
        )
        """
        self.connection.execute(query, values)

    def update_message_active_swipe(self, message_id: str, swipe_id: str, updated_at: str) -> None:
        query = """
        UPDATE messages
        SET active_swipe_id = ?, updated_at = ?
        WHERE id = ?
        """
        self.connection.execute(query, (swipe_id, updated_at, message_id))

    def create_message_swipe(self, values: dict[str, Any]) -> None:
        query = """
        INSERT INTO message_swipes (
            id,
            message_id,
            swipe_index,
            generation_status,
            raw_response,
            cleaned_response,
            display_response,
            provider_name,
            model_name,
            finish_reason,
            token_usage,
            trace_id,
            created_at
        ) VALUES (
            :id,
            :message_id,
            :swipe_index,
            :generation_status,
            :raw_response,
            :cleaned_response,
            :display_response,
            :provider_name,
            :model_name,
            :finish_reason,
            :token_usage,
            :trace_id,
            :created_at
        )
        """
        self.connection.execute(query, values)

    def list_swipes_by_message_ids(self, message_ids: list[str]) -> list[sqlite3.Row]:
        if not message_ids:
            return []
        placeholders = ",".join("?" for _ in message_ids)
        query = f"""
        SELECT
            s.id,
            s.message_id,
            s.swipe_index,
            s.generation_status,
            s.raw_response,
            s.cleaned_response,
            s.display_response,
            s.provider_name,
            s.model_name,
            s.finish_reason,
            s.token_usage,
            s.trace_id,
            s.created_at
        FROM message_swipes AS s
        WHERE s.message_id IN ({placeholders})
        ORDER BY s.message_id, s.swipe_index ASC
        """
        return self.connection.execute(query, tuple(message_ids)).fetchall()
