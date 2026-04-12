from app.services.gateway_api_key_repository import GatewayApiKeyRepository


def test_create_resolve_and_revoke_api_key(tmp_path) -> None:
    db_path = str(tmp_path / 'gateway.db')
    repo = GatewayApiKeyRepository(db_path)
    created = repo.create_key(client_id='client-a', api_key='key-a')
    assert repo.resolve_client_id('key-a') == 'client-a'
    assert created.enabled is True
    assert repo.revoke_key(created.key_id) is True
    assert repo.resolve_client_id('key-a') is None
