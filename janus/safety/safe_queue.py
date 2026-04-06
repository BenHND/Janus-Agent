"""
SafeQueue - Persistent Action Queue for Offline Mode

This module provides a persistent queue for actions when services are unavailable.
Actions are stored in SQLite and automatically processed when services come back online.

Features:
- Persistent queue storage in SQLite
- Automatic retry with exponential backoff
- Queue expiration and purge policies
- Thread-safe operations
- Priority queue support
- Failed action tracking and retry limits
"""

import json
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class QueueStatus(Enum):
    """Status of queued action."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class QueuedAction:
    """Represents an action in the queue."""
    
    id: Optional[int]
    action_type: str
    action_data: Dict[str, Any]
    priority: int  # Lower number = higher priority
    status: QueueStatus
    created_at: datetime
    scheduled_for: Optional[datetime]  # Delayed execution
    expires_at: Optional[datetime]  # Expiration time
    retry_count: int
    max_retries: int
    last_error: Optional[str]
    completed_at: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "action_type": self.action_type,
            "action_data": self.action_data,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "last_error": self.last_error,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class SafeQueue:
    """
    Thread-safe persistent queue for offline action storage and retry.
    
    Example:
        queue = SafeQueue()
        
        # Enqueue action when service is offline
        queue.enqueue(
            action_type="email.send",
            action_data={"to": "user@example.com", "subject": "Hello"},
            priority=1,
            max_retries=3,
            expires_in_hours=24
        )
        
        # Process queue when service is online
        def send_email(action_data):
            # Send email logic
            return True
        
        queue.register_processor("email.send", send_email)
        queue.process_pending()
    """
    
    def __init__(self, db_path: str = "janus_data.db", auto_purge: bool = True):
        """
        Initialize SafeQueue.
        
        Args:
            db_path: Path to SQLite database
            auto_purge: Automatically purge expired/completed actions (default: True)
        """
        self.db_path = Path(db_path)
        self._processors: Dict[str, Callable] = {}
        self._lock = threading.RLock()
        self.auto_purge = auto_purge
        self._initialize_db()
        
        if self.auto_purge:
            self._purge_expired()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _initialize_db(self):
        """Create queue tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS action_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    action_data TEXT NOT NULL,
                    priority INTEGER DEFAULT 5,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    scheduled_for TEXT,
                    expires_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    last_error TEXT,
                    completed_at TEXT
                )
                """
            )
            # Indexes for efficient queries
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_queue_status_priority
                ON action_queue(status, priority, scheduled_for)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_queue_created_at
                ON action_queue(created_at DESC)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_queue_expires_at
                ON action_queue(expires_at)
                """
            )
    
    def enqueue(
        self,
        action_type: str,
        action_data: Dict[str, Any],
        priority: int = 5,
        max_retries: int = 3,
        delay_seconds: Optional[float] = None,
        expires_in_hours: Optional[int] = None,
    ) -> int:
        """
        Add action to queue.
        
        Args:
            action_type: Type of action (e.g., "email.send", "slack.message")
            action_data: Action data/parameters
            priority: Priority level (lower = higher priority, default: 5)
            max_retries: Maximum retry attempts (default: 3)
            delay_seconds: Delay execution by N seconds (default: None = immediate)
            expires_in_hours: Expire action after N hours (default: None = never)
        
        Returns:
            Queue item ID
        """
        with self._lock:
            now = datetime.now()
            scheduled_for = now + timedelta(seconds=delay_seconds) if delay_seconds else now
            expires_at = now + timedelta(hours=expires_in_hours) if expires_in_hours else None
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO action_queue 
                    (action_type, action_data, priority, status, created_at, 
                     scheduled_for, expires_at, retry_count, max_retries)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        action_type,
                        json.dumps(action_data),
                        priority,
                        QueueStatus.PENDING.value,
                        now.isoformat(),
                        scheduled_for.isoformat(),
                        expires_at.isoformat() if expires_at else None,
                        0,
                        max_retries,
                    )
                )
                action_id = cursor.lastrowid
                
                logger.info(
                    f"Action queued: {action_type} (id={action_id}, priority={priority}, "
                    f"max_retries={max_retries})"
                )
                return action_id
    
    def register_processor(self, action_type: str, processor: Callable[[Dict[str, Any]], bool]):
        """
        Register processor function for an action type.
        
        Args:
            action_type: Type of action to process
            processor: Callable that takes action_data and returns True on success
        
        Example:
            def send_email(data):
                send_email_via_smtp(data["to"], data["subject"], data["body"])
                return True
            
            queue.register_processor("email.send", send_email)
        """
        self._processors[action_type] = processor
        logger.info(f"Processor registered for action type: {action_type}")
    
    def _get_next_pending(self) -> Optional[QueuedAction]:
        """Get next pending action (by priority and schedule)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                """
                SELECT * FROM action_queue
                WHERE status = ?
                  AND (scheduled_for IS NULL OR scheduled_for <= ?)
                  AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY priority ASC, created_at ASC
                LIMIT 1
                """,
                (QueueStatus.PENDING.value, now, now)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return QueuedAction(
                id=row["id"],
                action_type=row["action_type"],
                action_data=json.loads(row["action_data"]),
                priority=row["priority"],
                status=QueueStatus(row["status"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                scheduled_for=datetime.fromisoformat(row["scheduled_for"]) if row["scheduled_for"] else None,
                expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                retry_count=row["retry_count"],
                max_retries=row["max_retries"],
                last_error=row["last_error"],
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            )
    
    def _update_status(
        self,
        action_id: int,
        status: QueueStatus,
        error: Optional[str] = None,
        increment_retry: bool = False
    ):
        """Update action status in database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            if status == QueueStatus.COMPLETED:
                cursor.execute(
                    """
                    UPDATE action_queue
                    SET status = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (status.value, now, action_id)
                )
            elif increment_retry:
                cursor.execute(
                    """
                    UPDATE action_queue
                    SET status = ?, retry_count = retry_count + 1, last_error = ?
                    WHERE id = ?
                    """,
                    (status.value, error, action_id)
                )
            else:
                cursor.execute(
                    """
                    UPDATE action_queue
                    SET status = ?, last_error = ?
                    WHERE id = ?
                    """,
                    (status.value, error, action_id)
                )
    
    def process_pending(self, max_actions: Optional[int] = None) -> Dict[str, int]:
        """
        Process pending actions in queue.
        
        Args:
            max_actions: Maximum number of actions to process (None = all)
        
        Returns:
            Statistics: {processed, succeeded, failed, skipped}
        """
        with self._lock:
            stats = {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}
            
            while True:
                if max_actions and stats["processed"] >= max_actions:
                    break
                
                action = self._get_next_pending()
                if not action:
                    break
                
                # Check if processor is registered
                if action.action_type not in self._processors:
                    logger.warning(f"No processor registered for action type: {action.action_type}")
                    # Mark as failed so it's not selected again
                    self._update_status(action.id, QueueStatus.FAILED, "No processor registered")
                    stats["skipped"] += 1
                    stats["processed"] += 1
                    continue
                
                # Mark as processing
                self._update_status(action.id, QueueStatus.PROCESSING)
                
                try:
                    # Execute processor
                    processor = self._processors[action.action_type]
                    success = processor(action.action_data)
                    
                    if success:
                        self._update_status(action.id, QueueStatus.COMPLETED)
                        stats["succeeded"] += 1
                        logger.info(f"Action completed successfully: {action.action_type} (id={action.id})")
                    else:
                        # Retry logic
                        if action.retry_count < action.max_retries:
                            # Calculate exponential backoff delay
                            delay = min(2 ** action.retry_count * 60, 3600)  # Max 1 hour
                            scheduled_for = datetime.now() + timedelta(seconds=delay)
                            
                            with self._get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    """
                                    UPDATE action_queue
                                    SET status = ?, retry_count = retry_count + 1,
                                        scheduled_for = ?, last_error = ?
                                    WHERE id = ?
                                    """,
                                    (
                                        QueueStatus.PENDING.value,
                                        scheduled_for.isoformat(),
                                        f"Retry {action.retry_count + 1}/{action.max_retries}",
                                        action.id
                                    )
                                )
                            
                            logger.info(
                                f"Action retry scheduled: {action.action_type} (id={action.id}, "
                                f"retry={action.retry_count + 1}/{action.max_retries}, delay={delay}s)"
                            )
                        else:
                            self._update_status(action.id, QueueStatus.FAILED, "Max retries exceeded")
                            stats["failed"] += 1
                            logger.error(
                                f"Action failed permanently: {action.action_type} (id={action.id}, "
                                f"retries={action.retry_count}/{action.max_retries})"
                            )
                
                except Exception as e:
                    error_msg = str(e)
                    logger.exception(f"Error processing action {action.id}: {error_msg}")
                    
                    # Retry logic for exceptions
                    if action.retry_count < action.max_retries:
                        delay = min(2 ** action.retry_count * 60, 3600)
                        scheduled_for = datetime.now() + timedelta(seconds=delay)
                        
                        with self._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                """
                                UPDATE action_queue
                                SET status = ?, retry_count = retry_count + 1,
                                    scheduled_for = ?, last_error = ?
                                WHERE id = ?
                                """,
                                (
                                    QueueStatus.PENDING.value,
                                    scheduled_for.isoformat(),
                                    error_msg,
                                    action.id
                                )
                            )
                    else:
                        self._update_status(action.id, QueueStatus.FAILED, error_msg)
                        stats["failed"] += 1
                
                stats["processed"] += 1
            
            logger.info(f"Queue processing complete: {stats}")
            return stats
    
    def _purge_expired(self):
        """Purge expired actions from queue."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                """
                UPDATE action_queue
                SET status = ?
                WHERE expires_at IS NOT NULL
                  AND expires_at < ?
                  AND status IN (?, ?)
                """,
                (QueueStatus.EXPIRED.value, now, QueueStatus.PENDING.value, QueueStatus.PROCESSING.value)
            )
            count = cursor.rowcount
            
            if count > 0:
                logger.info(f"Purged {count} expired actions from queue")
    
    def purge_completed(self, older_than_hours: int = 168):
        """
        Purge completed actions older than specified hours.
        
        Args:
            older_than_hours: Remove completed actions older than this (default: 168 = 1 week)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(hours=older_than_hours)).isoformat()
            cursor.execute(
                """
                DELETE FROM action_queue
                WHERE status = ?
                  AND completed_at < ?
                """,
                (QueueStatus.COMPLETED.value, cutoff)
            )
            count = cursor.rowcount
            
            if count > 0:
                logger.info(f"Purged {count} completed actions from queue")
    
    def cancel(self, action_id: int) -> bool:
        """
        Cancel a pending action.
        
        Args:
            action_id: ID of action to cancel
        
        Returns:
            True if cancelled, False if not found or not cancellable
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE action_queue
                    SET status = ?
                    WHERE id = ? AND status IN (?, ?)
                    """,
                    (QueueStatus.CANCELLED.value, action_id, QueueStatus.PENDING.value, QueueStatus.PROCESSING.value)
                )
                
                if cursor.rowcount > 0:
                    logger.info(f"Action cancelled: id={action_id}")
                    return True
                return False
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get queue statistics.
        
        Returns:
            Statistics by status
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT status, COUNT(*) as count
                FROM action_queue
                GROUP BY status
                """
            )
            
            stats = {status.value: 0 for status in QueueStatus}
            for row in cursor.fetchall():
                stats[row["status"]] = row["count"]
            
            return stats
    
    def get_pending_count(self) -> int:
        """Get count of pending actions ready to process."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                """
                SELECT COUNT(*) FROM action_queue
                WHERE status = ?
                  AND (scheduled_for IS NULL OR scheduled_for <= ?)
                  AND (expires_at IS NULL OR expires_at > ?)
                """,
                (QueueStatus.PENDING.value, now, now)
            )
            return cursor.fetchone()[0]
