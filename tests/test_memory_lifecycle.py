from datetime import datetime, timedelta, timezone

from app.schemas import MemoryEntryUpsert
from app.services.memory_repository import MemoryRepository
from app.services.memory_service import MemoryService
from app.schemas import ChatMessage


def test_memory_archive_and_prune_expired(tmp_path) -> None:
    db_path = str(tmp_path / 'gateway.db')
    repo = MemoryRepository(db_path)
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    entry = repo.upsert_entry(MemoryEntryUpsert(client_id='client-a', user_id='user-1', type='fact', key='temp', value='temporary memory', expires_at=past))
    archived, deleted = repo.prune_expired()
    fetched = repo.get_entry(entry.memory_id)
    assert archived == 1
    assert deleted == 0
    assert fetched is not None
    assert fetched.archived_at is not None


def test_memory_retrieval_excludes_archived_and_expired(tmp_path) -> None:
    db_path = str(tmp_path / 'gateway.db')
    service = MemoryService(MemoryRepository(db_path))
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    active = service.upsert_entry(MemoryEntryUpsert(client_id='client-a', user_id='user-1', type='fact', key='active', value='still valid'))
    expired = service.upsert_entry(MemoryEntryUpsert(client_id='client-a', user_id='user-1', type='fact', key='expired', value='old', expires_at=past))
    service.archive_entry(expired.memory_id)
    context = service.retrieve_context('client-a', [ChatMessage(role='user', content='valid')], user_id='user-1', limit=5)
    assert any('still valid' in item for item in context)
    assert all('old' not in item for item in context)
