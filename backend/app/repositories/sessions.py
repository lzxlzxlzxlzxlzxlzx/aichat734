import sqlite3
from typing import Any


class SessionRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_sessions(self) -> list[sqlite3.Row]:
        query = """
        SELECT
            s.id,
            s.mode,
            s.name,
            s.status,
            s.card_id,
            s.card_version_id,
            s.worldbook_id,
            s.project_id,
            s.persona_id,
            s.preset_version_id,
            s.origin_session_id,
            s.origin_snapshot_id,
            s.message_count,
            s.last_message_id,
            s.last_message_at,
            s.current_state_snapshot_id,
            ss.variables AS current_state_snapshot_variables,
            s.model_name,
            s.created_at,
            s.updated_at
        FROM sessions AS s
        LEFT JOIN state_snapshots AS ss
          ON ss.id = s.current_state_snapshot_id
        ORDER BY s.updated_at DESC
        """
        return self.connection.execute(query).fetchall()

    def list_sessions_by_mode(self, mode: str) -> list[sqlite3.Row]:
        query = """
        SELECT
            s.id,
            s.mode,
            s.name,
            s.status,
            s.card_id,
            s.card_version_id,
            s.worldbook_id,
            s.project_id,
            s.persona_id,
            s.preset_version_id,
            s.origin_session_id,
            s.origin_snapshot_id,
            s.message_count,
            s.last_message_id,
            s.last_message_at,
            s.current_state_snapshot_id,
            ss.variables AS current_state_snapshot_variables,
            s.model_name,
            s.created_at,
            s.updated_at
        FROM sessions AS s
        LEFT JOIN state_snapshots AS ss
          ON ss.id = s.current_state_snapshot_id
        WHERE s.mode = ?
        ORDER BY s.updated_at DESC
        """
        return self.connection.execute(query, (mode,)).fetchall()

    def get_session(self, session_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            s.id,
            s.mode,
            s.name,
            s.status,
            s.card_id,
            s.card_version_id,
            s.worldbook_id,
            s.project_id,
            s.persona_id,
            s.preset_version_id,
            s.origin_session_id,
            s.origin_snapshot_id,
            s.message_count,
            s.last_message_id,
            s.last_message_at,
            s.current_state_snapshot_id,
            ss.variables AS current_state_snapshot_variables,
            s.model_name,
            s.created_at,
            s.updated_at
        FROM sessions AS s
        LEFT JOIN state_snapshots AS ss
          ON ss.id = s.current_state_snapshot_id
        WHERE s.id = ?
        """
        return self.connection.execute(query, (session_id,)).fetchone()

    def create_session(self, values: dict[str, Any]) -> None:
        query = """
        INSERT INTO sessions (
            id,
            mode,
            name,
            status,
            card_id,
            card_version_id,
            worldbook_id,
            project_id,
            persona_id,
            preset_version_id,
            origin_session_id,
            origin_snapshot_id,
            message_count,
            last_message_id,
            last_message_at,
            current_state_snapshot_id,
            model_name,
            created_at,
            updated_at
        ) VALUES (
            :id,
            :mode,
            :name,
            :status,
            :card_id,
            :card_version_id,
            :worldbook_id,
            :project_id,
            :persona_id,
            :preset_version_id,
            :origin_session_id,
            :origin_snapshot_id,
            :message_count,
            :last_message_id,
            :last_message_at,
            :current_state_snapshot_id,
            :model_name,
            :created_at,
            :updated_at
        )
        """
        self.connection.execute(query, values)

    def update_latest_session_for_card(
        self, card_id: str, session_id: str, updated_at: str
    ) -> None:
        query = """
        UPDATE character_cards
        SET latest_session_id = ?, updated_at = ?
        WHERE id = ?
        """
        self.connection.execute(query, (session_id, updated_at, card_id))

    def update_session_activity(
        self,
        session_id: str,
        message_count: int,
        last_message_id: str,
        last_message_at: str,
        updated_at: str,
    ) -> None:
        query = """
        UPDATE sessions
        SET
            message_count = ?,
            last_message_id = ?,
            last_message_at = ?,
            updated_at = ?
        WHERE id = ?
        """
        self.connection.execute(
            query,
            (message_count, last_message_id, last_message_at, updated_at, session_id),
        )

    def update_current_state_snapshot(
        self,
        session_id: str,
        snapshot_id: str,
        updated_at: str,
    ) -> None:
        query = """
        UPDATE sessions
        SET
            current_state_snapshot_id = ?,
            updated_at = ?
        WHERE id = ?
        """
        self.connection.execute(query, (snapshot_id, updated_at, session_id))

    def update_session_metadata(
        self,
        session_id: str,
        *,
        name: str | None = None,
        status: str | None = None,
        model_name: str | None = None,
        updated_at: str,
    ) -> None:
        assignments: list[str] = []
        parameters: list[Any] = []
        if name is not None:
            assignments.append("name = ?")
            parameters.append(name)
        if status is not None:
            assignments.append("status = ?")
            parameters.append(status)
        if model_name is not None:
            assignments.append("model_name = ?")
            parameters.append(model_name)
        assignments.append("updated_at = ?")
        parameters.append(updated_at)
        parameters.append(session_id)
        query = f"""
        UPDATE sessions
        SET {", ".join(assignments)}
        WHERE id = ?
        """
        self.connection.execute(query, tuple(parameters))
