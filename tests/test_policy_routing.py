from app.core.config import Settings
from app.schemas import ChatMessage, ChatRequest, ProviderResult
from app.services.n8n import N8NClient
from app.services.orchestrator import OrchestratorService
from app.services.secrets import SecretResolver


class InMemoryCache:
    def make_key(self, payload: dict) -> str:
        return str(sorted(payload.items()))

    async def get(self, key: str):
        return None

    async def set(self, key: str, value: dict) -> None:
        return None


class FakeProvider:
    def __init__(self, name: str, latency_ms: int = 10) -> None:
        self.config = type('Cfg', (), {'name': name, 'timeout_seconds': latency_ms / 1000, 'priority': 1})()
        self._latency_ms = latency_ms

    async def chat(self, messages, temperature, max_tokens):
        return ProviderResult(provider=self.config.name, model='m', content=self.config.name, latency_ms=self._latency_ms, success=True)


class TestOrchestrator(OrchestratorService):
    def __init__(self, providers):
        settings = Settings(groq_enabled=False, openrouter_enabled=False, huggingface_enabled=False, n8n_base_url=None, max_parallel_providers=3)
        super().__init__(settings, InMemoryCache(), N8NClient(None, None), SecretResolver())
        self._providers = providers

    def _build_providers(self, runtime_policy=None):
        providers = self._providers
        preferred = (runtime_policy or {}).get('preferred_providers') or []
        if preferred:
            providers = [provider for provider in providers if provider.config.name in preferred]
        return providers


def test_runtime_policy_filters_preferred_providers() -> None:
    orchestrator = TestOrchestrator([FakeProvider('groq'), FakeProvider('openrouter')])
    request = ChatRequest(messages=[ChatMessage(role='user', content='hello')], strategy='balanced')
    selected = orchestrator._select_providers(orchestrator._build_providers({'preferred_providers': ['openrouter']}), request, {'max_parallel_providers': 2})
    assert [provider.config.name for provider in selected] == ['openrouter']


def test_runtime_policy_limits_parallel_providers() -> None:
    orchestrator = TestOrchestrator([FakeProvider('groq'), FakeProvider('openrouter'), FakeProvider('huggingface')])
    request = ChatRequest(messages=[ChatMessage(role='user', content='hello')], strategy='quality')
    selected = orchestrator._select_providers(orchestrator._build_providers({}), request, {'max_parallel_providers': 1})
    assert len(selected) == 1
