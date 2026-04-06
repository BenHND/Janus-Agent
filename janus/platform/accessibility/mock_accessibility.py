"""
Mock Accessibility Backend - Null implementation for testing and fallback.

This module provides a no-op accessibility backend that always returns
empty results. Used for:
    - Testing without real accessibility APIs
    - Fallback when no platform backend is available
    - Graceful degradation to vision-only mode
"""

import logging
from typing import Any, Dict, List, Optional

from janus.platform.accessibility.base_accessibility import (
    AccessibilityBackend,
    AccessibilityElement,
    AccessibilityRole,
    AccessibilityResult,
)

logger = logging.getLogger(__name__)


class MockAccessibility(AccessibilityBackend):
    """
    Mock accessibility backend that provides no-op implementations.
    
    This backend always returns empty/None results and is used when:
        - No platform-specific backend is available
        - Testing without real accessibility APIs
        - Graceful fallback to vision-only automation
    
    All methods are implemented but do nothing, allowing code to use
    accessibility API uniformly without platform checks everywhere.
    """
    
    def __init__(self):
        """Initialize mock accessibility backend."""
        logger.debug("MockAccessibility initialized (no-op backend)")
    
    # ========== Platform Detection ==========
    
    def is_available(self) -> bool:
        """Mock backend is never available for actual use."""
        return False
    
    def get_platform_name(self) -> str:
        """Get platform name."""
        return "Mock"
    
    # ========== Element Finding ==========
    
    def find_element(
        self,
        name: Optional[str] = None,
        role: Optional[AccessibilityRole] = None,
        attributes: Optional[Dict[str, Any]] = None,
        timeout: float = 5.0,
    ) -> Optional[AccessibilityElement]:
        """Always returns None (no elements found)."""
        logger.debug("MockAccessibility.find_element called - returning None")
        return None
    
    def find_elements(
        self,
        name: Optional[str] = None,
        role: Optional[AccessibilityRole] = None,
        attributes: Optional[Dict[str, Any]] = None,
        max_results: int = 100,
    ) -> List[AccessibilityElement]:
        """Always returns empty list."""
        logger.debug("MockAccessibility.find_elements called - returning []")
        return []
    
    def get_focused_element(self) -> Optional[AccessibilityElement]:
        """Always returns None (no focused element)."""
        logger.debug("MockAccessibility.get_focused_element called - returning None")
        return None
    
    # ========== Element Interaction ==========
    
    def click_element(self, element: AccessibilityElement) -> AccessibilityResult:
        """Always fails (no-op)."""
        logger.debug("MockAccessibility.click_element called - returning failure")
        return AccessibilityResult(
            success=False,
            error="Mock backend does not support element interaction"
        )
    
    def focus_element(self, element: AccessibilityElement) -> AccessibilityResult:
        """Always fails (no-op)."""
        logger.debug("MockAccessibility.focus_element called - returning failure")
        return AccessibilityResult(
            success=False,
            error="Mock backend does not support element interaction"
        )
    
    def set_value(
        self,
        element: AccessibilityElement,
        value: str
    ) -> AccessibilityResult:
        """Always fails (no-op)."""
        logger.debug("MockAccessibility.set_value called - returning failure")
        return AccessibilityResult(
            success=False,
            error="Mock backend does not support element interaction"
        )
    
    # ========== State Retrieval ==========
    
    def get_element_state(self, element: AccessibilityElement) -> set:
        """Always returns empty set."""
        logger.debug("MockAccessibility.get_element_state called - returning empty set")
        return set()
    
    def get_element_bounds(
        self,
        element: AccessibilityElement
    ) -> Optional[Dict[str, int]]:
        """Always returns None."""
        logger.debug("MockAccessibility.get_element_bounds called - returning None")
        return None
    
    # ========== Tree Inspection ==========
    
    def get_ui_tree(
        self,
        root: Optional[AccessibilityElement] = None,
        max_depth: int = 10,
    ) -> Dict[str, Any]:
        """Always returns empty dict."""
        logger.debug("MockAccessibility.get_ui_tree called - returning {}")
        return {}
    
    def get_children(
        self,
        element: AccessibilityElement
    ) -> List[AccessibilityElement]:
        """Always returns empty list."""
        logger.debug("MockAccessibility.get_children called - returning []")
        return []
    
    def get_parent(
        self,
        element: AccessibilityElement
    ) -> Optional[AccessibilityElement]:
        """Always returns None."""
        logger.debug("MockAccessibility.get_parent called - returning None")
        return None
    
    # ========== Application Context ==========
    
    def get_active_app(self) -> Optional[AccessibilityElement]:
        """Always returns None."""
        logger.debug("MockAccessibility.get_active_app called - returning None")
        return None
    
    def get_app_windows(
        self,
        app_name: Optional[str] = None
    ) -> List[AccessibilityElement]:
        """Always returns empty list."""
        logger.debug("MockAccessibility.get_app_windows called - returning []")
        return []
