from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core.config import get_settings


class SQLiteStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or get_settings().sqlite_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS client_policies (
                    client_id TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL,
                    plan TEXT NOT NULL,
                    default_strategy TEXT NOT NULL,
                    allowed_strategies TEXT NOT NULL,
                    allowed_response_formats TEXT NOT NULL,
                    max_requests_per_minute INTEGER NOT NULL,
                    max_parallel_providers INTEGER NOT NULL,
                    allow_workflows INTEGER NOT NULL,
                    preferred_providers TEXT NOT NULL,
                    max_input_chars INTEGER NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS client_usage (
                    client_id TEXT PRIMARY KEY,
                    requests_total INTEGER NOT NULL
                )
                '''
            )
            count = conn.execute('SELECT COUNT(*) AS total FROM client_policies').fetchone()['total']
            if count == 0:
                conn.execute(
                    '''
                    INSERT INTO client_policies (
                        client_id, enabled, plan, default_strategy, allowed_strategies,
                        allowed_response_formats, max_requests_per_minute, max_parallel_providers,
                        allow_workflows, preferred_providers, max_input_chars
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    ('default', 1, 'starter', 'balanced', 'fast,balanced,quality', 'text,json_object', 60, 3, 1, '', 12000),
                )
            conn.commit()
