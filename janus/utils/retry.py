"""
Retry and fallback utilities for Janus
Ticket 9.3: Error Handling & Fallback
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, List, Optional, Type

from ..constants import (
    EXPONENTIAL_BACKOFF_BASE,
    INITIAL_RETRY_DELAY,
    JITTER_MULTIPLIER_MIN,
    MAX_RETRY_ATTEMPTS,
    MAX_RETRY_DELAY,
)


class RetryConfig:
    """Configuration for retry behavior"""

    def __init__(
        self,
        max_attempts: int = MAX_RETRY_ATTEMPTS,
        initial_delay: float = INITIAL_RETRY_DELAY,
        max_delay: float = MAX_RETRY_DELAY,
        exponential_base: float = EXPONENTIAL_BACKOFF_BASE,
        jitter: bool = True,
        retry_on_exceptions: Optional[List[Type[Exception]]] = None,
    ):
        """
        Initialize retry configuration

        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to delay
            retry_on_exceptions: List of exception types to retry on (None = all)
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on_exceptions = retry_on_exceptions or [Exception]

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        import random

        # Exponential backoff
        delay = min(self.initial_delay * (self.exponential_base**attempt), self.max_delay)

        # Add jitter if enabled
        if self.jitter:
            delay = delay * (JITTER_MULTIPLIER_MIN + random.random())

        return delay

    def should_retry(self, exception: Exception) -> bool:
        """
        Check if exception should trigger a retry

        Args:
            exception: Exception that occurred

        Returns:
            True if should retry
        """
        return any(isinstance(exception, exc_type) for exc_type in self.retry_on_exceptions)


def retry_with_fallback(
    config: Optional[RetryConfig] = None,
    fallback_func: Optional[Callable] = None,
    log_failures: bool = True,
):
    """
    Decorator for retrying functions with exponential backoff and fallback

    Args:
        config: Retry configuration (uses default if None)
        fallback_func: Fallback function to call if all retries fail
        log_failures: Log retry attempts and failures

    Returns:
        Decorated function

    Example:
        @retry_with_fallback(RetryConfig(max_attempts=3))
        def unreliable_function():
            # Code that might fail
            pass
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    result = func(*args, **kwargs)

                    # Log successful retry
                    if attempt > 0 and log_failures:
                        logging.info(f"Function {func.__name__} succeeded on attempt {attempt + 1}")

                    return result

                except Exception as e:
                    last_exception = e

                    # Check if we should retry this exception
                    if not config.should_retry(e):
                        if log_failures:
                            logging.error(
                                f"Function {func.__name__} failed with non-retryable error: {e}"
                            )
                        raise

                    # Check if we have more attempts
                    if attempt < config.max_attempts - 1:
                        delay = config.calculate_delay(attempt)

                        if log_failures:
                            logging.warning(
                                f"Function {func.__name__} failed (attempt {attempt + 1}/{config.max_attempts}): {e}. "
                                f"Retrying in {delay:.2f}s..."
                            )

                        time.sleep(delay)
                    else:
                        if log_failures:
                            logging.error(
                                f"Function {func.__name__} failed after {config.max_attempts} attempts: {e}"
                            )

            # All retries exhausted, try fallback if available
            if fallback_func:
                if log_failures:
                    logging.info(f"Attempting fallback for {func.__name__}")
                try:
                    return fallback_func(*args, **kwargs)
                except Exception as fallback_error:
                    if log_failures:
                        logging.error(f"Fallback also failed: {fallback_error}")
                    raise fallback_error

            # No fallback available, raise the last exception
            raise last_exception

        return wrapper

    return decorator


class FallbackChain:
    """
    Execute a chain of fallback functions until one succeeds
    """

    def __init__(self, log_attempts: bool = True):
        """
        Initialize fallback chain

        Args:
            log_attempts: Log fallback attempts
        """
        self.log_attempts = log_attempts
        self._chain: List[tuple[str, Callable, Optional[RetryConfig]]] = []

    def add(
        self, name: str, func: Callable, retry_config: Optional[RetryConfig] = None
    ) -> "FallbackChain":
        """
        Add a function to the fallback chain

        Args:
            name: Name for the function (for logging)
            func: Function to execute
            retry_config: Optional retry configuration for this function

        Returns:
            Self for chaining
        """
        self._chain.append((name, func, retry_config))
        return self

    def execute(self, *args, **kwargs) -> Any:
        """
        Execute the fallback chain

        Args:
            *args: Arguments to pass to functions
            **kwargs: Keyword arguments to pass to functions

        Returns:
            Result from first successful function

        Raises:
            Exception: If all functions in chain fail
        """
        last_exception = None

        for name, func, retry_config in self._chain:
            try:
                if self.log_attempts:
                    logging.info(f"Attempting: {name}")

                # Apply retry if configured
                if retry_config:
                    retried_func = retry_with_fallback(
                        config=retry_config, log_failures=self.log_attempts
                    )(func)
                    result = retried_func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                if self.log_attempts:
                    logging.info(f"Success: {name}")

                return result

            except Exception as e:
                last_exception = e
                if self.log_attempts:
                    logging.warning(f"Failed: {name} - {e}")
                continue

        # All fallbacks failed
        if self.log_attempts:
            logging.error("All fallback attempts exhausted")

        raise last_exception or Exception("Fallback chain failed with no exceptions")


def with_timeout(timeout_seconds: float, default_value: Any = None):
    """
    Decorator to add timeout to a function

    Args:
        timeout_seconds: Timeout in seconds
        default_value: Value to return on timeout (if None, raises TimeoutError)

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError(f"Function {func.__name__} timed out after {timeout_seconds}s")

            # Set up timeout (Unix only)
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(timeout_seconds))

                try:
                    result = func(*args, **kwargs)
                    signal.alarm(0)  # Cancel alarm
                    return result
                except TimeoutError:
                    if default_value is not None:
                        logging.warning(
                            f"Function {func.__name__} timed out, returning default value"
                        )
                        return default_value
                    raise
                finally:
                    signal.signal(signal.SIGALRM, old_handler)

            except (AttributeError, ValueError):
                # signal.SIGALRM not available (Windows) or other error
                # Fall back to simple execution without timeout
                logging.warning(
                    f"Timeout not available for {func.__name__}, executing without timeout"
                )
                return func(*args, **kwargs)

        return wrapper

    return decorator
