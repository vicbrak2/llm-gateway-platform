from __future__ import annotations

import time


class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 3, recovery_timeout_seconds: int = 30) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.failure_count = 0
        self.opened_until = 0.0

    def allow_request(self) -> bool:
        now = time.time()
        if self.opened_until and now >= self.opened_until:
            self.opened_until = 0.0
            self.failure_count = 0
        return now >= self.opened_until

    def record_success(self) -> None:
        self.failure_count = 0
        self.opened_until = 0.0

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.opened_until = time.time() + self.recovery_timeout_seconds

    def snapshot(self) -> dict[str, float | int | str]:
        state = 'open' if time.time() < self.opened_until else 'closed'
        return {'provider': self.name, 'state': state, 'failure_count': self.failure_count, 'opened_until': self.opened_until}


_BREAKERS: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, failure_threshold: int = 3, recovery_timeout_seconds: int = 30) -> CircuitBreaker:
    breaker = _BREAKERS.get(name)
    if breaker is None:
        breaker = CircuitBreaker(name=name, failure_threshold=failure_threshold, recovery_timeout_seconds=recovery_timeout_seconds)
        _BREAKERS[name] = breaker
    return breaker


def get_breaker_snapshots() -> list[dict[str, float | int | str]]:
    return [breaker.snapshot() for _, breaker in sorted(_BREAKERS.items())]
