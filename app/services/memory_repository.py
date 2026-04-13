from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.schemas import ConversationSummary, MemoryEntry, MemoryEntryUpsert
from app.services.sqlite_store import SQLiteStore


class MemoryRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.store = SQLiteStore(db_path)

    def list_entries(self, client_id: str) -> list[MemoryEntry]:
        with self.store.connect() as conn:
            rows = conn.execute('SELECT * FROM memory_entries WHERE client_id = ? ORDER BY priority DESC, updated_at DESC', (client_id,)).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def get_entry(self, memory_id: str) -> MemoryEntry | None:
        with self.store.connect() as conn:
            row = conn.execute('SELECT * FROM memory_entries WHERE memory_id = ?', (memory_id,)).fetchone()
        return self._row_to_entry(row) if row else None

    def upsert_entry(self, entry: MemoryEntryUpsert) -> MemoryEntry:
        memory_id = entry.memory_id or uuid.uuid4().hex
        updated_at = datetime.now(timezone.utc).isoformat()
        with self.store.connect() as conn:
            conn.execute(
                '''
                INSERT INTO memory_entries (memory_id, client_id, type, key, value, priority, confidence, is_active, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(memory_id) DO UPDATE SET
                    client_id=excluded.client_id,
                    type=excluded.type,
                    key=excluded.key,
                    value=excluded.value,
                    priority=excluded.priority,
                    confidence=excluded.confidence,
                    is_active=excluded.is_active,
                    updated_at=excluded.updated_at
                ''',
                (memory_id, entry.client_id, entry.type, entry.key, entry.value, entry.priority, entry.confidence, 1 if entry.is_active else 0, updated_at),
            )
            conn.commit()
        return MemoryEntry(memory_id=memory_id, client_id=entry.client_id, type=entry.type, key=entry.key, value=entry.value, priority=entry.priority, confidence=entry.confidence, is_active=entry.is_active, updated_at=updated_at)

    def delete_entry(self, memory_id: str) -> bool:
        with self.store.connect() as conn:
            result = conn.execute('DELETE FROM memory_entries WHERE memory_id = ?', (memory_id,))
            conn.commit()
        return result.rowcount > 0

    def search_relevant(self, client_id: str, query: str, limit: int = 5) -> list[MemoryEntry]:
        pattern = f'%{query[:120]}%'
        with self.store.connect() as conn:
            rows = conn.execute(
                '''
                SELECT * FROM memory_entries
                WHERE client_id = ? AND is_active = 1 AND (key LIKE ? OR value LIKE ?)
                ORDER BY priority DESC, updated_at DESC
                LIMIT ?
                ''',
                (client_id, pattern, pattern, limit),
            ).fetchall()
            if not rows:
                rows = conn.execute(
                    'SELECT * FROM memory_entries WHERE client_id = ? AND is_active = 1 ORDER BY priority DESC, updated_at DESC LIMIT ?',
                    (client_id, limit),
                ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def save_summary(self, client_id: str, summary: str) -> ConversationSummary:
        summary_id = uuid.uuid4().hex
        updated_at = datetime.now(timezone.utc).isoformat()
        with self.store.connect() as conn:
            conn.execute(
                'INSERT INTO conversation_summaries (summary_id, client_id, summary, updated_at) VALUES (?, ?, ?, ?)',
                (summary_id, client_id, summary, updated_at),
            )
            conn.commit()
        return ConversationSummary(summary_id=summary_id, client_id=client_id, summary=summary, updated_at=updated_at)

    def list_summaries(self, client_id: str, limit: int = 20) -> list[ConversationSummary]:
        with self.store.connect() as conn:
            rows = conn.execute(
                'SELECT * FROM conversation_summaries WHERE client_id = ? ORDER BY updated_at DESC LIMIT ?',
                (client_id, limit),
            ).fetchall()
        return [ConversationSummary(summary_id=row['summary_id'], client_id=row['client_id'], summary=row['summary'], updated_at=row['updated_at']) for row in rows]

    @staticmethod
    def _row_to_entry(row) -> MemoryEntry:
        return MemoryEntry(memory_id=row['memory_id'], client_id=row['client_id'], type=row['type'], key=row['key'], value=row['value'], priority=row['priority'], confidence=row['confidence'], is_active=bool(row['is_active']), updated_at=row['updated_at'])
