from __future__ import annotations

from app.core.config import Settings
from app.services.circuit_breaker import get_circuit_breaker
from app.services.providers import OpenAICompatibleProvider, ProviderConfig
from app.services.secrets import SecretResolver


class ProviderRegistry:
    def __init__(self, settings: Settings, secret_resolver: SecretResolver) -> None:
        self.settings = settings
        self.secret_resolver = secret_resolver

    def available_providers(self) -> list[OpenAICompatibleProvider]:
        providers: list[ProviderConfig] = []
        groq_key = self.secret_resolver.get('GROQ_API_KEY')
        if self.settings.groq_enabled and groq_key:
            providers.append(ProviderConfig(name='groq', base_url=self.settings.groq_base_url, api_key=groq_key, model=self.settings.groq_model, timeout_seconds=self.settings.groq_timeout_seconds, priority=self.settings.groq_priority))
        openrouter_key = self.secret_resolver.get('OPENROUTER_API_KEY')
        if self.settings.openrouter_enabled and openrouter_key:
            headers = {}
            if self.settings.openrouter_referer:
                headers['HTTP-Referer'] = self.settings.openrouter_referer
            if self.settings.openrouter_title:
                headers['X-Title'] = self.settings.openrouter_title
            providers.append(ProviderConfig(name='openrouter', base_url=self.settings.openrouter_base_url, api_key=openrouter_key, model=self.settings.openrouter_model, timeout_seconds=self.settings.openrouter_timeout_seconds, priority=self.settings.openrouter_priority, headers=headers or None))
        hf_key = self.secret_resolver.get('HUGGINGFACE_API_KEY')
        if self.settings.huggingface_enabled and hf_key:
            providers.append(ProviderConfig(name='huggingface', base_url=self.settings.huggingface_base_url, api_key=hf_key, model=self.settings.huggingface_model, timeout_seconds=self.settings.huggingface_timeout_seconds, priority=self.settings.huggingface_priority))
        providers.sort(key=lambda x: x.priority)
        return [OpenAICompatibleProvider(cfg, breaker=get_circuit_breaker(cfg.name, failure_threshold=self.settings.circuit_breaker_failure_threshold, recovery_timeout_seconds=self.settings.circuit_breaker_recovery_seconds), max_retries=self.settings.provider_max_retries, backoff_seconds=self.settings.retry_backoff_seconds) for cfg in providers[: self.settings.max_parallel_providers]]
