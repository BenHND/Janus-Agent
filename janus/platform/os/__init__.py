"""
OS-level utilities for Janus.

This module provides low-level OS interactions including:
- Foreground app synchronization
- Window management
- System state tracking
- System abstraction layer (SystemBridge)

TICKET-AUDIT-007: System Abstraction Layer
"""

import logging
import platform
from typing import Optional

from .foreground_app_sync import (
    ForegroundAppSync,
    get_active_app,
    ensure_frontmost,
    wait_until_frontmost,
)
from .system_bridge import (
    SystemBridge,
    SystemBridgeResult,
    SystemBridgeStatus,
    WindowInfo,
)

logger = logging.getLogger(__name__)

# Singleton instance for global use
_system_bridge_instance: Optional[SystemBridge] = None


def get_system_bridge() -> SystemBridge:
    """
    Get the appropriate SystemBridge for the current platform.
    
    Returns a singleton instance of the platform-specific SystemBridge
    implementation. On macOS, returns MacOSBridge. On Windows/Linux,
    returns stub implementations.
    
    Returns:
        SystemBridge implementation for the current platform
        
    Example:
        bridge = get_system_bridge()
        if bridge.is_available():
            bridge.open_app("Safari")
            bridge.type_text("Hello, World!")
    """
    global _system_bridge_instance
    
    if _system_bridge_instance is None:
        _system_bridge_instance = create_system_bridge()
    
    return _system_bridge_instance


def create_system_bridge() -> SystemBridge:
    """
    Create a new SystemBridge instance for the current platform.
    
    Unlike get_system_bridge(), this always creates a new instance.
    Useful for testing or when you need custom configuration.
    
    Returns:
        New SystemBridge implementation for the current platform
    """
    system = platform.system()
    
    if system == "Darwin":
        logger.info("Creating MacOSBridge for macOS platform")
        from .macos_bridge import MacOSBridge
        return MacOSBridge()
    
    elif system == "Windows":
        logger.info("Creating WindowsBridge for Windows platform")
        from .windows_bridge import WindowsBridge
        return WindowsBridge()
    
    elif system == "Linux":
        logger.info("Creating LinuxBridge for Linux platform")
        from .linux_bridge import LinuxBridge
        return LinuxBridge()
    
    else:
        logger.warning(f"Unknown platform '{system}', using Linux stub")
        from .linux_bridge import LinuxBridge
        return LinuxBridge()


def reset_system_bridge() -> None:
    """
    Reset the singleton SystemBridge instance.
    
    Useful for testing or when platform detection needs to be re-evaluated.
    """
    global _system_bridge_instance
    _system_bridge_instance = None
    logger.debug("SystemBridge singleton reset")


__all__ = [
    # Legacy foreground app sync
    "ForegroundAppSync",
    "get_active_app",
    "ensure_frontmost", 
    "wait_until_frontmost",
    # SystemBridge (TICKET-AUDIT-007)
    "SystemBridge",
    "SystemBridgeResult",
    "SystemBridgeStatus",
    "WindowInfo",
    "get_system_bridge",
    "create_system_bridge",
    "reset_system_bridge",
]
