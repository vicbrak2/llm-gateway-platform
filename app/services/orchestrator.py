from __future__ import annotations

import asyncio

from app.core.config import Settings
from app.schemas import ChatRequest, ChatResponse, ProviderResult
from app.services.cache import CacheService
from app.services.metrics import metrics_registry
from app.services.n8n import N8NClient
from app.services.provider_registry import ProviderRegistry
from app.services.providers import OpenAICompatibleProvider
from app.services.response_ranker import ResponseRanker
from app.services.routing_policy import RoutingPolicy
from app.services.secrets import SecretResolver


class OrchestratorService:
    def __init__(self, settings: Settings, cache: CacheService, n8n_client: N8NClient, secret_resolver: SecretResolver) -> None:
        self.settings = settings
        self.cache = cache
        self.n8n_client = n8n_client
        self.secret_resolver = secret_resolver
        self.provider_registry = ProviderRegistry(settings, secret_resolver)
        self.routing_policy = RoutingPolicy(max_parallel_providers=settings.max_parallel_providers, complexity_threshold=settings.n8n_complexity_threshold)
        self.response_ranker = ResponseRanker()

    def _build_providers(self) -> list[OpenAICompatibleProvider]:
        return self.provider_registry.available_providers()

    def _select_providers(self, providers: list[OpenAICompatibleProvider], request: ChatRequest) -> list[OpenAICompatibleProvider]:
        return self.routing_policy.select_providers(providers, request)

    async def run(self, request: ChatRequest, trace_id: str) -> ChatResponse:
        cache_key = self.cache.make_key({'messages': [m.model_dump() for m in request.messages], 'strategy': request.strategy, 'temperature': request.temperature, 'max_tokens': request.max_tokens})
        cached = await self.cache.get(cache_key)
        if cached:
            metrics_registry.record_cache_hit()
            return ChatResponse(**cached)
        metrics_registry.record_cache_miss()
        providers = self._select_providers(self._build_providers(), request)
        if not providers:
            return ChatResponse(trace_id=trace_id, strategy=request.strategy, content='No provider is configured.', provider_results=[])
        messages = [m.model_dump() for m in request.messages]
        provider_results = await self._execute_strategy(providers, request.strategy, messages, request.temperature, request.max_tokens)
        metrics_registry.record_provider_results(provider_results)
        content, winner = self._refine(provider_results)
        workflow_invoked = False
        if request.require_workflow or self._looks_complex(messages):
            if self.n8n_client.enabled:
                workflow_invoked = True
                try:
                    await self.n8n_client.trigger_webhook('llm-complex-task', {'messages': messages, 'trace_id': trace_id}, trace_id)
                except Exception:
                    workflow_invoked = False
        response = ChatResponse(trace_id=trace_id, strategy=request.strategy, winner=winner, content=content, provider_results=provider_results, workflow_invoked=workflow_invoked)
        await self.cache.set(cache_key, response.model_dump())
        return response

    async def _execute_strategy(self, providers: list[OpenAICompatibleProvider], strategy: str, messages: list[dict[str, str]], temperature: float, max_tokens: int) -> list[ProviderResult]:
        if strategy == 'fast':
            tasks = [asyncio.create_task(p.chat(messages, temperature, max_tokens)) for p in providers]
            results: list[ProviderResult] = []
            try:
                for completed in asyncio.as_completed(tasks):
                    result = await completed
                    results.append(result)
                    if result.success and result.content.strip():
                        for task in tasks:
                            if not task.done():
                                task.cancel()
                        return self.response_ranker.rank(results)
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()
            return self.response_ranker.rank(results)
        results = await asyncio.gather(*(p.chat(messages, temperature, max_tokens) for p in providers))
        return self.response_ranker.rank(results)

    def _refine(self, provider_results: list[ProviderResult]) -> tuple[str, str | None]:
        winner = self.response_ranker.choose_winner(provider_results)
        if winner is None or not winner.success or not winner.content.strip():
            return (winner.error if winner and winner.error else 'No provider succeeded.', None)
        if self.settings.refinement_strategy in {'none', 'first_success'}:
            return winner.content, winner.provider
        successes = [r for r in provider_results if r.success and r.content.strip()]
        if len(successes) == 1:
            return winner.content, winner.provider
        merged = self.response_ranker.merge_contents(successes)
        return merged, winner.provider

    def _looks_complex(self, messages: list[dict[str, str]]) -> bool:
        total_len = sum(len(m.get('content', '')) for m in messages)
        return total_len >= self.settings.n8n_complexity_threshold
