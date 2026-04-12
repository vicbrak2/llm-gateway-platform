from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    strategy: Literal["fast", "balanced", "quality"] = "balanced"
    temperature: float = 0.2
    max_tokens: int = 512
    user_id: str | None = None
    trace_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    require_workflow: bool = False


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


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    app: str
    env: str


class N8NWorkflowRequest(BaseModel):
    workflow_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class N8NWorkflowResponse(BaseModel):
    trace_id: str
    workflow_id: str
    status_code: int
    data: dict[str, Any] | list[Any] | str | None = None
