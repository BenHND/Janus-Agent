"""
macOS Accessibility Backend - AXUIElement implementation.

This module implements the AccessibilityBackend interface using macOS Accessibility API
(AXUIElement via pyobjc). The Accessibility API is the standard way to interact with
UI elements on macOS.

Features:
    - Element finding using AX attributes and parameterized attributes
    - Element interaction (click, focus, set value) via AX actions
    - State retrieval from AX attributes
    - UI tree traversal using AXChildren hierarchy
    - Support for native apps, some Electron apps, and limited webviews

Dependencies:
    - pyobjc-framework-ApplicationServices (for AXUIElement)
    - pyobjc-framework-Cocoa (for NSWorkspace, NSRunningApplication)

Performance:
    - Element finding: 10-100ms (vs 200-500ms for vision)
    - State retrieval: <5ms (vs 100-300ms for OCR)
    - Click action: <10ms (vs 50-100ms for vision)

Compatibility:
    - Native macOS apps: Excellent
    - Electron apps: Good (via AXUIElement)
    - Webviews: Partial (depends on implementation)
    - Legacy apps: Good (macOS has strong accessibility support)
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


# Role mapping: AXRole to AccessibilityRole
AX_ROLE_MAP = {
    "AXButton": AccessibilityRole.BUTTON,
    "AXCheckBox": AccessibilityRole.CHECKBOX,
    "AXRadioButton": AccessibilityRole.RADIO_BUTTON,
    "AXTextField": AccessibilityRole.TEXT_FIELD,
    "AXTextArea": AccessibilityRole.TEXT_AREA,
    "AXComboBox": AccessibilityRole.COMBO_BOX,
    "AXList": AccessibilityRole.LIST,
    "AXRow": AccessibilityRole.LIST_ITEM,
    "AXTable": AccessibilityRole.TABLE,
    "AXCell": AccessibilityRole.CELL,
    "AXSlider": AccessibilityRole.SLIDER,
    "AXMenu": AccessibilityRole.MENU,
    "AXMenuItem": AccessibilityRole.MENU_ITEM,
    "AXMenuBar": AccessibilityRole.MENU_BAR,
    "AXRadioGroup": AccessibilityRole.TAB_GROUP,
    "AXTab": AccessibilityRole.TAB,
    "AXWindow": AccessibilityRole.WINDOW,
    "AXDialog": AccessibilityRole.DIALOG,
    "AXGroup": AccessibilityRole.GROUP,
    "AXScrollArea": AccessibilityRole.SCROLL_AREA,
    "AXToolbar": AccessibilityRole.TOOLBAR,
    "AXStaticText": AccessibilityRole.STATIC_TEXT,
    "AXImage": AccessibilityRole.IMAGE,
    "AXLink": AccessibilityRole.LINK,
    "AXHeading": AccessibilityRole.HEADING,
    "AXApplication": AccessibilityRole.APPLICATION,
}


class MacOSAccessibility(AccessibilityBackend):
    """
    macOS accessibility backend using AXUIElement.
    
    This implementation uses the macOS Accessibility API (via pyobjc)
    to provide cross-application UI accessibility on macOS platforms.
    
    AXUIElement provides:
        - Tree-based UI structure via AXChildren
        - Element attributes (AXTitle, AXRole, AXValue, AXPosition, etc.)
        - Element actions (AXPress, AXRaise, etc.)
        - Parameterized attributes for complex queries
    
    Limitations:
        - Requires Accessibility permissions in System Preferences
        - Some apps may not expose full accessibility tree
        - Performance varies by application complexity
        - Some webviews may have limited accessibility info
    """
    
    def __init__(self):
        """Initialize macOS accessibility backend."""
        self._ax_available = False
        self._check_dependencies()
        logger.info(
            f"MacOSAccessibility initialized (ax_available={self._ax_available})"
        )
    
    def _check_dependencies(self):
        """Check availability of AXUIElement libraries."""
        if platform.system() != "Darwin":
            return
        
        try:
            from ApplicationServices import (
                AXUIElementCreateSystemWide,
                AXUIElementCopyAttributeValue,
                AXValueGetValue,
            )
            from Cocoa import NSWorkspace
            self._ax_available = True
            logger.debug("AXUIElement available")
        except ImportError as e:
            logger.debug(f"AXUIElement not available: {e}")
    
    # ========== Platform Detection ==========
    
    def is_available(self) -> bool:
        """Check if AXUIElement is available."""
        return platform.system() == "Darwin" and self._ax_available
    
    def get_platform_name(self) -> str:
        """Get platform name."""
        return "macOS"
    
    # ========== Element Finding ==========
    
    def find_element(
        self,
        name: Optional[str] = None,
        role: Optional[AccessibilityRole] = None,
        attributes: Optional[Dict[str, Any]] = None,
        timeout: float = 5.0,
    ) -> Optional[AccessibilityElement]:
        """
        Find a single UI element using AXUIElement.
        
        Searches the accessibility tree starting from the focused application.
        """
        if not self.is_available():
            logger.warning("MacOSAccessibility not available")
            return None
        
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # Get active application
                app_element = self.get_active_app()
                if not app_element:
                    time.sleep(0.1)
                    continue
                
                # Search recursively
                result = self._search_element(
                    app_element,
                    name=name,
                    role=role,
                    attributes=attributes,
                    max_depth=20
                )
                
                if result:
                    return result
                
                time.sleep(0.1)
            
            logger.debug(f"Element not found: name={name}, role={role}")
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
        
        Searches the accessibility tree and returns all matching elements.
        """
        if not self.is_available():
            logger.warning("MacOSAccessibility not available")
            return []
        
        try:
            results = []
            app_element = self.get_active_app()
            if not app_element:
                return []
            
            # Search recursively
            self._collect_elements(
                app_element,
                name=name,
                role=role,
                attributes=attributes,
                results=results,
                max_results=max_results,
                max_depth=20,
                current_depth=0
            )
            
            logger.debug(f"Found {len(results)} elements")
            return results
            
        except Exception as e:
            logger.error(f"Error finding elements: {e}", exc_info=True)
            return []
    
    def get_focused_element(self) -> Optional[AccessibilityElement]:
        """Get currently focused element using AXFocusedUIElement."""
        if not self.is_available():
            return None
        
        try:
            from ApplicationServices import (
                AXUIElementCreateSystemWide,
                AXUIElementCopyAttributeValue,
                kAXFocusedUIElementAttribute,
            )
            
            system_wide = AXUIElementCreateSystemWide()
            error, focused = AXUIElementCopyAttributeValue(
                system_wide,
                kAXFocusedUIElementAttribute,
                None
            )
            
            if error == 0 and focused:
                return self._wrap_element(focused)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting focused element: {e}", exc_info=True)
            return None
    
    # ========== Element Interaction ==========
    
    def click_element(self, element: AccessibilityElement) -> AccessibilityResult:
        """
        Click element using AXPress action.
        
        Falls back to clicking element's center coordinates if AXPress not available.
        """
        if not element or not element.native_element:
            return AccessibilityResult(
                success=False,
                error="Invalid element"
            )
        
        try:
            from ApplicationServices import (
                AXUIElementPerformAction,
                kAXPressAction,
            )
            
            # Try AXPress action
            native = element.native_element
            error = AXUIElementPerformAction(native, kAXPressAction)
            
            if error == 0:
                logger.debug(f"Clicked element via AXPress: {element.name}")
                return AccessibilityResult(success=True)
            
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
                error=f"Could not click element (AXPress error={error})"
            )
            
        except Exception as e:
            logger.error(f"Error clicking element: {e}", exc_info=True)
            return AccessibilityResult(
                success=False,
                error=f"Click failed: {str(e)}"
            )
    
    def focus_element(self, element: AccessibilityElement) -> AccessibilityResult:
        """Set focus to element using AXFocused attribute."""
        if not element or not element.native_element:
            return AccessibilityResult(success=False, error="Invalid element")
        
        try:
            from ApplicationServices import (
                AXUIElementSetAttributeValue,
                kAXFocusedAttribute,
            )
            from Cocoa import NSNumber
            
            native = element.native_element
            error = AXUIElementSetAttributeValue(
                native,
                kAXFocusedAttribute,
                NSNumber.numberWithBool_(True)
            )
            
            if error == 0:
                logger.debug(f"Focused element: {element.name}")
                return AccessibilityResult(success=True)
            
            return AccessibilityResult(
                success=False,
                error=f"SetFocus error={error}"
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
        """Set element value using AXValue attribute."""
        if not element or not element.native_element:
            return AccessibilityResult(success=False, error="Invalid element")
        
        try:
            from ApplicationServices import (
                AXUIElementSetAttributeValue,
                kAXValueAttribute,
            )
            from Cocoa import NSString
            
            native = element.native_element
            error = AXUIElementSetAttributeValue(
                native,
                kAXValueAttribute,
                NSString.stringWithString_(value)
            )
            
            if error == 0:
                logger.debug(f"Set value '{value}' on element: {element.name}")
                return AccessibilityResult(success=True)
            
            return AccessibilityResult(
                success=False,
                error=f"SetValue error={error}"
            )
            
        except Exception as e:
            logger.error(f"Error setting value: {e}", exc_info=True)
            return AccessibilityResult(
                success=False,
                error=f"Set value failed: {str(e)}"
            )
    
    # ========== State Retrieval ==========
    
    def get_element_state(self, element: AccessibilityElement) -> set:
        """Get element states from AX attributes."""
        if not element or not element.native_element:
            return set()
        
        states = set()
        try:
            from ApplicationServices import AXUIElementCopyAttributeValue
            
            # TICKET-ARCHI: Handle import failure gracefully
            try:
                from Cocoa import (
                    kAXEnabledAttribute,
                    kAXFocusedAttribute,
                    kAXValueAttribute,
                )
            except ImportError:
                # Fallback to string constants (works on most macOS versions)
                kAXEnabledAttribute = "AXEnabled"
                kAXFocusedAttribute = "AXFocused"
                kAXValueAttribute = "AXValue"
            
            native = element.native_element
            
            # Check enabled
            error, enabled = AXUIElementCopyAttributeValue(
                native, kAXEnabledAttribute, None
            )
            if error == 0 and enabled:
                states.add(AccessibilityState.ENABLED)
            else:
                states.add(AccessibilityState.DISABLED)
            
            # Check focused
            error, focused = AXUIElementCopyAttributeValue(
                native, kAXFocusedAttribute, None
            )
            if error == 0 and focused:
                states.add(AccessibilityState.FOCUSED)
            
            # Check value for checkboxes (0=unchecked, 1=checked)
            if element.role == AccessibilityRole.CHECKBOX:
                error, value = AXUIElementCopyAttributeValue(
                    native, kAXValueAttribute, None
                )
                if error == 0 and value is not None:
                    if value == 1:
                        states.add(AccessibilityState.CHECKED)
                    else:
                        states.add(AccessibilityState.UNCHECKED)
            
            # Assume visible (macOS doesn't have a direct "visible" attribute)
            states.add(AccessibilityState.VISIBLE)
            
        except Exception as e:
            logger.debug(f"Error getting element state: {e}")
        
        return states
    
    def get_element_bounds(
        self,
        element: AccessibilityElement
    ) -> Optional[Dict[str, int]]:
        """Get element bounding rectangle from AXPosition and AXSize."""
        if not element or not element.native_element:
            return None
        
        try:
            from ApplicationServices import (
                AXUIElementCopyAttributeValue,
                AXValueGetValue,
            )
            import time
            import objc
            
            # TICKET-ARCHI: Handle import failure gracefully
            try:
                from ApplicationServices import (
                    kAXPositionAttribute,
                    kAXSizeAttribute,
                )
            except ImportError:
                # Fallback to string constants (works on most macOS versions)
                kAXPositionAttribute = "AXPosition"
                kAXSizeAttribute = "AXSize"

            try:
                from Quartz import CGPoint, CGSize
            except Exception:
                CGPoint = None
                CGSize = None
            
            native = element.native_element
            
            # Get position
            error, position_value = AXUIElementCopyAttributeValue(
                native, kAXPositionAttribute, None
            )
            if error != 0:
                return None
            
            # Get size
            error, size_value = AXUIElementCopyAttributeValue(
                native, kAXSizeAttribute, None
            )
            if error != 0:
                return None
            
            # Extract CGPoint and CGSize
            if CGPoint is None or CGSize is None:
                return None

            position = CGPoint()
            size = CGSize()

            # PyObjC expects the out-parameter pointer semantics; passing the struct
            # instance directly can produce: "'valuePtr' should be None".
            AXValueGetValue(position_value, 1, objc.byref(position))  # kAXValueCGPointType = 1
            AXValueGetValue(size_value, 2, objc.byref(size))  # kAXValueCGSizeType = 2
            
            return {
                "x": int(position.x),
                "y": int(position.y),
                "width": int(size.width),
                "height": int(size.height),
            }
            
        except Exception as e:
            # Avoid flooding logs/terminal when bounds are unavailable.
            now = time.time()
            last = getattr(self, "_bounds_error_last_log_ts", 0.0)
            if now - last > 5.0:
                self._bounds_error_last_log_ts = now
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
                root = self.get_active_app()
            
            if not root:
                return {}
            
            return self._build_tree_dict(root, max_depth, 0)
            
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
        """Get child elements using AXChildren attribute."""
        if not element or not element.native_element:
            return []
        
        try:
            from ApplicationServices import AXUIElementCopyAttributeValue
            
            # TICKET-ARCHI: Handle import failure gracefully
            try:
                from Cocoa import kAXChildrenAttribute
            except ImportError:
                kAXChildrenAttribute = "AXChildren"
            
            native = element.native_element
            error, children_ref = AXUIElementCopyAttributeValue(
                native, kAXChildrenAttribute, None
            )
            
            if error == 0 and children_ref:
                children = []
                for child_ref in children_ref:
                    wrapped = self._wrap_element(child_ref)
                    if wrapped:
                        children.append(wrapped)
                return children
            
            return []
            
        except Exception as e:
            logger.debug(f"Error getting children: {e}")
            return []
    
    def get_parent(
        self,
        element: AccessibilityElement
    ) -> Optional[AccessibilityElement]:
        """Get parent element using AXParent attribute."""
        if not element or not element.native_element:
            return None
        
        try:
            from ApplicationServices import AXUIElementCopyAttributeValue
            
            # TICKET-ARCHI: Handle import failure gracefully
            try:
                from Cocoa import kAXParentAttribute
            except ImportError:
                kAXParentAttribute = "AXParent"
            
            native = element.native_element
            error, parent_ref = AXUIElementCopyAttributeValue(
                native, kAXParentAttribute, None
            )
            
            if error == 0 and parent_ref:
                return self._wrap_element(parent_ref)
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting parent: {e}")
            return None
    
    # ========== Application Context ==========
    
    def get_active_app(self) -> Optional[AccessibilityElement]:
        """Get active application using NSWorkspace."""
        if not self.is_available():
            return None
        
        try:
            from ApplicationServices import AXUIElementCreateApplication
            from Cocoa import NSWorkspace
            
            workspace = NSWorkspace.sharedWorkspace()
            active_app = workspace.frontmostApplication()
            
            if active_app:
                pid = active_app.processIdentifier()
                app_ref = AXUIElementCreateApplication(pid)
                return self._wrap_element(app_ref)
            
            return None
            
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
            from ApplicationServices import (
                AXUIElementCreateApplication,
                AXUIElementCopyAttributeValue,
            )
            from Cocoa import NSWorkspace
            
            # TICKET-ARCHI: Handle import failure gracefully
            try:
                from Cocoa import kAXWindowsAttribute
            except ImportError:
                kAXWindowsAttribute = "AXWindows"
            
            workspace = NSWorkspace.sharedWorkspace()
            windows = []
            
            for app in workspace.runningApplications():
                if app_name and app_name.lower() not in app.localizedName().lower():
                    continue
                
                pid = app.processIdentifier()
                app_ref = AXUIElementCreateApplication(pid)
                
                error, windows_ref = AXUIElementCopyAttributeValue(
                    app_ref, kAXWindowsAttribute, None
                )
                
                if error == 0 and windows_ref:
                    for window_ref in windows_ref:
                        wrapped = self._wrap_element(window_ref)
                        if wrapped:
                            windows.append(wrapped)
            
            return windows
            
        except Exception as e:
            logger.error(f"Error getting app windows: {e}", exc_info=True)
            return []
    
    # ========== Helper Methods ==========
    
    def _wrap_element(self, native_element: Any) -> Optional[AccessibilityElement]:
        """
        Wrap native AXUIElement into AccessibilityElement.
        
        Extracts common AX attributes and maps them to the unified format.
        """
        if not native_element:
            return None
        
        try:
            from ApplicationServices import AXUIElementCopyAttributeValue
            
            # TICKET-ARCHI: Handle kAXTitleAttribute import failure gracefully
            # Some versions of PyObjC/macOS don't expose these constants
            try:
                from ApplicationServices import (
                    kAXTitleAttribute,
                    kAXRoleAttribute,
                    kAXValueAttribute,
                    kAXDescriptionAttribute,
                )
            except ImportError as e:
                logger.warning(f"Failed to import AX constants from ApplicationServices: {e}")
                # Fallback to string constants (works on most macOS versions)
                kAXTitleAttribute = "AXTitle"
                kAXRoleAttribute = "AXRole"
                kAXValueAttribute = "AXValue"
                kAXDescriptionAttribute = "AXDescription"
            
            # Get title (name)
            error, title = AXUIElementCopyAttributeValue(
                native_element, kAXTitleAttribute, None
            )
            name = str(title) if error == 0 and title else None
            
            # Get role
            error, ax_role = AXUIElementCopyAttributeValue(
                native_element, kAXRoleAttribute, None
            )
            role_str = str(ax_role) if error == 0 and ax_role else "AXUnknown"
            role = AX_ROLE_MAP.get(role_str, AccessibilityRole.UNKNOWN)
            
            # Get value
            error, ax_value = AXUIElementCopyAttributeValue(
                native_element, kAXValueAttribute, None
            )
            value = str(ax_value) if error == 0 and ax_value else None
            
            # Get description
            error, ax_desc = AXUIElementCopyAttributeValue(
                native_element, kAXDescriptionAttribute, None
            )
            description = str(ax_desc) if error == 0 and ax_desc else None
            
            # Create element
            element = AccessibilityElement(
                native_element=native_element,
                role=role,
                name=name,
                value=value,
                description=description,
            )
            
            # Get bounds
            element.bounds = self.get_element_bounds(element)
            
            # Get states
            element.states = self.get_element_state(element)
            
            return element
            
        except Exception as e:
            logger.debug(f"Error wrapping element: {e}")
            return None
    
    def _search_element(
        self,
        element: AccessibilityElement,
        name: Optional[str] = None,
        role: Optional[AccessibilityRole] = None,
        attributes: Optional[Dict[str, Any]] = None,
        max_depth: int = 20,
        current_depth: int = 0
    ) -> Optional[AccessibilityElement]:
        """Recursively search for element matching criteria."""
        if current_depth >= max_depth:
            return None
        
        # Check if current element matches
        if self._element_matches(element, name, role, attributes):
            return element
        
        # Search children
        for child in self.get_children(element):
            result = self._search_element(
                child, name, role, attributes, max_depth, current_depth + 1
            )
            if result:
                return result
        
        return None
    
    def _collect_elements(
        self,
        element: AccessibilityElement,
        name: Optional[str] = None,
        role: Optional[AccessibilityRole] = None,
        attributes: Optional[Dict[str, Any]] = None,
        results: Optional[List[AccessibilityElement]] = None,
        max_results: int = 100,
        max_depth: int = 20,
        current_depth: int = 0
    ):
        """Recursively collect all elements matching criteria."""
        if results is None:
            results = []
        
        if current_depth >= max_depth or len(results) >= max_results:
            return
        
        # Check if current element matches
        if self._element_matches(element, name, role, attributes):
            results.append(element)
        
        # Search children
        for child in self.get_children(element):
            self._collect_elements(
                child, name, role, attributes, results,
                max_results, max_depth, current_depth + 1
            )
    
    def _element_matches(
        self,
        element: AccessibilityElement,
        name: Optional[str] = None,
        role: Optional[AccessibilityRole] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if element matches search criteria."""
        if name and element.name:
            if name.lower() not in element.name.lower():
                return False
        
        if role and element.role != role:
            return False
        
        if attributes:
            for key, value in attributes.items():
                if element.attributes.get(key) != value:
                    return False
        
        return True
