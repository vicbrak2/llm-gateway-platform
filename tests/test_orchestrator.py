import asyncio

from app.core.config import Settings
from app.schemas import ChatMessage, ChatRequest, ProviderResult
from app.services.n8n import N8NClient
from app.services.orchestrator import OrchestratorService
from app.services.secrets import SecretResolver


class InMemoryCache:
    def __init__(self) -> None:
        self.storage: dict[str, dict] = {}

    def make_key(self, payload: dict) -> str:
        return str(sorted(payload.items()))

    async def get(self, key: str):
        return self.storage.get(key)

    async def set(self, key: str, value: dict) -> None:
        self.storage[key] = value


class FakeProvider:
    def __init__(self, result: ProviderResult, delay_seconds: float = 0.0) -> None:
        self.result = result
        self.delay_seconds = delay_seconds
        self.calls = 0
        self.config = type('Cfg', (), {'timeout_seconds': 1.0, 'priority': 1, 'name': result.provider})()

    async def chat(self, messages, temperature, max_tokens):
        self.calls += 1
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        return self.result


class TestOrchestrator(OrchestratorService):
    def __init__(self, settings, cache, n8n_client, secret_resolver, providers):
        super().__init__(settings, cache, n8n_client, secret_resolver)
        self._providers = providers

    def _build_providers(self):
        return self._providers


def make_request(strategy: str = 'balanced') -> ChatRequest:
    return ChatRequest(messages=[ChatMessage(role='user', content='hello')], strategy=strategy, temperature=0.1, max_tokens=50)


def make_settings() -> Settings:
    return Settings(groq_enabled=False, openrouter_enabled=False, huggingface_enabled=False, n8n_base_url=None, max_parallel_providers=3)


def test_fast_strategy_waits_for_first_success() -> None:
    failure = FakeProvider(ProviderResult(provider='p1', model='m1', content='', latency_ms=10, success=False, error='boom'), delay_seconds=0.01)
    success = FakeProvider(ProviderResult(provider='p2', model='m2', content='ok', latency_ms=20, success=True), delay_seconds=0.02)
    orchestrator = TestOrchestrator(make_settings(), InMemoryCache(), N8NClient(None, None), SecretResolver(), [failure, success])
    response = asyncio.run(orchestrator.run(make_request(strategy='fast'), 'trace-1'))
    assert response.content == 'ok'
    assert response.winner == 'p2'
    assert len(response.provider_results) == 2


def test_response_is_cached_between_identical_requests() -> None:
    provider = FakeProvider(ProviderResult(provider='p-cache', model='m-cache', content='cached', latency_ms=5, success=True))
    orchestrator = TestOrchestrator(make_settings(), InMemoryCache(), N8NClient(None, None), SecretResolver(), [provider])
    first = asyncio.run(orchestrator.run(make_request(), 'trace-1'))
    second = asyncio.run(orchestrator.run(make_request(), 'trace-1'))
    assert first.content == 'cached'
    assert second.content == 'cached'
    assert provider.calls == 1
