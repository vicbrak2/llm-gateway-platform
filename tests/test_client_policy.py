from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services.client_policy_repository import ClientPolicyRepository
from app.services.rate_limiter import rate_limiter


def test_client_policy_blocks_disallowed_strategy() -> None:
    get_settings.cache_clear()
    rate_limiter.reset()
    repo = ClientPolicyRepository()
    repo.upsert_policy(
        {
            'client_id': 'default',
            'enabled': True,
            'plan': 'starter',
            'default_strategy': 'balanced',
            'allowed_strategies': ['balanced'],
            'allowed_response_formats': ['text'],
            'max_requests_per_minute': 60,
            'max_parallel_providers': 3,
            'allow_workflows': False,
            'preferred_providers': [],
            'max_input_chars': 100,
        }
    )
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = 'secret-key'
    response = client.post('/v1/chat/completions', headers={'x-api-key': 'secret-key'}, json={'messages': [{'role': 'user', 'content': 'hello'}], 'strategy': 'quality'})
    assert response.status_code == 403


def test_admin_clients_endpoint_lists_items() -> None:
    get_settings.cache_clear()
    rate_limiter.reset()
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = 'secret-key'
    response = client.get('/admin/clients', headers={'x-api-key': 'secret-key'})
    assert response.status_code == 200
    assert 'items' in response.json()
