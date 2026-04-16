from app.core.config import get_settings
from app.core.database import get_connection
from app.core.exceptions import AppError, NotFoundError
from app.core.ids import new_id
from app.core.time import utc_now_iso
from app.repositories.long_term_memories import LongTermMemoryRepository
from app.repositories.messages import MessageRepository
from app.repositories.sessions import SessionRepository
from app.schemas.long_term_memories import (
    AutoExtractLongTermMemoryResponse,
    CreateLongTermMemoryRequest,
    DeleteLongTermMemoryResponse,
    LongTermMemoryResponse,
    MarkMessageAsLongTermMemoryRequest,
    UpdateLongTermMemoryRequest,
)


def _row_to_response(row) -> LongTermMemoryResponse:
    return LongTermMemoryResponse(
        id=row["id"],
        scope_type=row["scope_type"],
        scope_id=row["scope_id"],
        content=row["content"],
        type=row["type"],
        importance=row["importance"],
        source_message_id=row["source_message_id"],
        created_at=row["created_at"],
    )


class LongTermMemoryService:
    _AUTO_KEYWORDS = (
        "记住",
        "设定",
        "规则",
        "约定",
        "关系",
        "决定",
        "目标",
        "身份",
        "名字",
        "我叫",
        "我是",
        "喜欢",
        "讨厌",
        "偏好",
        "必须",
        "always",
        "rule",
        "preference",
        "identity",
        "name",
        "goal",
    )

    def _validate_scope(
        self, *, session_row, scope_type: str, scope_id: str
    ) -> tuple[str, str]:
        normalized_scope_type = (scope_type or "").strip().lower()
        normalized_scope_id = (scope_id or "").strip()

        if normalized_scope_type not in {"session", "card", "global"}:
            raise AppError(f"Unsupported scope_type: {scope_type}", status_code=400)

        if normalized_scope_type == "session":
            if normalized_scope_id != session_row["id"]:
                raise AppError("session scope_id must match current session.", 400)
            return normalized_scope_type, normalized_scope_id

        if normalized_scope_type == "card":
            session_card_id = session_row["card_id"]
            if not session_card_id:
                raise AppError("Current session has no card scope.", 400)
            if normalized_scope_id != session_card_id:
                raise AppError("card scope_id must match current session card.", 400)
            return normalized_scope_type, normalized_scope_id

        if normalized_scope_id != "global":
            raise AppError("global scope_id must be 'global'.", 400)
        return normalized_scope_type, normalized_scope_id

    def _default_scope_for_session(self, session_row) -> tuple[str, str]:
        if session_row["mode"] == "play" and session_row["card_id"]:
            return "card", session_row["card_id"]
        return "session", session_row["id"]

    def _normalize_candidate_text(self, text: str) -> str:
        normalized = " ".join((text or "").strip().split())
        return normalized[:180].strip()

    def _fallback_extract_memory(
        self,
        *,
        session_row,
        user_text: str,
        assistant_text: str,
    ) -> tuple[bool, str | None, str]:
        combined = f"{user_text}\n{assistant_text}".strip()
        lowered = combined.lower()
        should_store = any(keyword.lower() in lowered for keyword in self._AUTO_KEYWORDS)
        if not should_store and len(combined) < 120:
            return False, None, "medium"

        importance = "high" if any(
            keyword in combined
            for keyword in ("设定", "规则", "约定", "决定", "身份", "名字", "目标")
        ) else "medium"

        preferred = assistant_text.strip() or user_text.strip()
        content = self._normalize_candidate_text(preferred)
        if not content:
            return False, None, "medium"
        return True, content, importance

    def _create_memory_row(
        self,
        *,
        repository: LongTermMemoryRepository,
        scope_type: str,
        scope_id: str,
        content: str,
        importance: str,
        memory_type: str,
        source_message_id: str | None,
    ) -> LongTermMemoryResponse:
        existing = repository.find_exact_match(
            scope_type=scope_type,
            scope_id=scope_id,
            content=content,
        )
        if existing is not None:
            return _row_to_response(existing)

        memory_id = new_id()
        repository.create_memory(
            {
                "id": memory_id,
                "scope_type": scope_type,
                "scope_id": scope_id,
                "content": content,
                "type": memory_type,
                "importance": importance,
                "source_message_id": source_message_id,
                "created_at": utc_now_iso(),
            }
        )
        created_row = repository.get_memory(memory_id)
        if created_row is None:
            raise AppError("Failed to create long-term memory.", 500)
        return _row_to_response(created_row)

    def list_scope_memories(
        self, *, session_id: str, scope_type: str, scope_id: str
    ) -> list[LongTermMemoryResponse]:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None:
                raise NotFoundError(f"Session not found: {session_id}")
            validated_scope_type, validated_scope_id = self._validate_scope(
                session_row=session_row,
                scope_type=scope_type,
                scope_id=scope_id,
            )
            repository = LongTermMemoryRepository(connection)
            return [
                _row_to_response(row)
                for row in repository.list_by_scope(
                    validated_scope_type,
                    validated_scope_id,
                    limit=100,
                )
            ]

    def create_memory(
        self, *, session_id: str, payload: CreateLongTermMemoryRequest
    ) -> LongTermMemoryResponse:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None:
                raise NotFoundError(f"Session not found: {session_id}")

            scope_type, scope_id = self._validate_scope(
                session_row=session_row,
                scope_type=payload.scope_type,
                scope_id=payload.scope_id,
            )
            if payload.source_message_id:
                messages = MessageRepository(connection)
                message_row = messages.get_message(payload.source_message_id)
                if (
                    message_row is None
                    or message_row["session_id"] != session_id
                    or bool(message_row["is_hidden"])
                ):
                    raise NotFoundError(
                        f"Message not found in session: {payload.source_message_id}"
                    )

            repository = LongTermMemoryRepository(connection)
            return self._create_memory_row(
                repository=repository,
                scope_type=scope_type,
                scope_id=scope_id,
                content=payload.content.strip(),
                importance=payload.importance,
                memory_type="manual",
                source_message_id=payload.source_message_id,
            )

    def mark_message_as_memory(
        self, *, message_id: str, payload: MarkMessageAsLongTermMemoryRequest
    ) -> LongTermMemoryResponse:
        with get_connection() as connection:
            messages = MessageRepository(connection)
            sessions = SessionRepository(connection)
            repository = LongTermMemoryRepository(connection)

            message_row = messages.get_message(message_id)
            if message_row is None or bool(message_row["is_hidden"]):
                raise NotFoundError(f"Message not found: {message_id}")

            session_row = sessions.get_session(message_row["session_id"])
            if session_row is None:
                raise NotFoundError(
                    f"Session not found: {message_row['session_id']}"
                )

            if payload.scope_type:
                if payload.scope_type == "session":
                    scope_type, scope_id = "session", session_row["id"]
                elif payload.scope_type == "card":
                    if not session_row["card_id"]:
                        raise AppError("Current session has no card scope.", 400)
                    scope_type, scope_id = "card", session_row["card_id"]
                elif payload.scope_type == "global":
                    scope_type, scope_id = "global", "global"
                else:
                    raise AppError(
                        f"Unsupported scope_type: {payload.scope_type}", 400
                    )
            else:
                scope_type, scope_id = self._default_scope_for_session(session_row)

            content = (payload.content or message_row["content"] or "").strip()
            if not content:
                raise AppError("Memory content must not be empty.", 400)

            return self._create_memory_row(
                repository=repository,
                scope_type=scope_type,
                scope_id=scope_id,
                content=content,
                importance=payload.importance,
                memory_type="manual",
                source_message_id=message_row["id"],
            )

    def delete_memory(
        self, *, session_id: str, memory_id: str
    ) -> DeleteLongTermMemoryResponse:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None:
                raise NotFoundError(f"Session not found: {session_id}")

            repository = LongTermMemoryRepository(connection)
            row = repository.get_memory(memory_id)
            if row is None:
                raise NotFoundError(f"Long-term memory not found: {memory_id}")

            allowed_scopes = {
                ("session", session_row["id"]),
                ("global", "global"),
            }
            if session_row["card_id"]:
                allowed_scopes.add(("card", session_row["card_id"]))
            if (row["scope_type"], row["scope_id"]) not in allowed_scopes:
                raise AppError("Memory does not belong to current session scopes.", 400)

            repository.delete_memory(memory_id)
            return DeleteLongTermMemoryResponse(memory_id=memory_id)

    def update_memory(
        self,
        *,
        session_id: str,
        memory_id: str,
        payload: UpdateLongTermMemoryRequest,
    ) -> LongTermMemoryResponse:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None:
                raise NotFoundError(f"Session not found: {session_id}")

            repository = LongTermMemoryRepository(connection)
            row = repository.get_memory(memory_id)
            if row is None:
                raise NotFoundError(f"Long-term memory not found: {memory_id}")

            allowed_scopes = {
                ("session", session_row["id"]),
                ("global", "global"),
            }
            if session_row["card_id"]:
                allowed_scopes.add(("card", session_row["card_id"]))
            if (row["scope_type"], row["scope_id"]) not in allowed_scopes:
                raise AppError("Memory does not belong to current session scopes.", 400)

            repository.update_memory(
                memory_id,
                {
                    "content": payload.content.strip(),
                    "importance": payload.importance,
                },
            )
            updated = repository.get_memory(memory_id)
            if updated is None:
                raise AppError("Failed to update long-term memory.", 500)
            return _row_to_response(updated)

    def list_prompt_injection_candidates(self, *, session_row, connection) -> list[LongTermMemoryResponse]:
        settings = get_settings()
        scopes: list[tuple[str, str]] = [("session", session_row["id"]), ("global", "global")]
        if session_row["card_id"]:
            scopes.append(("card", session_row["card_id"]))

        repository = LongTermMemoryRepository(connection)
        rows = repository.list_for_scopes(
            scopes,
            limit=settings.memory_prompt_long_term_limit,
        )
        return [_row_to_response(row) for row in rows]

    def maybe_auto_extract_for_session(
        self,
        *,
        session_id: str,
        connection=None,
    ) -> AutoExtractLongTermMemoryResponse:
        if connection is not None:
            return self._maybe_auto_extract_for_session_with_connection(
                session_id=session_id,
                connection=connection,
            )
        with get_connection() as new_connection:
            return self._maybe_auto_extract_for_session_with_connection(
                session_id=session_id,
                connection=new_connection,
            )

    def cleanup_auto_memories_from_sequence(
        self,
        *,
        session_id: str,
        sequence: int,
        connection=None,
    ) -> int:
        if connection is not None:
            return self._cleanup_auto_memories_from_sequence_with_connection(
                session_id=session_id,
                sequence=sequence,
                connection=connection,
            )
        with get_connection() as new_connection:
            return self._cleanup_auto_memories_from_sequence_with_connection(
                session_id=session_id,
                sequence=sequence,
                connection=new_connection,
            )

    def refresh_auto_memory_for_message(
        self,
        *,
        session_id: str,
        assistant_message_id: str,
        connection=None,
    ) -> AutoExtractLongTermMemoryResponse:
        if connection is not None:
            return self._refresh_auto_memory_for_message_with_connection(
                session_id=session_id,
                assistant_message_id=assistant_message_id,
                connection=connection,
            )
        with get_connection() as new_connection:
            return self._refresh_auto_memory_for_message_with_connection(
                session_id=session_id,
                assistant_message_id=assistant_message_id,
                connection=new_connection,
            )

    def _cleanup_auto_memories_from_sequence_with_connection(
        self,
        *,
        session_id: str,
        sequence: int,
        connection,
    ) -> int:
        repository = LongTermMemoryRepository(connection)
        memory_ids = repository.list_auto_memory_ids_from_sequence(
            session_id=session_id,
            sequence=sequence,
        )
        for memory_id in memory_ids:
            repository.delete_memory(memory_id)
        return len(memory_ids)

    def _resolve_auto_extract_candidate(
        self,
        *,
        session_id: str,
        assistant_message_id: str | None,
        connection,
    ):
        messages = MessageRepository(connection)
        visible_rows = messages.list_messages_by_session(session_id)
        if len(visible_rows) < 2:
            return None, None

        if assistant_message_id:
            assistant_row = messages.get_message(assistant_message_id)
            if (
                assistant_row is None
                or assistant_row["session_id"] != session_id
                or bool(assistant_row["is_hidden"])
            ):
                return None, None
        else:
            assistant_row = visible_rows[-1]

        if assistant_row["role"] != "assistant":
            return None, None

        user_row = None
        for row in reversed(visible_rows):
            if int(row["sequence"]) >= int(assistant_row["sequence"]):
                continue
            if row["role"] == "user":
                user_row = row
                break
        if user_row is None:
            return None, None
        return user_row, assistant_row

    def _refresh_auto_memory_for_message_with_connection(
        self,
        *,
        session_id: str,
        assistant_message_id: str,
        connection,
    ) -> AutoExtractLongTermMemoryResponse:
        repository = LongTermMemoryRepository(connection)
        existing = repository.get_by_source_message_id(assistant_message_id)
        if existing is not None and existing["type"] == "auto":
            repository.delete_memory(existing["id"])
        return self._maybe_auto_extract_for_session_with_connection(
            session_id=session_id,
            connection=connection,
            assistant_message_id=assistant_message_id,
        )

    def _maybe_auto_extract_for_session_with_connection(
        self,
        *,
        session_id: str,
        connection,
        assistant_message_id: str | None = None,
    ) -> AutoExtractLongTermMemoryResponse:
        sessions = SessionRepository(connection)
        repository = LongTermMemoryRepository(connection)

        session_row = sessions.get_session(session_id)
        if session_row is None:
            raise NotFoundError(f"Session not found: {session_id}")

        user_row, assistant_row = self._resolve_auto_extract_candidate(
            session_id=session_id,
            assistant_message_id=assistant_message_id,
            connection=connection,
        )
        if user_row is None or assistant_row is None:
            return AutoExtractLongTermMemoryResponse(created=False, memory=None)

        existing_by_source = repository.get_by_source_message_id(assistant_row["id"])
        if existing_by_source is not None:
            return AutoExtractLongTermMemoryResponse(
                created=False,
                memory=_row_to_response(existing_by_source),
            )

        scope_type, scope_id = self._default_scope_for_session(session_row)
        should_store, content, importance = self._fallback_extract_memory(
            session_row=session_row,
            user_text=user_row["content"] or "",
            assistant_text=assistant_row["content"] or "",
        )
        if not should_store or not content:
            return AutoExtractLongTermMemoryResponse(created=False, memory=None)

        created = self._create_memory_row(
            repository=repository,
            scope_type=scope_type,
            scope_id=scope_id,
            content=content,
            importance=importance,
            memory_type="auto",
            source_message_id=assistant_row["id"],
        )
        return AutoExtractLongTermMemoryResponse(created=True, memory=created)
