"""
Linux Accessibility Backend - AT-SPI2 Implementation

Phase 4: Advanced Features - Linux Support
- Uses AT-SPI2 (Assistive Technology Service Provider Interface)
- Works with GNOME, KDE, and other desktops supporting AT-SPI
- Requires python-atspi package

Installation:
    Ubuntu/Debian: sudo apt-get install python3-pyatspi
    Or: pip install pyatspi2 (if available)
    
Permissions:
    No special permissions required on most Linux desktops
"""

import logging
import platform
from typing import Any, Dict, List, Optional

from .base_accessibility import (
    AccessibilityBackend,
    AccessibilityElement,
    AccessibilityRole,
    AccessibilityState,
    AccessibilityResult,
)

logger = logging.getLogger(__name__)


# AT-SPI2 role mapping to AccessibilityRole
ATSPI_ROLE_MAP = {
    # Using role names as strings since we may not have pyatspi imported
    "ROLE_PUSH_BUTTON": AccessibilityRole.BUTTON,
    "ROLE_CHECK_BOX": AccessibilityRole.CHECKBOX,
    "ROLE_RADIO_BUTTON": AccessibilityRole.RADIO_BUTTON,
    "ROLE_COMBO_BOX": AccessibilityRole.COMBO_BOX,
    "ROLE_TEXT": AccessibilityRole.TEXT_FIELD,
    "ROLE_ENTRY": AccessibilityRole.TEXT_FIELD,
    "ROLE_PASSWORD_TEXT": AccessibilityRole.TEXT_FIELD,
    "ROLE_LINK": AccessibilityRole.LINK,
    "ROLE_IMAGE": AccessibilityRole.IMAGE,
    "ROLE_MENU": AccessibilityRole.MENU,
    "ROLE_MENU_BAR": AccessibilityRole.MENU_BAR,
    "ROLE_MENU_ITEM": AccessibilityRole.MENU_ITEM,
    "ROLE_LIST": AccessibilityRole.LIST,
    "ROLE_LIST_ITEM": AccessibilityRole.LIST_ITEM,
    "ROLE_WINDOW": AccessibilityRole.WINDOW,
    "ROLE_DIALOG": AccessibilityRole.DIALOG,
    "ROLE_FRAME": AccessibilityRole.WINDOW,
    "ROLE_PANEL": AccessibilityRole.PANE,
    "ROLE_SCROLL_PANE": AccessibilityRole.SCROLL_AREA,
    "ROLE_TOOL_BAR": AccessibilityRole.TOOLBAR,
    "ROLE_SLIDER": AccessibilityRole.SLIDER,
    "ROLE_PAGE_TAB": AccessibilityRole.TAB,
    "ROLE_PAGE_TAB_LIST": AccessibilityRole.TAB_GROUP,
    "ROLE_LABEL": AccessibilityRole.STATIC_TEXT,
    "ROLE_HEADING": AccessibilityRole.HEADING,
    "ROLE_APPLICATION": AccessibilityRole.APPLICATION,
}


class LinuxAccessibility(AccessibilityBackend):
    """
    Linux accessibility backend using AT-SPI2.
    
    Provides accessibility API for GNOME, KDE, and other Linux desktops.
    
    Features:
        - Element finding by name and role
        - Click/invoke actions
        - Text field value setting
        - UI tree traversal
        - State retrieval
    
    Limitations:
        - Requires AT-SPI2 support in applications
        - Some custom UI may not expose full accessibility
        - Performance varies by desktop environment
    
    Example:
        backend = LinuxAccessibility()
        if backend.is_available():
            button = backend.find_element(name="OK", role=AccessibilityRole.BUTTON)
            if button:
                backend.click_element(button)
    """
    
    def __init__(self):
        """Initialize Linux accessibility backend."""
        self._atspi = None
        self._available = False
        
        # Try to import pyatspi
        try:
            import pyatspi
            self._atspi = pyatspi
            self._available = True
            logger.info("✓ Linux AT-SPI2 accessibility available")
        except ImportError:
            logger.info(
                "⚠️  pyatspi not available. Install with: "
                "sudo apt-get install python3-pyatspi"
            )
    
    # ========== Platform Detection ==========
    
    def is_available(self) -> bool:
        """Check if AT-SPI2 accessibility is available."""
        return platform.system() == "Linux" and self._available
    
    def get_platform_name(self) -> str:
        """Get platform name."""
        return "Linux (AT-SPI2)"
    
    # ========== Element Finding ==========
    
    def find_element(
        self,
        name: Optional[str] = None,
        role: Optional[AccessibilityRole] = None,
        attributes: Optional[Dict[str, Any]] = None,
        timeout: float = 5.0
    ) -> Optional[AccessibilityElement]:
        """
        Find first element matching criteria.
        
        Args:
            name: Element name/label
            role: Element role
            attributes: Additional attributes
            timeout: Search timeout
            
        Returns:
            AccessibilityElement or None
        """
        if not self._available:
            return None
        
        try:
            # Get desktop object (root of accessibility tree)
            desktop = self._atspi.Registry.getDesktop(0)
            
            # Search for element
            element = self._search_tree(desktop, name, role, max_depth=20)
            
            return element
            
        except Exception as e:
            logger.debug(f"Failed to find element: {e}")
            return None
    
    def find_elements(
        self,
        name: Optional[str] = None,
        role: Optional[AccessibilityRole] = None,
        attributes: Optional[Dict[str, Any]] = None,
        max_results: int = 100
    ) -> List[AccessibilityElement]:
        """Find all elements matching criteria."""
        if not self._available:
            return []
        
        try:
            desktop = self._atspi.Registry.getDesktop(0)
            results = []
            self._collect_elements(desktop, name, role, results, max_results)
            return results
        except Exception as e:
            logger.debug(f"Failed to find elements: {e}")
            return []
    
    def get_focused_element(self) -> Optional[AccessibilityElement]:
        """Get currently focused element."""
        if not self._available:
            return None
        
        try:
            # Get active window first
            desktop = self._atspi.Registry.getDesktop(0)
            
            for app_idx in range(desktop.childCount):
                app = desktop.getChildAtIndex(app_idx)
                
                # Find focused element in this app
                focused = self._find_focused_in_tree(app)
                if focused:
                    return focused
            
            return None
        except Exception as e:
            logger.debug(f"Failed to get focused element: {e}")
            return None
    
    # ========== Element Interaction ==========
    
    def click_element(self, element: AccessibilityElement) -> AccessibilityResult:
        """Click/invoke element."""
        if not self._available or not element:
            return AccessibilityResult(
                success=False,
                error="AT-SPI2 not available or invalid element"
            )
        
        try:
            native = element.native_element
            
            # Try to invoke the action
            action_iface = native.queryAction()
            
            if action_iface:
                # Find and invoke the default action (usually "click" or "press")
                for i in range(action_iface.nActions):
                    action_name = action_iface.getName(i)
                    if action_name in ["click", "press", "activate"]:
                        action_iface.doAction(i)
                        return AccessibilityResult(success=True)
                
                # If no specific action found, try first action
                if action_iface.nActions > 0:
                    action_iface.doAction(0)
                    return AccessibilityResult(success=True)
            
            return AccessibilityResult(
                success=False,
                error="No action interface available"
            )
            
        except Exception as e:
            return AccessibilityResult(success=False, error=str(e))
    
    def focus_element(self, element: AccessibilityElement) -> AccessibilityResult:
        """Focus element."""
        if not self._available or not element:
            return AccessibilityResult(success=False, error="Not available")
        
        try:
            native = element.native_element
            component = native.queryComponent()
            
            if component:
                component.grabFocus()
                return AccessibilityResult(success=True)
            
            return AccessibilityResult(success=False, error="No component interface")
        except Exception as e:
            return AccessibilityResult(success=False, error=str(e))
    
    def set_value(
        self,
        element: AccessibilityElement,
        value: str
    ) -> AccessibilityResult:
        """Set element value (for text fields)."""
        if not self._available or not element:
            return AccessibilityResult(success=False, error="Not available")
        
        try:
            native = element.native_element
            editable_text = native.queryEditableText()
            
            if editable_text:
                # Clear existing text
                text_length = editable_text.characterCount
                if text_length > 0:
                    editable_text.deleteText(0, text_length)
                
                # Insert new text
                editable_text.insertText(0, value, len(value))
                return AccessibilityResult(success=True)
            
            return AccessibilityResult(
                success=False,
                error="Element not editable"
            )
        except Exception as e:
            return AccessibilityResult(success=False, error=str(e))
    
    # ========== State Retrieval ==========
    
    def get_element_state(self, element: AccessibilityElement) -> set:
        """Get element states."""
        if not element or not element.native_element:
            return set()
        
        return element.states
    
    def get_element_bounds(
        self,
        element: AccessibilityElement
    ) -> Optional[Dict[str, int]]:
        """Get element position and size."""
        if not element or not element.native_element:
            return None
        
        return element.bounds
    
    # ========== Tree Inspection ==========
    
    def get_ui_tree(
        self,
        root: Optional[AccessibilityElement] = None,
        max_depth: int = 10
    ) -> Dict[str, Any]:
        """Get UI element tree."""
        if not self._available:
            return {}
        
        try:
            if root:
                native = root.native_element
            else:
                desktop = self._atspi.Registry.getDesktop(0)
                native = desktop
            
            return self._build_tree_dict(native, max_depth=max_depth)
        except Exception as e:
            logger.debug(f"Failed to get UI tree: {e}")
            return {}
    
    def get_children(
        self,
        element: AccessibilityElement
    ) -> List[AccessibilityElement]:
        """Get child elements."""
        if not element or not element.native_element:
            return []
        
        try:
            native = element.native_element
            children = []
            
            for i in range(native.childCount):
                child = native.getChildAtIndex(i)
                if child:
                    child_elem = self._create_element(child)
                    if child_elem:
                        children.append(child_elem)
            
            return children
        except Exception as e:
            logger.debug(f"Failed to get children: {e}")
            return []
    
    def get_parent(
        self,
        element: AccessibilityElement
    ) -> Optional[AccessibilityElement]:
        """Get parent element."""
        if not element or not element.native_element:
            return None
        
        try:
            parent = element.native_element.parent
            return self._create_element(parent) if parent else None
        except Exception as e:
            logger.debug(f"Failed to get parent: {e}")
            return None
    
    # ========== Application Context ==========
    
    def get_active_app(self) -> Optional[AccessibilityElement]:
        """Get active application."""
        if not self._available:
            return None
        
        try:
            desktop = self._atspi.Registry.getDesktop(0)
            
            # Find first active window
            for app_idx in range(desktop.childCount):
                app = desktop.getChildAtIndex(app_idx)
                
                for win_idx in range(app.childCount):
                    window = app.getChildAtIndex(win_idx)
                    state_set = window.getState()
                    
                    if state_set.contains(self._atspi.STATE_ACTIVE):
                        return self._create_element(app)
            
            return None
        except Exception as e:
            logger.debug(f"Failed to get active app: {e}")
            return None
    
    def get_app_windows(self, app_name: str) -> List[AccessibilityElement]:
        """Get all windows for an application."""
        # Not implemented yet
        return []
    
    # ========== Helper Methods ==========
    
    def _create_element(self, native) -> Optional[AccessibilityElement]:
        """Create AccessibilityElement from AT-SPI object."""
        if not native:
            return None
        
        try:
            # Get role
            role_name = str(native.getRoleName()).upper().replace(" ", "_")
            role = ATSPI_ROLE_MAP.get(f"ROLE_{role_name}", AccessibilityRole.UNKNOWN)
            
            # Get name
            name = native.name if hasattr(native, 'name') else None
            
            # Get description
            description = native.description if hasattr(native, 'description') else None
            
            # Get bounds
            bounds = None
            try:
                component = native.queryComponent()
                if component:
                    extents = component.getExtents(0)  # 0 = screen coordinates
                    bounds = {
                        "x": extents.x,
                        "y": extents.y,
                        "width": extents.width,
                        "height": extents.height
                    }
            except:
                pass
            
            # Get states
            states = set()
            try:
                state_set = native.getState()
                if state_set.contains(self._atspi.STATE_ENABLED):
                    states.add(AccessibilityState.ENABLED)
                else:
                    states.add(AccessibilityState.DISABLED)
                
                if state_set.contains(self._atspi.STATE_VISIBLE):
                    states.add(AccessibilityState.VISIBLE)
                else:
                    states.add(AccessibilityState.HIDDEN)
                
                if state_set.contains(self._atspi.STATE_FOCUSED):
                    states.add(AccessibilityState.FOCUSED)
                
                if state_set.contains(self._atspi.STATE_CHECKED):
                    states.add(AccessibilityState.CHECKED)
            except:
                pass
            
            return AccessibilityElement(
                native_element=native,
                role=role,
                name=name,
                value=None,
                description=description,
                bounds=bounds,
                states=states,
                attributes={}
            )
            
        except Exception as e:
            logger.debug(f"Failed to create element: {e}")
            return None
    
    def _search_tree(
        self,
        node,
        name: Optional[str],
        role: Optional[AccessibilityRole],
        current_depth: int = 0,
        max_depth: int = 20
    ) -> Optional[AccessibilityElement]:
        """Recursively search tree for element."""
        if current_depth >= max_depth:
            return None
        
        try:
            # Check current node
            element = self._create_element(node)
            
            if element and self._matches(element, name, role):
                return element
            
            # Search children
            for i in range(node.childCount):
                child = node.getChildAtIndex(i)
                if child:
                    result = self._search_tree(child, name, role, current_depth + 1, max_depth)
                    if result:
                        return result
            
            return None
        except Exception as e:
            logger.debug(f"Search error: {e}")
            return None
    
    def _matches(
        self,
        element: AccessibilityElement,
        name: Optional[str],
        role: Optional[AccessibilityRole]
    ) -> bool:
        """Check if element matches search criteria."""
        if name and (not element.name or name.lower() not in element.name.lower()):
            return False
        
        if role and element.role != role:
            return False
        
        return True
    
    def _collect_elements(
        self,
        node,
        name: Optional[str],
        role: Optional[AccessibilityRole],
        results: List[AccessibilityElement],
        max_results: int,
        current_depth: int = 0,
        max_depth: int = 20
    ):
        """Recursively collect matching elements."""
        if current_depth >= max_depth or len(results) >= max_results:
            return
        
        try:
            element = self._create_element(node)
            
            if element and self._matches(element, name, role):
                results.append(element)
            
            for i in range(node.childCount):
                child = node.getChildAtIndex(i)
                if child:
                    self._collect_elements(
                        child, name, role, results, max_results,
                        current_depth + 1, max_depth
                    )
        except Exception as e:
            logger.debug(f"Collect error: {e}")
    
    def _find_focused_in_tree(self, node) -> Optional[AccessibilityElement]:
        """Find focused element in tree."""
        try:
            state_set = node.getState()
            
            if state_set.contains(self._atspi.STATE_FOCUSED):
                return self._create_element(node)
            
            for i in range(node.childCount):
                child = node.getChildAtIndex(i)
                if child:
                    result = self._find_focused_in_tree(child)
                    if result:
                        return result
            
            return None
        except:
            return None
    
    def _build_tree_dict(
        self,
        node,
        current_depth: int = 0,
        max_depth: int = 10
    ) -> Dict[str, Any]:
        """Build dictionary representation of tree."""
        if current_depth >= max_depth:
            return {}
        
        try:
            element = self._create_element(node)
            
            if not element:
                return {}
            
            tree = element.to_dict()
            tree["children"] = []
            
            for i in range(node.childCount):
                child = node.getChildAtIndex(i)
                if child:
                    child_tree = self._build_tree_dict(child, current_depth + 1, max_depth)
                    if child_tree:
                        tree["children"].append(child_tree)
            
            return tree
        except Exception as e:
            logger.debug(f"Build tree error: {e}")
            return {}
