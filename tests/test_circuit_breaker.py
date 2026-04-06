"""
Unit tests for Circuit Breaker

Tests circuit breaker state transitions and failure handling.
"""

import time
from unittest.mock import Mock
import pytest

from janus.safety.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitState,
    get_circuit_breaker,
)


def _fail_with_error(error_msg="fail"):
    """Helper function to raise an exception"""
    raise ValueError(error_msg)


class TestCircuitBreaker:
    """Test cases for CircuitBreaker"""

    def test_initial_state_is_closed(self):
        """Test that circuit breaker starts in CLOSED state"""
        breaker = CircuitBreaker("test")
        assert breaker.state == CircuitState.CLOSED

    def test_successful_calls_keep_circuit_closed(self):
        """Test that successful calls keep the circuit closed"""
        breaker = CircuitBreaker("test")
        
        for _ in range(10):
            result = breaker.call(lambda: "success")
            assert result == "success"
        
        assert breaker.state == CircuitState.CLOSED
        stats = breaker.get_stats()
        assert stats["successful_calls"] == 10
        assert stats["failed_calls"] == 0

    def test_failures_open_circuit(self):
        """Test that repeated failures open the circuit"""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test", config)
        
        # Fail 3 times to reach threshold
        for i in range(3):
            with pytest.raises(ValueError):
                breaker.call(_fail_with_error)
        
        # Circuit should now be OPEN
        assert breaker.state == CircuitState.OPEN
        stats = breaker.get_stats()
        assert stats["failed_calls"] == 3

    def test_open_circuit_rejects_calls(self):
        """Test that OPEN circuit rejects calls immediately"""
        config = CircuitBreakerConfig(failure_threshold=2, timeout_seconds=10)
        breaker = CircuitBreaker("test", config)
        
        # Fail twice to open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(_fail_with_error)
        
        assert breaker.state == CircuitState.OPEN
        
        # Next call should be rejected immediately
        with pytest.raises(CircuitBreakerError, match="Circuit breaker.*is OPEN"):
            breaker.call(lambda: "should not execute")
        
        stats = breaker.get_stats()
        assert stats["rejected_calls"] == 1

    def test_half_open_after_timeout(self):
        """Test that circuit transitions to HALF_OPEN after timeout"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            timeout_seconds=0.1  # Short timeout for testing
        )
        breaker = CircuitBreaker("test", config)
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(_fail_with_error)
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for timeout
        time.sleep(0.15)
        
        # Next call should transition to HALF_OPEN and execute
        result = breaker.call(lambda: "success")
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN

    def test_half_open_closes_after_success_threshold(self):
        """Test that HALF_OPEN circuit closes after enough successes"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
            timeout_seconds=0.1
        )
        breaker = CircuitBreaker("test", config)
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(_fail_with_error)
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for timeout
        time.sleep(0.15)
        
        # Make 2 successful calls to close circuit
        breaker.call(lambda: "success1")
        assert breaker.state == CircuitState.HALF_OPEN
        
        breaker.call(lambda: "success2")
        assert breaker.state == CircuitState.CLOSED

    def test_half_open_reopens_on_failure(self):
        """Test that HALF_OPEN circuit reopens immediately on failure"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            timeout_seconds=0.1
        )
        breaker = CircuitBreaker("test", config)
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(_fail_with_error)
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for timeout and transition to HALF_OPEN
        time.sleep(0.15)
        breaker.call(lambda: "success")
        assert breaker.state == CircuitState.HALF_OPEN
        
        # Failure should immediately reopen circuit
        with pytest.raises(ValueError):
            breaker.call(_fail_with_error)
        
        assert breaker.state == CircuitState.OPEN

    def test_manual_reset(self):
        """Test manual circuit reset"""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker("test", config)
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(_fail_with_error)
        
        assert breaker.state == CircuitState.OPEN
        
        # Manual reset
        breaker.reset()
        
        assert breaker.state == CircuitState.CLOSED
        stats = breaker.get_stats()
        assert stats["failure_count"] == 0

    def test_state_change_callback(self):
        """Test that state change callback is invoked"""
        callback_calls = []
        
        def on_state_change(old_state, new_state):
            callback_calls.append((old_state, new_state))
        
        config = CircuitBreakerConfig(
            failure_threshold=2,
            on_state_change=on_state_change
        )
        breaker = CircuitBreaker("test", config)
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(_fail_with_error)
        
        # Should have one transition: CLOSED -> OPEN
        assert len(callback_calls) == 1
        assert callback_calls[0] == (CircuitState.CLOSED, CircuitState.OPEN)

    def test_statistics_tracking(self):
        """Test that statistics are tracked correctly"""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test", config)
        
        # Successful calls
        for _ in range(5):
            breaker.call(lambda: "ok")
        
        # Failed calls
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(_fail_with_error)
        
        stats = breaker.get_stats()
        assert stats["total_calls"] == 7
        assert stats["successful_calls"] == 5
        assert stats["failed_calls"] == 2
        assert stats["rejected_calls"] == 0
        assert stats["state"] == "closed"  # Still closed (threshold is 3)

    def test_thread_safety(self):
        """Test that circuit breaker is thread-safe"""
        import threading
        
        breaker = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=10))
        results = []
        
        def worker():
            for _ in range(10):
                try:
                    result = breaker.call(lambda: "ok")
                    results.append(result)
                except Exception:
                    pass
        
        # Run multiple threads concurrently
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All calls should succeed
        assert len(results) == 50


class TestCircuitBreakerRegistry:
    """Test cases for CircuitBreakerRegistry"""

    def test_get_circuit_breaker_creates_new(self):
        """Test that get_circuit_breaker creates a new breaker"""
        breaker = get_circuit_breaker("test_service")
        
        assert breaker is not None
        assert breaker.name == "test_service"

    def test_get_circuit_breaker_returns_same_instance(self):
        """Test that get_circuit_breaker returns the same instance"""
        breaker1 = get_circuit_breaker("test_service")
        breaker2 = get_circuit_breaker("test_service")
        
        assert breaker1 is breaker2

    def test_different_names_get_different_breakers(self):
        """Test that different names get different breaker instances"""
        breaker1 = get_circuit_breaker("service1")
        breaker2 = get_circuit_breaker("service2")
        
        assert breaker1 is not breaker2
        assert breaker1.name == "service1"
        assert breaker2.name == "service2"


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker"""

    def test_protects_against_failing_service(self):
        """Test that circuit breaker protects against a failing service"""
        call_count = 0
        
        def failing_service():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Service unavailable")
        
        config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout_seconds=0.1
        )
        breaker = CircuitBreaker("failing_service", config)
        
        # Fail 3 times to open circuit
        for _ in range(3):
            with pytest.raises(ConnectionError):
                breaker.call(failing_service)
        
        assert call_count == 3
        assert breaker.state == CircuitState.OPEN
        
        # Next calls should be rejected without calling the service
        for _ in range(5):
            with pytest.raises(CircuitBreakerError):
                breaker.call(failing_service)
        
        # Service wasn't called (still at 3)
        assert call_count == 3

    def test_recovers_when_service_heals(self):
        """Test that circuit breaker recovers when service heals"""
        call_count = 0
        service_healthy = False
        
        def flaky_service():
            nonlocal call_count
            call_count += 1
            if not service_healthy:
                raise ConnectionError("Service unavailable")
            return "ok"
        
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
            timeout_seconds=0.1
        )
        breaker = CircuitBreaker("flaky_service", config)
        
        # Fail twice to open circuit
        for _ in range(2):
            with pytest.raises(ConnectionError):
                breaker.call(flaky_service)
        
        assert breaker.state == CircuitState.OPEN
        
        # Service becomes healthy
        service_healthy = True
        
        # Wait for timeout
        time.sleep(0.15)
        
        # Circuit should attempt recovery and succeed
        result1 = breaker.call(flaky_service)
        assert result1 == "ok"
        assert breaker.state == CircuitState.HALF_OPEN
        
        result2 = breaker.call(flaky_service)
        assert result2 == "ok"
        assert breaker.state == CircuitState.CLOSED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
