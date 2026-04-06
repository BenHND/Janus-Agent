"""
Accessibility Layer - Unified abstraction for Windows UIAutomation, macOS AXUIElement, and Linux AT-SPI2.

This module provides a stable, cross-platform API for UI accessibility operations,
abstracting away differences between Windows, macOS, and Linux.

Architecture:
    - AccessibilityBackend: Abstract base class defining the unified API
    - WindowsAccessibility: UIAutomation implementation for Windows
    - MacOSAccessibility: AXUIElement implementation for macOS
    - LinuxAccessibility: AT-SPI2 implementation for Linux (Phase 4)
    - Factory method: get_accessibility_backend() for automatic platform detection
    - Automatic fallback to vision-only mode when accessibility is unavailable

Key Features:
    - Element finding (by name, role, attributes)
    - UI element interaction (click, focus, set value)
    - State retrieval (enabled, visible, selected, focused)
    - UI tree traversal and inspection
    - Platform-agnostic element representation
    - Performance benchmarking vs vision-based approaches
    - Caching for improved performance (Phase 3)
    - Smart fallback strategies (Phase 3)
    - Telemetry tracking (Phase 3)

Usage:
    from janus.platform.accessibility import get_accessibility_backend
    
    backend = get_accessibility_backend()
    if backend.is_available():
        element = backend.find_element(name="OK", role="button")
        if element:
            backend.click_element(element)
    else:
        # Fallback to vision-based approach
        pass
"""

from janus.platform.accessibility.base_accessibility import (
    AccessibilityBackend,
    AccessibilityElement,
    AccessibilityRole,
    AccessibilityState,
    AccessibilityResult,
)
from janus.platform.accessibility.factory import (
    get_accessibility_backend,
    create_accessibility_backend,
    reset_accessibility_backend,
    is_accessibility_available,
)
from janus.platform.accessibility.accessibility_cache import AccessibilityCache
from janus.platform.accessibility.accessibility_telemetry import (
    AccessibilityTelemetry,
    AccessibilityMetric,
)
from janus.platform.accessibility.smart_fallback import SmartFallbackStrategy

__all__ = [
    "AccessibilityBackend",
    "AccessibilityElement",
    "AccessibilityRole",
    "AccessibilityState",
    "AccessibilityResult",
    "get_accessibility_backend",
    "create_accessibility_backend",
    "reset_accessibility_backend",
    "is_accessibility_available",
    "AccessibilityCache",
    "AccessibilityTelemetry",
    "AccessibilityMetric",
    "SmartFallbackStrategy",
]
