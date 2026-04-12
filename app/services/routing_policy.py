from __future__ import annotations

from app.schemas import ChatRequest
from app.services.providers import OpenAICompatibleProvider


class RoutingPolicy:
    def __init__(self, max_parallel_providers: int, complexity_threshold: int = 80) -> None:
        self.max_parallel_providers = max_parallel_providers
        self.complexity_threshold = complexity_threshold

    def select_providers(self, providers: list[OpenAICompatibleProvider], request: ChatRequest) -> list[OpenAICompatibleProvider]:
        if not providers:
            return []
        total_chars = sum(len(message.content) for message in request.messages)
        if request.strategy == 'fast':
            ordered = sorted(providers, key=lambda p: (p.config.timeout_seconds, p.config.priority))
            return ordered[: max(1, min(2, self.max_parallel_providers))]
        if request.strategy == 'quality':
            ordered = sorted(providers, key=lambda p: (-p.config.timeout_seconds, p.config.priority))
            return ordered[: self.max_parallel_providers]
        ordered = sorted(providers, key=lambda p: (p.config.priority, p.config.timeout_seconds))
        if total_chars >= self.complexity_threshold:
            ordered = sorted(providers, key=lambda p: (-p.config.timeout_seconds, p.config.priority))
        return ordered[: self.max_parallel_providers]
