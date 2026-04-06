"""
Unit tests for LLM Retry Handler

Tests retry logic, error classification, and exponential backoff.
"""

import time
from unittest.mock import Mock
import pytest
import requests

from janus.ai.llm.retry_handler import (
    LLMRetryHandler,
    RetryConfig,
    ErrorCategory,
    classify_error,
    calculate_delay,
    get_retry_handler,
)


class TestErrorClassification:
    """Test error classification logic"""

    def test_classify_network_error(self):
        """Test network error classification"""
        error = requests.exceptions.ConnectionError("Connection refused")
        category, retryable = classify_error(error)
        
        assert category == ErrorCategory.NETWORK
        assert retryable is True

    def test_classify_timeout_error(self):
        """Test timeout error classification"""
        error = requests.exceptions.Timeout("Request timed out")
        category, retryable = classify_error(error)
        
        assert category == ErrorCategory.TIMEOUT
        assert retryable is True

    def test_classify_http_429_rate_limit(self):
        """Test rate limit error classification"""
        response = Mock()
        response.status_code = 429
        error = requests.exceptions.HTTPError(response=response)
        
        category, retryable = classify_error(error)
        
        assert category == ErrorCategory.RATE_LIMIT
        assert retryable is True

    def test_classify_http_5xx_server_error(self):
        """Test server error classification"""
        response = Mock()
        response.status_code = 503
        error = requests.exceptions.HTTPError(response=response)
        
        category, retryable = classify_error(error)
        
        assert category == ErrorCategory.SERVER_ERROR
        assert retryable is True

    def test_classify_http_4xx_client_error(self):
        """Test client error classification (non-retryable)"""
        response = Mock()
        response.status_code = 404
        error = requests.exceptions.HTTPError(response=response)
        
        category, retryable = classify_error(error)
        
        assert category == ErrorCategory.CLIENT_ERROR
        assert retryable is False

    def test_classify_unknown_error(self):
        """Test unknown error classification"""
        error = ValueError("Some random error")
        category, retryable = classify_error(error)
        
        assert category == ErrorCategory.UNKNOWN
        assert retryable is False


class TestDelayCalculation:
    """Test exponential backoff delay calculation"""

    def test_delay_increases_exponentially(self):
        """Test that delay increases exponentially with attempts"""
        config = RetryConfig(
            initial_delay_ms=1000,
            exponential_base=2.0,
            jitter_factor=0.0  # No jitter for predictable testing
        )
        
        # Attempt 0: 1000ms
        delay_0 = calculate_delay(0, config, ErrorCategory.NETWORK)
        assert 0.9 <= delay_0 <= 1.1  # ~1 second
        
        # Attempt 1: 2000ms
        delay_1 = calculate_delay(1, config, ErrorCategory.NETWORK)
        assert 1.9 <= delay_1 <= 2.1  # ~2 seconds
        
        # Attempt 2: 4000ms
        delay_2 = calculate_delay(2, config, ErrorCategory.NETWORK)
        assert 3.9 <= delay_2 <= 4.1  # ~4 seconds

    def test_delay_capped_at_max(self):
        """Test that delay is capped at max_delay_ms"""
        config = RetryConfig(
            initial_delay_ms=1000,
            max_delay_ms=5000,
            exponential_base=2.0,
            jitter_factor=0.0
        )
        
        # Attempt 10 would be 1024 seconds, but should cap at 5
        delay = calculate_delay(10, config, ErrorCategory.NETWORK)
        assert delay <= 5.5  # Max + some margin for jitter

    def test_rate_limit_gets_extra_delay(self):
        """Test that rate limit errors get 2x delay"""
        config = RetryConfig(
            initial_delay_ms=1000,
            jitter_factor=0.0
        )
        
        delay_network = calculate_delay(0, config, ErrorCategory.NETWORK)
        delay_rate_limit = calculate_delay(0, config, ErrorCategory.RATE_LIMIT)
        
        # Rate limit should be roughly 2x
        assert delay_rate_limit > delay_network * 1.8


class TestLLMRetryHandler:
    """Test retry handler functionality"""

    def test_successful_call_no_retry(self):
        """Test that successful calls don't retry"""
        handler = LLMRetryHandler(RetryConfig(max_retries=3))
        
        call_count = 0
        def succeed_immediately():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = handler.execute_with_retry(succeed_immediately, "test")
        
        assert result == "success"
        assert call_count == 1
        assert handler.stats["successful_calls"] == 1
        assert handler.stats["total_retries"] == 0

    def test_retries_on_network_error(self):
        """Test that network errors are retried"""
        handler = LLMRetryHandler(RetryConfig(
            max_retries=3,
            initial_delay_ms=10,  # Very short for testing
        ))
        
        call_count = 0
        def fail_twice_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise requests.exceptions.ConnectionError("Connection failed")
            return "success"
        
        result = handler.execute_with_retry(fail_twice_then_succeed, "test")
        
        assert result == "success"
        assert call_count == 3
        assert handler.stats["successful_calls"] == 1
        assert handler.stats["total_retries"] == 2

    def test_does_not_retry_client_errors(self):
        """Test that client errors (4xx) are not retried"""
        handler = LLMRetryHandler(RetryConfig(max_retries=3))
        
        call_count = 0
        def client_error():
            nonlocal call_count
            call_count += 1
            response = Mock()
            response.status_code = 400
            raise requests.exceptions.HTTPError(response=response)
        
        with pytest.raises(requests.exceptions.HTTPError):
            handler.execute_with_retry(client_error, "test")
        
        # Should only be called once (no retries)
        assert call_count == 1
        assert handler.stats["failed_calls"] == 1
        assert handler.stats["total_retries"] == 0

    def test_exhausts_retries(self):
        """Test that retries are exhausted after max attempts"""
        handler = LLMRetryHandler(RetryConfig(
            max_retries=2,
            initial_delay_ms=10,
        ))
        
        call_count = 0
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise requests.exceptions.ConnectionError("Always fails")
        
        with pytest.raises(requests.exceptions.ConnectionError):
            handler.execute_with_retry(always_fail, "test")
        
        # Should be called 3 times (initial + 2 retries)
        assert call_count == 3
        assert handler.stats["failed_calls"] == 1
        assert handler.stats["total_retries"] == 2

    def test_retry_callback_invoked(self):
        """Test that retry callback is called on each retry"""
        callback_calls = []
        
        def on_retry(attempt, error, delay):
            callback_calls.append((attempt, str(error), delay))
        
        config = RetryConfig(
            max_retries=2,
            initial_delay_ms=10,
            on_retry=on_retry
        )
        handler = LLMRetryHandler(config)
        
        call_count = 0
        def fail_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise requests.exceptions.Timeout("Timeout")
            return "success"
        
        handler.execute_with_retry(fail_once, "test")
        
        # Callback should be called once
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == 1  # First retry

    def test_stats_tracking(self):
        """Test that stats are tracked correctly"""
        handler = LLMRetryHandler(RetryConfig(
            max_retries=2,
            initial_delay_ms=10,
        ))
        
        # Successful call
        handler.execute_with_retry(lambda: "ok", "test1")
        
        # Failed call with retries
        try:
            call_count = 0
            def fail_twice():
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise requests.exceptions.Timeout("Timeout")
                return "ok"
            handler.execute_with_retry(fail_twice, "test2")
        except:
            pass
        
        stats = handler.get_stats()
        assert stats["total_calls"] == 2
        assert stats["successful_calls"] == 2
        assert stats["total_retries"] == 2

    def test_timeout_error_retried_when_configured(self):
        """Test that timeout errors are retried when configured"""
        handler = LLMRetryHandler(RetryConfig(
            max_retries=2,
            initial_delay_ms=10,
            retry_on_timeout=True,
        ))
        
        call_count = 0
        def timeout_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise requests.exceptions.Timeout("Timeout")
            return "success"
        
        result = handler.execute_with_retry(timeout_once, "test")
        
        assert result == "success"
        assert call_count == 2

    def test_timeout_error_not_retried_when_disabled(self):
        """Test that timeout errors are not retried when disabled"""
        handler = LLMRetryHandler(RetryConfig(
            max_retries=2,
            retry_on_timeout=False,
        ))
        
        call_count = 0
        def always_timeout():
            nonlocal call_count
            call_count += 1
            raise requests.exceptions.Timeout("Timeout")
        
        with pytest.raises(requests.exceptions.Timeout):
            handler.execute_with_retry(always_timeout, "test")
        
        # Should not retry
        assert call_count == 1


class TestGlobalRetryHandler:
    """Test global retry handler singleton"""

    def test_get_retry_handler_returns_singleton(self):
        """Test that get_retry_handler returns the same instance"""
        handler1 = get_retry_handler()
        handler2 = get_retry_handler()
        
        assert handler1 is handler2

    def test_global_handler_has_default_config(self):
        """Test that global handler has sensible defaults"""
        handler = get_retry_handler()
        
        assert handler.config.max_retries == 3
        assert handler.config.initial_delay_ms == 1000
        assert handler.config.max_delay_ms == 30000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
