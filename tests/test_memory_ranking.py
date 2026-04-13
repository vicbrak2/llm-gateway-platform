from app.schemas import ChatMessage, MemoryEntryUpsert
from app.services.memory_repository import MemoryRepository
from app.services.memory_service import MemoryService


def test_memory_consolidates_duplicate_keys(tmp_path) -> None:
    db_path = str(tmp_path / 'gateway.db')
    repo = MemoryRepository(db_path)
    first = repo.upsert_entry(MemoryEntryUpsert(client_id='client-a', user_id='user-1', type='preference', key='preference', value='Prefiero español', priority=90, confidence=0.9))
    second = repo.upsert_entry(MemoryEntryUpsert(client_id='client-a', user_id='user-1', type='preference', key='preference', value='Prefiero respuestas breves', priority=95, confidence=0.95))
    entries = repo.list_entries('client-a', user_id='user-1')
    assert len(entries) == 1
    assert first.memory_id == second.memory_id
    assert 'Prefiero español' in entries[0].value
    assert 'Prefiero respuestas breves' in entries[0].value


def test_memory_ranking_prefers_relevant_entries(tmp_path) -> None:
    db_path = str(tmp_path / 'gateway.db')
    service = MemoryService(MemoryRepository(db_path))
    service.upsert_entry(MemoryEntryUpsert(client_id='client-a', user_id='user-1', type='project_context', key='project_context', value='Mi proyecto usa gateway LLM y billing', priority=80, confidence=0.8))
    service.upsert_entry(MemoryEntryUpsert(client_id='client-a', user_id='user-1', type='fact', key='other', value='Me gusta el café', priority=95, confidence=0.95))
    context = service.retrieve_context('client-a', [ChatMessage(role='user', content='háblame de mi proyecto billing gateway')], user_id='user-1', limit=1)
    assert len(context) == 1
    assert 'gateway LLM y billing' in context[0]
