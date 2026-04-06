"""
Accessibility Factory - Platform detection and backend instantiation.

This module provides factory methods for creating the appropriate accessibility
backend based on the current platform, with automatic fallback handling.
"""

import logging
import platform
from typing import Optional

from janus.platform.accessibility.base_accessibility import AccessibilityBackend

logger = logging.getLogger(__name__)

# Singleton instance
_accessibility_backend: Optional[AccessibilityBackend] = None


def get_accessibility_backend() -> AccessibilityBackend:
    """
    Get the accessibility backend singleton for the current platform.
    
    Returns the same instance on subsequent calls (singleton pattern).
    Automatically detects platform and creates appropriate backend.
    
    Returns:
        AccessibilityBackend implementation for current platform
        
    Example:
        backend = get_accessibility_backend()
        if backend.is_available():
            element = backend.find_element(name="OK", role=AccessibilityRole.BUTTON)
    """
    global _accessibility_backend
    
    if _accessibility_backend is None:
        _accessibility_backend = create_accessibility_backend()
    
    return _accessibility_backend


def create_accessibility_backend(
    platform_override: Optional[str] = None
) -> AccessibilityBackend:
    """
    Create a new accessibility backend for the current platform.
    
    Args:
        platform_override: Optional platform name to override detection
                          ("Windows", "Darwin", "Linux")
    
    Returns:
        AccessibilityBackend implementation for specified platform
        
    Example:
        # Explicit platform
        backend = create_accessibility_backend("Windows")
        
        # Auto-detect
        backend = create_accessibility_backend()
    """
    system = platform_override or platform.system()
    
    logger.info(f"Creating accessibility backend for platform: {system}")
    
    if system == "Windows":
        try:
            from janus.platform.accessibility.windows_accessibility import WindowsAccessibility
            backend = WindowsAccessibility()
            if backend.is_available():
                logger.info("✓ Windows accessibility backend (UIAutomation) available")
                return backend
            else:
                logger.warning("Windows accessibility backend created but not available")
        except Exception as e:
            logger.error(f"Failed to create Windows accessibility backend: {e}")
    
    elif system == "Darwin":
        try:
            from janus.platform.accessibility.macos_accessibility import MacOSAccessibility
            backend = MacOSAccessibility()
            if backend.is_available():
                logger.info("✓ macOS accessibility backend (AXUIElement) available")
                return backend
            else:
                logger.warning("macOS accessibility backend created but not available")
        except Exception as e:
            logger.error(f"Failed to create macOS accessibility backend: {e}")
    
    elif system == "Linux":
        try:
            from janus.platform.accessibility.linux_accessibility import LinuxAccessibility
            backend = LinuxAccessibility()
            if backend.is_available():
                logger.info("✓ Linux accessibility backend (AT-SPI2) available")
                return backend
            else:
                logger.info("Linux accessibility backend created but AT-SPI2 not available")
        except Exception as e:
            logger.error(f"Failed to create Linux accessibility backend: {e}")
    
    # Fallback to mock/null backend
    logger.warning(
        "No accessibility backend available for this platform - "
        "falling back to mock backend. Vision-only mode will be used."
    )
    from janus.platform.accessibility.mock_accessibility import MockAccessibility
    return MockAccessibility()


def reset_accessibility_backend():
    """
    Reset the accessibility backend singleton.
    
    Forces recreation of the backend on next call to get_accessibility_backend().
    Useful for testing or when platform dependencies change.
    
    Example:
        reset_accessibility_backend()
        backend = get_accessibility_backend()  # Creates new instance
    """
    global _accessibility_backend
    _accessibility_backend = None
    logger.debug("Accessibility backend singleton reset")


def is_accessibility_available() -> bool:
    """
    Check if accessibility API is available on current platform.
    
    Returns:
        True if accessibility backend is available and functional
        
    Example:
        if is_accessibility_available():
            # Use accessibility-based automation
            backend = get_accessibility_backend()
            element = backend.find_element(name="OK")
        else:
            # Fall back to vision-based automation
            use_vision_fallback()
    """
    backend = get_accessibility_backend()
    return backend.is_available()
