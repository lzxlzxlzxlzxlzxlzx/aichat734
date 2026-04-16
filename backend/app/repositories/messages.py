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
          AND m.is_hidden = 0
        ORDER BY m.sequence ASC
        """
        return self.connection.execute(query, (session_id,)).fetchall()

    def list_messages_before_sequence(
        self, session_id: str, sequence: int
    ) -> list[sqlite3.Row]:
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
          AND m.is_hidden = 0
          AND m.sequence < ?
        ORDER BY m.sequence ASC
        """
        return self.connection.execute(query, (session_id, sequence)).fetchall()

    def list_messages_through_sequence(
        self, session_id: str, sequence: int
    ) -> list[sqlite3.Row]:
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
          AND m.is_hidden = 0
          AND m.sequence <= ?
        ORDER BY m.sequence ASC
        """
        return self.connection.execute(query, (session_id, sequence)).fetchall()

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
        query = """
        SELECT COALESCE(MAX(sequence), 0)
        FROM messages
        WHERE session_id = ?
        """
        row = self.connection.execute(query, (session_id,)).fetchone()
        if row is None:
            return 0
        return int(row[0])

    def get_last_visible_message(self, session_id: str) -> sqlite3.Row | None:
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
          AND m.is_hidden = 0
        ORDER BY m.sequence DESC
        LIMIT 1
        """
        return self.connection.execute(query, (session_id,)).fetchone()

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

    def update_message_content(
        self,
        message_id: str,
        *,
        content: str,
        raw_content: str,
        structured_content: str | None = None,
        is_edited: int | None = None,
        updated_at: str,
    ) -> None:
        assignments = ["content = ?", "raw_content = ?"]
        parameters: list[Any] = [content, raw_content]
        if structured_content is not None:
            assignments.append("structured_content = ?")
            parameters.append(structured_content)
        if is_edited is not None:
            assignments.append("is_edited = ?")
            parameters.append(is_edited)
        assignments.append("updated_at = ?")
        parameters.append(updated_at)
        parameters.append(message_id)
        query = f"""
        UPDATE messages
        SET {", ".join(assignments)}
        WHERE id = ?
        """
        self.connection.execute(query, tuple(parameters))

    def update_message_lock(
        self, message_id: str, *, is_locked: bool, updated_at: str
    ) -> None:
        query = """
        UPDATE messages
        SET is_locked = ?, updated_at = ?
        WHERE id = ?
        """
        self.connection.execute(
            query, (1 if is_locked else 0, updated_at, message_id)
        )

    def hide_messages_from_sequence(
        self, session_id: str, sequence: int, updated_at: str
    ) -> None:
        query = """
        UPDATE messages
        SET is_hidden = 1, updated_at = ?
        WHERE session_id = ?
          AND is_hidden = 0
          AND sequence >= ?
        """
        self.connection.execute(query, (updated_at, session_id, sequence))

    def hide_messages_after_sequence(
        self, session_id: str, sequence: int, updated_at: str
    ) -> None:
        query = """
        UPDATE messages
        SET is_hidden = 1, updated_at = ?
        WHERE session_id = ?
          AND is_hidden = 0
          AND sequence > ?
        """
        self.connection.execute(query, (updated_at, session_id, sequence))

    def restore_messages_through_sequence(
        self, session_id: str, sequence: int, updated_at: str
    ) -> None:
        query = """
        UPDATE messages
        SET is_hidden = 0, updated_at = ?
        WHERE session_id = ?
          AND is_hidden = 1
          AND sequence <= ?
        """
        self.connection.execute(query, (updated_at, session_id, sequence))

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

    def update_message_swipe_postprocess(
        self,
        swipe_id: str,
        *,
        raw_response: str,
        cleaned_response: str,
        display_response: str,
        token_usage: str,
    ) -> None:
        query = """
        UPDATE message_swipes
        SET
            raw_response = :raw_response,
            cleaned_response = :cleaned_response,
            display_response = :display_response,
            token_usage = :token_usage
        WHERE id = :swipe_id
        """
        self.connection.execute(
            query,
            {
                "swipe_id": swipe_id,
                "raw_response": raw_response,
                "cleaned_response": cleaned_response,
                "display_response": display_response,
                "token_usage": token_usage,
            },
        )

    def get_swipe(self, swipe_id: str) -> sqlite3.Row | None:
        query = """
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
        WHERE s.id = ?
        """
        return self.connection.execute(query, (swipe_id,)).fetchone()

    def get_next_swipe_index(self, message_id: str) -> int:
        query = """
        SELECT COALESCE(MAX(swipe_index), -1) + 1
        FROM message_swipes
        WHERE message_id = ?
        """
        row = self.connection.execute(query, (message_id,)).fetchone()
        return int(row[0]) if row is not None else 0

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

    def delete_swipe(self, swipe_id: str) -> None:
        query = """
        DELETE FROM message_swipes
        WHERE id = ?
        """
        self.connection.execute(query, (swipe_id,))
