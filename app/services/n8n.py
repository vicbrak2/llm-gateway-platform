from __future__ import annotations

from typing import Any

import httpx


class N8NClient:
    def __init__(self, base_url: str | None, api_key: str | None, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip('/') if base_url else None
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    async def trigger_webhook(self, workflow_id: str, payload: dict[str, Any], trace_id: str) -> tuple[int, Any]:
        if not self.base_url:
            raise RuntimeError('n8n integration is not configured')
        headers = {'X-Trace-Id': trace_id}
        if self.api_key:
            headers['X-N8N-API-KEY'] = self.api_key
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f'{self.base_url}/webhook/{workflow_id}', json=payload, headers=headers)
        response.raise_for_status()
        content_type = response.headers.get('content-type', '')
        if 'application/json' in content_type:
            return response.status_code, response.json()
        return response.status_code, response.text
