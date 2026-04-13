from __future__ import annotations

from app.schemas import ChatMessage, MemoryEntry, MemoryEntryUpsert
from app.services.memory_repository import MemoryRepository


class MemoryService:
    def __init__(self, repository: MemoryRepository | None = None) -> None:
        self.repository = repository or MemoryRepository()

    def list_entries(self, client_id: str) -> list[MemoryEntry]:
        return self.repository.list_entries(client_id)

    def upsert_entry(self, entry: MemoryEntryUpsert) -> MemoryEntry:
        return self.repository.upsert_entry(entry)

    def delete_entry(self, memory_id: str) -> bool:
        return self.repository.delete_entry(memory_id)

    def list_summaries(self, client_id: str) -> list:
        return self.repository.list_summaries(client_id)

    def retrieve_context(self, client_id: str, messages: list[ChatMessage], limit: int = 5) -> list[str]:
        query = ' '.join(message.content for message in messages if message.role == 'user')[:400]
        entries = self.repository.search_relevant(client_id, query, limit=limit)
        return [f"{entry.key}: {entry.value}" for entry in entries]

    def extract_from_text(self, client_id: str, text: str) -> list[MemoryEntry]:
        extracted: list[MemoryEntry] = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for index, line in enumerate(lines[:5]):
            lower = line.lower()
            entry: MemoryEntryUpsert | None = None
            if lower.startswith(('prefiero', 'prefer', 'siempre', 'nunca')):
                entry = MemoryEntryUpsert(client_id=client_id, type='preference', key=f'preference_{index + 1}', value=line, priority=90, confidence=0.9)
            elif 'proyecto' in lower or 'project' in lower:
                entry = MemoryEntryUpsert(client_id=client_id, type='project_context', key=f'project_{index + 1}', value=line, priority=80, confidence=0.85)
            elif len(line) > 20:
                entry = MemoryEntryUpsert(client_id=client_id, type='fact', key=f'fact_{index + 1}', value=line, priority=60, confidence=0.7)
            if entry is not None:
                extracted.append(self.repository.upsert_entry(entry))
        return extracted

    def process_interaction(self, client_id: str, user_text: str, assistant_text: str) -> None:
        self.extract_from_text(client_id, user_text)
        summary = f"User: {user_text[:240]} | Assistant: {assistant_text[:240]}"
        self.repository.save_summary(client_id, summary)
