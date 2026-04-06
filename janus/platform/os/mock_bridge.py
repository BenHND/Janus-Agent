"""
Mock System Bridge - Test implementation of SystemBridge.

TICKET-AUDIT-007: Create System Abstraction Layer (SystemBridge)

This module provides a mock implementation of SystemBridge for testing.
All operations succeed by default and return predictable values.

Usage:
    from janus.platform.os.mock_bridge import MockSystemBridge
    
    # In tests
    mock_bridge = MockSystemBridge()
    result = mock_bridge.open_app("TestApp")
    assert result.success
"""

import logging
from typing import Any, Dict, List, Optional

from janus.platform.os.system_bridge import (
    SystemBridge,
    SystemBridgeResult,
    SystemBridgeStatus,
    WindowInfo,
)

logger = logging.getLogger(__name__)


class MockSystemBridge(SystemBridge):
    """
    Mock implementation of SystemBridge for testing.
    
    All operations succeed by default and return predictable values.
    Can be configured to simulate failures or specific behaviors.
    
    Attributes:
        call_log: List of all method calls (name, args, kwargs)
        should_fail: If True, all operations return ERROR status
        running_apps: List of mock running applications
        active_window: Mock active window info
    """
    
    def __init__(
        self,
        should_fail: bool = False,
        running_apps: Optional[List[str]] = None,
    ):
        """
        Initialize mock bridge.
        
        Args:
            should_fail: If True, all operations return ERROR
            running_apps: List of mock running apps
        """
        self.call_log: List[Dict[str, Any]] = []
        self.should_fail = should_fail
        self.running_apps = running_apps or ["Finder", "Safari", "Terminal"]
        self.active_window = WindowInfo(
            title="Mock Window",
            app_name="MockApp",
            is_active=True,
        )
        self.clipboard_content = ""
        
        logger.info(f"MockSystemBridge initialized (should_fail={should_fail})")
    
    def _log_call(self, method_name: str, **kwargs):
        """Log a method call."""
        self.call_log.append({
            "method": method_name,
            "args": kwargs,
        })
    
    def _create_result(
        self,
        data: Optional[Dict[str, Any]] = None
    ) -> SystemBridgeResult:
        """Create a result based on should_fail setting."""
        if self.should_fail:
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error="Mock failure (should_fail=True)"
            )
        return SystemBridgeResult(
            status=SystemBridgeStatus.SUCCESS,
            data=data or {}
        )
    
    # ========== Platform Detection ==========
    
    def is_available(self) -> bool:
        """Mock is always available."""
        return True
    
    def get_platform_name(self) -> str:
        """Get platform name."""
        return "Mock"
    
    # ========== Application Management ==========
    
    def open_app(self, app_name: str, timeout: Optional[float] = None) -> SystemBridgeResult:
        """Mock open application."""
        self._log_call("open_app", app_name=app_name, timeout=timeout)
        
        # Add to running apps if not already there
        if app_name not in self.running_apps:
            self.running_apps.append(app_name)
        
        return self._create_result({"app_name": app_name})
    
    def close_app(self, app_name: str) -> SystemBridgeResult:
        """Mock close application."""
        self._log_call("close_app", app_name=app_name)
        
        # Remove from running apps if present
        if app_name in self.running_apps:
            self.running_apps.remove(app_name)
        
        return self._create_result({"app_name": app_name})
    
    def get_running_apps(self) -> SystemBridgeResult:
        """Mock get running apps."""
        self._log_call("get_running_apps")
        return self._create_result({"apps": self.running_apps.copy()})
    
    # ========== Window Management ==========
    
    def get_active_window(self) -> SystemBridgeResult:
        """Mock get active window."""
        self._log_call("get_active_window")
        return self._create_result({"window": self.active_window})
    
    def list_windows(self) -> SystemBridgeResult:
        """Mock list windows."""
        self._log_call("list_windows")
        
        # Create mock windows from running apps
        windows = []
        for app_name in self.running_apps:
            windows.append(WindowInfo(
                title=f"{app_name} Window",
                app_name=app_name,
                is_active=(app_name == self.active_window.app_name),
            ))
        
        return self._create_result({"windows": windows})
    
    def focus_window(self, app_name: str, timeout: Optional[float] = None) -> SystemBridgeResult:
        """Mock focus window."""
        self._log_call("focus_window", app_name=app_name, timeout=timeout)
        
        # Update active window
        self.active_window = WindowInfo(
            title=f"{app_name} Window",
            app_name=app_name,
            is_active=True,
        )
        
        return self._create_result({"app_name": app_name})
    
    # ========== UI Interactions ==========
    
    def click(self, x: int, y: int, button: str = "left") -> SystemBridgeResult:
        """Mock click."""
        self._log_call("click", x=x, y=y, button=button)
        return self._create_result({"x": x, "y": y, "button": button})
    
    def type_text(self, text: str) -> SystemBridgeResult:
        """Mock type text."""
        self._log_call("type_text", text=text)
        return self._create_result({"text_length": len(text)})
    
    def press_key(self, key: str, modifiers: Optional[List[str]] = None) -> SystemBridgeResult:
        """Mock press key."""
        self._log_call("press_key", key=key, modifiers=modifiers)
        return self._create_result({"key": key, "modifiers": modifiers})
    
    def send_keys(self, keys: str, modifiers: Optional[List[str]] = None) -> SystemBridgeResult:
        """Mock send keys."""
        self._log_call("send_keys", keys=keys, modifiers=modifiers)
        return self._create_result({"keys": keys, "modifiers": modifiers})
    
    # ========== Clipboard Operations ==========
    
    def get_clipboard(self) -> SystemBridgeResult:
        """Mock get clipboard."""
        self._log_call("get_clipboard")
        return self._create_result({"text": self.clipboard_content})
    
    def set_clipboard(self, text: str) -> SystemBridgeResult:
        """Mock set clipboard."""
        self._log_call("set_clipboard", text=text)
        self.clipboard_content = text
        return self._create_result({"text_length": len(text)})
    
    # ========== System Operations ==========
    
    def show_notification(
        self,
        message: str,
        title: Optional[str] = None
    ) -> SystemBridgeResult:
        """Mock show notification."""
        self._log_call("show_notification", message=message, title=title)
        return self._create_result({"message": message, "title": title})
    
    def run_script(
        self,
        script: str,
        timeout: Optional[float] = None
    ) -> SystemBridgeResult:
        """Mock run script."""
        self._log_call("run_script", script=script, timeout=timeout)
        return self._create_result({
            "stdout": "Mock script output",
            "stderr": "",
        })
    
    # ========== Test Helpers ==========
    
    def reset_call_log(self):
        """Reset the call log."""
        self.call_log = []
    
    def get_call_count(self, method_name: str) -> int:
        """Get number of times a method was called."""
        return sum(1 for call in self.call_log if call["method"] == method_name)
    
    def was_called(self, method_name: str) -> bool:
        """Check if a method was called."""
        return any(call["method"] == method_name for call in self.call_log)
    
    def get_last_call(self, method_name: str) -> Optional[Dict[str, Any]]:
        """Get the last call to a specific method."""
        for call in reversed(self.call_log):
            if call["method"] == method_name:
                return call
        return None
