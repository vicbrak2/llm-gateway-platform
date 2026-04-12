from __future__ import annotations

import uuid

from app.schemas import GatewayApiKey
from app.services.sqlite_store import SQLiteStore


class GatewayApiKeyRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.store = SQLiteStore(db_path)

    def list_keys(self) -> list[GatewayApiKey]:
        with self.store.connect() as conn:
            rows = conn.execute('SELECT key_id, client_id, api_key, enabled FROM gateway_api_keys ORDER BY client_id, key_id').fetchall()
        return [GatewayApiKey(client_id=row['client_id'], key_id=row['key_id'], api_key=row['api_key'], enabled=bool(row['enabled'])) for row in rows]

    def create_key(self, client_id: str, api_key: str | None = None) -> GatewayApiKey:
        key_value = api_key or uuid.uuid4().hex
        key_id = uuid.uuid4().hex
        with self.store.connect() as conn:
            conn.execute(
                'INSERT INTO gateway_api_keys (key_id, client_id, api_key, enabled) VALUES (?, ?, ?, ?)',
                (key_id, client_id, key_value, 1),
            )
            conn.commit()
        return GatewayApiKey(client_id=client_id, key_id=key_id, api_key=key_value, enabled=True)

    def resolve_client_id(self, api_key: str) -> str | None:
        with self.store.connect() as conn:
            row = conn.execute('SELECT client_id FROM gateway_api_keys WHERE api_key = ? AND enabled = 1', (api_key,)).fetchone()
        return row['client_id'] if row else None

    def revoke_key(self, key_id: str) -> bool:
        with self.store.connect() as conn:
            result = conn.execute('UPDATE gateway_api_keys SET enabled = 0 WHERE key_id = ?', (key_id,))
            conn.commit()
        return result.rowcount > 0
