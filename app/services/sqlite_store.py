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
                    allowed_capabilities TEXT NOT NULL DEFAULT 'summarize,extract,generate_json,route_workflow',
                    max_requests_per_minute INTEGER NOT NULL,
                    max_parallel_providers INTEGER NOT NULL,
                    allow_workflows INTEGER NOT NULL,
                    preferred_providers TEXT NOT NULL,
                    max_input_chars INTEGER NOT NULL
                )
                '''
            )
            columns = [row['name'] for row in conn.execute("PRAGMA table_info(client_policies)").fetchall()]
            if 'allowed_capabilities' not in columns:
                conn.execute("ALTER TABLE client_policies ADD COLUMN allowed_capabilities TEXT NOT NULL DEFAULT 'summarize,extract,generate_json,route_workflow'")
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS client_usage (
                    client_id TEXT PRIMARY KEY,
                    requests_total INTEGER NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS client_usage_capability (
                    client_id TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    requests_total INTEGER NOT NULL,
                    PRIMARY KEY (client_id, capability)
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS client_usage_daily (
                    client_id TEXT NOT NULL,
                    usage_date TEXT NOT NULL,
                    requests_total INTEGER NOT NULL,
                    PRIMARY KEY (client_id, usage_date)
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS gateway_api_keys (
                    key_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    api_key TEXT NOT NULL UNIQUE,
                    enabled INTEGER NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS memory_entries (
                    memory_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    user_id TEXT,
                    type TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    is_active INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            memory_columns = [row['name'] for row in conn.execute("PRAGMA table_info(memory_entries)").fetchall()]
            if 'user_id' not in memory_columns:
                conn.execute("ALTER TABLE memory_entries ADD COLUMN user_id TEXT")
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    summary_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    user_id TEXT,
                    summary TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            summary_columns = [row['name'] for row in conn.execute("PRAGMA table_info(conversation_summaries)").fetchall()]
            if 'user_id' not in summary_columns:
                conn.execute("ALTER TABLE conversation_summaries ADD COLUMN user_id TEXT")
            count = conn.execute('SELECT COUNT(*) AS total FROM client_policies').fetchone()['total']
            if count == 0:
                conn.execute(
                    '''
                    INSERT INTO client_policies (
                        client_id, enabled, plan, default_strategy, allowed_strategies,
                        allowed_response_formats, allowed_capabilities, max_requests_per_minute, max_parallel_providers,
                        allow_workflows, preferred_providers, max_input_chars
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    ('default', 1, 'starter', 'balanced', 'fast,balanced,quality', 'text,json_object', 'summarize,extract,generate_json,route_workflow', 60, 3, 1, '', 12000),
                )
            conn.commit()
