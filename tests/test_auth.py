from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def test_chat_requires_api_key_when_configured() -> None:
    get_settings.cache_clear()
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = 'secret-key'
    response = client.post('/v1/chat/completions', json={'messages': [{'role': 'user', 'content': 'hello'}]})
    assert response.status_code == 401
    data = response.json()
    assert data['error']['code'] == 'http_error'


def test_chat_allows_request_with_valid_api_key() -> None:
    get_settings.cache_clear()
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = 'secret-key'
    response = client.post('/v1/chat/completions', headers={'x-api-key': 'secret-key'}, json={'messages': [{'role': 'user', 'content': 'hello'}]})
    assert response.status_code in {200, 500}
