from __future__ import annotations

from fastapi import Header, HTTPException

from app.core.config import Settings, get_settings
from app.services.rate_limiter import rate_limiter


async def require_gateway_api_key(
    x_api_key: str | None = Header(default=None),
) -> None:
    settings: Settings = get_settings()
    expected = settings.gateway_api_key
    if not expected:
        return
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail='invalid or missing api key')
    if not rate_limiter.allow(x_api_key, settings.rate_limit_requests, settings.rate_limit_window_seconds):
        raise HTTPException(status_code=429, detail='rate limit exceeded')
