from app.schemas import MemoryEntryUpsert
from app.services.memory_repository import MemoryRepository
from app.services.memory_service import MemoryService
from app.schemas import ChatMessage


def test_memory_user_scope_separates_entries(tmp_path) -> None:
    db_path = str(tmp_path / 'gateway.db')
    repo = MemoryRepository(db_path)
    service = MemoryService(repo)
    repo.upsert_entry(MemoryEntryUpsert(client_id='client-a', user_id='user-1', type='preference', key='lang', value='es', priority=90, confidence=0.9))
    repo.upsert_entry(MemoryEntryUpsert(client_id='client-a', user_id='user-2', type='preference', key='lang', value='en', priority=90, confidence=0.9))
    repo.upsert_entry(MemoryEntryUpsert(client_id='client-a', user_id=None, type='fact', key='tenant', value='shared', priority=50, confidence=0.8))

    user1 = service.retrieve_context('client-a', [ChatMessage(role='user', content='idioma')], user_id='user-1')
    user2 = service.retrieve_context('client-a', [ChatMessage(role='user', content='idioma')], user_id='user-2')

    assert any('es' in item for item in user1)
    assert any('en' in item for item in user2)
    assert any('shared' in item for item in user1)
    assert any('shared' in item for item in user2)


def test_memory_summaries_user_scope(tmp_path) -> None:
    db_path = str(tmp_path / 'gateway.db')
    repo = MemoryRepository(db_path)
    repo.save_summary('client-a', 'summary user1', user_id='user-1')
    repo.save_summary('client-a', 'summary shared', user_id=None)
    user1 = repo.list_summaries('client-a', user_id='user-1')
    assert len(user1) == 2
