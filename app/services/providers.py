from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.schemas import ProviderResult


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
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    async def chat(self, messages: list[dict[str, str]], temperature: float, max_tokens: int) -> ProviderResult:
        started = time.perf_counter()
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        if self.config.headers:
            headers.update(self.config.headers)

        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(f"{self.config.base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
            latency_ms = int((time.perf_counter() - started) * 1000)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return ProviderResult(
                provider=self.config.name,
                model=self.config.model,
                content=content,
                latency_ms=latency_ms,
                success=True,
                status_code=response.status_code,
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            return ProviderResult(
                provider=self.config.name,
                model=self.config.model,
                content="",
                latency_ms=latency_ms,
                success=False,
                status_code=status_code,
                error=str(exc),
            )
