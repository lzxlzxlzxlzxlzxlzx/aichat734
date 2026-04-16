import json
import re
from copy import deepcopy
from typing import Any

from app.core.database import get_connection
from app.core.exceptions import NotFoundError
from app.core.ids import new_id
from app.core.time import utc_now_iso
from app.repositories.sessions import SessionRepository
from app.repositories.states import StateRepository
from app.repositories.worldbooks import WorldBookRepository
from app.schemas.states import (
    SessionStateResponse,
    StateChangeItemResponse,
    StateChangeLogResponse,
    StateParseResult,
    StateSnapshotResponse,
)


STATE_UPDATE_PATTERN = re.compile(
    r"<state_update>\s*(.*?)\s*</state_update>", re.IGNORECASE | re.DOTALL
)
DELTA_VALUE_PATTERN = re.compile(r"^[+-]\d+(?:\.\d+)?$")


def _safe_json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return deepcopy(default)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return deepcopy(default)


def _normalize_state_schema(raw_schema: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(raw_schema, dict):
        return {}

    if "state_schema" in raw_schema and isinstance(raw_schema["state_schema"], dict):
        raw_schema = raw_schema["state_schema"]

    normalized: dict[str, dict[str, Any]] = {}
    for key, value in raw_schema.items():
        if isinstance(value, dict):
            normalized[str(key)] = value
    return normalized


def _build_initial_variables(schema: dict[str, dict[str, Any]]) -> dict[str, Any]:
    variables: dict[str, Any] = {}
    for key, field_schema in schema.items():
        variables[key] = deepcopy(field_schema.get("default"))
    return variables


def _coerce_scalar(value: str) -> Any:
    stripped = value.strip()
    if stripped.lower() in {"true", "false"}:
        return stripped.lower() == "true"
    if re.fullmatch(r"-?\d+", stripped):
        return int(stripped)
    if re.fullmatch(r"-?\d+\.\d+", stripped):
        return float(stripped)
    return stripped


def _coerce_value(raw_value: str, field_schema: dict[str, Any], current_value: Any) -> tuple[Any, str | None]:
    value_type = str(field_schema.get("type") or "string")
    stripped = raw_value.strip()

    if value_type == "number":
        if DELTA_VALUE_PATTERN.fullmatch(stripped):
            base_value = current_value if isinstance(current_value, (int, float)) else field_schema.get("default", 0) or 0
            return base_value + float(stripped), "delta"
        if re.fullmatch(r"-?\d+(?:\.\d+)?", stripped):
            return float(stripped), None
        raise ValueError("expected number")

    if value_type == "boolean":
        lowered = stripped.lower()
        if lowered in {"true", "false"}:
            return lowered == "true", None
        raise ValueError("expected boolean")

    if value_type == "enum":
        options = field_schema.get("options") or []
        if options and stripped not in options:
            raise ValueError("value not in enum options")
        return stripped, None

    if value_type == "object_map":
        result: dict[str, Any] = {}
        if not stripped:
            return result, None
        for part in stripped.split(","):
            item = part.strip()
            if not item:
                continue
            if "=" not in item:
                raise ValueError("expected key=value pairs")
            item_key, item_value = item.split("=", 1)
            result[item_key.strip()] = item_value.strip()
        return result, None

    if value_type == "string":
        return stripped, None

    return _coerce_scalar(stripped), None


def _validate_value(key: str, value: Any, field_schema: dict[str, Any]) -> Any:
    value_type = str(field_schema.get("type") or "string")

    if value_type == "number":
        if not isinstance(value, (int, float)):
            raise ValueError(f"{key}: expected number")
        minimum = field_schema.get("min")
        maximum = field_schema.get("max")
        if isinstance(minimum, (int, float)) and value < minimum:
            value = minimum
        if isinstance(maximum, (int, float)) and value > maximum:
            value = maximum
        return int(value) if float(value).is_integer() else float(value)

    if value_type == "boolean":
        if not isinstance(value, bool):
            raise ValueError(f"{key}: expected boolean")
        return value

    if value_type == "enum":
        options = field_schema.get("options") or []
        if options and value not in options:
            raise ValueError(f"{key}: value not in enum options")
        return value

    if value_type == "object_map":
        if not isinstance(value, dict):
            raise ValueError(f"{key}: expected object_map")
        return value

    return value


def _row_to_snapshot_response(row) -> StateSnapshotResponse:
    return StateSnapshotResponse(
        id=row["id"],
        session_id=row["session_id"],
        message_id=row["message_id"],
        variables=_safe_json_loads(row["variables"], {}),
        created_at=row["created_at"],
    )


def _row_to_change_log_response(row) -> StateChangeLogResponse:
    changes = _safe_json_loads(row["changes"], [])
    return StateChangeLogResponse(
        id=row["id"],
        session_id=row["session_id"],
        message_id=row["message_id"],
        changes=[StateChangeItemResponse(**item) for item in changes],
        raw_block=row["raw_block"],
        source_type=row["source_type"],
        created_at=row["created_at"],
    )


class StateService:
    def strip_state_update_block(self, text: str) -> str:
        stripped = STATE_UPDATE_PATTERN.sub("", text or "")
        return stripped.strip()

    def render_state_summary(
        self,
        *,
        variables: dict[str, Any],
        state_schema: dict[str, dict[str, Any]] | None = None,
    ) -> str:
        schema = state_schema or {}
        if not variables and not schema:
            return ""

        ordered_keys = list(schema.keys()) if schema else list(variables.keys())
        lines = ["Current session state:"]
        for key in ordered_keys:
            value = variables.get(key)
            if isinstance(value, dict):
                rendered = ", ".join(f"{sub_key}={sub_value}" for sub_key, sub_value in value.items())
            else:
                rendered = str(value)
            lines.append(f"- {key}: {rendered}")
        return "\n".join(lines)

    def _get_schema_for_session(
        self,
        *,
        session_row,
        worldbooks: WorldBookRepository,
    ) -> dict[str, dict[str, Any]]:
        if not session_row["worldbook_id"]:
            return {}
        worldbook_row = worldbooks.get_worldbook(session_row["worldbook_id"])
        if worldbook_row is None:
            return {}
        raw_schema = _safe_json_loads(worldbook_row["state_schema"], {})
        return _normalize_state_schema(raw_schema)

    def restore_state_before_sequence(
        self,
        *,
        session_id: str,
        sequence: int,
        connection,
    ) -> SessionStateResponse:
        sessions = SessionRepository(connection)
        states = StateRepository(connection)
        worldbooks = WorldBookRepository(connection)

        session_row = sessions.get_session(session_id)
        if session_row is None:
            raise NotFoundError(f"Session not found: {session_id}")

        snapshot = states.get_latest_state_snapshot_before_sequence(session_id, sequence)
        if snapshot is None:
            initialized = self.initialize_session_state(session_id)
            snapshot = states.get_state_snapshot(initialized.snapshot_id)

        now = utc_now_iso()
        sessions.update_current_state_snapshot(
            session_id=session_id,
            snapshot_id=snapshot["id"],
            updated_at=now,
        )

        return SessionStateResponse(
            session_id=session_id,
            snapshot_id=snapshot["id"],
            state_schema=self._get_schema_for_session(
                session_row=session_row,
                worldbooks=worldbooks,
            ),
            variables=_safe_json_loads(snapshot["variables"], {}),
            created_at=snapshot["created_at"],
        )

    def restore_state_snapshot(
        self,
        *,
        session_id: str,
        snapshot_id: str,
        connection,
    ) -> SessionStateResponse:
        sessions = SessionRepository(connection)
        states = StateRepository(connection)
        worldbooks = WorldBookRepository(connection)

        session_row = sessions.get_session(session_id)
        if session_row is None:
            raise NotFoundError(f"Session not found: {session_id}")

        snapshot = states.get_state_snapshot(snapshot_id)
        if snapshot is None or snapshot["session_id"] != session_id:
            raise NotFoundError(f"State snapshot not found: {snapshot_id}")

        now = utc_now_iso()
        sessions.update_current_state_snapshot(
            session_id=session_id,
            snapshot_id=snapshot_id,
            updated_at=now,
        )

        return SessionStateResponse(
            session_id=session_id,
            snapshot_id=snapshot["id"],
            state_schema=self._get_schema_for_session(
                session_row=session_row,
                worldbooks=worldbooks,
            ),
            variables=_safe_json_loads(snapshot["variables"], {}),
            created_at=snapshot["created_at"],
        )

    def initialize_session_state(self, session_id: str) -> SessionStateResponse:
        now = utc_now_iso()
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            states = StateRepository(connection)
            worldbooks = WorldBookRepository(connection)

            session_row = sessions.get_session(session_id)
            if session_row is None:
                raise NotFoundError(f"Session not found: {session_id}")

            latest_snapshot = states.get_latest_state_snapshot(session_id)
            schema = self._get_schema_for_session(
                session_row=session_row,
                worldbooks=worldbooks,
            )

            if latest_snapshot is None:
                variables = _build_initial_variables(schema)
                snapshot_id = new_id()
                states.create_state_snapshot(
                    {
                        "id": snapshot_id,
                        "session_id": session_id,
                        "message_id": None,
                        "variables": json.dumps(variables, ensure_ascii=False),
                        "created_at": now,
                    }
                )
                sessions.update_current_state_snapshot(
                    session_id=session_id,
                    snapshot_id=snapshot_id,
                    updated_at=now,
                )
                latest_snapshot = states.get_state_snapshot(snapshot_id)

            return SessionStateResponse(
                session_id=session_id,
                snapshot_id=latest_snapshot["id"],
                state_schema=schema,
                variables=_safe_json_loads(latest_snapshot["variables"], {}),
                created_at=latest_snapshot["created_at"],
            )

    def get_current_state(self, session_id: str) -> SessionStateResponse:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            worldbooks = WorldBookRepository(connection)
            states = StateRepository(connection)

            session_row = sessions.get_session(session_id)
            if session_row is None:
                raise NotFoundError(f"Session not found: {session_id}")

            schema = self._get_schema_for_session(
                session_row=session_row,
                worldbooks=worldbooks,
            )
            current_snapshot = None
            if session_row["current_state_snapshot_id"]:
                current_snapshot = states.get_state_snapshot(
                    session_row["current_state_snapshot_id"]
                )
            if current_snapshot is None:
                current_snapshot = states.get_latest_state_snapshot(session_id)
            if current_snapshot is None:
                return self.initialize_session_state(session_id)

            return SessionStateResponse(
                session_id=session_id,
                snapshot_id=current_snapshot["id"],
                state_schema=schema,
                variables=_safe_json_loads(current_snapshot["variables"], {}),
                created_at=current_snapshot["created_at"],
            )

    def list_state_snapshots(self, session_id: str) -> list[StateSnapshotResponse]:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            if sessions.get_session(session_id) is None:
                raise NotFoundError(f"Session not found: {session_id}")

            states = StateRepository(connection)
            return [
                _row_to_snapshot_response(row)
                for row in states.list_state_snapshots(session_id)
            ]

    def list_state_change_logs(self, session_id: str) -> list[StateChangeLogResponse]:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            if sessions.get_session(session_id) is None:
                raise NotFoundError(f"Session not found: {session_id}")

            states = StateRepository(connection)
            return [
                _row_to_change_log_response(row)
                for row in states.list_state_change_logs(session_id)
            ]

    def parse_and_apply_model_update(
        self,
        *,
        session_row,
        message_id: str,
        assistant_text: str,
        connection,
    ) -> StateParseResult:
        states = StateRepository(connection)
        worldbooks = WorldBookRepository(connection)
        sessions = SessionRepository(connection)

        schema = self._get_schema_for_session(
            session_row=session_row,
            worldbooks=worldbooks,
        )
        latest_snapshot = states.get_latest_state_snapshot(session_row["id"])
        if latest_snapshot is None:
            initialized = self.initialize_session_state(session_row["id"])
            latest_snapshot = states.get_state_snapshot(initialized.snapshot_id)

        current_variables = _safe_json_loads(latest_snapshot["variables"], {})
        current_variables = {**_build_initial_variables(schema), **current_variables}

        parse_result = StateParseResult()
        block_match = STATE_UPDATE_PATTERN.search(assistant_text or "")
        if not block_match:
            return parse_result

        parse_result.raw_block = block_match.group(0)
        block_content = block_match.group(1)
        next_variables = deepcopy(current_variables)

        for raw_line in block_content.splitlines():
            line = raw_line.strip()
            if not line or ":" not in line:
                continue
            key, raw_value = line.split(":", 1)
            key = key.strip()
            raw_value = raw_value.strip()
            if key not in schema:
                parse_result.ignored_fields.append(key)
                continue

            field_schema = schema[key]
            try:
                parsed_value, operation = _coerce_value(
                    raw_value,
                    field_schema,
                    current_variables.get(key),
                )
                validated_value = _validate_value(key, parsed_value, field_schema)
            except ValueError as exc:
                parse_result.validation_errors.append(f"{key}: {exc}")
                continue

            old_value = current_variables.get(key)
            next_variables[key] = validated_value
            parse_result.parsed_updates[key] = validated_value
            if operation == "delta":
                parse_result.delta_updates[key] = parsed_value - (
                    old_value if isinstance(old_value, (int, float)) else 0
                )
            parse_result.applied_changes.append(
                StateChangeItemResponse(
                    key=key,
                    old=old_value,
                    new=validated_value,
                    operation=operation or "set",
                )
            )

        parse_result.has_update = bool(
            parse_result.applied_changes
            or parse_result.validation_errors
            or parse_result.ignored_fields
        )

        snapshot_id = new_id()
        now = utc_now_iso()
        states.create_state_snapshot(
            {
                "id": snapshot_id,
                "session_id": session_row["id"],
                "message_id": message_id,
                "variables": json.dumps(next_variables, ensure_ascii=False),
                "created_at": now,
            }
        )
        sessions.update_current_state_snapshot(
            session_id=session_row["id"],
            snapshot_id=snapshot_id,
            updated_at=now,
        )

        if parse_result.applied_changes or parse_result.raw_block:
            states.create_state_change_log(
                {
                    "id": new_id(),
                    "session_id": session_row["id"],
                    "message_id": message_id,
                    "changes": json.dumps(
                        [item.model_dump() for item in parse_result.applied_changes],
                        ensure_ascii=False,
                    ),
                    "raw_block": parse_result.raw_block,
                    "source_type": "model",
                    "created_at": now,
                }
            )

        return parse_result
