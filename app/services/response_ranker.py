from __future__ import annotations

from app.schemas import ProviderResult


class ResponseRanker:
    def rank(self, results: list[ProviderResult]) -> list[ProviderResult]:
        return sorted(results, key=self._sort_key)

    def choose_winner(self, results: list[ProviderResult]) -> ProviderResult | None:
        ranked = self.rank(results)
        return ranked[0] if ranked else None

    def merge_contents(self, results: list[ProviderResult]) -> str:
        ranked = [r for r in self.rank(results) if r.success and r.content.strip()]
        return '\n\n---\n\n'.join([f'[{r.provider}]\n{r.content.strip()}' for r in ranked])

    @staticmethod
    def _sort_key(result: ProviderResult) -> tuple[int, int, int, str]:
        success_rank = 0 if result.success and result.content.strip() else 1
        error_penalty = 0 if result.error is None else 1
        return (success_rank, error_penalty, result.latency_ms, result.provider)
