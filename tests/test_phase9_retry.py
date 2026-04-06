"""
Tests for Phase 9: Optimization and Robustness
Tests retry mechanisms, fallback chains, and performance optimizations
"""
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

from janus.utils.retry import FallbackChain, RetryConfig, retry_with_fallback


class TestRetryConfig(unittest.TestCase):
    """Test RetryConfig class"""

    def test_default_config(self):
        """Test default retry configuration"""
        config = RetryConfig()
        self.assertEqual(config.max_attempts, 3)
        self.assertEqual(config.initial_delay, 1.0)
        self.assertEqual(config.max_delay, 60.0)
        self.assertEqual(config.exponential_base, 2.0)
        self.assertTrue(config.jitter)

    def test_custom_config(self):
        """Test custom retry configuration"""
        config = RetryConfig(
            max_attempts=5, initial_delay=0.5, max_delay=30.0, exponential_base=3.0, jitter=False
        )
        self.assertEqual(config.max_attempts, 5)
        self.assertEqual(config.initial_delay, 0.5)
        self.assertEqual(config.max_delay, 30.0)
        self.assertEqual(config.exponential_base, 3.0)
        self.assertFalse(config.jitter)

    def test_calculate_delay_exponential(self):
        """Test exponential backoff delay calculation"""
        config = RetryConfig(initial_delay=1.0, exponential_base=2.0, max_delay=60.0, jitter=False)

        # Test exponential growth
        delay_0 = config.calculate_delay(0)
        delay_1 = config.calculate_delay(1)
        delay_2 = config.calculate_delay(2)

        self.assertEqual(delay_0, 1.0)  # 1 * 2^0
        self.assertEqual(delay_1, 2.0)  # 1 * 2^1
        self.assertEqual(delay_2, 4.0)  # 1 * 2^2

    def test_calculate_delay_max_cap(self):
        """Test delay is capped at max_delay"""
        config = RetryConfig(initial_delay=1.0, exponential_base=2.0, max_delay=5.0, jitter=False)

        delay = config.calculate_delay(10)  # Would be 1024 without cap
        self.assertEqual(delay, 5.0)

    def test_should_retry_on_exception(self):
        """Test exception type checking for retry"""
        config = RetryConfig(retry_on_exceptions=[ValueError, TypeError])

        self.assertTrue(config.should_retry(ValueError("test")))
        self.assertTrue(config.should_retry(TypeError("test")))
        self.assertFalse(config.should_retry(KeyError("test")))


class TestRetryDecorator(unittest.TestCase):
    """Test retry_with_fallback decorator"""

    def test_successful_first_attempt(self):
        """Test function succeeds on first attempt"""
        mock_func = Mock(return_value="success")

        config = RetryConfig(max_attempts=3)
        decorated = retry_with_fallback(config)(mock_func)

        result = decorated()

        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 1)

    def test_retry_until_success(self):
        """Test function retries and eventually succeeds"""
        # Fail twice, then succeed
        mock_func = Mock(side_effect=[Exception("fail 1"), Exception("fail 2"), "success"])

        config = RetryConfig(max_attempts=3, initial_delay=0.1)
        decorated = retry_with_fallback(config, log_failures=False)(mock_func)

        result = decorated()

        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 3)

    def test_exhausted_retries(self):
        """Test all retries exhausted raises exception"""
        mock_func = Mock(side_effect=Exception("persistent failure"))

        config = RetryConfig(max_attempts=2, initial_delay=0.1)
        decorated = retry_with_fallback(config, log_failures=False)(mock_func)

        with self.assertRaises(Exception) as context:
            decorated()

        self.assertIn("persistent failure", str(context.exception))
        self.assertEqual(mock_func.call_count, 2)

    def test_fallback_on_failure(self):
        """Test fallback function is called when retries exhausted"""
        mock_func = Mock(side_effect=Exception("always fails"))
        fallback_func = Mock(return_value="fallback result")

        config = RetryConfig(max_attempts=2, initial_delay=0.1)
        decorated = retry_with_fallback(config, fallback_func=fallback_func, log_failures=False)(
            mock_func
        )

        result = decorated()

        self.assertEqual(result, "fallback result")
        self.assertEqual(mock_func.call_count, 2)
        self.assertEqual(fallback_func.call_count, 1)

    def test_non_retryable_exception(self):
        """Test non-retryable exception is not retried"""
        mock_func = Mock(side_effect=KeyError("not retryable"))

        config = RetryConfig(
            max_attempts=3, retry_on_exceptions=[ValueError]  # Only retry ValueError
        )
        decorated = retry_with_fallback(config, log_failures=False)(mock_func)

        with self.assertRaises(KeyError):
            decorated()

        # Should fail immediately without retry
        self.assertEqual(mock_func.call_count, 1)


class TestFallbackChain(unittest.TestCase):
    """Test FallbackChain class"""

    def test_first_function_succeeds(self):
        """Test first function in chain succeeds"""
        func1 = Mock(return_value="result1")
        func2 = Mock(return_value="result2")

        chain = FallbackChain(log_attempts=False)
        chain.add("func1", func1)
        chain.add("func2", func2)

        result = chain.execute()

        self.assertEqual(result, "result1")
        self.assertEqual(func1.call_count, 1)
        self.assertEqual(func2.call_count, 0)  # Not called

    def test_fallback_to_second_function(self):
        """Test fallback to second function when first fails"""
        func1 = Mock(side_effect=Exception("func1 failed"))
        func2 = Mock(return_value="result2")

        chain = FallbackChain(log_attempts=False)
        chain.add("func1", func1)
        chain.add("func2", func2)

        result = chain.execute()

        self.assertEqual(result, "result2")
        self.assertEqual(func1.call_count, 1)
        self.assertEqual(func2.call_count, 1)

    def test_all_functions_fail(self):
        """Test all functions in chain fail"""
        func1 = Mock(side_effect=Exception("func1 failed"))
        func2 = Mock(side_effect=Exception("func2 failed"))
        func3 = Mock(side_effect=Exception("func3 failed"))

        chain = FallbackChain(log_attempts=False)
        chain.add("func1", func1)
        chain.add("func2", func2)
        chain.add("func3", func3)

        with self.assertRaises(Exception) as context:
            chain.execute()

        self.assertIn("func3 failed", str(context.exception))
        self.assertEqual(func1.call_count, 1)
        self.assertEqual(func2.call_count, 1)
        self.assertEqual(func3.call_count, 1)

    def test_chain_with_retry_config(self):
        """Test fallback chain with retry configuration"""
        # Fail twice then succeed
        func1 = Mock(side_effect=[Exception("fail 1"), Exception("fail 2"), "success"])

        chain = FallbackChain(log_attempts=False)
        chain.add("func1", func1, retry_config=RetryConfig(max_attempts=3, initial_delay=0.1))

        result = chain.execute()

        self.assertEqual(result, "success")
        self.assertEqual(func1.call_count, 3)

    def test_chain_with_arguments(self):
        """Test fallback chain passes arguments to functions"""
        func1 = Mock(side_effect=Exception("func1 failed"))
        func2 = Mock(return_value="result2")

        chain = FallbackChain(log_attempts=False)
        chain.add("func1", func1)
        chain.add("func2", func2)

        result = chain.execute("arg1", "arg2", kwarg1="value1")

        self.assertEqual(result, "result2")
        func1.assert_called_once_with("arg1", "arg2", kwarg1="value1")
        func2.assert_called_once_with("arg1", "arg2", kwarg1="value1")


class TestPerformanceMetrics(unittest.TestCase):
    """Test performance metrics tracking"""

    def test_retry_timing(self):
        """Test that retries add appropriate delays"""
        call_times = []

        def timed_func():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise Exception("retry me")
            return "success"

        config = RetryConfig(max_attempts=3, initial_delay=0.1, jitter=False)
        decorated = retry_with_fallback(config, log_failures=False)(timed_func)

        result = decorated()

        self.assertEqual(result, "success")
        self.assertEqual(len(call_times), 3)

        # Check delays between attempts (allowing some margin)
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        self.assertGreater(delay1, 0.09)  # ~0.1s
        self.assertGreater(delay2, 0.19)  # ~0.2s (exponential)


if __name__ == "__main__":
    unittest.main()
