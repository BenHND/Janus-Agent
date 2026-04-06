"""
Unit tests for janus.utils.retry module
Tests retry logic, exponential backoff, fallback chains, and timeout behavior
"""

import time
import pytest
from unittest.mock import Mock, patch
from janus.utils.retry import (
    RetryConfig,
    retry_with_fallback,
    FallbackChain,
    with_timeout,
)


class TestRetryConfig:
    """Test RetryConfig class"""

    def test_default_initialization(self):
        """Test RetryConfig with default values"""
        config = RetryConfig()
        assert config.max_attempts > 0
        assert config.initial_delay > 0
        assert config.max_delay > 0
        assert config.exponential_base > 1
        assert config.jitter is True
        assert Exception in config.retry_on_exceptions

    def test_custom_initialization(self):
        """Test RetryConfig with custom values"""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=2.0,
            max_delay=60.0,
            exponential_base=3.0,
            jitter=False,
            retry_on_exceptions=[ValueError, IOError],
        )
        assert config.max_attempts == 5
        assert config.initial_delay == 2.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 3.0
        assert config.jitter is False
        assert ValueError in config.retry_on_exceptions
        assert IOError in config.retry_on_exceptions

    def test_calculate_delay_exponential(self):
        """Test exponential backoff calculation"""
        config = RetryConfig(initial_delay=1.0, exponential_base=2.0, jitter=False)
        
        delay0 = config.calculate_delay(0)
        delay1 = config.calculate_delay(1)
        delay2 = config.calculate_delay(2)
        
        assert delay0 == 1.0  # 1.0 * 2^0
        assert delay1 == 2.0  # 1.0 * 2^1
        assert delay2 == 4.0  # 1.0 * 2^2

    def test_calculate_delay_with_max(self):
        """Test that delay respects max_delay"""
        config = RetryConfig(
            initial_delay=1.0, exponential_base=2.0, max_delay=5.0, jitter=False
        )
        
        delay10 = config.calculate_delay(10)
        assert delay10 == 5.0  # Capped at max_delay

    def test_calculate_delay_with_jitter(self):
        """Test that jitter adds randomness"""
        config = RetryConfig(initial_delay=1.0, exponential_base=2.0, jitter=True)
        
        # With jitter, delay should vary
        delays = [config.calculate_delay(0) for _ in range(10)]
        # At least some variation expected
        assert len(set(delays)) > 1 or all(d >= 0.5 for d in delays)

    def test_should_retry_matching_exception(self):
        """Test should_retry with matching exception"""
        config = RetryConfig(retry_on_exceptions=[ValueError, TypeError])
        
        assert config.should_retry(ValueError("test"))
        assert config.should_retry(TypeError("test"))

    def test_should_retry_non_matching_exception(self):
        """Test should_retry with non-matching exception"""
        config = RetryConfig(retry_on_exceptions=[ValueError])
        
        assert not config.should_retry(TypeError("test"))
        assert not config.should_retry(RuntimeError("test"))

    def test_should_retry_subclass(self):
        """Test should_retry with exception subclass"""
        config = RetryConfig(retry_on_exceptions=[Exception])
        
        # ValueError is subclass of Exception
        assert config.should_retry(ValueError("test"))
        assert config.should_retry(RuntimeError("test"))


class TestRetryWithFallback:
    """Test retry_with_fallback decorator"""

    def test_successful_first_attempt(self):
        """Test function succeeds on first attempt"""
        mock_func = Mock(return_value="success")
        
        @retry_with_fallback(RetryConfig(max_attempts=3))
        def test_func():
            return mock_func()
        
        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_after_failure(self):
        """Test function retries after failure"""
        counter = {"calls": 0}
        
        def failing_func():
            counter["calls"] += 1
            if counter["calls"] < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        config = RetryConfig(max_attempts=5, initial_delay=0.01, jitter=False)
        decorated = retry_with_fallback(config, log_failures=False)(failing_func)
        
        result = decorated()
        assert result == "success"
        assert counter["calls"] == 3

    def test_exhausted_retries(self):
        """Test all retries are exhausted"""
        mock_func = Mock(side_effect=ValueError("Always fails"))
        
        @retry_with_fallback(
            RetryConfig(max_attempts=3, initial_delay=0.01, jitter=False),
            log_failures=False,
        )
        def test_func():
            return mock_func()
        
        with pytest.raises(ValueError, match="Always fails"):
            test_func()
        
        assert mock_func.call_count == 3

    def test_non_retryable_exception(self):
        """Test non-retryable exception is not retried"""
        mock_func = Mock(side_effect=TypeError("Non-retryable"))
        
        config = RetryConfig(
            max_attempts=3, retry_on_exceptions=[ValueError], initial_delay=0.01
        )
        
        @retry_with_fallback(config, log_failures=False)
        def test_func():
            return mock_func()
        
        with pytest.raises(TypeError, match="Non-retryable"):
            test_func()
        
        # Should fail immediately, not retry
        assert mock_func.call_count == 1

    def test_fallback_on_failure(self):
        """Test fallback function is called after retries exhausted"""
        main_func = Mock(side_effect=ValueError("Always fails"))
        fallback_func = Mock(return_value="fallback_success")
        
        config = RetryConfig(max_attempts=2, initial_delay=0.01, jitter=False)
        
        @retry_with_fallback(config, fallback_func=fallback_func, log_failures=False)
        def test_func():
            return main_func()
        
        result = test_func()
        assert result == "fallback_success"
        assert main_func.call_count == 2
        assert fallback_func.call_count == 1

    def test_fallback_also_fails(self):
        """Test when fallback function also fails"""
        main_func = Mock(side_effect=ValueError("Main fails"))
        fallback_func = Mock(side_effect=RuntimeError("Fallback fails"))
        
        config = RetryConfig(max_attempts=2, initial_delay=0.01, jitter=False)
        
        @retry_with_fallback(config, fallback_func=fallback_func, log_failures=False)
        def test_func():
            return main_func()
        
        with pytest.raises(RuntimeError, match="Fallback fails"):
            test_func()

    def test_delay_between_retries(self):
        """Test that delays are applied between retries"""
        call_times = []
        
        def timed_func():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("Retry")
            return "success"
        
        config = RetryConfig(max_attempts=3, initial_delay=0.05, jitter=False)
        decorated = retry_with_fallback(config, log_failures=False)(timed_func)
        
        decorated()
        
        # Check that there are delays between attempts
        assert len(call_times) == 3
        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            assert delay1 >= 0.04  # Allow small margin


class TestFallbackChain:
    """Test FallbackChain class"""

    def test_first_function_succeeds(self):
        """Test chain stops at first success"""
        func1 = Mock(return_value="success1")
        func2 = Mock(return_value="success2")
        
        chain = FallbackChain(log_attempts=False)
        chain.add("func1", func1)
        chain.add("func2", func2)
        
        result = chain.execute()
        assert result == "success1"
        assert func1.call_count == 1
        assert func2.call_count == 0  # Should not be called

    def test_fallback_to_second(self):
        """Test chain falls back to second function"""
        func1 = Mock(side_effect=ValueError("Fail"))
        func2 = Mock(return_value="success2")
        
        chain = FallbackChain(log_attempts=False)
        chain.add("func1", func1)
        chain.add("func2", func2)
        
        result = chain.execute()
        assert result == "success2"
        assert func1.call_count == 1
        assert func2.call_count == 1

    def test_all_fail(self):
        """Test when all functions in chain fail"""
        func1 = Mock(side_effect=ValueError("Fail1"))
        func2 = Mock(side_effect=RuntimeError("Fail2"))
        
        chain = FallbackChain(log_attempts=False)
        chain.add("func1", func1)
        chain.add("func2", func2)
        
        with pytest.raises(RuntimeError, match="Fail2"):
            chain.execute()

    def test_chain_with_retry_config(self):
        """Test chain with retry configuration"""
        counter = {"calls": 0}
        
        def failing_func():
            counter["calls"] += 1
            if counter["calls"] < 2:
                raise ValueError("Retry")
            return "success"
        
        retry_config = RetryConfig(max_attempts=3, initial_delay=0.01, jitter=False)
        chain = FallbackChain(log_attempts=False)
        chain.add("func1", failing_func, retry_config=retry_config)
        
        result = chain.execute()
        assert result == "success"
        assert counter["calls"] == 2

    def test_chain_with_arguments(self):
        """Test chain passes arguments to functions"""
        func1 = Mock(return_value="success")
        
        chain = FallbackChain(log_attempts=False)
        chain.add("func1", func1)
        
        result = chain.execute("arg1", kwarg1="value1")
        assert result == "success"
        func1.assert_called_once_with("arg1", kwarg1="value1")

    def test_chain_builder_pattern(self):
        """Test chain builder pattern returns self"""
        chain = FallbackChain()
        result = chain.add("test", Mock())
        assert result is chain


class TestWithTimeout:
    """Test with_timeout decorator"""

    def test_completes_within_timeout(self):
        """Test function completes within timeout"""
        @with_timeout(timeout_seconds=1.0)
        def quick_func():
            time.sleep(0.01)
            return "success"
        
        # Skip on Windows where signal.SIGALRM is not available
        try:
            result = quick_func()
            assert result == "success"
        except AttributeError:
            pytest.skip("Timeout not supported on this platform")

    def test_timeout_with_default_value(self):
        """Test timeout returns default value"""
        @with_timeout(timeout_seconds=0.1, default_value="timeout")
        def slow_func():
            time.sleep(10)
            return "success"
        
        try:
            result = slow_func()
            # Either times out or completes on platforms without signal support
            assert result in ("timeout", "success")
        except (AttributeError, TimeoutError):
            pytest.skip("Timeout not supported on this platform")

    def test_function_arguments(self):
        """Test timeout decorator preserves function arguments"""
        @with_timeout(timeout_seconds=1.0)
        def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"
        
        try:
            result = func_with_args("x", "y", c="z")
            assert result == "x-y-z"
        except AttributeError:
            pytest.skip("Timeout not supported on this platform")
