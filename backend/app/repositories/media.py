import sqlite3
from typing import Any


class MediaRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create_media_asset(self, values: dict[str, Any]) -> None:
        query = """
        INSERT INTO media_assets (
            id,
            media_type,
            category,
            file_name,
            file_path,
            mime_type,
            size_bytes,
            meta,
            created_at
        ) VALUES (
            :id,
            :media_type,
            :category,
            :file_name,
            :file_path,
            :mime_type,
            :size_bytes,
            :meta,
            :created_at
        )
        """
        self.connection.execute(query, values)

    def get_media_asset(self, media_asset_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            m.id,
            m.media_type,
            m.category,
            m.file_name,
            m.file_path,
            m.mime_type,
            m.size_bytes,
            m.meta,
            m.created_at
        FROM media_assets AS m
        WHERE m.id = ?
        """
        return self.connection.execute(query, (media_asset_id,)).fetchone()

    def create_message_attachment(self, values: dict[str, Any]) -> None:
        query = """
        INSERT INTO message_attachments (
            id,
            message_id,
            media_asset_id,
            attachment_type,
            order_index,
            caption,
            created_at
        ) VALUES (
            :id,
            :message_id,
            :media_asset_id,
            :attachment_type,
            :order_index,
            :caption,
            :created_at
        )
        """
        self.connection.execute(query, values)

    def list_attachments_by_message_ids(
        self, message_ids: list[str]
    ) -> list[sqlite3.Row]:
        if not message_ids:
            return []
        placeholders = ",".join("?" for _ in message_ids)
        query = f"""
        SELECT
            a.id,
            a.message_id,
            a.media_asset_id,
            a.attachment_type,
            a.order_index,
            a.caption,
            a.created_at AS attachment_created_at,
            m.id AS asset_id,
            m.media_type,
            m.category,
            m.file_name,
            m.file_path,
            m.mime_type,
            m.size_bytes,
            m.meta,
            m.created_at AS asset_created_at
        FROM message_attachments AS a
        INNER JOIN media_assets AS m
          ON m.id = a.media_asset_id
        WHERE a.message_id IN ({placeholders})
        ORDER BY a.message_id ASC, a.order_index ASC, a.created_at ASC
        """
        return self.connection.execute(query, tuple(message_ids)).fetchall()

    def delete_attachments_by_message_id(self, message_id: str) -> None:
        query = """
        DELETE FROM message_attachments
        WHERE message_id = ?
        """
        self.connection.execute(query, (message_id,))
