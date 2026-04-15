import sqlite3
from pathlib import Path

from app.core.config import get_settings


def _ensure_parent_directory(file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)


def _read_schema(schema_path: Path) -> str:
    if not schema_path.exists():
        raise FileNotFoundError(f"SQLite schema file not found: {schema_path}")
    return schema_path.read_text(encoding="utf-8")


def initialize_database() -> None:
    settings = get_settings()
    database_path = settings.resolved_database_path
    schema_path = settings.resolved_schema_path

    _ensure_parent_directory(database_path)
    schema_sql = _read_schema(schema_path)

    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(schema_sql)
        connection.commit()
    finally:
        connection.close()
