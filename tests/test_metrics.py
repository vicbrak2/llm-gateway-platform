from fastapi.testclient import TestClient

from app.main import app


def test_metrics_endpoint_returns_counters() -> None:
    client = TestClient(app)
    client.get('/health')
    response = client.get('/metrics')
    assert response.status_code == 200
    data = response.json()
    assert 'requests_total' in data
    assert 'average_request_latency_ms' in data
