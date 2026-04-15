import sqlite3
from typing import Any


class PromptTraceRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_by_session(self, session_id: str) -> list[sqlite3.Row]:
        query = """
        SELECT
            t.id,
            t.session_id,
            t.message_id,
            t.swipe_id,
            t.mode,
            t.created_at
        FROM prompt_traces AS t
        WHERE t.session_id = ?
        ORDER BY t.created_at DESC
        """
        return self.connection.execute(query, (session_id,)).fetchall()

    def get_by_id(self, trace_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            t.id,
            t.session_id,
            t.message_id,
            t.swipe_id,
            t.mode,
            t.raw_user_input,
            t.normalized_input,
            t.preset_layers,
            t.injection_items,
            t.final_messages,
            t.token_stats,
            t.tool_calls,
            t.raw_response,
            t.cleaned_response,
            t.display_response,
            t.regex_hits,
            t.state_update,
            t.created_at
        FROM prompt_traces AS t
        WHERE t.id = ?
        """
        return self.connection.execute(query, (trace_id,)).fetchone()

    def get_latest_by_message_id(self, message_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            t.id,
            t.session_id,
            t.message_id,
            t.swipe_id,
            t.mode,
            t.raw_user_input,
            t.normalized_input,
            t.preset_layers,
            t.injection_items,
            t.final_messages,
            t.token_stats,
            t.tool_calls,
            t.raw_response,
            t.cleaned_response,
            t.display_response,
            t.regex_hits,
            t.state_update,
            t.created_at
        FROM prompt_traces AS t
        WHERE t.message_id = ?
        ORDER BY t.created_at DESC
        LIMIT 1
        """
        return self.connection.execute(query, (message_id,)).fetchone()

    def create_prompt_trace(self, values: dict[str, Any]) -> None:
        query = """
        INSERT INTO prompt_traces (
            id,
            session_id,
            message_id,
            swipe_id,
            mode,
            raw_user_input,
            normalized_input,
            preset_layers,
            injection_items,
            final_messages,
            token_stats,
            tool_calls,
            raw_response,
            cleaned_response,
            display_response,
            regex_hits,
            state_update,
            created_at
        ) VALUES (
            :id,
            :session_id,
            :message_id,
            :swipe_id,
            :mode,
            :raw_user_input,
            :normalized_input,
            :preset_layers,
            :injection_items,
            :final_messages,
            :token_stats,
            :tool_calls,
            :raw_response,
            :cleaned_response,
            :display_response,
            :regex_hits,
            :state_update,
            :created_at
        )
        """
        self.connection.execute(query, values)

    def update_prompt_trace_swipe_id(self, trace_id: str, swipe_id: str) -> None:
        query = "UPDATE prompt_traces SET swipe_id = ? WHERE id = ?"
        self.connection.execute(query, (swipe_id, trace_id))
