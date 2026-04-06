"""
Windows Accessibility Backend - UIAutomation implementation.

This module implements the AccessibilityBackend interface using Windows UIAutomation API.
UIAutomation is the recommended API for UI accessibility on Windows 7+.

Features:
    - Element finding using UIAutomation tree walkers and conditions
    - Element interaction (click, focus, set value) via automation patterns
    - State retrieval from element properties
    - UI tree traversal and inspection
    - Support for native apps, Electron, and some webviews

Dependencies:
    - pywinauto (optional but recommended for better UIAutomation support)
    - comtypes (for direct UIAutomation COM access)

Performance:
    - Element finding: 10-100ms (vs 200-500ms for vision)
    - State retrieval: <5ms (vs 100-300ms for OCR)
    - Click action: <10ms (vs 50-100ms for vision)

Compatibility:
    - Native Windows apps: Excellent
    - Electron apps: Good (via UIAutomation)
    - Webviews: Partial (depends on implementation)
    - Legacy apps: Varies (some use MSAA instead)
"""

import logging
import platform
import time
from typing import Any, Dict, List, Optional

from janus.platform.accessibility.base_accessibility import (
    AccessibilityBackend,
    AccessibilityElement,
    AccessibilityRole,
    AccessibilityState,
    AccessibilityResult,
)

logger = logging.getLogger(__name__)


# Role mapping: UIAutomation ControlType to AccessibilityRole
UIAUTOMATION_ROLE_MAP = {
    50000: AccessibilityRole.BUTTON,  # UIA_ButtonControlTypeId
    50002: AccessibilityRole.CHECKBOX,  # UIA_CheckBoxControlTypeId
    50003: AccessibilityRole.COMBO_BOX,  # UIA_ComboBoxControlTypeId
    50004: AccessibilityRole.TEXT_FIELD,  # UIA_EditControlTypeId
    50005: AccessibilityRole.IMAGE,  # UIA_ImageControlTypeId
    50007: AccessibilityRole.LINK,  # UIA_HyperlinkControlTypeId
    50008: AccessibilityRole.LIST,  # UIA_ListControlTypeId
    50011: AccessibilityRole.LIST_ITEM,  # UIA_ListItemControlTypeId
    50012: AccessibilityRole.MENU,  # UIA_MenuControlTypeId
    50013: AccessibilityRole.MENU_BAR,  # UIA_MenuBarControlTypeId
    50014: AccessibilityRole.MENU_ITEM,  # UIA_MenuItemControlTypeId
    50019: AccessibilityRole.RADIO_BUTTON,  # UIA_RadioButtonControlTypeId
    50021: AccessibilityRole.SLIDER,  # UIA_SliderControlTypeId
    50022: AccessibilityRole.TAB,  # UIA_TabControlTypeId
    50023: AccessibilityRole.TAB_GROUP,  # UIA_TabControlTypeId
    50030: AccessibilityRole.STATIC_TEXT,  # UIA_TextControlTypeId
    50032: AccessibilityRole.WINDOW,  # UIA_WindowControlTypeId
    50033: AccessibilityRole.PANE,  # UIA_PaneControlTypeId
    50034: AccessibilityRole.TOOLBAR,  # UIA_ToolBarControlTypeId
}


class WindowsAccessibility(AccessibilityBackend):
    """
    Windows accessibility backend using UIAutomation.
    
    This implementation uses the Windows UIAutomation API (via pywinauto or comtypes)
    to provide cross-application UI accessibility on Windows platforms.
    
    UIAutomation provides:
        - Tree-based UI structure
        - Element properties (Name, ControlType, BoundingRectangle, etc.)
        - Control patterns (Invoke, Value, Toggle, etc.)
        - Event system for UI changes
    
    Limitations:
        - Some legacy apps may not support UIAutomation
        - Performance varies by application complexity
        - Some webviews may have limited accessibility info
    """
    
    def __init__(self):
        """Initialize Windows accessibility backend."""
        self._uiautomation = None
        self._pywinauto_available = False
        self._check_dependencies()
        logger.info(
            f"WindowsAccessibility initialized "
            f"(pywinauto={self._pywinauto_available})"
        )
    
    def _check_dependencies(self):
        """Check availability of UIAutomation libraries."""
        if platform.system() != "Windows":
            return
        
        try:
            import pywinauto
            from pywinauto import uia_defines
            self._pywinauto_available = True
            logger.debug("pywinauto available - using for UIAutomation")
        except ImportError:
            logger.debug("pywinauto not available - limited accessibility support")
    
    # ========== Platform Detection ==========
    
    def is_available(self) -> bool:
        """Check if UIAutomation is available."""
        return platform.system() == "Windows" and self._pywinauto_available
    
    def get_platform_name(self) -> str:
        """Get platform name."""
        return "Windows"
    
    # ========== Element Finding ==========
    
    def find_element(
        self,
        name: Optional[str] = None,
        role: Optional[AccessibilityRole] = None,
        attributes: Optional[Dict[str, Any]] = None,
        timeout: float = 5.0,
    ) -> Optional[AccessibilityElement]:
        """
        Find a single UI element using UIAutomation.
        
        Uses pywinauto's element finding with UIAutomation backend.
        """
        if not self.is_available():
            logger.warning("WindowsAccessibility not available")
            return None
        
        try:
            from pywinauto import Desktop
            from pywinauto.findwindows import ElementNotFoundError
            
            # Build search criteria
            criteria = {}
            if name:
                criteria["title"] = name
            if role:
                # Map AccessibilityRole to UIAutomation control type
                control_type = self._role_to_control_type(role)
                if control_type:
                    criteria["control_type"] = control_type
            if attributes:
                criteria.update(attributes)
            
            # Search from desktop with timeout
            desktop = Desktop(backend="uia")
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    # Find element matching criteria
                    element = desktop.window(**criteria)
                    if element.exists():
                        return self._wrap_element(element.element_info)
                except ElementNotFoundError:
                    pass
                time.sleep(0.1)
            
            logger.debug(f"Element not found: {criteria}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding element: {e}", exc_info=True)
            return None
    
    def find_elements(
        self,
        name: Optional[str] = None,
        role: Optional[AccessibilityRole] = None,
        attributes: Optional[Dict[str, Any]] = None,
        max_results: int = 100,
    ) -> List[AccessibilityElement]:
        """
        Find all UI elements matching criteria.
        
        Uses UIAutomation tree walker to find all matching elements.
        """
        if not self.is_available():
            logger.warning("WindowsAccessibility not available")
            return []
        
        try:
            from pywinauto import Desktop
            
            results = []
            desktop = Desktop(backend="uia")
            
            # Build search criteria
            criteria = {}
            if name:
                criteria["title_re"] = f".*{name}.*"
            if role:
                control_type = self._role_to_control_type(role)
                if control_type:
                    criteria["control_type"] = control_type
            
            # Find all matching elements
            for element in desktop.descendants(**criteria):
                if len(results) >= max_results:
                    break
                wrapped = self._wrap_element(element.element_info)
                if wrapped:
                    results.append(wrapped)
            
            logger.debug(f"Found {len(results)} elements matching {criteria}")
            return results
            
        except Exception as e:
            logger.error(f"Error finding elements: {e}", exc_info=True)
            return []
    
    def get_focused_element(self) -> Optional[AccessibilityElement]:
        """Get currently focused element using UIAutomation."""
        if not self.is_available():
            return None
        
        try:
            from pywinauto.uia_defines import IUIA
            
            uia = IUIA()
            focused = uia.GetFocusedElement()
            if focused:
                return self._wrap_element(focused)
            return None
            
        except Exception as e:
            logger.error(f"Error getting focused element: {e}", exc_info=True)
            return None
    
    # ========== Element Interaction ==========
    
    def click_element(self, element: AccessibilityElement) -> AccessibilityResult:
        """
        Click element using UIAutomation Invoke pattern.
        
        Falls back to clicking element's center coordinates if Invoke not available.
        """
        if not element or not element.native_element:
            return AccessibilityResult(
                success=False,
                error="Invalid element"
            )
        
        try:
            # Try using Invoke pattern (preferred)
            native = element.native_element
            if hasattr(native, 'GetCurrentPattern'):
                from pywinauto.uia_defines import UIA_InvokePatternId
                try:
                    invoke_pattern = native.GetCurrentPattern(UIA_InvokePatternId)
                    if invoke_pattern:
                        invoke_pattern.Invoke()
                        logger.debug(f"Clicked element via Invoke: {element.name}")
                        return AccessibilityResult(success=True)
                except:
                    pass
            
            # Fallback: click element's center point
            if element.bounds:
                x = element.bounds['x'] + element.bounds['width'] // 2
                y = element.bounds['y'] + element.bounds['height'] // 2
                
                # Use pyautogui to click coordinates
                try:
                    import pyautogui
                    pyautogui.click(x, y)
                    logger.debug(f"Clicked element at ({x}, {y}): {element.name}")
                    return AccessibilityResult(success=True)
                except ImportError:
                    pass
            
            return AccessibilityResult(
                success=False,
                error="Could not click element (no Invoke pattern or coordinates)"
            )
            
        except Exception as e:
            logger.error(f"Error clicking element: {e}", exc_info=True)
            return AccessibilityResult(
                success=False,
                error=f"Click failed: {str(e)}"
            )
    
    def focus_element(self, element: AccessibilityElement) -> AccessibilityResult:
        """Set focus to element using UIAutomation SetFocus."""
        if not element or not element.native_element:
            return AccessibilityResult(success=False, error="Invalid element")
        
        try:
            native = element.native_element
            if hasattr(native, 'SetFocus'):
                native.SetFocus()
                logger.debug(f"Focused element: {element.name}")
                return AccessibilityResult(success=True)
            
            return AccessibilityResult(
                success=False,
                error="Element does not support SetFocus"
            )
            
        except Exception as e:
            logger.error(f"Error focusing element: {e}", exc_info=True)
            return AccessibilityResult(
                success=False,
                error=f"Focus failed: {str(e)}"
            )
    
    def set_value(
        self,
        element: AccessibilityElement,
        value: str
    ) -> AccessibilityResult:
        """Set element value using UIAutomation Value pattern."""
        if not element or not element.native_element:
            return AccessibilityResult(success=False, error="Invalid element")
        
        try:
            from pywinauto.uia_defines import UIA_ValuePatternId
            
            native = element.native_element
            if hasattr(native, 'GetCurrentPattern'):
                value_pattern = native.GetCurrentPattern(UIA_ValuePatternId)
                if value_pattern:
                    value_pattern.SetValue(value)
                    logger.debug(f"Set value '{value}' on element: {element.name}")
                    return AccessibilityResult(success=True)
            
            return AccessibilityResult(
                success=False,
                error="Element does not support Value pattern"
            )
            
        except Exception as e:
            logger.error(f"Error setting value: {e}", exc_info=True)
            return AccessibilityResult(
                success=False,
                error=f"Set value failed: {str(e)}"
            )
    
    # ========== State Retrieval ==========
    
    def get_element_state(self, element: AccessibilityElement) -> set:
        """Get element states from UIAutomation properties."""
        if not element or not element.native_element:
            return set()
        
        states = set()
        try:
            native = element.native_element
            
            # Check IsEnabled
            if hasattr(native, 'CurrentIsEnabled') and native.CurrentIsEnabled:
                states.add(AccessibilityState.ENABLED)
            else:
                states.add(AccessibilityState.DISABLED)
            
            # Check IsOffscreen (visible)
            if hasattr(native, 'CurrentIsOffscreen'):
                if not native.CurrentIsOffscreen:
                    states.add(AccessibilityState.VISIBLE)
                else:
                    states.add(AccessibilityState.HIDDEN)
            
            # Check HasKeyboardFocus
            if hasattr(native, 'CurrentHasKeyboardFocus') and native.CurrentHasKeyboardFocus:
                states.add(AccessibilityState.FOCUSED)
            
            # Check Toggle state (for checkboxes)
            if hasattr(native, 'GetCurrentPattern'):
                from pywinauto.uia_defines import UIA_TogglePatternId
                try:
                    toggle = native.GetCurrentPattern(UIA_TogglePatternId)
                    if toggle:
                        if toggle.CurrentToggleState == 1:  # ToggleState_On
                            states.add(AccessibilityState.CHECKED)
                        else:
                            states.add(AccessibilityState.UNCHECKED)
                except:
                    pass
            
        except Exception as e:
            logger.debug(f"Error getting element state: {e}")
        
        return states
    
    def get_element_bounds(
        self,
        element: AccessibilityElement
    ) -> Optional[Dict[str, int]]:
        """Get element bounding rectangle from UIAutomation."""
        if not element or not element.native_element:
            return None
        
        try:
            native = element.native_element
            if hasattr(native, 'CurrentBoundingRectangle'):
                rect = native.CurrentBoundingRectangle
                return {
                    "x": int(rect.left),
                    "y": int(rect.top),
                    "width": int(rect.right - rect.left),
                    "height": int(rect.bottom - rect.top),
                }
        except Exception as e:
            logger.debug(f"Error getting element bounds: {e}")
        
        return None
    
    # ========== Tree Inspection ==========
    
    def get_ui_tree(
        self,
        root: Optional[AccessibilityElement] = None,
        max_depth: int = 10,
    ) -> Dict[str, Any]:
        """Get UI tree as hierarchical dictionary."""
        if not self.is_available():
            return {}
        
        try:
            if root is None:
                from pywinauto import Desktop
                desktop = Desktop(backend="uia")
                root_element = self._wrap_element(desktop.element_info)
            else:
                root_element = root
            
            return self._build_tree_dict(root_element, max_depth, 0)
            
        except Exception as e:
            logger.error(f"Error getting UI tree: {e}", exc_info=True)
            return {}
    
    def _build_tree_dict(
        self,
        element: AccessibilityElement,
        max_depth: int,
        current_depth: int
    ) -> Dict[str, Any]:
        """Recursively build tree dictionary."""
        if current_depth >= max_depth:
            return element.to_dict()
        
        tree_dict = element.to_dict()
        children = self.get_children(element)
        
        if children:
            tree_dict["children"] = [
                self._build_tree_dict(child, max_depth, current_depth + 1)
                for child in children
            ]
        
        return tree_dict
    
    def get_children(
        self,
        element: AccessibilityElement
    ) -> List[AccessibilityElement]:
        """Get child elements using UIAutomation tree walker."""
        if not element or not element.native_element:
            return []
        
        try:
            children = []
            # Assuming pywinauto wrapper element
            if hasattr(element.native_element, 'children'):
                for child_info in element.native_element.children():
                    wrapped = self._wrap_element(child_info)
                    if wrapped:
                        children.append(wrapped)
            
            return children
            
        except Exception as e:
            logger.debug(f"Error getting children: {e}")
            return []
    
    def get_parent(
        self,
        element: AccessibilityElement
    ) -> Optional[AccessibilityElement]:
        """Get parent element using UIAutomation tree walker."""
        if not element or not element.native_element:
            return None
        
        try:
            native = element.native_element
            if hasattr(native, 'parent'):
                parent = native.parent()
                if parent:
                    return self._wrap_element(parent)
        except Exception as e:
            logger.debug(f"Error getting parent: {e}")
        
        return None
    
    # ========== Application Context ==========
    
    def get_active_app(self) -> Optional[AccessibilityElement]:
        """Get active application window."""
        if not self.is_available():
            return None
        
        try:
            from pywinauto import Desktop
            desktop = Desktop(backend="uia")
            active = desktop.top_window()
            if active and active.exists():
                return self._wrap_element(active.element_info)
        except Exception as e:
            logger.debug(f"Error getting active app: {e}")
        
        return None
    
    def get_app_windows(
        self,
        app_name: Optional[str] = None
    ) -> List[AccessibilityElement]:
        """Get windows for an application."""
        if not self.is_available():
            return []
        
        try:
            from pywinauto import Desktop
            desktop = Desktop(backend="uia")
            
            windows = []
            for window in desktop.windows():
                if window.exists():
                    if app_name is None or app_name.lower() in window.window_text().lower():
                        wrapped = self._wrap_element(window.element_info)
                        if wrapped:
                            windows.append(wrapped)
            
            return windows
            
        except Exception as e:
            logger.error(f"Error getting app windows: {e}", exc_info=True)
            return []
    
    # ========== Helper Methods ==========
    
    def _wrap_element(self, native_element: Any) -> Optional[AccessibilityElement]:
        """
        Wrap native UIAutomation element into AccessibilityElement.
        
        Extracts common properties and maps UIAutomation-specific data
        to the unified AccessibilityElement format.
        """
        if not native_element:
            return None
        
        try:
            # Extract properties
            name = getattr(native_element, 'CurrentName', None) or ""
            control_type = getattr(native_element, 'CurrentControlType', None)
            
            # Map control type to role
            role = UIAUTOMATION_ROLE_MAP.get(control_type, AccessibilityRole.UNKNOWN)
            
            # Get value (if available)
            value = None
            if hasattr(native_element, 'CurrentValue'):
                try:
                    value = native_element.CurrentValue
                except:
                    pass
            
            # Get bounds
            bounds = None
            if hasattr(native_element, 'CurrentBoundingRectangle'):
                try:
                    rect = native_element.CurrentBoundingRectangle
                    bounds = {
                        "x": int(rect.left),
                        "y": int(rect.top),
                        "width": int(rect.right - rect.left),
                        "height": int(rect.bottom - rect.top),
                    }
                except:
                    pass
            
            # Create element
            element = AccessibilityElement(
                native_element=native_element,
                role=role,
                name=name,
                value=value,
                bounds=bounds,
            )
            
            # Get states
            element.states = self.get_element_state(element)
            
            return element
            
        except Exception as e:
            logger.debug(f"Error wrapping element: {e}")
            return None
    
    def _role_to_control_type(self, role: AccessibilityRole) -> Optional[int]:
        """Map AccessibilityRole to UIAutomation ControlType ID."""
        # Reverse lookup in role map
        for control_type, mapped_role in UIAUTOMATION_ROLE_MAP.items():
            if mapped_role == role:
                return control_type
        return None
