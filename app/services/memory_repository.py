from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.schemas import ConversationSummary, MemoryEntry, MemoryEntryUpsert
from app.services.sqlite_store import SQLiteStore


class MemoryRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.store = SQLiteStore(db_path)

    def list_entries(self, client_id: str, user_id: str | None = None, include_archived: bool = False) -> list[MemoryEntry]:
        archived_clause = '' if include_archived else ' AND archived_at IS NULL'
        with self.store.connect() as conn:
            if user_id:
                rows = conn.execute(f'SELECT * FROM memory_entries WHERE client_id = ? AND (user_id = ? OR user_id IS NULL){archived_clause} ORDER BY priority DESC, updated_at DESC', (client_id, user_id)).fetchall()
            else:
                rows = conn.execute(f'SELECT * FROM memory_entries WHERE client_id = ?{archived_clause} ORDER BY priority DESC, updated_at DESC', (client_id,)).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def get_entry(self, memory_id: str) -> MemoryEntry | None:
        with self.store.connect() as conn:
            row = conn.execute('SELECT * FROM memory_entries WHERE memory_id = ?', (memory_id,)).fetchone()
        return self._row_to_entry(row) if row else None

    def find_duplicate(self, client_id: str, user_id: str | None, entry_type: str, key: str) -> MemoryEntry | None:
        with self.store.connect() as conn:
            if user_id is None:
                row = conn.execute(
                    'SELECT * FROM memory_entries WHERE client_id = ? AND user_id IS NULL AND type = ? AND key = ? AND archived_at IS NULL LIMIT 1',
                    (client_id, entry_type, key),
                ).fetchone()
            else:
                row = conn.execute(
                    'SELECT * FROM memory_entries WHERE client_id = ? AND user_id = ? AND type = ? AND key = ? AND archived_at IS NULL LIMIT 1',
                    (client_id, user_id, entry_type, key),
                ).fetchone()
        return self._row_to_entry(row) if row else None

    def upsert_entry(self, entry: MemoryEntryUpsert) -> MemoryEntry:
        duplicate = self.find_duplicate(entry.client_id, entry.user_id, entry.type, entry.key)
        memory_id = entry.memory_id or (duplicate.memory_id if duplicate else uuid.uuid4().hex)
        updated_at = datetime.now(timezone.utc).isoformat()
        value = entry.value
        if duplicate and duplicate.value.strip() != entry.value.strip() and entry.value.strip() not in duplicate.value:
            value = f'{duplicate.value} | {entry.value}'
        with self.store.connect() as conn:
            conn.execute(
                '''
                INSERT INTO memory_entries (memory_id, client_id, user_id, type, key, value, priority, confidence, is_active, updated_at, expires_at, archived_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(memory_id) DO UPDATE SET
                    client_id=excluded.client_id,
                    user_id=excluded.user_id,
                    type=excluded.type,
                    key=excluded.key,
                    value=excluded.value,
                    priority=excluded.priority,
                    confidence=excluded.confidence,
                    is_active=excluded.is_active,
                    updated_at=excluded.updated_at,
                    expires_at=excluded.expires_at,
                    archived_at=excluded.archived_at
                ''',
                (memory_id, entry.client_id, entry.user_id, entry.type, entry.key, value, entry.priority, entry.confidence, 1 if entry.is_active else 0, updated_at, entry.expires_at, None),
            )
            conn.commit()
        return MemoryEntry(memory_id=memory_id, client_id=entry.client_id, user_id=entry.user_id, type=entry.type, key=entry.key, value=value, priority=entry.priority, confidence=entry.confidence, is_active=entry.is_active, updated_at=updated_at, expires_at=entry.expires_at, archived_at=None)

    def archive_entry(self, memory_id: str) -> bool:
        archived_at = datetime.now(timezone.utc).isoformat()
        with self.store.connect() as conn:
            result = conn.execute('UPDATE memory_entries SET archived_at = ?, is_active = 0 WHERE memory_id = ? AND archived_at IS NULL', (archived_at, memory_id))
            conn.commit()
        return result.rowcount > 0

    def delete_entry(self, memory_id: str) -> bool:
        with self.store.connect() as conn:
            result = conn.execute('DELETE FROM memory_entries WHERE memory_id = ?', (memory_id,))
            conn.commit()
        return result.rowcount > 0

    def prune_expired(self) -> tuple[int, int]:
        now = datetime.now(timezone.utc).isoformat()
        with self.store.connect() as conn:
            archived = conn.execute('UPDATE memory_entries SET archived_at = ?, is_active = 0 WHERE expires_at IS NOT NULL AND expires_at <= ? AND archived_at IS NULL', (now, now)).rowcount
            deleted = conn.execute('DELETE FROM memory_entries WHERE archived_at IS NOT NULL AND archived_at <= datetime(?, \'-30 days\')', (now,)).rowcount
            conn.commit()
        return archived, deleted

    def search_relevant(self, client_id: str, query: str, user_id: str | None = None, limit: int = 5) -> list[MemoryEntry]:
        pattern = f'%{query[:120]}%'
        now = datetime.now(timezone.utc).isoformat()
        with self.store.connect() as conn:
            if user_id:
                rows = conn.execute(
                    '''
                    SELECT * FROM memory_entries
                    WHERE client_id = ? AND (user_id = ? OR user_id IS NULL) AND is_active = 1 AND archived_at IS NULL AND (expires_at IS NULL OR expires_at > ?) AND (key LIKE ? OR value LIKE ?)
                    ORDER BY priority DESC, updated_at DESC
                    LIMIT 50
                    ''',
                    (client_id, user_id, now, pattern, pattern),
                ).fetchall()
                if not rows:
                    rows = conn.execute(
                        'SELECT * FROM memory_entries WHERE client_id = ? AND (user_id = ? OR user_id IS NULL) AND is_active = 1 AND archived_at IS NULL AND (expires_at IS NULL OR expires_at > ?) ORDER BY priority DESC, updated_at DESC LIMIT 50',
                        (client_id, user_id, now),
                    ).fetchall()
            else:
                rows = conn.execute(
                    '''
                    SELECT * FROM memory_entries
                    WHERE client_id = ? AND is_active = 1 AND archived_at IS NULL AND (expires_at IS NULL OR expires_at > ?) AND (key LIKE ? OR value LIKE ?)
                    ORDER BY priority DESC, updated_at DESC
                    LIMIT 50
                    ''',
                    (client_id, now, pattern, pattern),
                ).fetchall()
                if not rows:
                    rows = conn.execute(
                        'SELECT * FROM memory_entries WHERE client_id = ? AND is_active = 1 AND archived_at IS NULL AND (expires_at IS NULL OR expires_at > ?) ORDER BY priority DESC, updated_at DESC LIMIT 50',
                        (client_id, now),
                    ).fetchall()
        return [self._row_to_entry(row) for row in rows[:limit]]

    def save_summary(self, client_id: str, summary: str, user_id: str | None = None) -> ConversationSummary:
        summary_id = uuid.uuid4().hex
        updated_at = datetime.now(timezone.utc).isoformat()
        with self.store.connect() as conn:
            conn.execute(
                'INSERT INTO conversation_summaries (summary_id, client_id, user_id, summary, updated_at) VALUES (?, ?, ?, ?, ?)',
                (summary_id, client_id, user_id, summary, updated_at),
            )
            conn.commit()
        return ConversationSummary(summary_id=summary_id, client_id=client_id, user_id=user_id, summary=summary, updated_at=updated_at)

    def list_summaries(self, client_id: str, user_id: str | None = None, limit: int = 20) -> list[ConversationSummary]:
        with self.store.connect() as conn:
            if user_id:
                rows = conn.execute(
                    'SELECT * FROM conversation_summaries WHERE client_id = ? AND (user_id = ? OR user_id IS NULL) ORDER BY updated_at DESC LIMIT ?',
                    (client_id, user_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    'SELECT * FROM conversation_summaries WHERE client_id = ? ORDER BY updated_at DESC LIMIT ?',
                    (client_id, limit),
                ).fetchall()
        return [ConversationSummary(summary_id=row['summary_id'], client_id=row['client_id'], user_id=row['user_id'], summary=row['summary'], updated_at=row['updated_at']) for row in rows]

    @staticmethod
    def _row_to_entry(row) -> MemoryEntry:
        return MemoryEntry(memory_id=row['memory_id'], client_id=row['client_id'], user_id=row['user_id'], type=row['type'], key=row['key'], value=row['value'], priority=row['priority'], confidence=row['confidence'], is_active=bool(row['is_active']), updated_at=row['updated_at'], expires_at=row['expires_at'], archived_at=row['archived_at'])
