from __future__ import annotations

import asyncio
from typing import Any

from app.core.config import Settings
from app.schemas import ChatRequest, ChatResponse, ProviderResult
from app.services.cache import CacheService
from app.services.n8n import N8NClient
from app.services.providers import OpenAICompatibleProvider, ProviderConfig
from app.services.secrets import SecretResolver


class OrchestratorService:
    def __init__(self, settings: Settings, cache: CacheService, n8n_client: N8NClient, secret_resolver: SecretResolver) -> None:
        self.settings = settings
        self.cache = cache
        self.n8n_client = n8n_client
        self.secret_resolver = secret_resolver

    def _build_providers(self) -> list[OpenAICompatibleProvider]:
        providers: list[ProviderConfig] = []
        groq_key = self.secret_resolver.get("GROQ_API_KEY")
        if self.settings.groq_enabled and groq_key:
            providers.append(
                ProviderConfig(
                    name="groq",
                    base_url=self.settings.groq_base_url,
                    api_key=groq_key,
                    model=self.settings.groq_model,
                    timeout_seconds=self.settings.groq_timeout_seconds,
                    priority=self.settings.groq_priority,
                )
            )

        openrouter_key = self.secret_resolver.get("OPENROUTER_API_KEY")
        if self.settings.openrouter_enabled and openrouter_key:
            headers = {}
            if self.settings.openrouter_referer:
                headers["HTTP-Referer"] = self.settings.openrouter_referer
            if self.settings.openrouter_title:
                headers["X-Title"] = self.settings.openrouter_title
            providers.append(
                ProviderConfig(
                    name="openrouter",
                    base_url=self.settings.openrouter_base_url,
                    api_key=openrouter_key,
                    model=self.settings.openrouter_model,
                    timeout_seconds=self.settings.openrouter_timeout_seconds,
                    priority=self.settings.openrouter_priority,
                    headers=headers or None,
                )
            )

        hf_key = self.secret_resolver.get("HUGGINGFACE_API_KEY")
        if self.settings.huggingface_enabled and hf_key:
            providers.append(
                ProviderConfig(
                    name="huggingface",
                    base_url=self.settings.huggingface_base_url,
                    api_key=hf_key,
                    model=self.settings.huggingface_model,
                    timeout_seconds=self.settings.huggingface_timeout_seconds,
                    priority=self.settings.huggingface_priority,
                )
            )

        providers.sort(key=lambda x: x.priority)
        return [OpenAICompatibleProvider(cfg) for cfg in providers[: self.settings.max_parallel_providers]]

    async def run(self, request: ChatRequest, trace_id: str) -> ChatResponse:
        cache_key = self.cache.make_key(
            {
                "messages": [m.model_dump() for m in request.messages],
                "strategy": request.strategy,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }
        )
        cached = await self.cache.get(cache_key)
        if cached:
            return ChatResponse(**cached)

        providers = self._build_providers()
        if not providers:
            return ChatResponse(trace_id=trace_id, strategy=request.strategy, content="No provider is configured.", provider_results=[])

        messages = [m.model_dump() for m in request.messages]
        provider_results = await self._execute_strategy(providers, request.strategy, messages, request.temperature, request.max_tokens)
        content, winner = self._refine(provider_results)

        workflow_invoked = False
        if request.require_workflow or self._looks_complex(messages):
            if self.n8n_client.enabled:
                workflow_invoked = True
                try:
                    await self.n8n_client.trigger_webhook("llm-complex-task", {"messages": messages, "trace_id": trace_id}, trace_id)
                except Exception:
                    workflow_invoked = False

        response = ChatResponse(
            trace_id=trace_id,
            strategy=request.strategy,
            winner=winner,
            content=content,
            provider_results=provider_results,
            workflow_invoked=workflow_invoked,
        )
        await self.cache.set(cache_key, response.model_dump())
        return response

    async def _execute_strategy(
        self,
        providers: list[OpenAICompatibleProvider],
        strategy: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> list[ProviderResult]:
        if strategy == "fast":
            tasks = [asyncio.create_task(p.chat(messages, temperature, max_tokens)) for p in providers]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            return [task.result() for task in done if not task.cancelled()]

        tasks = [p.chat(messages, temperature, max_tokens) for p in providers]
        results = await asyncio.gather(*tasks)
        if strategy == "balanced":
            return sorted(results, key=lambda r: (not r.success, r.latency_ms))
        return sorted(results, key=lambda r: (not r.success, r.latency_ms))

    def _refine(self, provider_results: list[ProviderResult]) -> tuple[str, str | None]:
        successes = [r for r in provider_results if r.success and r.content.strip()]
        if not successes:
            first = provider_results[0] if provider_results else None
            return (first.error if first and first.error else "No provider succeeded.", None)

        if self.settings.refinement_strategy == "none":
            winner = successes[0]
            return winner.content, winner.provider

        if self.settings.refinement_strategy == "first_success":
            winner = successes[0]
            return winner.content, winner.provider

        winner = successes[0]
        if len(successes) == 1:
            return winner.content, winner.provider

        merged = "\n\n---\n\n".join([f"[{r.provider}]\n{r.content}" for r in successes])
        return merged, winner.provider

    def _looks_complex(self, messages: list[dict[str, str]]) -> bool:
        total_len = sum(len(m.get("content", "")) for m in messages)
        return total_len >= self.settings.n8n_complexity_threshold
