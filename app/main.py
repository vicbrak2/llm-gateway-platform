from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, trace_id_ctx
from app.schemas import ChatRequest, ChatResponse, HealthResponse, N8NWorkflowRequest, N8NWorkflowResponse
from app.services.cache import CacheService
from app.services.n8n import N8NClient
from app.services.orchestrator import OrchestratorService
from app.services.secrets import SecretResolver

logger = logging.getLogger(__name__)
redis_client: Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.redis_url:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
    yield
    if redis_client:
        await redis_client.aclose()


app = FastAPI(title="LLM Orchestrator", version="0.2.0", lifespan=lifespan)


def build_orchestrator(settings: Settings = Depends(get_settings)) -> OrchestratorService:
    cache = CacheService(redis_client, ttl_seconds=settings.cache_ttl_seconds)
    n8n_client = N8NClient(
        base_url=settings.n8n_base_url,
        api_key=settings.n8n_api_key,
        timeout_seconds=settings.n8n_timeout_seconds,
    )
    secret_resolver = SecretResolver(
        infisical_enabled=settings.infisical_enabled,
        host=settings.infisical_host,
        token=settings.infisical_token,
        project_id=settings.infisical_project_id,
        environment_slug=settings.infisical_environment_slug,
        secret_path=settings.infisical_secret_path,
    )
    return OrchestratorService(settings, cache, n8n_client, secret_resolver)


@app.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(app=settings.app_name, env=settings.app_env)


@app.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(
    request: ChatRequest,
    orchestrator: OrchestratorService = Depends(build_orchestrator),
    x_trace_id: str | None = Header(default=None),
) -> ChatResponse:
    trace_id = request.trace_id or x_trace_id or str(uuid.uuid4())
    trace_id_ctx.set(trace_id)
    logger.info("chat request received", extra={"extra_data": {"trace_id": trace_id, "strategy": request.strategy}})
    return await orchestrator.run(request, trace_id)


@app.post("/v1/workflows/trigger", response_model=N8NWorkflowResponse)
async def trigger_workflow(
    request: N8NWorkflowRequest,
    settings: Settings = Depends(get_settings),
    x_trace_id: str | None = Header(default=None),
) -> N8NWorkflowResponse:
    trace_id = x_trace_id or str(uuid.uuid4())
    trace_id_ctx.set(trace_id)
    client = N8NClient(settings.n8n_base_url, settings.n8n_api_key, settings.n8n_timeout_seconds)
    if not client.enabled:
        raise HTTPException(status_code=400, detail="n8n integration is not configured")
    status_code, data = await client.trigger_webhook(request.workflow_id, request.payload, trace_id)
    return N8NWorkflowResponse(trace_id=trace_id, workflow_id=request.workflow_id, status_code=status_code, data=data)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=int(os.getenv("PORT", settings.effective_port)), reload=False)
