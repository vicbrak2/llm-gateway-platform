import time

from app.services.circuit_breaker import CircuitBreaker


def test_circuit_breaker_opens_after_threshold() -> None:
    breaker = CircuitBreaker('demo', failure_threshold=2, recovery_timeout_seconds=10)
    assert breaker.allow_request() is True
    breaker.record_failure()
    assert breaker.allow_request() is True
    breaker.record_failure()
    assert breaker.allow_request() is False


def test_circuit_breaker_recovers_after_timeout() -> None:
    breaker = CircuitBreaker('demo', failure_threshold=1, recovery_timeout_seconds=1)
    breaker.record_failure()
    assert breaker.allow_request() is False
    breaker.opened_until = time.time() - 1
    assert breaker.allow_request() is True
