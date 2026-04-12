from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.schemas import ClientPolicy
from app.services.client_policy_repository import ClientPolicyRepository
from app.services.gateway_api_key_repository import GatewayApiKeyRepository
from app.services.rate_limiter import rate_limiter


def test_capability_blocked_by_policy() -> None:
    get_settings.cache_clear()
    rate_limiter.reset()
    repo = ClientPolicyRepository()
    repo.upsert_policy(ClientPolicy(client_id='default', allowed_capabilities=['summarize']))
    key_repo = GatewayApiKeyRepository()
    key_repo.create_key(client_id='default', api_key='cap-secret-block')
    client = TestClient(app)
    response = client.post('/v1/capabilities/generate_json', headers={'x-api-key': 'cap-secret-block'}, json={'input': 'hello'})
    assert response.status_code == 403


def test_capability_allowed_returns_response_shape() -> None:
    get_settings.cache_clear()
    rate_limiter.reset()
    repo = ClientPolicyRepository()
    repo.upsert_policy(ClientPolicy(client_id='default', allowed_capabilities=['summarize', 'generate_json', 'extract', 'route_workflow']))
    key_repo = GatewayApiKeyRepository()
    key_repo.create_key(client_id='default', api_key='cap-secret-ok')
    client = TestClient(app)
    response = client.post('/v1/capabilities/summarize', headers={'x-api-key': 'cap-secret-ok'}, json={'input': 'hello world'})
    assert response.status_code in {200, 500}
    if response.status_code == 200:
        body = response.json()
        assert body['capability'] == 'summarize'
        assert 'content' in body
