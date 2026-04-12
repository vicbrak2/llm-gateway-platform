from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import Settings
from app.schemas import BreakerStatus, HealthResponse, ProviderHealth
from app.services.circuit_breaker import get_breaker_snapshots
from app.services.provider_registry import ProviderRegistry
from app.services.secrets import SecretResolver


async def build_health_response(settings: Settings, redis_client: Redis | None, secret_resolver: SecretResolver) -> HealthResponse:
    redis_status = 'disabled'
    if settings.redis_url:
        if redis_client is None:
            redis_status = 'degraded'
        else:
            try:
                await redis_client.ping()
                redis_status = 'connected'
            except Exception:
                redis_status = 'degraded'

    n8n_status = 'configured' if settings.n8n_base_url else 'disabled'
    registry = ProviderRegistry(settings, secret_resolver)
    providers = registry.available_providers()
    provider_health = [ProviderHealth(provider=p.config.name, model=p.config.model, priority=p.config.priority, timeout_seconds=p.config.timeout_seconds) for p in providers]
    breakers = [BreakerStatus(**snapshot) for snapshot in get_breaker_snapshots()]
    status = 'degraded' if redis_status == 'degraded' else 'ok'
    return HealthResponse(status=status, app=settings.app_name, env=settings.app_env, redis=redis_status, n8n=n8n_status, providers=provider_health, breakers=breakers)
