from __future__ import annotations

from app.schemas import ClientUsage
from app.services.sqlite_store import SQLiteStore


class UsageRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.store = SQLiteStore(db_path)

    def increment(self, client_id: str) -> None:
        with self.store.connect() as conn:
            conn.execute(
                '''
                INSERT INTO client_usage (client_id, requests_total)
                VALUES (?, 1)
                ON CONFLICT(client_id) DO UPDATE SET requests_total = requests_total + 1
                ''',
                (client_id,),
            )
            conn.commit()

    def list_usage(self) -> list[ClientUsage]:
        with self.store.connect() as conn:
            rows = conn.execute('SELECT client_id, requests_total FROM client_usage ORDER BY client_id').fetchall()
        return [ClientUsage(client_id=row['client_id'], requests_total=row['requests_total']) for row in rows]
