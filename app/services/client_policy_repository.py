from __future__ import annotations

import json
from pathlib import Path

from app.schemas import ClientPolicy


class ClientPolicyRepository:
    def __init__(self, path: str = 'app/data/clients.json') -> None:
        self.path = Path(path)

    def list_policies(self) -> list[ClientPolicy]:
        return [ClientPolicy(**item) for item in self._read_raw()]

    def get_policy(self, client_id: str) -> ClientPolicy | None:
        for item in self.list_policies():
            if item.client_id == client_id:
                return item
        return None

    def upsert_policy(self, policy: ClientPolicy) -> ClientPolicy:
        items = self._read_raw()
        replaced = False
        for index, item in enumerate(items):
            if item.get('client_id') == policy.client_id:
                items[index] = policy.model_dump()
                replaced = True
                break
        if not replaced:
            items.append(policy.model_dump())
        self._write_raw(items)
        return policy

    def _read_raw(self) -> list[dict]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding='utf-8'))

    def _write_raw(self, items: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')
