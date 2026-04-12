from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get('/health')
    assert response.status_code == 200
    data = response.json()
    assert data['app']
    assert data['status'] in {'ok', 'degraded'}
    assert 'providers' in data
    assert 'breakers' in data
