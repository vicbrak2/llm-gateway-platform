from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal['system', 'user', 'assistant', 'tool']
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    strategy: Literal['fast', 'balanced', 'quality'] = 'balanced'
    temperature: float = 0.2
    max_tokens: int = 512
    user_id: str | None = None
    trace_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    require_workflow: bool = False
    response_format: Literal['text', 'json_object'] = 'text'


class CapabilityRequest(BaseModel):
    input: str
    trace_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class CapabilityResponse(BaseModel):
    capability: Literal['summarize', 'extract', 'generate_json', 'route_workflow']
    trace_id: str
    strategy: str
    winner: str | None = None
    content: str
    provider_results: list['ProviderResult']
    workflow_invoked: bool = False
    structured_output_valid: bool | None = None


class ProviderResult(BaseModel):
    provider: str
    model: str
    content: str
    latency_ms: int
    success: bool
    status_code: int | None = None
    error: str | None = None


class ChatResponse(BaseModel):
    trace_id: str
    strategy: str
    winner: str | None = None
    content: str
    provider_results: list[ProviderResult]
    workflow_invoked: bool = False
    structured_output_valid: bool | None = None


class BreakerStatus(BaseModel):
    provider: str
    state: Literal['closed', 'open']
    failure_count: int
    opened_until: float


class ProviderHealth(BaseModel):
    provider: str
    model: str
    priority: int
    timeout_seconds: float


class ErrorDetail(BaseModel):
    code: str
    message: str
    trace_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ClientUsage(BaseModel):
    client_id: str
    requests_total: int


class GatewayApiKey(BaseModel):
    client_id: str
    key_id: str
    api_key: str
    enabled: bool = True


class GatewayApiKeyListResponse(BaseModel):
    items: list[GatewayApiKey] = Field(default_factory=list)


class MetricsResponse(BaseModel):
    requests_total: int
    request_errors_total: int
    chat_requests_total: int
    workflow_requests_total: int
    cache_hits_total: int
    cache_misses_total: int
    provider_success_total: int
    provider_failure_total: int
    average_request_latency_ms: int
    client_usage: list[ClientUsage] = Field(default_factory=list)


class ClientPolicy(BaseModel):
    client_id: str
    enabled: bool = True
    plan: str = 'starter'
    default_strategy: Literal['fast', 'balanced', 'quality'] = 'balanced'
    allowed_strategies: list[Literal['fast', 'balanced', 'quality']] = Field(default_factory=lambda: ['fast', 'balanced', 'quality'])
    allowed_response_formats: list[Literal['text', 'json_object']] = Field(default_factory=lambda: ['text', 'json_object'])
    allowed_capabilities: list[Literal['summarize', 'extract', 'generate_json', 'route_workflow']] = Field(default_factory=lambda: ['summarize', 'extract', 'generate_json', 'route_workflow'])
    max_requests_per_minute: int = 60
    max_parallel_providers: int = 3
    allow_workflows: bool = True
    preferred_providers: list[str] = Field(default_factory=list)
    max_input_chars: int = 12000


class ClientPolicyListResponse(BaseModel):
    items: list[ClientPolicy] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: Literal['ok', 'degraded']
    app: str
    env: str
    redis: Literal['connected', 'disabled', 'degraded']
    n8n: Literal['configured', 'disabled']
    providers: list[ProviderHealth] = Field(default_factory=list)
    breakers: list[BreakerStatus] = Field(default_factory=list)


class N8NWorkflowRequest(BaseModel):
    workflow_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class N8NWorkflowResponse(BaseModel):
    trace_id: str
    workflow_id: str
    status_code: int
    data: dict[str, Any] | list[Any] | str | None = None
