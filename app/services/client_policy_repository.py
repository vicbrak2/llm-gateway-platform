from __future__ import annotations

from app.schemas import ClientPolicy
from app.services.sqlite_store import SQLiteStore


class ClientPolicyRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.store = SQLiteStore(db_path)

    def list_policies(self) -> list[ClientPolicy]:
        with self.store.connect() as conn:
            rows = conn.execute('SELECT * FROM client_policies ORDER BY client_id').fetchall()
        return [self._row_to_policy(row) for row in rows]

    def get_policy(self, client_id: str) -> ClientPolicy | None:
        with self.store.connect() as conn:
            row = conn.execute('SELECT * FROM client_policies WHERE client_id = ?', (client_id,)).fetchone()
        return self._row_to_policy(row) if row else None

    def upsert_policy(self, policy: ClientPolicy) -> ClientPolicy:
        with self.store.connect() as conn:
            conn.execute(
                '''
                INSERT INTO client_policies (
                    client_id, enabled, plan, default_strategy, allowed_strategies,
                    allowed_response_formats, allowed_capabilities, max_requests_per_minute, max_parallel_providers,
                    allow_workflows, preferred_providers, max_input_chars
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(client_id) DO UPDATE SET
                    enabled=excluded.enabled,
                    plan=excluded.plan,
                    default_strategy=excluded.default_strategy,
                    allowed_strategies=excluded.allowed_strategies,
                    allowed_response_formats=excluded.allowed_response_formats,
                    allowed_capabilities=excluded.allowed_capabilities,
                    max_requests_per_minute=excluded.max_requests_per_minute,
                    max_parallel_providers=excluded.max_parallel_providers,
                    allow_workflows=excluded.allow_workflows,
                    preferred_providers=excluded.preferred_providers,
                    max_input_chars=excluded.max_input_chars
                ''',
                (
                    policy.client_id,
                    1 if policy.enabled else 0,
                    policy.plan,
                    policy.default_strategy,
                    ','.join(policy.allowed_strategies),
                    ','.join(policy.allowed_response_formats),
                    ','.join(policy.allowed_capabilities),
                    policy.max_requests_per_minute,
                    policy.max_parallel_providers,
                    1 if policy.allow_workflows else 0,
                    ','.join(policy.preferred_providers),
                    policy.max_input_chars,
                ),
            )
            conn.commit()
        return policy

    @staticmethod
    def _row_to_policy(row) -> ClientPolicy:
        return ClientPolicy(
            client_id=row['client_id'],
            enabled=bool(row['enabled']),
            plan=row['plan'],
            default_strategy=row['default_strategy'],
            allowed_strategies=[item for item in row['allowed_strategies'].split(',') if item],
            allowed_response_formats=[item for item in row['allowed_response_formats'].split(',') if item],
            allowed_capabilities=[item for item in row['allowed_capabilities'].split(',') if item],
            max_requests_per_minute=row['max_requests_per_minute'],
            max_parallel_providers=row['max_parallel_providers'],
            allow_workflows=bool(row['allow_workflows']),
            preferred_providers=[item for item in row['preferred_providers'].split(',') if item],
            max_input_chars=row['max_input_chars'],
        )
