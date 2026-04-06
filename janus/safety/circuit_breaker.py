"""
Circuit Breaker - Fail-fast pattern for external services

TICKET-RESILIENCE-002: Implements:
- CLOSED: Normal operation
- OPEN: Service unavailable, fail immediately
- HALF_OPEN: Testing if service recovered

This pattern prevents cascading failures when external services are down.
When a service fails repeatedly, the circuit "opens" and requests fail fast
without attempting to contact the service. After a timeout, the circuit enters
"half-open" state to test if the service has recovered.
"""

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5       # Failures before opening
    success_threshold: int = 2       # Successes to close from half-open
    timeout_seconds: float = 60.0    # Time before trying half-open
    
    # Optional callbacks
    on_state_change: Optional[Callable[[CircuitState, CircuitState], None]] = None


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker for protecting against failing services.
    
    Usage:
        breaker = CircuitBreaker("ollama_service")
        
        try:
            result = breaker.call(lambda: make_api_call())
        except CircuitBreakerError:
            # Service is down, use fallback
            result = use_fallback()
    
    Features:
    - Automatic state transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
    - Configurable thresholds and timeouts
    - Thread-safe operation
    - State change callbacks for monitoring
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Name of the service/circuit (for logging)
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # State management
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._lock = threading.Lock()
        
        # Statistics
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "rejected_calls": 0,  # Calls rejected due to open circuit
            "state_changes": 0,
        }
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        with self._lock:
            return self._state
    
    def call(self, func: Callable[[], Any]) -> Any:
        """
        Execute a function through the circuit breaker.
        
        Args:
            func: Function to execute
        
        Returns:
            Result of the function
        
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Any exception raised by the function
        """
        with self._lock:
            self.stats["total_calls"] += 1
            
            # Check if circuit should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_state(CircuitState.HALF_OPEN)
                else:
                    # Circuit is open, reject the call
                    self.stats["rejected_calls"] += 1
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Service unavailable, failing fast."
                    )
            
            # Allow the call in CLOSED or HALF_OPEN state
            current_state = self._state
        
        # Execute the function outside the lock
        try:
            result = func()
            self._on_success()
            self.stats["successful_calls"] += 1
            return result
            
        except Exception as e:
            self._on_failure()
            self.stats["failed_calls"] += 1
            raise
    
    def _on_success(self):
        """Handle successful call"""
        with self._lock:
            self._failure_count = 0
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                
                # Check if we have enough successes to close the circuit
                if self._success_count >= self.config.success_threshold:
                    logger.info(
                        f"✅ Circuit breaker '{self.name}': Service recovered, "
                        f"closing circuit after {self._success_count} successes"
                    )
                    self._transition_state(CircuitState.CLOSED)
                    self._success_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Any failure in HALF_OPEN immediately opens the circuit
                logger.warning(
                    f"⚠️ Circuit breaker '{self.name}': Recovery test failed, "
                    f"reopening circuit"
                )
                self._transition_state(CircuitState.OPEN)
                self._success_count = 0
                
            elif self._state == CircuitState.CLOSED:
                # Check if we've hit the failure threshold
                if self._failure_count >= self.config.failure_threshold:
                    logger.error(
                        f"❌ Circuit breaker '{self.name}': Failure threshold reached "
                        f"({self._failure_count} failures), opening circuit"
                    )
                    self._transition_state(CircuitState.OPEN)
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self._last_failure_time is None:
            return True
        
        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.config.timeout_seconds
    
    def _transition_state(self, new_state: CircuitState):
        """
        Transition to a new state.
        
        Must be called with lock held.
        """
        old_state = self._state
        self._state = new_state
        self.stats["state_changes"] += 1
        
        logger.info(
            f"🔄 Circuit breaker '{self.name}': "
            f"State transition {old_state.value} -> {new_state.value}"
        )
        
        # Call state change callback if provided
        if self.config.on_state_change:
            # Call outside the lock to avoid deadlocks
            try:
                self.config.on_state_change(old_state, new_state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")
    
    def reset(self):
        """
        Manually reset the circuit breaker to CLOSED state.
        
        This can be used for administrative purposes or testing.
        """
        with self._lock:
            logger.info(f"🔧 Circuit breaker '{self.name}': Manual reset to CLOSED")
            self._transition_state(CircuitState.CLOSED)
            self._failure_count = 0
            self._success_count = 0
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                **self.stats
            }


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.
    
    Usage:
        registry = CircuitBreakerRegistry()
        breaker = registry.get_or_create("ollama_service")
        
        result = breaker.call(lambda: make_api_call())
    """
    
    def __init__(self):
        """Initialize the registry"""
        self._breakers = {}
        self._lock = threading.Lock()
    
    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Get existing circuit breaker or create a new one.
        
        Args:
            name: Name of the circuit breaker
            config: Configuration (only used if creating new breaker)
        
        Returns:
            CircuitBreaker instance
        """
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
            return self._breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """
        Get existing circuit breaker.
        
        Args:
            name: Name of the circuit breaker
        
        Returns:
            CircuitBreaker instance or None if not found
        """
        with self._lock:
            return self._breakers.get(name)
    
    def reset_all(self):
        """Reset all circuit breakers to CLOSED state"""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
    
    def get_all_stats(self) -> dict:
        """Get statistics for all circuit breakers"""
        with self._lock:
            return {
                name: breaker.get_stats()
                for name, breaker in self._breakers.items()
            }


# Global registry instance
_global_registry = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get or create the global circuit breaker registry"""
    global _global_registry
    if _global_registry is None:
        _global_registry = CircuitBreakerRegistry()
    return _global_registry


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """
    Convenience function to get or create a circuit breaker.
    
    Args:
        name: Name of the circuit breaker
        config: Configuration (only used if creating new breaker)
    
    Returns:
        CircuitBreaker instance
    """
    return get_circuit_breaker_registry().get_or_create(name, config)
