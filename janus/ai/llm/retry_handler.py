"""
LLM Retry Handler - Robust retry logic for LLM calls

TICKET-RESILIENCE-001: Implements:
- Exponential backoff with jitter
- Configurable retry policies
- Circuit breaker integration
- Detailed error classification
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """Base class for errors that can be retried"""
    pass


class NonRetryableError(Exception):
    """Base class for errors that should NOT be retried"""
    pass


class ErrorCategory(Enum):
    """Classification of errors for retry decisions"""
    NETWORK = "network"          # Connection errors, timeouts
    RATE_LIMIT = "rate_limit"    # 429 Too Many Requests
    SERVER_ERROR = "server"      # 5xx errors
    CLIENT_ERROR = "client"      # 4xx errors (usually non-retryable)
    TIMEOUT = "timeout"          # Request timeout
    UNKNOWN = "unknown"


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    initial_delay_ms: int = 1000  # 1 second
    max_delay_ms: int = 30000     # 30 seconds
    exponential_base: float = 2.0
    jitter_factor: float = 0.1   # 10% jitter
    retry_on_timeout: bool = True
    retry_on_5xx: bool = True
    retry_on_429: bool = True
    
    # Callbacks
    on_retry: Optional[Callable[[int, Exception, float], None]] = None


def classify_error(error: Exception) -> Tuple[ErrorCategory, bool]:
    """
    Classify an error and determine if it's retryable.
    
    Args:
        error: The exception to classify
    
    Returns:
        Tuple of (ErrorCategory, is_retryable)
    """
    error_str = str(error).lower()
    
    # Network errors - retryable
    if isinstance(error, (
        requests.exceptions.ConnectionError,
        requests.exceptions.ChunkedEncodingError,
        ConnectionRefusedError,
        ConnectionResetError,
    )):
        return ErrorCategory.NETWORK, True
    
    # Timeout - usually retryable
    if isinstance(error, (
        requests.exceptions.Timeout,
        requests.exceptions.ReadTimeout,
        TimeoutError,
        asyncio.TimeoutError,
    )):
        return ErrorCategory.TIMEOUT, True
    
    # HTTP errors
    if isinstance(error, requests.exceptions.HTTPError):
        status_code = getattr(error.response, 'status_code', 0)
        
        if status_code == 429:  # Rate limit
            return ErrorCategory.RATE_LIMIT, True
        elif 500 <= status_code < 600:  # Server error
            return ErrorCategory.SERVER_ERROR, True
        elif 400 <= status_code < 500:  # Client error
            return ErrorCategory.CLIENT_ERROR, False
    
    # Check error message for common patterns
    if any(x in error_str for x in ["timeout", "timed out"]):
        return ErrorCategory.TIMEOUT, True
    if any(x in error_str for x in ["connection", "network", "unreachable"]):
        return ErrorCategory.NETWORK, True
    if "rate limit" in error_str or "too many requests" in error_str:
        return ErrorCategory.RATE_LIMIT, True
    
    return ErrorCategory.UNKNOWN, False


def calculate_delay(
    attempt: int,
    config: RetryConfig,
    error_category: ErrorCategory
) -> float:
    """
    Calculate delay before next retry with exponential backoff and jitter.
    
    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration
        error_category: Category of the error
    
    Returns:
        Delay in seconds
    """
    # Base exponential delay
    base_delay_ms = config.initial_delay_ms * (config.exponential_base ** attempt)
    
    # Cap at max delay
    delay_ms = min(base_delay_ms, config.max_delay_ms)
    
    # Add jitter to prevent thundering herd
    jitter = delay_ms * config.jitter_factor * random.random()
    delay_ms += jitter
    
    # Rate limit errors get extra delay
    if error_category == ErrorCategory.RATE_LIMIT:
        delay_ms *= 2
    
    return delay_ms / 1000.0  # Convert to seconds


class LLMRetryHandler:
    """
    Handles retry logic for LLM API calls.
    
    Features:
    - Exponential backoff with jitter
    - Error classification
    - Configurable retry policies
    - Callback hooks for UI feedback
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry handler.
        
        Args:
            config: Retry configuration (uses defaults if None)
        """
        self.config = config or RetryConfig()
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_retries": 0,
            "errors_by_category": {},
        }
    
    def execute_with_retry(
        self,
        func: Callable[[], Any],
        operation_name: str = "LLM call",
    ) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            operation_name: Name for logging
        
        Returns:
            Result of the function
        
        Raises:
            Exception: If all retries exhausted
        """
        self.stats["total_calls"] += 1
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                result = func()
                self.stats["successful_calls"] += 1
                
                if attempt > 0:
                    logger.info(
                        f"✅ {operation_name} succeeded after {attempt} retries"
                    )
                
                return result
                
            except Exception as e:
                last_error = e
                category, is_retryable = classify_error(e)
                
                # Track error stats
                self.stats["errors_by_category"][category.value] = \
                    self.stats["errors_by_category"].get(category.value, 0) + 1
                
                # Check if we should retry
                should_retry = (
                    is_retryable and
                    attempt < self.config.max_retries and
                    self._should_retry_category(category)
                )
                
                if should_retry:
                    delay = calculate_delay(attempt, self.config, category)
                    self.stats["total_retries"] += 1
                    
                    logger.warning(
                        f"⚠️ {operation_name} failed ({category.value}): {str(e)[:100]}. "
                        f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{self.config.max_retries})"
                    )
                    
                    # Call retry callback if provided
                    if self.config.on_retry:
                        self.config.on_retry(attempt + 1, e, delay)
                    
                    time.sleep(delay)
                else:
                    # No more retries
                    logger.error(
                        f"❌ {operation_name} failed permanently ({category.value}): {str(e)[:200]}"
                    )
                    break
        
        self.stats["failed_calls"] += 1
        raise last_error
    
    async def execute_with_retry_async(
        self,
        func: Callable[[], Any],
        operation_name: str = "LLM call",
    ) -> Any:
        """
        Async version of execute_with_retry.
        
        Args:
            func: Async function to execute
            operation_name: Name for logging
        
        Returns:
            Result of the function
        """
        self.stats["total_calls"] += 1
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func()
                else:
                    result = func()
                
                self.stats["successful_calls"] += 1
                return result
                
            except Exception as e:
                last_error = e
                category, is_retryable = classify_error(e)
                
                should_retry = (
                    is_retryable and
                    attempt < self.config.max_retries and
                    self._should_retry_category(category)
                )
                
                if should_retry:
                    delay = calculate_delay(attempt, self.config, category)
                    self.stats["total_retries"] += 1
                    
                    logger.warning(
                        f"⚠️ {operation_name} failed ({category.value}). "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    if self.config.on_retry:
                        self.config.on_retry(attempt + 1, e, delay)
                    
                    await asyncio.sleep(delay)
                else:
                    break
        
        self.stats["failed_calls"] += 1
        raise last_error
    
    def _should_retry_category(self, category: ErrorCategory) -> bool:
        """Check if we should retry for a given error category"""
        if category == ErrorCategory.TIMEOUT:
            return self.config.retry_on_timeout
        elif category == ErrorCategory.SERVER_ERROR:
            return self.config.retry_on_5xx
        elif category == ErrorCategory.RATE_LIMIT:
            return self.config.retry_on_429
        elif category == ErrorCategory.NETWORK:
            return True
        elif category == ErrorCategory.CLIENT_ERROR:
            return False
        return False
    
    def get_stats(self) -> dict:
        """Get retry statistics"""
        return self.stats.copy()


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for adding retry logic to a function.
    
    Usage:
        @with_retry(RetryConfig(max_retries=5))
        def call_llm():
            return requests.post(...)
    """
    handler = LLMRetryHandler(config)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return handler.execute_with_retry(
                lambda: func(*args, **kwargs),
                operation_name=func.__name__
            )
        return wrapper
    
    return decorator


# Global retry handler with default config
_default_retry_handler = None


def get_retry_handler() -> LLMRetryHandler:
    """Get or create default retry handler"""
    global _default_retry_handler
    if _default_retry_handler is None:
        _default_retry_handler = LLMRetryHandler(RetryConfig(
            max_retries=3,
            initial_delay_ms=1000,
            max_delay_ms=30000,
        ))
    return _default_retry_handler
