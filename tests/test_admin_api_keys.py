from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services.gateway_api_key_repository import GatewayApiKeyRepository
from app.services.rate_limiter import rate_limiter


def test_admin_api_key_crud_flow() -> None:
    get_settings.cache_clear()
    rate_limiter.reset()
    repo = GatewayApiKeyRepository()
    admin_key = repo.create_key(client_id='default', api_key='admin-secret')
    client = TestClient(app)

    create_response = client.post('/admin/api-keys', headers={'x-api-key': 'admin-secret'}, json={'client_id': 'client-b', 'key_id': 'ignored', 'api_key': 'client-b-key', 'enabled': True})
    assert create_response.status_code == 200
    key_id = create_response.json()['key_id']

    list_response = client.get('/admin/api-keys', headers={'x-api-key': 'admin-secret'})
    assert list_response.status_code == 200
    assert len(list_response.json()['items']) >= 2

    revoke_response = client.post(f'/admin/api-keys/{key_id}/revoke', headers={'x-api-key': 'admin-secret'})
    assert revoke_response.status_code == 200
    assert revoke_response.json()['status'] == 'revoked'
