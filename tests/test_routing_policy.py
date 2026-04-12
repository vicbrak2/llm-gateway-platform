from app.schemas import ChatMessage, ChatRequest
from app.services.routing_policy import RoutingPolicy


class DummyProvider:
    def __init__(self, name: str, timeout_seconds: float, priority: int) -> None:
        self.config = type('Cfg', (), {'name': name, 'timeout_seconds': timeout_seconds, 'priority': priority})()


def make_request(strategy: str, content: str = 'hello') -> ChatRequest:
    return ChatRequest(messages=[ChatMessage(role='user', content=content)], strategy=strategy)


def test_fast_prefers_low_timeout_and_limits_parallelism() -> None:
    policy = RoutingPolicy(max_parallel_providers=3, complexity_threshold=80)
    providers = [DummyProvider('slow', 5.0, 2), DummyProvider('fastest', 1.0, 3), DummyProvider('fast', 2.0, 1)]
    selected = policy.select_providers(providers, make_request('fast'))
    assert [p.config.name for p in selected] == ['fastest', 'fast']


def test_quality_prefers_higher_timeout_profiles() -> None:
    policy = RoutingPolicy(max_parallel_providers=3, complexity_threshold=80)
    providers = [DummyProvider('p1', 1.0, 1), DummyProvider('p2', 6.0, 3), DummyProvider('p3', 3.0, 2)]
    selected = policy.select_providers(providers, make_request('quality'))
    assert [p.config.name for p in selected] == ['p2', 'p3', 'p1']


def test_balanced_switches_for_complex_requests() -> None:
    policy = RoutingPolicy(max_parallel_providers=3, complexity_threshold=10)
    providers = [DummyProvider('p1', 1.0, 1), DummyProvider('p2', 6.0, 2), DummyProvider('p3', 3.0, 3)]
    selected = policy.select_providers(providers, make_request('balanced', content='x' * 20))
    assert [p.config.name for p in selected] == ['p2', 'p3', 'p1']
