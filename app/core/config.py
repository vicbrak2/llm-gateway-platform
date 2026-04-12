from functools import lru_cache
from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=False)

    app_name: str = 'llm-orchestrator'
    app_env: str = 'dev'
    log_level: str = 'INFO'
    host: str = '0.0.0.0'
    port: int = 8000
    default_timeout_seconds: float = 12.0

    redis_url: str | None = None
    cache_ttl_seconds: int = 300
    gateway_api_key: str | None = None
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    groq_enabled: bool = False
    groq_api_key: str | None = None
    groq_model: str = 'llama-3.3-70b-versatile'
    groq_base_url: str = 'https://api.groq.com/openai/v1'
    groq_timeout_seconds: float = 3.0
    groq_priority: int = 1

    openrouter_enabled: bool = False
    openrouter_api_key: str | None = None
    openrouter_model: str = 'openai/gpt-4o-mini'
    openrouter_base_url: str = 'https://openrouter.ai/api/v1'
    openrouter_timeout_seconds: float = 5.0
    openrouter_priority: int = 2
    openrouter_referer: str | None = None
    openrouter_title: str | None = None

    huggingface_enabled: bool = False
    huggingface_api_key: str | None = None
    huggingface_model: str = 'meta-llama/Llama-3.1-8B-Instruct'
    huggingface_base_url: str = 'https://router.huggingface.co/v1'
    huggingface_timeout_seconds: float = 8.0
    huggingface_priority: int = 3

    refinement_strategy: Literal['none', 'first_success', 'aggregate'] = 'aggregate'
    max_parallel_providers: int = 3
    provider_max_retries: int = 2
    retry_backoff_seconds: float = 0.25
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_recovery_seconds: int = 30

    n8n_base_url: str | None = None
    n8n_api_key: str | None = None
    n8n_timeout_seconds: float = 10.0
    n8n_complexity_threshold: int = 80

    infisical_enabled: bool = False
    infisical_host: str = 'https://app.infisical.com'
    infisical_token: str | None = None
    infisical_project_id: str | None = None
    infisical_environment_slug: str = 'dev'
    infisical_secret_path: str = '/'

    @computed_field
    @property
    def effective_port(self) -> int:
        return self.port


@lru_cache
def get_settings() -> Settings:
    return Settings()
