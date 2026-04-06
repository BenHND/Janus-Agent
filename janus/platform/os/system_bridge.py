"""
System Bridge - Unified abstraction layer for system operations.

TICKET-AUDIT-007: Create System Abstraction Layer (SystemBridge)

This module provides a unified, platform-agnostic API for system operations,
abstracting away differences between macOS, Windows, and Linux.

Architecture:
    - SystemBridge: Abstract base class defining the unified API
    - Platform-specific implementations: MacOSBridge, WindowsBridge, LinuxBridge
    - Factory method: get_system_bridge() for automatic platform detection
    - MockSystemBridge: Test implementation for mocking

Key Features:
    - Application management (open, close, list running apps)
    - Window management (list, focus, get active window)
    - UI interactions (click, type, press keys)
    - Clipboard operations (get, set)
    - System notifications
    - Platform detection and availability checks

Usage:
    from janus.platform.os import get_system_bridge
    
    bridge = get_system_bridge()
    bridge.open_app("Safari")
    bridge.type_text("Hello, World!")
    clipboard_content = bridge.get_clipboard()
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SystemBridgeStatus(Enum):
    """Status codes for SystemBridge operations."""
    SUCCESS = "success"
    ERROR = "error"
    NOT_AVAILABLE = "not_available"
    TIMEOUT = "timeout"


@dataclass
class WindowInfo:
    """
    Information about a window.
    
    Attributes:
        title: Window title/name
        app_name: Name of the application owning the window
        window_id: Platform-specific window identifier
        is_active: Whether this is the currently active window
        bounds: Optional dict with x, y, width, height
    """
    title: str
    app_name: str
    window_id: Optional[str] = None
    is_active: bool = False
    bounds: Optional[Dict[str, int]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "title": self.title,
            "app_name": self.app_name,
            "window_id": self.window_id,
            "is_active": self.is_active,
            "bounds": self.bounds,
        }


class SystemBridgeResult:
    """
    Result container for SystemBridge operations.
    
    Provides consistent way to return results from system operations,
    with success/failure status and optional data/error information.
    
    Attributes:
        status: Operation status (success, error, etc.)
        data: Optional data returned by the operation
        error: Optional error message if operation failed
    """
    
    def __init__(
        self,
        status: SystemBridgeStatus,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        self.status = status
        self.data = data or {}
        self.error = error
    
    @property
    def success(self) -> bool:
        """Check if operation was successful."""
        return self.status == SystemBridgeStatus.SUCCESS
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        result: Dict[str, Any] = {
            "status": self.status.value,
        }
        if self.data:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        return result
    
    def __repr__(self) -> str:
        return f"SystemBridgeResult(status={self.status.value}, data={self.data}, error={self.error})"


class SystemBridge(ABC):
    """
    Abstract base class for system-level interactions.
    
    This interface defines a unified, platform-agnostic API for system operations.
    Platform-specific implementations (MacOSBridge, WindowsBridge, LinuxBridge)
    provide the actual functionality.
    
    All methods return SystemBridgeResult for consistent error handling.
    
    Categories:
        - Platform detection: is_available, get_platform_name
        - Application management: open_app, close_app, get_running_apps
        - Window management: get_active_window, list_windows, focus_window
        - UI interactions: click, type_text, press_key, send_keys
        - Clipboard: get_clipboard, set_clipboard
        - System: show_notification, run_script
    """
    
    # ========== Platform Detection ==========
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this bridge is available on the current platform.
        
        Returns:
            True if this bridge can be used, False otherwise
            
        Example:
            bridge = get_system_bridge()
            if bridge.is_available():
                bridge.open_app("Safari")
        """
        pass
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """
        Get the platform name this bridge supports.
        
        Returns:
            Platform name (e.g., "macOS", "Windows", "Linux")
        """
        pass
    
    # ========== Application Management ==========
    
    @abstractmethod
    def open_app(self, app_name: str, timeout: Optional[float] = None) -> SystemBridgeResult:
        """
        Open/launch an application.
        
        Args:
            app_name: Name of the application to open (e.g., "Safari", "Chrome")
            timeout: Optional timeout in seconds for the operation
            
        Returns:
            SystemBridgeResult with success status and app info
            
        Example:
            result = bridge.open_app("Safari")
            if result.success:
                print("Safari opened successfully")
        """
        pass
    
    @abstractmethod
    def close_app(self, app_name: str) -> SystemBridgeResult:
        """
        Close/quit an application.
        
        Args:
            app_name: Name of the application to close
            
        Returns:
            SystemBridgeResult with success status
            
        Example:
            result = bridge.close_app("TextEdit")
        """
        pass
    
    @abstractmethod
    def get_running_apps(self) -> SystemBridgeResult:
        """
        Get list of currently running applications.
        
        Returns:
            SystemBridgeResult with data["apps"] containing list of app names
            
        Example:
            result = bridge.get_running_apps()
            if result.success:
                print(f"Running apps: {result.data['apps']}")
        """
        pass
    
    # ========== Window Management ==========
    
    @abstractmethod
    def get_active_window(self) -> SystemBridgeResult:
        """
        Get information about the currently active window.
        
        Returns:
            SystemBridgeResult with data["window"] containing WindowInfo
            
        Example:
            result = bridge.get_active_window()
            if result.success:
                window = result.data["window"]
                print(f"Active: {window.app_name} - {window.title}")
        """
        pass
    
    @abstractmethod
    def list_windows(self) -> SystemBridgeResult:
        """
        Get list of all windows.
        
        Returns:
            SystemBridgeResult with data["windows"] containing list of WindowInfo
            
        Example:
            result = bridge.list_windows()
            if result.success:
                for window in result.data["windows"]:
                    print(f"{window.app_name}: {window.title}")
        """
        pass
    
    @abstractmethod
    def focus_window(self, app_name: str, timeout: Optional[float] = None) -> SystemBridgeResult:
        """
        Bring a window/application to the foreground.
        
        Args:
            app_name: Name of the application to focus
            timeout: Optional timeout in seconds
            
        Returns:
            SystemBridgeResult with success status
            
        Example:
            result = bridge.focus_window("Safari")
        """
        pass
    
    # ========== UI Interactions ==========
    
    @abstractmethod
    def click(self, x: int, y: int, button: str = "left") -> SystemBridgeResult:
        """
        Perform a mouse click at coordinates.
        
        Args:
            x: X coordinate (screen position)
            y: Y coordinate (screen position)
            button: Mouse button ("left", "right", "middle")
            
        Returns:
            SystemBridgeResult with success status
            
        Example:
            result = bridge.click(100, 200)
        """
        pass
    
    @abstractmethod
    def type_text(self, text: str) -> SystemBridgeResult:
        """
        Type text as if from the keyboard.
        
        Args:
            text: Text to type
            
        Returns:
            SystemBridgeResult with success status
            
        Example:
            result = bridge.type_text("Hello, World!")
        """
        pass
    
    @abstractmethod
    def press_key(self, key: str, modifiers: Optional[List[str]] = None) -> SystemBridgeResult:
        """
        Press a key or key combination.
        
        Args:
            key: Key to press (e.g., "a", "return", "escape")
            modifiers: Optional list of modifier keys (e.g., ["command", "shift"])
            
        Returns:
            SystemBridgeResult with success status
            
        Example:
            # Press Cmd+C (copy)
            result = bridge.press_key("c", modifiers=["command"])
            
            # Press Enter
            result = bridge.press_key("return")
        """
        pass
    
    @abstractmethod
    def send_keys(self, keys: str, modifiers: Optional[List[str]] = None) -> SystemBridgeResult:
        """
        Send keyboard input to the active window.
        
        This is an alias for press_key().
        
        Args:
            keys: Keys to send
            modifiers: Optional list of modifier keys
            
        Returns:
            SystemBridgeResult with success status
        """
        pass
    
    # ========== Clipboard Operations ==========
    
    @abstractmethod
    def get_clipboard(self) -> SystemBridgeResult:
        """
        Get text from clipboard.
        
        Returns:
            SystemBridgeResult with data["text"] containing clipboard text
            
        Example:
            result = bridge.get_clipboard()
            if result.success:
                print(f"Clipboard: {result.data['text']}")
        """
        pass
    
    @abstractmethod
    def set_clipboard(self, text: str) -> SystemBridgeResult:
        """
        Set clipboard text.
        
        Args:
            text: Text to write to clipboard
            
        Returns:
            SystemBridgeResult with success status
            
        Example:
            result = bridge.set_clipboard("Hello, World!")
        """
        pass
    
    # ========== System Operations ==========
    
    @abstractmethod
    def show_notification(
        self,
        message: str,
        title: Optional[str] = None
    ) -> SystemBridgeResult:
        """
        Display a system notification.
        
        Args:
            message: Notification message
            title: Optional notification title
            
        Returns:
            SystemBridgeResult with success status
            
        Example:
            result = bridge.show_notification(
                "Task completed",
                title="Janus"
            )
        """
        pass
    
    @abstractmethod
    def run_script(
        self,
        script: str,
        timeout: Optional[float] = None
    ) -> SystemBridgeResult:
        """
        Execute a platform-specific script.
        
        This is a lower-level method for custom automation scripts.
        On macOS, this runs AppleScript. On Windows, PowerShell.
        On Linux, bash script.
        
        Args:
            script: Script content to execute
            timeout: Optional timeout in seconds
            
        Returns:
            SystemBridgeResult with data["stdout"] and optional data["stderr"]
            
        Example:
            # macOS AppleScript
            result = bridge.run_script(
                'tell application "Finder" to activate'
            )
        """
        pass
    
    # ========== Accessibility API ==========
    
    def get_accessibility_backend(self):
        """
        Get the accessibility backend for this platform.
        
        Returns the platform-specific accessibility implementation
        (WindowsAccessibility or MacOSAccessibility) or None if not available.
        
        Returns:
            AccessibilityBackend instance or None
            
        Example:
            backend = bridge.get_accessibility_backend()
            if backend and backend.is_available():
                element = backend.find_element(name="OK", role=AccessibilityRole.BUTTON)
        """
        # Default implementation returns None (no accessibility)
        # Platform-specific bridges can override to provide accessibility
        return None
    
    def find_ui_element(
        self,
        name: Optional[str] = None,
        role: Optional[str] = None,
        timeout: float = 5.0,
    ) -> SystemBridgeResult:
        """
        Find a UI element using accessibility API with automatic fallback.
        
        Tries accessibility API first for fast, reliable element finding.
        Falls back to vision-based approach if accessibility is unavailable.
        
        Args:
            name: Element name/label to search for
            role: Element role (button, text_field, etc.)
            timeout: Maximum time to wait for element
            
        Returns:
            SystemBridgeResult with data["element"] containing element info
            
        Example:
            result = bridge.find_ui_element(name="OK", role="button")
            if result.success:
                element = result.data["element"]
        """
        # Try accessibility first
        backend = self.get_accessibility_backend()
        if backend and backend.is_available():
            try:
                from janus.platform.accessibility import AccessibilityRole
                
                # Map string role to AccessibilityRole enum
                role_enum = None
                if role:
                    role_map = {r.value: r for r in AccessibilityRole}
                    role_enum = role_map.get(role)
                
                element = backend.find_element(
                    name=name,
                    role=role_enum,
                    timeout=timeout
                )
                
                if element:
                    return SystemBridgeResult(
                        status=SystemBridgeStatus.SUCCESS,
                        data={"element": element.to_dict(), "method": "accessibility"}
                    )
            except Exception as e:
                logger.debug(f"Accessibility find failed: {e}")
        
        # Fallback to vision-based approach
        return SystemBridgeResult(
            status=SystemBridgeStatus.NOT_AVAILABLE,
            error="Element not found via accessibility, vision fallback not implemented"
        )
    
    def click_ui_element(
        self,
        name: Optional[str] = None,
        role: Optional[str] = None,
        timeout: float = 5.0,
    ) -> SystemBridgeResult:
        """
        Find and click a UI element using accessibility API.
        
        Combines element finding and clicking in a single operation.
        Uses accessibility API for fast, reliable interaction.
        
        Args:
            name: Element name/label
            role: Element role (button, etc.)
            timeout: Maximum time to wait for element
            
        Returns:
            SystemBridgeResult with success status
            
        Example:
            result = bridge.click_ui_element(name="Submit", role="button")
            if result.success:
                print("Button clicked successfully")
        """
        # Find element first
        find_result = self.find_ui_element(name=name, role=role, timeout=timeout)
        
        if not find_result.success:
            return find_result
        
        # Click using accessibility
        backend = self.get_accessibility_backend()
        if backend and backend.is_available():
            try:
                from janus.platform.accessibility import AccessibilityElement
                
                # Reconstruct element from dict (would need native_element)
                # For now, find again and click
                from janus.platform.accessibility import AccessibilityRole
                
                role_enum = None
                if role:
                    role_map = {r.value: r for r in AccessibilityRole}
                    role_enum = role_map.get(role)
                
                element = backend.find_element(name=name, role=role_enum, timeout=1.0)
                if element:
                    click_result = backend.click_element(element)
                    if click_result.success:
                        return SystemBridgeResult(
                            status=SystemBridgeStatus.SUCCESS,
                            data={"method": "accessibility"}
                        )
                    else:
                        return SystemBridgeResult(
                            status=SystemBridgeStatus.ERROR,
                            error=f"Click failed: {click_result.error}"
                        )
            except Exception as e:
                logger.error(f"Accessibility click failed: {e}")
        
        return SystemBridgeResult(
            status=SystemBridgeStatus.ERROR,
            error="Could not click element"
        )
