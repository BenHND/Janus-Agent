"""
Global Shutdown Module - TICKET 1 (P0)

Provides a global shutdown flag to prevent any OS actions after shutdown is requested.
This prevents issues like "continues to open YouTube after app is closed" and CPU/M4 heating.

Thread-safe implementation using threading.Lock for concurrent access.
"""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# Global shutdown state
_shutdown_lock = threading.Lock()
_shutdown_requested = False
_shutdown_reason: Optional[str] = None


def request_shutdown(reason: str = "User requested shutdown") -> None:
    """
    Request global shutdown of the Janus runtime.
    
    After this is called, all OS actions, AppleScript execution, and new
    command processing should be prevented.
    
    Args:
        reason: Human-readable reason for shutdown (for logging)
    """
    global _shutdown_requested, _shutdown_reason
    
    with _shutdown_lock:
        if _shutdown_requested:
            logger.debug(f"Shutdown already requested (previous reason: {_shutdown_reason})")
            return
        
        _shutdown_requested = True
        _shutdown_reason = reason
        logger.info(f"🛑 Global shutdown requested: {reason}")


def is_shutdown_requested() -> bool:
    """
    Check if global shutdown has been requested.
    
    Returns:
        True if shutdown was requested, False otherwise
    """
    with _shutdown_lock:
        return _shutdown_requested


def get_shutdown_reason() -> Optional[str]:
    """
    Get the reason for shutdown.
    
    Returns:
        Shutdown reason string if shutdown was requested, None otherwise
    """
    with _shutdown_lock:
        return _shutdown_reason


def reset_shutdown_state() -> None:
    """
    Reset shutdown state (primarily for testing).
    
    WARNING: This should NOT be called in production code.
    Only use this in test cleanup.
    """
    global _shutdown_requested, _shutdown_reason
    
    with _shutdown_lock:
        _shutdown_requested = False
        _shutdown_reason = None
        logger.debug("Shutdown state reset")
