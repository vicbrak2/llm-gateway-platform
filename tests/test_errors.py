from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app


@app.get('/_test_http_exception')
async def _test_http_exception():
    raise HTTPException(status_code=418, detail='teapot')


def test_http_exception_is_normalized() -> None:
    client = TestClient(app)
    response = client.get('/_test_http_exception', headers={'x-trace-id': 'trace-test'})
    assert response.status_code == 418
    data = response.json()
    assert data['error']['code'] == 'http_error'
    assert data['error']['trace_id'] == 'trace-test'
