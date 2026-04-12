from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import BillingSummaryResponse, ClientUsage, UsageByCapability, UsageByDay
from app.services.sqlite_store import SQLiteStore


class UsageRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.store = SQLiteStore(db_path)

    def increment(self, client_id: str, capability: str | None = None, usage_date: str | None = None) -> None:
        effective_date = usage_date or datetime.now(timezone.utc).date().isoformat()
        effective_capability = capability or 'chat'
        with self.store.connect() as conn:
            conn.execute(
                '''
                INSERT INTO client_usage (client_id, requests_total)
                VALUES (?, 1)
                ON CONFLICT(client_id) DO UPDATE SET requests_total = requests_total + 1
                ''',
                (client_id,),
            )
            conn.execute(
                '''
                INSERT INTO client_usage_capability (client_id, capability, requests_total)
                VALUES (?, ?, 1)
                ON CONFLICT(client_id, capability) DO UPDATE SET requests_total = requests_total + 1
                ''',
                (client_id, effective_capability),
            )
            conn.execute(
                '''
                INSERT INTO client_usage_daily (client_id, usage_date, requests_total)
                VALUES (?, ?, 1)
                ON CONFLICT(client_id, usage_date) DO UPDATE SET requests_total = requests_total + 1
                ''',
                (client_id, effective_date),
            )
            conn.commit()

    def list_usage(self) -> list[ClientUsage]:
        with self.store.connect() as conn:
            rows = conn.execute('SELECT client_id, requests_total FROM client_usage ORDER BY client_id').fetchall()
        return [ClientUsage(client_id=row['client_id'], requests_total=row['requests_total']) for row in rows]

    def list_usage_by_capability(self) -> list[UsageByCapability]:
        with self.store.connect() as conn:
            rows = conn.execute('SELECT client_id, capability, requests_total FROM client_usage_capability ORDER BY client_id, capability').fetchall()
        return [UsageByCapability(client_id=row['client_id'], capability=row['capability'], requests_total=row['requests_total']) for row in rows]

    def list_usage_by_day(self) -> list[UsageByDay]:
        with self.store.connect() as conn:
            rows = conn.execute('SELECT client_id, usage_date, requests_total FROM client_usage_daily ORDER BY usage_date, client_id').fetchall()
        return [UsageByDay(client_id=row['client_id'], usage_date=row['usage_date'], requests_total=row['requests_total']) for row in rows]

    def billing_summary(self) -> BillingSummaryResponse:
        return BillingSummaryResponse(total_usage=self.list_usage(), usage_by_capability=self.list_usage_by_capability(), usage_by_day=self.list_usage_by_day())
