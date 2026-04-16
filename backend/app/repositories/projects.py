import sqlite3
from typing import Any


class CreationProjectRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get_project(self, project_id: str) -> sqlite3.Row | None:
        query = """
        SELECT
            p.id,
            p.name,
            p.description,
            p.project_type,
            p.ip_name,
            p.status,
            p.default_model,
            p.created_at,
            p.updated_at
        FROM creation_projects AS p
        WHERE p.id = ?
        """
        return self.connection.execute(query, (project_id,)).fetchone()

    def create_project(self, values: dict[str, Any]) -> None:
        query = """
        INSERT INTO creation_projects (
            id,
            name,
            description,
            project_type,
            ip_name,
            status,
            default_model,
            created_at,
            updated_at
        ) VALUES (
            :id,
            :name,
            :description,
            :project_type,
            :ip_name,
            :status,
            :default_model,
            :created_at,
            :updated_at
        )
        """
        self.connection.execute(query, values)

    def list_projects(self) -> list[sqlite3.Row]:
        query = """
        SELECT
            p.id,
            p.name,
            p.description,
            p.project_type,
            p.ip_name,
            p.status,
            p.default_model,
            p.created_at,
            p.updated_at,
            COUNT(DISTINCT c.id) AS card_count,
            COUNT(DISTINCT w.id) AS worldbook_count
        FROM creation_projects AS p
        LEFT JOIN character_cards AS c
          ON c.project_id = p.id
        LEFT JOIN worldbooks AS w
          ON w.project_id = p.id
        GROUP BY
            p.id,
            p.name,
            p.description,
            p.project_type,
            p.ip_name,
            p.status,
            p.default_model,
            p.created_at,
            p.updated_at
        ORDER BY p.updated_at DESC
        """
        return self.connection.execute(query).fetchall()

    def update_project(self, project_id: str, values: dict[str, Any]) -> None:
        payload = dict(values)
        payload["id"] = project_id
        query = """
        UPDATE creation_projects
        SET
            name = :name,
            description = :description,
            project_type = :project_type,
            ip_name = :ip_name,
            status = :status,
            default_model = :default_model,
            updated_at = :updated_at
        WHERE id = :id
        """
        self.connection.execute(query, payload)
