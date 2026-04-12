from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.schemas import ProviderResult
from app.services.circuit_breaker import CircuitBreaker


@dataclass(slots=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float
    priority: int
    headers: dict[str, str] | None = None


class OpenAICompatibleProvider:
    def __init__(self, config: ProviderConfig, *, breaker: CircuitBreaker | None = None, max_retries: int = 2, backoff_seconds: float = 0.25) -> None:
        self.config = config
        self.breaker = breaker
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    async def chat(self, messages: list[dict[str, str]], temperature: float, max_tokens: int) -> ProviderResult:
        started = time.perf_counter()
        if self.breaker and not self.breaker.allow_request():
            return ProviderResult(provider=self.config.name, model=self.config.model, content='', latency_ms=0, success=False, error='Circuit breaker is open for this provider.')
        headers = {'Authorization': f'Bearer {self.config.api_key}', 'Content-Type': 'application/json'}
        if self.config.headers:
            headers.update(self.config.headers)
        payload: dict[str, Any] = {'model': self.config.model, 'messages': messages, 'temperature': temperature, 'max_tokens': max_tokens}
        try:
            response = None
            async for attempt in AsyncRetrying(stop=stop_after_attempt(self.max_retries + 1), wait=wait_exponential(multiplier=self.backoff_seconds, min=self.backoff_seconds, max=2), retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError)), reraise=True):
                with attempt:
                    async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                        response = await client.post(f"{self.config.base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
                    response.raise_for_status()
            latency_ms = int((time.perf_counter() - started) * 1000)
            data = response.json()
            content = data['choices'][0]['message']['content']
            if self.breaker:
                self.breaker.record_success()
            return ProviderResult(provider=self.config.name, model=self.config.model, content=content, latency_ms=latency_ms, success=True, status_code=response.status_code)
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            if self.breaker:
                self.breaker.record_failure()
            status_code = getattr(getattr(exc, 'response', None), 'status_code', None)
            return ProviderResult(provider=self.config.name, model=self.config.model, content='', latency_ms=latency_ms, success=False, status_code=status_code, error=str(exc))
