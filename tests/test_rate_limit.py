from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services.rate_limiter import rate_limiter


def test_rate_limit_blocks_after_limit() -> None:
    get_settings.cache_clear()
    rate_limiter.reset()
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = 'secret-key'
    settings.rate_limit_requests = 1
    settings.rate_limit_window_seconds = 60

    first = client.get('/metrics', headers={'x-api-key': 'secret-key'})
    second = client.get('/metrics', headers={'x-api-key': 'secret-key'})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()['error']['code'] == 'http_error'


def test_rate_limit_allows_requests_under_limit() -> None:
    get_settings.cache_clear()
    rate_limiter.reset()
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = 'secret-key'
    settings.rate_limit_requests = 2
    settings.rate_limit_window_seconds = 60

    first = client.get('/metrics', headers={'x-api-key': 'secret-key'})
    second = client.get('/metrics', headers={'x-api-key': 'secret-key'})

    assert first.status_code == 200
    assert second.status_code == 200
