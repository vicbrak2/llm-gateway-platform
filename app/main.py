from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, trace_id_ctx
from app.schemas import ChatRequest, ChatResponse, ClientPolicy, ClientPolicyListResponse, ErrorResponse, GatewayApiKey, GatewayApiKeyListResponse, HealthResponse, MetricsResponse, N8NWorkflowRequest, N8NWorkflowResponse
from app.services.auth import require_gateway_api_key
from app.services.cache import CacheService
from app.services.client_policy_service import ClientPolicyService
from app.services.errors import build_error_response
from app.services.gateway_api_key_repository import GatewayApiKeyRepository
from app.services.health import build_health_response
from app.services.metrics import metrics_registry
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
    GatewayApiKeyRepository()
    yield
    if redis_client:
        await redis_client.aclose()


app = FastAPI(title='LLM Orchestrator', version='0.11.0', lifespan=lifespan)


@app.middleware('http')
async def metrics_middleware(request: Request, call_next):
    started = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        latency_ms = int((time.perf_counter() - started) * 1000)
        metrics_registry.record_request(path=request.url.path, status_code=getattr(response, 'status_code', 500), latency_ms=latency_ms)


def build_secret_resolver(settings: Settings = Depends(get_settings)) -> SecretResolver:
    return SecretResolver(
        infisical_enabled=settings.infisical_enabled,
        host=settings.infisical_host,
        token=settings.infisical_token,
        project_id=settings.infisical_project_id,
        environment_slug=settings.infisical_environment_slug,
        secret_path=settings.infisical_secret_path,
    )


def build_orchestrator(settings: Settings = Depends(get_settings), secret_resolver: SecretResolver = Depends(build_secret_resolver)) -> OrchestratorService:
    cache = CacheService(redis_client, ttl_seconds=settings.cache_ttl_seconds)
    n8n_client = N8NClient(settings.n8n_base_url, settings.n8n_api_key, settings.n8n_timeout_seconds)
    return OrchestratorService(settings, cache, n8n_client, secret_resolver)


def build_client_policy_service() -> ClientPolicyService:
    return ClientPolicyService()


def build_api_key_repository() -> GatewayApiKeyRepository:
    return GatewayApiKeyRepository()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    trace_id = request.headers.get('x-trace-id') or trace_id_ctx.get()
    payload = build_error_response(code='http_error', message=str(exc.detail), trace_id=trace_id)
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    trace_id = request.headers.get('x-trace-id') or trace_id_ctx.get()
    logger.exception('unhandled exception', extra={'extra_data': {'trace_id': trace_id}})
    payload = build_error_response(code='internal_error', message='Internal server error', trace_id=trace_id)
    return JSONResponse(status_code=500, content=payload.model_dump())


@app.get('/health', response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings), secret_resolver: SecretResolver = Depends(build_secret_resolver)) -> HealthResponse:
    return await build_health_response(settings, redis_client, secret_resolver)


@app.get('/metrics', response_model=MetricsResponse, responses={401: {'model': ErrorResponse}, 429: {'model': ErrorResponse}})
async def metrics(_: str = Depends(require_gateway_api_key)) -> MetricsResponse:
    return metrics_registry.snapshot()


@app.get('/admin/clients', response_model=ClientPolicyListResponse, responses={401: {'model': ErrorResponse}, 429: {'model': ErrorResponse}})
async def list_clients(_: str = Depends(require_gateway_api_key), service: ClientPolicyService = Depends(build_client_policy_service)) -> ClientPolicyListResponse:
    return ClientPolicyListResponse(items=service.list_policies())


@app.post('/admin/clients', response_model=ClientPolicy, responses={401: {'model': ErrorResponse}, 429: {'model': ErrorResponse}})
async def upsert_client(policy: ClientPolicy, _: str = Depends(require_gateway_api_key), service: ClientPolicyService = Depends(build_client_policy_service)) -> ClientPolicy:
    return service.upsert_policy(policy)


@app.get('/admin/api-keys', response_model=GatewayApiKeyListResponse, responses={401: {'model': ErrorResponse}, 429: {'model': ErrorResponse}})
async def list_api_keys(_: str = Depends(require_gateway_api_key), repository: GatewayApiKeyRepository = Depends(build_api_key_repository)) -> GatewayApiKeyListResponse:
    return GatewayApiKeyListResponse(items=repository.list_keys())


@app.post('/admin/api-keys', response_model=GatewayApiKey, responses={401: {'model': ErrorResponse}, 429: {'model': ErrorResponse}})
async def create_api_key(payload: GatewayApiKey, _: str = Depends(require_gateway_api_key), repository: GatewayApiKeyRepository = Depends(build_api_key_repository)) -> GatewayApiKey:
    return repository.create_key(client_id=payload.client_id, api_key=payload.api_key)


@app.post('/admin/api-keys/{key_id}/revoke', responses={401: {'model': ErrorResponse}, 404: {'model': ErrorResponse}, 429: {'model': ErrorResponse}})
async def revoke_api_key(key_id: str, _: str = Depends(require_gateway_api_key), repository: GatewayApiKeyRepository = Depends(build_api_key_repository)) -> dict:
    if not repository.revoke_key(key_id):
        raise HTTPException(status_code=404, detail='api key not found')
    return {'status': 'revoked', 'key_id': key_id}


@app.post('/v1/chat/completions', response_model=ChatResponse, responses={401: {'model': ErrorResponse}, 403: {'model': ErrorResponse}, 413: {'model': ErrorResponse}, 429: {'model': ErrorResponse}, 500: {'model': ErrorResponse}})
async def chat_completions(request: ChatRequest, orchestrator: OrchestratorService = Depends(build_orchestrator), policy_service: ClientPolicyService = Depends(build_client_policy_service), x_trace_id: str | None = Header(default=None), client_id: str = Depends(require_gateway_api_key)) -> ChatResponse:
    trace_id = request.trace_id or x_trace_id or str(uuid.uuid4())
    trace_id_ctx.set(trace_id)
    logger.info('chat request received', extra={'extra_data': {'trace_id': trace_id, 'strategy': request.strategy, 'client_id': client_id}})
    request, runtime_policy = policy_service.enforce_chat_policy(client_id, request)
    return await orchestrator.run(request, trace_id, runtime_policy)


@app.post('/v1/workflows/trigger', response_model=N8NWorkflowResponse, responses={400: {'model': ErrorResponse}, 401: {'model': ErrorResponse}, 429: {'model': ErrorResponse}, 500: {'model': ErrorResponse}})
async def trigger_workflow(request: N8NWorkflowRequest, settings: Settings = Depends(get_settings), x_trace_id: str | None = Header(default=None), _: str = Depends(require_gateway_api_key)) -> N8NWorkflowResponse:
    trace_id = x_trace_id or str(uuid.uuid4())
    trace_id_ctx.set(trace_id)
    client = N8NClient(settings.n8n_base_url, settings.n8n_api_key, settings.n8n_timeout_seconds)
    if not client.enabled:
        raise HTTPException(status_code=400, detail='n8n integration is not configured')
    status_code, data = await client.trigger_webhook(request.workflow_id, request.payload, trace_id)
    return N8NWorkflowResponse(trace_id=trace_id, workflow_id=request.workflow_id, status_code=status_code, data=data)


if __name__ == '__main__':
    import uvicorn

    settings = get_settings()
    uvicorn.run('app.main:app', host=settings.host, port=int(os.getenv('PORT', settings.effective_port)), reload=False)
