"""
Rate Limiter for Janus - Token Bucket Algorithm

This module provides rate limiting functionality to prevent overload and denial
of service on external providers (Slack, Teams, Email, etc.) and to enforce
global/per-agent/per-provider rate limits.

Features:
- Token bucket algorithm for smooth rate limiting
- Global, per-agent, and per-provider rate limits
- Thread-safe implementation
- Configurable burst allowance
- Persistent rate limit state across restarts
"""

import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration for a specific scope."""
    
    max_requests: int  # Maximum requests per time window
    time_window_seconds: float  # Time window in seconds
    burst_allowance: int = 0  # Additional burst capacity beyond sustained rate
    
    @property
    def refill_rate(self) -> float:
        """Calculate token refill rate (tokens per second)."""
        return self.max_requests / self.time_window_seconds


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, scope: str, retry_after_seconds: float):
        self.scope = scope
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f"Rate limit exceeded for '{scope}'. Retry after {retry_after_seconds:.1f} seconds."
        )


class RateLimiter:
    """
    Thread-safe rate limiter using token bucket algorithm.
    
    Supports:
    - Global rate limits
    - Per-agent rate limits (e.g., "email", "slack")
    - Per-provider rate limits (e.g., "slack:workspace_id", "email:smtp_server")
    
    Example:
        limiter = RateLimiter()
        limiter.configure("global", max_requests=100, time_window_seconds=60)
        limiter.configure("email", max_requests=10, time_window_seconds=60)
        
        if limiter.check_and_consume("global") and limiter.check_and_consume("email"):
            # Safe to execute action
            send_email()
        else:
            # Rate limit exceeded, queue or reject
            pass
    """
    
    def __init__(self, db_path: str = "janus_data.db"):
        """
        Initialize rate limiter.
        
        Args:
            db_path: Path to SQLite database for persistent state
        """
        self.db_path = Path(db_path)
        self._configs: Dict[str, RateLimitConfig] = {}
        self._buckets: Dict[str, Dict[str, float]] = {}  # scope -> {tokens, last_update}
        self._lock = threading.RLock()
        self._initialize_db()
        self._load_state()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _initialize_db(self):
        """Create rate limiter tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS rate_limiter_state (
                    scope TEXT PRIMARY KEY,
                    tokens REAL NOT NULL,
                    last_update REAL NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS rate_limiter_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scope TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    tokens_before REAL,
                    tokens_after REAL,
                    exceeded INTEGER DEFAULT 0
                )
                """
            )
            # Index for querying recent events
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_rate_limiter_events_timestamp
                ON rate_limiter_events(timestamp DESC)
                """
            )
    
    def _load_state(self):
        """Load rate limiter state from database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT scope, tokens, last_update FROM rate_limiter_state")
            for row in cursor.fetchall():
                scope, tokens, last_update = row
                self._buckets[scope] = {"tokens": tokens, "last_update": last_update}
    
    def _save_state(self, scope: str):
        """Save rate limiter state to database."""
        if scope not in self._buckets:
            return
        
        bucket = self._buckets[scope]
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO rate_limiter_state (scope, tokens, last_update, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                """,
                (scope, bucket["tokens"], bucket["last_update"])
            )
    
    def _log_event(self, scope: str, action: str, tokens_before: float, tokens_after: float, exceeded: bool):
        """Log rate limiter event."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO rate_limiter_events (scope, action, timestamp, tokens_before, tokens_after, exceeded)
                VALUES (?, ?, datetime('now'), ?, ?, ?)
                """,
                (scope, action, tokens_before, tokens_after, 1 if exceeded else 0)
            )
    
    def configure(
        self,
        scope: str,
        max_requests: int,
        time_window_seconds: float,
        burst_allowance: int = 0
    ):
        """
        Configure rate limit for a scope.
        
        Args:
            scope: Rate limit scope (e.g., "global", "email", "slack:workspace")
            max_requests: Maximum requests allowed per time window
            time_window_seconds: Time window in seconds
            burst_allowance: Additional burst capacity (default: 0)
        
        Example:
            # Allow 100 requests per minute globally
            limiter.configure("global", max_requests=100, time_window_seconds=60)
            
            # Allow 10 emails per minute with burst of 5
            limiter.configure("email", max_requests=10, time_window_seconds=60, burst_allowance=5)
        """
        with self._lock:
            config = RateLimitConfig(max_requests, time_window_seconds, burst_allowance)
            self._configs[scope] = config
            
            # Initialize bucket if not exists
            if scope not in self._buckets:
                max_tokens = max_requests + burst_allowance
                self._buckets[scope] = {
                    "tokens": float(max_tokens),
                    "last_update": time.time()
                }
                self._save_state(scope)
            
            logger.info(
                f"Rate limit configured for '{scope}': {max_requests} requests per "
                f"{time_window_seconds}s (burst: {burst_allowance})"
            )
    
    def _refill_tokens(self, scope: str) -> float:
        """
        Refill tokens based on elapsed time.
        
        Args:
            scope: Rate limit scope
        
        Returns:
            Current token count after refill
        """
        if scope not in self._configs or scope not in self._buckets:
            return 0.0
        
        config = self._configs[scope]
        bucket = self._buckets[scope]
        
        now = time.time()
        elapsed = now - bucket["last_update"]
        
        # Calculate tokens to add
        tokens_to_add = elapsed * config.refill_rate
        max_tokens = config.max_requests + config.burst_allowance
        
        # Refill tokens (capped at max)
        bucket["tokens"] = min(bucket["tokens"] + tokens_to_add, max_tokens)
        bucket["last_update"] = now
        
        return bucket["tokens"]
    
    def check_and_consume(self, scope: str, tokens: float = 1.0) -> bool:
        """
        Check if rate limit allows request and consume tokens if allowed.
        
        Args:
            scope: Rate limit scope
            tokens: Number of tokens to consume (default: 1.0)
        
        Returns:
            True if request is allowed, False if rate limit exceeded
        
        Raises:
            RateLimitExceeded: If rate limit is exceeded and configured to raise
        """
        with self._lock:
            if scope not in self._configs:
                # No rate limit configured for this scope
                return True
            
            # Refill tokens
            current_tokens = self._refill_tokens(scope)
            tokens_before = current_tokens
            
            # Check if we have enough tokens
            if current_tokens >= tokens:
                # Consume tokens
                self._buckets[scope]["tokens"] = current_tokens - tokens
                tokens_after = self._buckets[scope]["tokens"]
                self._save_state(scope)
                self._log_event(scope, "consume", tokens_before, tokens_after, False)
                logger.debug(f"Rate limit check passed for '{scope}': {tokens_after:.2f} tokens remaining")
                return True
            else:
                # Rate limit exceeded
                tokens_after = current_tokens
                self._log_event(scope, "exceeded", tokens_before, tokens_after, True)
                
                # Calculate retry after time
                config = self._configs[scope]
                tokens_needed = tokens - current_tokens
                retry_after = tokens_needed / config.refill_rate
                
                logger.warning(
                    f"Rate limit exceeded for '{scope}': need {tokens:.1f} tokens, "
                    f"have {current_tokens:.2f}. Retry after {retry_after:.1f}s"
                )
                return False
    
    def get_remaining(self, scope: str) -> Optional[float]:
        """
        Get remaining tokens for a scope.
        
        Args:
            scope: Rate limit scope
        
        Returns:
            Number of tokens remaining, or None if scope not configured
        """
        with self._lock:
            if scope not in self._configs:
                return None
            
            current_tokens = self._refill_tokens(scope)
            return current_tokens
    
    def reset(self, scope: str):
        """
        Reset rate limit for a scope (refill to max tokens).
        
        Args:
            scope: Rate limit scope
        """
        with self._lock:
            if scope not in self._configs:
                return
            
            config = self._configs[scope]
            max_tokens = config.max_requests + config.burst_allowance
            
            self._buckets[scope] = {
                "tokens": float(max_tokens),
                "last_update": time.time()
            }
            self._save_state(scope)
            logger.info(f"Rate limit reset for '{scope}': {max_tokens} tokens available")
    
    def get_stats(self, scope: str, hours: int = 24) -> Dict[str, any]:
        """
        Get rate limit statistics for a scope.
        
        Args:
            scope: Rate limit scope
            hours: Number of hours to look back
        
        Returns:
            Statistics dictionary with counts and exceeded events
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_events,
                    SUM(CASE WHEN exceeded = 1 THEN 1 ELSE 0 END) as exceeded_count,
                    AVG(tokens_after) as avg_tokens_remaining
                FROM rate_limiter_events
                WHERE scope = ? 
                  AND timestamp > datetime('now', '-' || ? || ' hours')
                """,
                (scope, hours)
            )
            row = cursor.fetchone()
            
            return {
                "scope": scope,
                "total_events": row[0] or 0,
                "exceeded_count": row[1] or 0,
                "avg_tokens_remaining": row[2] or 0.0,
                "current_tokens": self.get_remaining(scope)
            }
