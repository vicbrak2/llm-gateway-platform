from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def test_metrics_endpoint_returns_counters() -> None:
    # /metrics only allows unauthenticated access when no gateway api key is
    # configured. get_settings() is a process-wide cached singleton that other
    # tests mutate, so reset it explicitly instead of relying on a clean default.
    get_settings.cache_clear()
    client = TestClient(app)
    settings = get_settings()
    settings.gateway_api_key = None
    settings.gateway_api_keys = None
    client.get('/health')
    response = client.get('/metrics')
    assert response.status_code == 200
    data = response.json()
    assert 'requests_total' in data
    assert 'average_request_latency_ms' in data
