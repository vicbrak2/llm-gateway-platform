from app.schemas import ProviderResult
from app.services.response_ranker import ResponseRanker


def test_choose_winner_prefers_successful_response() -> None:
    ranker = ResponseRanker()
    results = [
        ProviderResult(provider='a', model='m', content='', latency_ms=5, success=False, error='boom'),
        ProviderResult(provider='b', model='m', content='ok', latency_ms=20, success=True),
    ]
    winner = ranker.choose_winner(results)
    assert winner is not None
    assert winner.provider == 'b'


def test_merge_contents_orders_by_rank() -> None:
    ranker = ResponseRanker()
    results = [
        ProviderResult(provider='slow', model='m', content='second', latency_ms=20, success=True),
        ProviderResult(provider='fast', model='m', content='first', latency_ms=10, success=True),
    ]
    merged = ranker.merge_contents(results)
    assert merged.startswith('[fast]')
    assert '[slow]' in merged
