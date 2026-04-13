from app.schemas import MemoryEntryUpsert
from app.services.memory_repository import MemoryRepository


def test_memory_repository_crud_and_summary(tmp_path) -> None:
    db_path = str(tmp_path / 'gateway.db')
    repo = MemoryRepository(db_path)
    created = repo.upsert_entry(MemoryEntryUpsert(client_id='client-a', type='preference', key='language', value='es-CL', priority=90, confidence=0.95))
    assert repo.get_entry(created.memory_id) is not None
    listed = repo.list_entries('client-a')
    assert len(listed) == 1
    repo.save_summary('client-a', 'summary text')
    summaries = repo.list_summaries('client-a')
    assert len(summaries) == 1
    assert repo.delete_entry(created.memory_id) is True
    assert repo.get_entry(created.memory_id) is None
