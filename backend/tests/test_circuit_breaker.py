"""
Tests for backend/circuit_breaker.py

Covers state transitions: CLOSED → OPEN → HALF_OPEN → CLOSED
"""
import time
import pytest
from backend.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ok(*_args, **_kwargs):
    return ["result"]


def _fail(*_args, **_kwargs):
    raise ConnectionError("service down")


# ── CLOSED state ──────────────────────────────────────────────────────────────

def test_initial_state_is_closed():
    cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=60)
    assert cb.state == CircuitState.CLOSED


def test_successful_call_stays_closed():
    cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=60)
    result = cb.call(_ok)
    assert result == ["result"]
    assert cb.state == CircuitState.CLOSED


def test_failure_below_threshold_stays_closed():
    cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=60)
    for _ in range(2):  # one below threshold
        with pytest.raises(ConnectionError):
            cb.call(_fail)
    assert cb.state == CircuitState.CLOSED


# ── Tripping to OPEN ──────────────────────────────────────────────────────────

def test_trip_to_open_after_threshold():
    cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=60)
    for _ in range(3):
        with pytest.raises(ConnectionError):
            cb.call(_fail)
    assert cb.state == CircuitState.OPEN


def test_open_circuit_raises_circuit_open_error():
    cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=60)
    with pytest.raises(ConnectionError):
        cb.call(_fail)  # trips circuit

    with pytest.raises(CircuitOpenError):
        cb.call(_ok)  # should be blocked


def test_open_circuit_does_not_call_underlying_function():
    cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=60)
    called = []

    def _track(*_a, **_kw):
        called.append(True)
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        cb.call(_track)  # trips

    with pytest.raises(CircuitOpenError):
        cb.call(_track)  # blocked — _track must NOT be called again

    assert len(called) == 1  # only the first (pre-trip) call reached it


# ── HALF_OPEN state ───────────────────────────────────────────────────────────

def test_transition_to_half_open_after_timeout():
    cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05)
    with pytest.raises(ConnectionError):
        cb.call(_fail)  # trips
    assert cb.state == CircuitState.OPEN

    time.sleep(0.1)  # wait for recovery timeout

    assert cb.state == CircuitState.HALF_OPEN


def test_successful_probe_closes_circuit():
    cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05)
    with pytest.raises(ConnectionError):
        cb.call(_fail)

    time.sleep(0.1)

    result = cb.call(_ok)  # probe succeeds
    assert result == ["result"]
    assert cb.state == CircuitState.CLOSED


def test_failed_probe_reopens_circuit():
    cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0.05)
    with pytest.raises(ConnectionError):
        cb.call(_fail)  # trip

    time.sleep(0.1)  # go HALF_OPEN

    with pytest.raises(ConnectionError):
        cb.call(_fail)  # probe fails → back to OPEN

    assert cb.state == CircuitState.OPEN


# ── Recovery after success ────────────────────────────────────────────────────

def test_success_resets_failure_count():
    """A success mid-way through failures should reset the counter."""
    cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=60)
    with pytest.raises(ConnectionError):
        cb.call(_fail)
    with pytest.raises(ConnectionError):
        cb.call(_fail)
    cb.call(_ok)  # reset
    with pytest.raises(ConnectionError):
        cb.call(_fail)
    # After reset + 1 new failure, circuit should still be CLOSED (not 3 total)
    assert cb.state == CircuitState.CLOSED


# ── Manual reset ──────────────────────────────────────────────────────────────

def test_manual_reset_closes_open_circuit():
    cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=9999)
    with pytest.raises(ConnectionError):
        cb.call(_fail)
    assert cb.state == CircuitState.OPEN

    cb.reset()
    assert cb.state == CircuitState.CLOSED


def test_after_manual_reset_calls_succeed():
    cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=9999)
    with pytest.raises(ConnectionError):
        cb.call(_fail)
    cb.reset()
    result = cb.call(_ok)
    assert result == ["result"]
