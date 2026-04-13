from app.services.memory_repository import MemoryRepository
from app.services.memory_service import MemoryService
from app.schemas import ChatMessage


def test_memory_service_extracts_and_retrieves_context(tmp_path) -> None:
    db_path = str(tmp_path / 'gateway.db')
    service = MemoryService(MemoryRepository(db_path))
    extracted = service.extract_from_text('client-a', 'Prefiero respuestas en español.\nMi proyecto es un gateway LLM.')
    assert len(extracted) >= 2
    context = service.retrieve_context('client-a', [ChatMessage(role='user', content='recuérdame mi proyecto')])
    assert len(context) >= 1
    service.process_interaction('client-a', 'hola', 'respuesta')
    summaries = service.list_summaries('client-a')
    assert len(summaries) >= 1
