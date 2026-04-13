from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.schemas import PromptPolicy, PromptPolicyUpsert
from app.services.sqlite_store import SQLiteStore


class PromptPolicyRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.store = SQLiteStore(db_path)

    def list_policies(self, client_id: str) -> list[PromptPolicy]:
        with self.store.connect() as conn:
            rows = conn.execute('SELECT * FROM prompt_policies WHERE client_id = ? ORDER BY capability, updated_at DESC', (client_id,)).fetchall()
        return [self._row_to_policy(row) for row in rows]

    def resolve_policy(self, client_id: str, capability: str | None = None) -> PromptPolicy | None:
        with self.store.connect() as conn:
            if capability:
                row = conn.execute('SELECT * FROM prompt_policies WHERE client_id = ? AND capability = ? AND is_active = 1 ORDER BY updated_at DESC LIMIT 1', (client_id, capability)).fetchone()
                if row:
                    return self._row_to_policy(row)
            row = conn.execute('SELECT * FROM prompt_policies WHERE client_id = ? AND capability IS NULL AND is_active = 1 ORDER BY updated_at DESC LIMIT 1', (client_id,)).fetchone()
        return self._row_to_policy(row) if row else None

    def upsert_policy(self, policy: PromptPolicyUpsert) -> PromptPolicy:
        policy_id = policy.policy_id or uuid.uuid4().hex
        updated_at = datetime.now(timezone.utc).isoformat()
        with self.store.connect() as conn:
            conn.execute(
                '''
                INSERT INTO prompt_policies (policy_id, client_id, capability, system_prompt, style_rules, content_rules, is_active, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(policy_id) DO UPDATE SET
                    client_id=excluded.client_id,
                    capability=excluded.capability,
                    system_prompt=excluded.system_prompt,
                    style_rules=excluded.style_rules,
                    content_rules=excluded.content_rules,
                    is_active=excluded.is_active,
                    updated_at=excluded.updated_at
                ''',
                (policy_id, policy.client_id, policy.capability, policy.system_prompt, policy.style_rules, policy.content_rules, 1 if policy.is_active else 0, updated_at),
            )
            conn.commit()
        return PromptPolicy(policy_id=policy_id, client_id=policy.client_id, capability=policy.capability, system_prompt=policy.system_prompt, style_rules=policy.style_rules, content_rules=policy.content_rules, is_active=policy.is_active, updated_at=updated_at)

    def _row_to_policy(self, row) -> PromptPolicy:
        return PromptPolicy(policy_id=row['policy_id'], client_id=row['client_id'], capability=row['capability'], system_prompt=row['system_prompt'], style_rules=row['style_rules'], content_rules=row['content_rules'], is_active=bool(row['is_active']), updated_at=row['updated_at'])
