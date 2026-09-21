from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services.rate_limiter import rate_limiter


def test_multi_key_resolves_clients_and_tracks_usage() -> None:
    # Usage is persisted in sqlite (UsageRepository), not an in-memory dict on
    # metrics_registry, so it is not reset between test runs/processes. Assert on
    # the *increase* around a baseline snapshot instead of an absolute count.
    get_settings.cache_clear()
    rate_limiter.reset()
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = None
    settings.gateway_api_keys = 'clientA:key-a,clientB:key-b'
    settings.rate_limit_requests = 10
    settings.rate_limit_window_seconds = 60

    def usage_map() -> dict[str, int]:
        snapshot = client.get('/metrics', headers={'x-api-key': 'key-a'}).json()
        return {item['client_id']: item['requests_total'] for item in snapshot['client_usage']}

    before = usage_map()  # this call itself counts as +1 for clientA

    r1 = client.get('/metrics', headers={'x-api-key': 'key-a'})
    r2 = client.get('/metrics', headers={'x-api-key': 'key-b'})
    r3 = client.get('/metrics', headers={'x-api-key': 'key-a'})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 200

    after = usage_map()  # this call itself also counts as +1 for clientA

    # r1, r3, and the trailing `after` snapshot call = 3 clientA requests.
    assert after.get('clientA', 0) - before.get('clientA', 0) >= 3
    # r2 = 1 clientB request.
    assert after.get('clientB', 0) - before.get('clientB', 0) >= 1


def test_invalid_multi_key_is_rejected() -> None:
    get_settings.cache_clear()
    rate_limiter.reset()
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = None
    settings.gateway_api_keys = 'clientA:key-a,clientB:key-b'

    response = client.get('/metrics', headers={'x-api-key': 'wrong'})
    assert response.status_code == 401
