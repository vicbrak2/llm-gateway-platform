from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def test_status_requires_api_key_when_configured() -> None:
    get_settings.cache_clear()
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = 'secret-key'
    response = client.get('/status')
    assert response.status_code == 401


def test_status_ok_with_valid_api_key() -> None:
    get_settings.cache_clear()
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = 'secret-key'
    response = client.get('/status', headers={'x-api-key': 'secret-key'})
    assert response.status_code == 200
    data = response.json()
    assert data['status'] in {'ok', 'degraded'}
    assert data['app']
    assert data['env']
    # /status must not leak internal provider/breaker details present on /health.
    assert 'providers' not in data
    assert 'breakers' not in data


def test_query_requires_api_key_when_configured() -> None:
    get_settings.cache_clear()
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = 'secret-key'
    response = client.post('/query', json={'question': 'hola'})
    assert response.status_code == 401


def test_query_allows_request_with_valid_api_key() -> None:
    get_settings.cache_clear()
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = 'secret-key'
    response = client.post('/query', headers={'x-api-key': 'secret-key'}, json={'question': 'hola'})
    # 500 is acceptable here: no real provider API keys are configured in tests,
    # so the orchestrator has nothing to call. What matters is auth passed (not 401).
    assert response.status_code in {200, 500}


def test_query_rejects_missing_question_field() -> None:
    get_settings.cache_clear()
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = 'secret-key'
    response = client.post('/query', headers={'x-api-key': 'secret-key'}, json={})
    assert response.status_code == 422


def test_cors_headers_present_on_status() -> None:
    get_settings.cache_clear()
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = None
    settings.gateway_api_keys = None
    response = client.get('/status', headers={'Origin': 'https://example.github.io'})
    assert response.headers.get('access-control-allow-origin') == '*'
