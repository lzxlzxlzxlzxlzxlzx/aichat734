import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.core.config import get_settings


def _configure_connection(connection: sqlite3.Connection) -> sqlite3.Connection:
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def create_connection() -> sqlite3.Connection:
    settings = get_settings()
    connection = sqlite3.connect(settings.resolved_database_path)
    return _configure_connection(connection)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    connection = create_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
