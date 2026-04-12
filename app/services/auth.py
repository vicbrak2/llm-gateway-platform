from __future__ import annotations

from fastapi import Header, HTTPException

from app.core.config import Settings, get_settings
from app.services.gateway_api_key_repository import GatewayApiKeyRepository
from app.services.metrics import metrics_registry
from app.services.rate_limiter import rate_limiter


def _resolve_client_id(x_api_key: str | None, settings: Settings) -> str | None:
    if x_api_key:
        db_client_id = GatewayApiKeyRepository().resolve_client_id(x_api_key)
        if db_client_id:
            return db_client_id
    if settings.gateway_api_keys:
        pairs = [item.strip() for item in settings.gateway_api_keys.split(',') if item.strip()]
        mapping: dict[str, str] = {}
        for pair in pairs:
            if ':' in pair:
                client_id, api_key = pair.split(':', 1)
                mapping[api_key.strip()] = client_id.strip()
        return mapping.get(x_api_key or '')
    if settings.gateway_api_key and x_api_key == settings.gateway_api_key:
        return 'default'
    if not settings.gateway_api_key and not settings.gateway_api_keys:
        return 'default'
    return None


async def require_gateway_api_key(
    x_api_key: str | None = Header(default=None),
) -> str:
    settings: Settings = get_settings()
    client_id = _resolve_client_id(x_api_key, settings)
    if client_id is None:
        raise HTTPException(status_code=401, detail='invalid or missing api key')
    limiter_key = x_api_key or client_id
    if not rate_limiter.allow(limiter_key, settings.rate_limit_requests, settings.rate_limit_window_seconds):
        raise HTTPException(status_code=429, detail='rate limit exceeded')
    metrics_registry.record_client_request(client_id)
    return client_id
