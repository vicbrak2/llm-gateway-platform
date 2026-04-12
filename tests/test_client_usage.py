from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services.metrics import metrics_registry
from app.services.rate_limiter import rate_limiter


def test_multi_key_resolves_clients_and_tracks_usage() -> None:
    get_settings.cache_clear()
    rate_limiter.reset()
    metrics_registry.client_usage.clear()
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = None
    settings.gateway_api_keys = 'clientA:key-a,clientB:key-b'
    settings.rate_limit_requests = 10
    settings.rate_limit_window_seconds = 60

    r1 = client.get('/metrics', headers={'x-api-key': 'key-a'})
    r2 = client.get('/metrics', headers={'x-api-key': 'key-b'})
    r3 = client.get('/metrics', headers={'x-api-key': 'key-a'})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 200

    snapshot = client.get('/metrics', headers={'x-api-key': 'key-a'}).json()
    usage = {item['client_id']: item['requests_total'] for item in snapshot['client_usage']}
    assert usage['clientA'] >= 3
    assert usage['clientB'] >= 1


def test_invalid_multi_key_is_rejected() -> None:
    get_settings.cache_clear()
    rate_limiter.reset()
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = None
    settings.gateway_api_keys = 'clientA:key-a,clientB:key-b'

    response = client.get('/metrics', headers={'x-api-key': 'wrong'})
    assert response.status_code == 401
