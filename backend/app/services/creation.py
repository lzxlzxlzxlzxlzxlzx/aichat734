import json

from app.core.config import get_settings
from app.core.database import get_connection
from app.core.exceptions import AppError, NotFoundError
from app.core.ids import new_id
from app.core.time import utc_now_iso
from app.repositories.cards import CardRepository
from app.repositories.creation import CreationRepository
from app.repositories.messages import MessageRepository
from app.repositories.prompt_traces import PromptTraceRepository
from app.repositories.projects import CreationProjectRepository
from app.repositories.quick_replies import QuickReplyRepository
from app.repositories.sessions import SessionRepository
from app.schemas.creation import (
    CharacterCardCreateRequest,
    CharacterCardUpdateRequest,
    CreationCardDetailResponse,
    CreationCardSummaryResponse,
    CreationHomeResponse,
    CreationLinkedSessionSummary,
    CreationProjectCreateRequest,
    CreationProjectDetailResponse,
    CreationProjectSummaryResponse,
    CreationProjectUpdateRequest,
    CreationQuickReplyGroup,
    CreationQuickReplyItem,
    CreationRecentEditResponse,
    CreationSessionCopyRequest,
    CreationSessionCreateRequest,
    CreationSessionExportResponse,
    CreationSessionModelRequest,
    CreationSessionOverviewResponse,
    CreationSessionRenameRequest,
    CreationSessionStatusRequest,
    CreationSessionSummaryResponse,
    CreationTraceListResponse,
)
from app.schemas.sessions import (
    SessionCopyRequest,
    SessionCopyResponse,
    SessionCreateRequest,
    SessionResponse,
)
from app.services.cards import CardService
from app.services.prompt_traces import PromptTraceService, _row_to_summary
from app.services.sessions import SessionService, _row_to_session_response


def _row_to_creation_card_summary(row) -> CreationCardSummaryResponse:
    return CreationCardSummaryResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        tags=json.loads(row["tags_json"]) if row["tags_json"] else [],
        cover_asset_id=row["cover_asset_id"],
        avatar_asset_id=row["avatar_asset_id"],
        worldbook_id=row["worldbook_id"],
        project_id=row["project_id"],
        status=row["status"],
        source_type=row["source_type"],
        current_draft_version_id=row["current_draft_version_id"],
        current_published_version_id=row["current_published_version_id"],
        latest_session_id=row["latest_session_id"],
        updated_at=row["updated_at"],
    )


def _row_to_creation_session_summary(row) -> CreationSessionSummaryResponse:
    return CreationSessionSummaryResponse(
        id=row["id"],
        name=row["name"],
        status=row["status"],
        card_id=row["card_id"],
        project_id=row["project_id"],
        message_count=row["message_count"],
        last_message_id=row["last_message_id"],
        last_message_at=row["last_message_at"],
        model_name=row["model_name"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_linked_session_summary(row) -> CreationLinkedSessionSummary:
    return CreationLinkedSessionSummary(
        id=row["id"],
        mode=row["mode"],
        name=row["name"],
        status=row["status"],
        last_message_at=row["last_message_at"],
        updated_at=row["updated_at"],
    )


def _row_to_project_summary(row) -> CreationProjectSummaryResponse:
    return CreationProjectSummaryResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        project_type=row["project_type"],
        ip_name=row["ip_name"],
        status=row["status"],
        default_model=row["default_model"],
        card_count=int(row["card_count"] or 0),
        worldbook_count=int(row["worldbook_count"] or 0),
        updated_at=row["updated_at"],
    )


def _row_to_recent_edit(row) -> CreationRecentEditResponse:
    return CreationRecentEditResponse(
        item_type=row["item_type"],
        id=row["item_id"],
        title=row["title"],
        subtitle=row["subtitle"] or "",
        project_id=row["project_id"],
        card_id=row["card_id"],
        session_id=row["session_id"],
        updated_at=row["updated_at"],
    )


class CreationService:
    def __init__(self) -> None:
        self.card_service = CardService()
        self.session_service = SessionService()
        self.prompt_trace_service = PromptTraceService()

    def _require_creation_session(self, session_id: str):
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None or session_row["mode"] != "creation":
                raise NotFoundError(f"Creation session not found: {session_id}")
            return session_row

    def _require_project(self, project_id: str):
        with get_connection() as connection:
            projects = CreationProjectRepository(connection)
            project_row = projects.get_project(project_id)
            if project_row is None:
                raise NotFoundError(f"Creation project not found: {project_id}")
            return project_row

    def list_projects(self) -> list[CreationProjectSummaryResponse]:
        with get_connection() as connection:
            projects = CreationProjectRepository(connection)
            return [_row_to_project_summary(row) for row in projects.list_projects()]

    def create_project(
        self, payload: CreationProjectCreateRequest
    ) -> CreationProjectSummaryResponse:
        now = utc_now_iso()
        project_id = new_id()
        with get_connection() as connection:
            projects = CreationProjectRepository(connection)
            projects.create_project(
                {
                    "id": project_id,
                    "name": payload.name,
                    "description": payload.description,
                    "project_type": payload.project_type,
                    "ip_name": payload.ip_name,
                    "status": payload.status,
                    "default_model": payload.default_model,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            created = projects.get_project(project_id)
        refreshed = self.list_projects()
        return next(item for item in refreshed if item.id == created["id"])

    def update_project(
        self, project_id: str, payload: CreationProjectUpdateRequest
    ) -> CreationProjectSummaryResponse:
        self._require_project(project_id)
        with get_connection() as connection:
            projects = CreationProjectRepository(connection)
            projects.update_project(
                project_id,
                {
                    "name": payload.name,
                    "description": payload.description,
                    "project_type": payload.project_type,
                    "ip_name": payload.ip_name,
                    "status": payload.status,
                    "default_model": payload.default_model,
                    "updated_at": utc_now_iso(),
                },
            )
        refreshed = self.list_projects()
        return next(item for item in refreshed if item.id == project_id)

    def get_project_detail(self, project_id: str) -> CreationProjectDetailResponse:
        self._require_project(project_id)
        with get_connection() as connection:
            projects = CreationProjectRepository(connection)
            creation = CreationRepository(connection)
            project_summary = next(
                _row_to_project_summary(row)
                for row in projects.list_projects()
                if row["id"] == project_id
            )
            cards = [
                _row_to_creation_card_summary(row)
                for row in creation.list_cards_by_project(project_id)
            ]
            sessions = [
                _row_to_creation_session_summary(row)
                for row in creation.list_creation_sessions_by_project(project_id)
            ]
        return CreationProjectDetailResponse(
            project=project_summary,
            cards=cards,
            sessions=sessions,
        )

    def get_home(self) -> CreationHomeResponse:
        with get_connection() as connection:
            projects = CreationProjectRepository(connection)
            creation = CreationRepository(connection)
            project_items = [
                _row_to_project_summary(row) for row in projects.list_projects()[:12]
            ]
            card_items = [
                _row_to_creation_card_summary(row)
                for row in creation.list_recent_creation_cards(limit=12)
            ]
            recent_edits = [
                _row_to_recent_edit(row)
                for row in creation.list_recent_creation_edits(limit=20)
            ]
        return CreationHomeResponse(
            projects=project_items,
            cards=card_items,
            recent_edits=recent_edits,
        )

    def list_creation_cards(self) -> list[CreationCardSummaryResponse]:
        with get_connection() as connection:
            repository = CreationRepository(connection)
            return [
                _row_to_creation_card_summary(row)
                for row in repository.list_creation_cards()
            ]

    def get_creation_card_detail(self, card_id: str) -> CreationCardDetailResponse:
        card = self.card_service.get_card(card_id)
        with get_connection() as connection:
            repository = CreationRepository(connection)
            creation_sessions = [
                _row_to_creation_session_summary(row)
                for row in repository.list_creation_sessions_by_card(card_id)
            ]
            linked_sessions = [
                _row_to_linked_session_summary(row)
                for row in repository.list_linked_sessions_by_card(card_id)
            ]
        return CreationCardDetailResponse(
            card=card,
            creation_sessions=creation_sessions,
            linked_sessions=linked_sessions,
        )

    def create_card(self, payload: CharacterCardCreateRequest):
        if payload.project_id:
            self._require_project(payload.project_id)
            return self.card_service.create_card(payload)

        now = utc_now_iso()
        project_id = new_id()
        with get_connection() as connection:
            projects = CreationProjectRepository(connection)
            projects.create_project(
                {
                    "id": project_id,
                    "name": f"{payload.name} 项目",
                    "description": payload.description,
                    "project_type": "original",
                    "ip_name": None,
                    "status": "draft",
                    "default_model": None,
                    "created_at": now,
                    "updated_at": now,
                }
            )

        return self.card_service.create_card(
            payload.model_copy(update={"project_id": project_id})
        )

    def update_card(self, card_id: str, payload: CharacterCardUpdateRequest):
        existing = self.card_service.get_card(card_id)
        project_id = payload.project_id or existing.project_id
        if project_id:
            self._require_project(project_id)
        return self.card_service.update_card(
            card_id,
            payload.model_copy(update={"project_id": project_id}),
        )

    def list_creation_sessions_by_card(
        self, card_id: str
    ) -> list[CreationSessionSummaryResponse]:
        self.card_service.get_card(card_id)
        with get_connection() as connection:
            repository = CreationRepository(connection)
            return [
                _row_to_creation_session_summary(row)
                for row in repository.list_creation_sessions_by_card(card_id)
            ]

    def create_creation_session(
        self, card_id: str, payload: CreationSessionCreateRequest
    ) -> SessionResponse:
        settings = get_settings()
        card = self._ensure_card_project_binding(card_id)
        existing_sessions = self.list_creation_sessions_by_card(card_id)
        if payload.use_latest_existing_session and existing_sessions:
            return self.session_service.get_session(existing_sessions[0].id)

        create_payload = SessionCreateRequest(
            mode="creation",
            name=(payload.name or f"{card.name} 创作会话").strip() or f"{card.name} 创作会话",
            status="active",
            card_id=card.id,
            card_version_id=(
                card.current_draft_version_id or card.current_published_version_id
            ),
            worldbook_id=card.worldbook_id,
            project_id=card.project_id or card.id,
            model_name=payload.model_name or settings.default_chat_model,
        )
        return self.session_service.create_session(create_payload)

    def copy_creation_session(
        self, session_id: str, payload: CreationSessionCopyRequest
    ) -> SessionCopyResponse:
        self._require_creation_session(session_id)
        response = self.session_service.copy_session(
            session_id,
            SessionCopyRequest(
                name=payload.name,
                source_message_id=payload.source_message_id,
            ),
        )
        session = self.session_service.get_session(response.session.id)
        if session.mode != "creation":
            raise AppError("Copied session is not creation mode.", 500)
        return response

    def _ensure_card_project_binding(self, card_id: str):
        card = self.card_service.get_card(card_id)
        if card.project_id:
            return card

        now = utc_now_iso()
        project_id = new_id()
        with get_connection() as connection:
            projects = CreationProjectRepository(connection)
            cards = CardRepository(connection)
            projects.create_project(
                {
                    "id": project_id,
                    "name": f"{card.name} 项目",
                    "description": card.description,
                    "project_type": "original",
                    "ip_name": None,
                    "status": "draft",
                    "default_model": None,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            cards.update_card_project_id(card_id, project_id)

        return self.card_service.get_card(card_id)

    def get_creation_session_overview(
        self, session_id: str
    ) -> CreationSessionOverviewResponse:
        session = self._require_creation_session(session_id)
        if not session["card_id"]:
            raise AppError("Creation session is missing card binding.", 400)

        card = self.card_service.get_card(session["card_id"])
        latest_trace = None
        with get_connection() as connection:
            repository = CreationRepository(connection)
            traces = PromptTraceRepository(connection)
            rows = traces.list_by_session(session_id)
            if rows:
                latest_trace = _row_to_summary(rows[0])
            linked_sessions = [
                _row_to_linked_session_summary(row)
                for row in repository.list_linked_sessions_by_card(session["card_id"])
                if row["id"] != session_id
            ]

        return CreationSessionOverviewResponse(
            session=_row_to_session_response(session),
            card=card,
            linked_sessions=linked_sessions,
            latest_trace=latest_trace,
        )

    def export_creation_session(
        self,
        session_id: str,
        *,
        export_format: str,
        export_scope: str,
    ) -> CreationSessionExportResponse:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            messages = MessageRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None or session_row["mode"] != "creation":
                raise NotFoundError(f"Creation session not found: {session_id}")
            visible_rows = messages.list_messages_by_session(session_id)

        file_ext = "md" if export_format == "markdown" else "txt"
        safe_name = session_row["name"].replace("/", "_").replace("\\", "_")
        file_name = f"{safe_name}.{file_ext}"
        if export_scope == "reader":
            content = self._render_reader_export(
                session_name=session_row["name"],
                messages=visible_rows,
                markdown=export_format == "markdown",
            )
        elif export_scope == "debug":
            content = self._render_debug_export(
                session_id=session_id,
                session_name=session_row["name"],
                messages=visible_rows,
                markdown=export_format == "markdown",
            )
        else:
            raise AppError(f"Unsupported export_scope: {export_scope}", 400)

        return CreationSessionExportResponse(
            session_id=session_id,
            export_format=export_format,
            export_scope=export_scope,
            file_name=file_name,
            content=content,
        )

    def rename_creation_session(
        self, session_id: str, payload: CreationSessionRenameRequest
    ) -> SessionResponse:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None or session_row["mode"] != "creation":
                raise NotFoundError(f"Creation session not found: {session_id}")
            sessions.update_session_metadata(
                session_id,
                name=payload.name,
                updated_at=utc_now_iso(),
            )
            return _row_to_session_response(sessions.get_session(session_id))

    def update_creation_session_status(
        self, session_id: str, payload: CreationSessionStatusRequest
    ) -> SessionResponse:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None or session_row["mode"] != "creation":
                raise NotFoundError(f"Creation session not found: {session_id}")
            sessions.update_session_metadata(
                session_id,
                status=payload.status,
                updated_at=utc_now_iso(),
            )
            return _row_to_session_response(sessions.get_session(session_id))

    def update_creation_session_model(
        self, session_id: str, payload: CreationSessionModelRequest
    ) -> SessionResponse:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None or session_row["mode"] != "creation":
                raise NotFoundError(f"Creation session not found: {session_id}")
            sessions.update_session_metadata(
                session_id,
                model_name=payload.model_name.strip(),
                updated_at=utc_now_iso(),
            )
            return _row_to_session_response(sessions.get_session(session_id))

    def list_quick_replies(self, session_id: str) -> list[CreationQuickReplyGroup]:
        with get_connection() as connection:
            sessions = SessionRepository(connection)
            quick_replies = QuickReplyRepository(connection)
            session_row = sessions.get_session(session_id)
            if session_row is None or session_row["mode"] != "creation":
                raise NotFoundError(f"Creation session not found: {session_id}")

            groups: list[CreationQuickReplyGroup] = []
            for row in quick_replies.list_global_sets():
                groups.append(self._row_to_quick_reply_group(row))
            if session_row["card_id"]:
                for row in quick_replies.list_card_sets(session_row["card_id"]):
                    groups.append(self._row_to_quick_reply_group(row))
            return groups

    def _row_to_quick_reply_group(self, row) -> CreationQuickReplyGroup:
        raw_items = json.loads(row["items"]) if row["items"] else []
        items: list[CreationQuickReplyItem] = []
        for index, item in enumerate(raw_items):
            if isinstance(item, str):
                items.append(
                    CreationQuickReplyItem(
                        id=f"{row['id']}#{index}",
                        label=item,
                        content=item,
                        order=index,
                    )
                )
                continue
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or item.get("text") or item.get("value") or "")
            if not content.strip():
                continue
            items.append(
                CreationQuickReplyItem(
                    id=str(item.get("id") or f"{row['id']}#{index}"),
                    label=str(
                        item.get("label")
                        or item.get("title")
                        or item.get("name")
                        or f"Quick Reply {index + 1}"
                    ),
                    content=content,
                    mode=str(item.get("mode") or "fill"),
                    order=int(item.get("order") or index),
                )
            )
        return CreationQuickReplyGroup(
            id=row["id"],
            name=row["name"],
            scope_type=row["scope_type"],
            items=items,
        )

    def list_creation_traces(self, session_id: str) -> CreationTraceListResponse:
        self._require_creation_session(session_id)
        return CreationTraceListResponse(
            items=self.prompt_trace_service.list_session_traces(session_id)
        )

    def get_latest_creation_trace(self, session_id: str):
        self._require_creation_session(session_id)
        return self.prompt_trace_service.get_latest_trace_by_session(session_id)

    def get_creation_trace(self, session_id: str, trace_id: str):
        self._require_creation_session(session_id)
        trace = self.prompt_trace_service.get_trace(trace_id)
        if trace.session_id != session_id:
            raise NotFoundError(
                f"Prompt trace not found in creation session: {trace_id}"
            )
        return trace

    def get_creation_trace_by_message(self, session_id: str, message_id: str):
        self._require_creation_session(session_id)
        trace = self.prompt_trace_service.get_latest_trace_by_message(message_id)
        if trace.session_id != session_id:
            raise NotFoundError(
                f"Prompt trace not found for message in creation session: {message_id}"
            )
        return trace

    def _render_reader_export(self, *, session_name: str, messages: list, markdown: bool) -> str:
        lines: list[str] = []
        if markdown:
            lines.append(f"# {session_name}")
            lines.append("")
        else:
            lines.append(session_name)
            lines.append("=" * len(session_name))
            lines.append("")

        for row in messages:
            role = "创作者" if row["role"] == "user" else "助手"
            if markdown:
                lines.append(f"## {role}")
                lines.append(row["content"])
                lines.append("")
            else:
                lines.append(f"[{role}]")
                lines.append(row["content"])
                lines.append("")
        return "\n".join(lines).strip()

    def _render_debug_export(
        self,
        *,
        session_id: str,
        session_name: str,
        messages: list,
        markdown: bool,
    ) -> str:
        reader = self._render_reader_export(
            session_name=session_name,
            messages=messages,
            markdown=markdown,
        )
        traces = self.prompt_trace_service.list_session_traces(session_id)
        if markdown:
            sections = [reader, "", "## Prompt Trace Summary", ""]
            for item in traces[:10]:
                sections.append(f"- {item.id} | message={item.message_id} | mode={item.mode}")
            return "\n".join(sections).strip()

        sections = [reader, "", "Prompt Trace Summary", "--------------------"]
        for item in traces[:10]:
            sections.append(f"* {item.id} | message={item.message_id} | mode={item.mode}")
        return "\n".join(sections).strip()
