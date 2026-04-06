"""
Base Accessibility API - Abstract interface for UI accessibility operations.

Defines the unified API for interacting with UI elements across platforms,
abstracting away platform-specific differences between Windows UIAutomation
and macOS AXUIElement.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AccessibilityRole(Enum):
    """
    Unified UI element roles across platforms.
    
    Maps to UIAutomation ControlType (Windows) and AXRole (macOS).
    """
    # Common interactive elements
    BUTTON = "button"
    CHECKBOX = "checkbox"
    RADIO_BUTTON = "radio_button"
    TEXT_FIELD = "text_field"
    TEXT_AREA = "text_area"
    COMBO_BOX = "combo_box"
    LIST = "list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    CELL = "cell"
    SLIDER = "slider"
    MENU = "menu"
    MENU_ITEM = "menu_item"
    MENU_BAR = "menu_bar"
    TAB = "tab"
    TAB_GROUP = "tab_group"
    
    # Container elements
    WINDOW = "window"
    DIALOG = "dialog"
    GROUP = "group"
    PANE = "pane"
    SCROLL_AREA = "scroll_area"
    TOOLBAR = "toolbar"
    
    # Content elements
    STATIC_TEXT = "static_text"
    IMAGE = "image"
    LINK = "link"
    HEADING = "heading"
    
    # Special elements
    APPLICATION = "application"
    UNKNOWN = "unknown"


class AccessibilityState(Enum):
    """UI element states."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    FOCUSED = "focused"
    VISIBLE = "visible"
    HIDDEN = "hidden"
    SELECTED = "selected"
    CHECKED = "checked"
    UNCHECKED = "unchecked"
    EXPANDED = "expanded"
    COLLAPSED = "collapsed"


@dataclass
class AccessibilityElement:
    """
    Platform-agnostic representation of a UI element.
    
    This dataclass unifies the representation of UI elements across platforms,
    providing a consistent interface for both Windows UIAutomation elements
    and macOS AXUIElement objects.
    
    Attributes:
        native_element: Platform-specific element object (UIAutomationElement or AXUIElementRef)
        role: Unified element role (button, text_field, etc.)
        name: Element name/label (from Name or AXTitle)
        value: Element value (from Value or AXValue)
        description: Element description (from HelpText or AXDescription)
        bounds: Element screen coordinates (x, y, width, height)
        states: Set of current element states
        attributes: Additional platform-specific attributes
        parent: Reference to parent element
        children: List of child elements
    """
    native_element: Any  # Platform-specific element object
    role: AccessibilityRole = AccessibilityRole.UNKNOWN
    name: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    bounds: Optional[Dict[str, int]] = None  # {x, y, width, height}
    states: set = field(default_factory=set)  # Set of AccessibilityState
    attributes: Dict[str, Any] = field(default_factory=dict)  # Platform-specific attrs
    parent: Optional['AccessibilityElement'] = None
    children: List['AccessibilityElement'] = field(default_factory=list)
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"AccessibilityElement(role={self.role.value}, name={self.name!r}, "
            f"value={self.value!r}, bounds={self.bounds})"
        )
    
    def is_enabled(self) -> bool:
        """Check if element is enabled."""
        return AccessibilityState.ENABLED in self.states
    
    def is_visible(self) -> bool:
        """Check if element is visible."""
        return AccessibilityState.VISIBLE in self.states
    
    def is_focused(self) -> bool:
        """Check if element is focused."""
        return AccessibilityState.FOCUSED in self.states
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "role": self.role.value,
            "name": self.name,
            "value": self.value,
            "description": self.description,
            "bounds": self.bounds,
            "states": [state.value for state in self.states],
            "attributes": self.attributes,
        }


@dataclass
class AccessibilityResult:
    """
    Result container for accessibility operations.
    
    Provides consistent result format with success/failure status
    and optional data/error information.
    
    Attributes:
        success: Whether the operation succeeded
        data: Optional data returned by the operation
        error: Optional error message if operation failed
    """
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        result: Dict[str, Any] = {"success": self.success}
        if self.data:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        return result
    
    def __repr__(self) -> str:
        return f"AccessibilityResult(success={self.success}, data={self.data}, error={self.error})"


class AccessibilityBackend(ABC):
    """
    Abstract base class for accessibility backends.
    
    This interface defines the unified, platform-agnostic API for UI accessibility
    operations. Platform-specific implementations (WindowsAccessibility, MacOSAccessibility)
    provide the actual functionality using UIAutomation or AXUIElement.
    
    Categories:
        - Platform detection: is_available, get_platform_name
        - Element finding: find_element, find_elements, get_focused_element
        - Element interaction: click_element, focus_element, set_value
        - State retrieval: get_element_state, get_element_bounds
        - Tree inspection: get_ui_tree, get_children, get_parent
        - Application context: get_active_app, get_app_windows
    """
    
    # ========== Platform Detection ==========
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this backend is available on the current platform.
        
        Returns:
            True if accessibility API is available and can be used
            
        Example:
            backend = get_accessibility_backend()
            if backend.is_available():
                element = backend.find_element(name="OK")
        """
        pass
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """
        Get the platform name this backend supports.
        
        Returns:
            Platform name (e.g., "Windows", "macOS")
        """
        pass
    
    # ========== Element Finding ==========
    
    @abstractmethod
    def find_element(
        self,
        name: Optional[str] = None,
        role: Optional[AccessibilityRole] = None,
        attributes: Optional[Dict[str, Any]] = None,
        timeout: float = 5.0,
    ) -> Optional[AccessibilityElement]:
        """
        Find a single UI element matching the criteria.
        
        Args:
            name: Element name/label to search for (partial match)
            role: Element role to filter by
            attributes: Additional attributes to match
            timeout: Maximum time to wait for element (seconds)
            
        Returns:
            AccessibilityElement if found, None otherwise
            
        Example:
            # Find OK button
            button = backend.find_element(name="OK", role=AccessibilityRole.BUTTON)
            
            # Find text field with specific automation ID
            field = backend.find_element(
                role=AccessibilityRole.TEXT_FIELD,
                attributes={"automation_id": "username"}
            )
        """
        pass
    
    @abstractmethod
    def find_elements(
        self,
        name: Optional[str] = None,
        role: Optional[AccessibilityRole] = None,
        attributes: Optional[Dict[str, Any]] = None,
        max_results: int = 100,
    ) -> List[AccessibilityElement]:
        """
        Find all UI elements matching the criteria.
        
        Args:
            name: Element name/label to search for (partial match)
            role: Element role to filter by
            attributes: Additional attributes to match
            max_results: Maximum number of results to return
            
        Returns:
            List of matching AccessibilityElement objects
            
        Example:
            # Find all buttons
            buttons = backend.find_elements(role=AccessibilityRole.BUTTON)
            
            # Find all text fields in a dialog
            fields = backend.find_elements(role=AccessibilityRole.TEXT_FIELD)
        """
        pass
    
    @abstractmethod
    def get_focused_element(self) -> Optional[AccessibilityElement]:
        """
        Get the currently focused UI element.
        
        Returns:
            AccessibilityElement for focused element, None if no element is focused
            
        Example:
            focused = backend.get_focused_element()
            if focused:
                print(f"Focused: {focused.name} ({focused.role.value})")
        """
        pass
    
    # ========== Element Interaction ==========
    
    @abstractmethod
    def click_element(self, element: AccessibilityElement) -> AccessibilityResult:
        """
        Click/activate a UI element.
        
        Args:
            element: Element to click
            
        Returns:
            AccessibilityResult with success status
            
        Example:
            button = backend.find_element(name="Submit", role=AccessibilityRole.BUTTON)
            if button:
                result = backend.click_element(button)
                if result.success:
                    print("Button clicked successfully")
        """
        pass
    
    @abstractmethod
    def focus_element(self, element: AccessibilityElement) -> AccessibilityResult:
        """
        Set focus to a UI element.
        
        Args:
            element: Element to focus
            
        Returns:
            AccessibilityResult with success status
            
        Example:
            field = backend.find_element(role=AccessibilityRole.TEXT_FIELD)
            if field:
                backend.focus_element(field)
        """
        pass
    
    @abstractmethod
    def set_value(
        self,
        element: AccessibilityElement,
        value: str
    ) -> AccessibilityResult:
        """
        Set the value of a UI element (text field, combo box, etc.).
        
        Args:
            element: Element to set value for
            value: Value to set
            
        Returns:
            AccessibilityResult with success status
            
        Example:
            field = backend.find_element(role=AccessibilityRole.TEXT_FIELD)
            if field:
                result = backend.set_value(field, "Hello, World!")
        """
        pass
    
    # ========== State Retrieval ==========
    
    @abstractmethod
    def get_element_state(
        self,
        element: AccessibilityElement
    ) -> set:
        """
        Get current states of a UI element.
        
        Args:
            element: Element to get states for
            
        Returns:
            Set of AccessibilityState values
            
        Example:
            states = backend.get_element_state(element)
            if AccessibilityState.ENABLED in states:
                print("Element is enabled")
        """
        pass
    
    @abstractmethod
    def get_element_bounds(
        self,
        element: AccessibilityElement
    ) -> Optional[Dict[str, int]]:
        """
        Get screen coordinates of a UI element.
        
        Args:
            element: Element to get bounds for
            
        Returns:
            Dictionary with x, y, width, height keys
            
        Example:
            bounds = backend.get_element_bounds(element)
            if bounds:
                print(f"Element at ({bounds['x']}, {bounds['y']})")
        """
        pass
    
    # ========== Tree Inspection ==========
    
    @abstractmethod
    def get_ui_tree(
        self,
        root: Optional[AccessibilityElement] = None,
        max_depth: int = 10,
    ) -> Dict[str, Any]:
        """
        Get UI element tree as a hierarchical dictionary.
        
        Args:
            root: Root element to start from (None = desktop/root)
            max_depth: Maximum tree depth to traverse
            
        Returns:
            Dictionary representing the UI tree
            
        Example:
            tree = backend.get_ui_tree()
            # Returns nested dict with element info and children
        """
        pass
    
    @abstractmethod
    def get_children(
        self,
        element: AccessibilityElement
    ) -> List[AccessibilityElement]:
        """
        Get child elements of a UI element.
        
        Args:
            element: Parent element
            
        Returns:
            List of child AccessibilityElement objects
            
        Example:
            dialog = backend.find_element(role=AccessibilityRole.DIALOG)
            if dialog:
                children = backend.get_children(dialog)
                for child in children:
                    print(f"  - {child.name} ({child.role.value})")
        """
        pass
    
    @abstractmethod
    def get_parent(
        self,
        element: AccessibilityElement
    ) -> Optional[AccessibilityElement]:
        """
        Get parent element of a UI element.
        
        Args:
            element: Child element
            
        Returns:
            Parent AccessibilityElement, or None if no parent
            
        Example:
            parent = backend.get_parent(element)
            if parent:
                print(f"Parent: {parent.name}")
        """
        pass
    
    # ========== Application Context ==========
    
    @abstractmethod
    def get_active_app(self) -> Optional[AccessibilityElement]:
        """
        Get the currently active application.
        
        Returns:
            AccessibilityElement for active app, or None
            
        Example:
            app = backend.get_active_app()
            if app:
                print(f"Active app: {app.name}")
        """
        pass
    
    @abstractmethod
    def get_app_windows(
        self,
        app_name: Optional[str] = None
    ) -> List[AccessibilityElement]:
        """
        Get windows for an application.
        
        Args:
            app_name: Application name (None = all windows)
            
        Returns:
            List of window AccessibilityElement objects
            
        Example:
            windows = backend.get_app_windows("Safari")
            for window in windows:
                print(f"Window: {window.name}")
        """
        pass
