import sqlite3


class QuickReplyRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_global_sets(self) -> list[sqlite3.Row]:
        query = """
        SELECT
            q.id,
            q.name,
            q.scope_type,
            q.scope_id,
            q.items,
            q.created_at
        FROM quick_reply_sets AS q
        WHERE q.scope_type = 'global'
        ORDER BY q.created_at ASC
        """
        return self.connection.execute(query).fetchall()

    def list_card_sets(self, card_id: str) -> list[sqlite3.Row]:
        query = """
        SELECT
            q.id,
            q.name,
            q.scope_type,
            q.scope_id,
            q.items,
            q.created_at
        FROM quick_reply_sets AS q
        INNER JOIN character_card_quick_reply_sets AS c
          ON c.quick_reply_set_id = q.id
        WHERE c.card_id = ?
        ORDER BY q.created_at ASC
        """
        return self.connection.execute(query, (card_id,)).fetchall()
