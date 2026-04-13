from __future__ import annotations

from app.schemas import ChatMessage, MemoryEntry, MemoryEntryUpsert
from app.services.memory_repository import MemoryRepository


class MemoryService:
    def __init__(self, repository: MemoryRepository | None = None) -> None:
        self.repository = repository or MemoryRepository()

    def list_entries(self, client_id: str, user_id: str | None = None) -> list[MemoryEntry]:
        return self.repository.list_entries(client_id, user_id=user_id)

    def upsert_entry(self, entry: MemoryEntryUpsert) -> MemoryEntry:
        return self.repository.upsert_entry(entry)

    def delete_entry(self, memory_id: str) -> bool:
        return self.repository.delete_entry(memory_id)

    def list_summaries(self, client_id: str, user_id: str | None = None) -> list:
        return self.repository.list_summaries(client_id, user_id=user_id)

    def retrieve_context(self, client_id: str, messages: list[ChatMessage], user_id: str | None = None, limit: int = 5) -> list[str]:
        query = ' '.join(message.content for message in messages if message.role == 'user')[:400]
        entries = self.repository.search_relevant(client_id, query, user_id=user_id, limit=limit * 3)
        ranked = self._rank_entries(entries, query)
        return [f"{entry.key}: {entry.value}" for entry in ranked[:limit]]

    def extract_from_text(self, client_id: str, text: str, user_id: str | None = None) -> list[MemoryEntry]:
        extracted: list[MemoryEntry] = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for index, line in enumerate(lines[:5]):
            lower = line.lower()
            entry: MemoryEntryUpsert | None = None
            if lower.startswith(('prefiero', 'prefer', 'siempre', 'nunca')):
                entry = MemoryEntryUpsert(client_id=client_id, user_id=user_id, type='preference', key='preference', value=line, priority=90, confidence=0.9)
            elif 'proyecto' in lower or 'project' in lower:
                entry = MemoryEntryUpsert(client_id=client_id, user_id=user_id, type='project_context', key='project_context', value=line, priority=80, confidence=0.85)
            elif len(line) > 20:
                entry = MemoryEntryUpsert(client_id=client_id, user_id=user_id, type='fact', key=f'fact_{index + 1}', value=line, priority=60, confidence=0.7)
            if entry is not None:
                extracted.append(self.repository.upsert_entry(entry))
        return extracted

    def process_interaction(self, client_id: str, user_text: str, assistant_text: str, user_id: str | None = None) -> None:
        self.extract_from_text(client_id, user_text, user_id=user_id)
        summary = f"User: {user_text[:240]} | Assistant: {assistant_text[:240]}"
        self.repository.save_summary(client_id, summary, user_id=user_id)

    def _rank_entries(self, entries: list[MemoryEntry], query: str) -> list[MemoryEntry]:
        query_terms = {term for term in query.lower().split() if len(term) > 2}

        def score(entry: MemoryEntry) -> tuple[int, int, float, str]:
            haystack = f'{entry.key} {entry.value}'.lower()
            overlap = sum(1 for term in query_terms if term in haystack)
            return (overlap, entry.priority, entry.confidence, entry.updated_at)

        deduped: dict[tuple[str, str | None, str, str], MemoryEntry] = {}
        for entry in entries:
            deduped[(entry.client_id, entry.user_id, entry.type, entry.key)] = entry
        return sorted(deduped.values(), key=score, reverse=True)
