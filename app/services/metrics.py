from __future__ import annotations

from dataclasses import dataclass

from app.schemas import MetricsResponse, ProviderResult


@dataclass
class MetricsRegistry:
    requests_total: int = 0
    request_errors_total: int = 0
    chat_requests_total: int = 0
    workflow_requests_total: int = 0
    cache_hits_total: int = 0
    cache_misses_total: int = 0
    provider_success_total: int = 0
    provider_failure_total: int = 0
    total_request_latency_ms: int = 0

    def record_request(self, path: str, status_code: int, latency_ms: int) -> None:
        self.requests_total += 1
        self.total_request_latency_ms += latency_ms
        if path == '/v1/chat/completions':
            self.chat_requests_total += 1
        elif path == '/v1/workflows/trigger':
            self.workflow_requests_total += 1
        if status_code >= 400:
            self.request_errors_total += 1

    def record_cache_hit(self) -> None:
        self.cache_hits_total += 1

    def record_cache_miss(self) -> None:
        self.cache_misses_total += 1

    def record_provider_results(self, results: list[ProviderResult]) -> None:
        for result in results:
            if result.success:
                self.provider_success_total += 1
            else:
                self.provider_failure_total += 1

    def snapshot(self) -> MetricsResponse:
        avg = int(self.total_request_latency_ms / self.requests_total) if self.requests_total else 0
        return MetricsResponse(
            requests_total=self.requests_total,
            request_errors_total=self.request_errors_total,
            chat_requests_total=self.chat_requests_total,
            workflow_requests_total=self.workflow_requests_total,
            cache_hits_total=self.cache_hits_total,
            cache_misses_total=self.cache_misses_total,
            provider_success_total=self.provider_success_total,
            provider_failure_total=self.provider_failure_total,
            average_request_latency_ms=avg,
        )


metrics_registry = MetricsRegistry()
