"""
macOS Bridge - SystemBridge implementation for macOS.

TICKET-AUDIT-007: Create System Abstraction Layer (SystemBridge)
TICKET-REVIEW-002: Review and decompose macos_bridge.py

This module implements SystemBridge for macOS using AppleScript and
system APIs for reliable automation with timeout, retry, and error handling.

Refactored Structure:
    - MacOSBridge: Facade/coordinator that delegates to specialized managers
    - MacOSAppManager: Application management operations
    - MacOSWindowManager: Window management operations
    - MacOSKeyboardManager: Keyboard input operations
    - MacOSClipboardManager: Clipboard operations

Features:
    - Application management via AppleScript
    - Window management via System Events
    - UI interactions via System Events
    - Clipboard operations via pbcopy/pbpaste
    - System notifications via AppleScript

Usage:
    from janus.platform.os.macos_bridge import MacOSBridge
    
    bridge = MacOSBridge()
    if bridge.is_available():
        bridge.open_app("Safari")
        bridge.type_text("Hello, World!")
"""

import logging
import platform
from typing import List, Optional

from janus.constants import ActionStatus
from janus.platform.os.system_bridge import (
    SystemBridge,
    SystemBridgeResult,
    SystemBridgeStatus,
    WindowInfo,
)

logger = logging.getLogger(__name__)


class MacOSBridge(SystemBridge):
    """
    macOS implementation of SystemBridge using AppleScript and System Events.
    
    Refactored as a Facade/Coordinator pattern that delegates operations to
    specialized manager classes for better maintainability and separation of concerns.
    
    Delegates to:
        - MacOSAppManager: Application management
        - MacOSWindowManager: Window management
        - MacOSKeyboardManager: Keyboard operations
        - MacOSClipboardManager: Clipboard operations
        - MacOSAccessibility: Accessibility API (AXUIElement)
    
    Features:
        - Application launch/quit via AppleScript
        - Window focus/activation via AppleScript
        - Keyboard input via System Events
        - Mouse clicks via System Events
        - Clipboard via pbcopy/pbpaste
        - Notifications via AppleScript
        - UI element finding via Accessibility API
    """
    
    def __init__(
        self,
        default_timeout: float = 10.0,
        max_retries: int = 2,
        retry_delay: float = 0.5,
    ):
        """
        Initialize macOS bridge and specialized managers.
        
        Args:
            default_timeout: Default timeout for operations (seconds)
            max_retries: Maximum number of retries on failure
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._applescript_executor = None
        
        # Lazy-loaded specialized managers
        self._app_manager = None
        self._window_manager = None
        self._keyboard_manager = None
        self._clipboard_manager = None
        self._accessibility_backend = None
        
        # Initialize accessibility if on macOS
        if platform.system() == "Darwin":
            self._init_accessibility()
        
        logger.info(
            f"MacOSBridge initialized (timeout={default_timeout}s, "
            f"retries={max_retries}, "
            f"accessibility={self._accessibility_backend is not None})"
        )
    
    def _init_accessibility(self):
        """Initialize accessibility backend."""
        try:
            from janus.platform.accessibility.macos_accessibility import MacOSAccessibility
            self._accessibility_backend = MacOSAccessibility()
            if self._accessibility_backend.is_available():
                logger.debug("macOS accessibility backend initialized")
        except Exception as e:
            logger.debug(f"Failed to initialize accessibility backend: {e}")
    
    @property
    def applescript_executor(self):
        """Lazy-load AppleScript executor."""
        if self._applescript_executor is None:
            from janus.platform.os.macos.applescript_executor import AppleScriptExecutor
            self._applescript_executor = AppleScriptExecutor(
                default_timeout=self.default_timeout,
                max_retries=self.max_retries,
                retry_delay=self.retry_delay,
            )
        return self._applescript_executor
    
    @property
    def app_manager(self):
        """Lazy-load application manager."""
        if self._app_manager is None:
            from janus.platform.os.macos.app_manager import MacOSAppManager
            self._app_manager = MacOSAppManager(
                self.applescript_executor,
                self.is_available
            )
        return self._app_manager
    
    @property
    def window_manager(self):
        """Lazy-load window manager."""
        if self._window_manager is None:
            from janus.platform.os.macos.window_manager import MacOSWindowManager
            self._window_manager = MacOSWindowManager(
                self.applescript_executor,
                self.is_available
            )
        return self._window_manager
    
    @property
    def keyboard_manager(self):
        """Lazy-load keyboard manager."""
        if self._keyboard_manager is None:
            from janus.platform.os.macos.keyboard_manager import MacOSKeyboardManager
            self._keyboard_manager = MacOSKeyboardManager(
                self.applescript_executor,
                self.is_available
            )
        return self._keyboard_manager
    
    @property
    def clipboard_manager(self):
        """Lazy-load clipboard manager."""
        if self._clipboard_manager is None:
            from janus.platform.os.macos.clipboard_manager import MacOSClipboardManager
            self._clipboard_manager = MacOSClipboardManager(self.is_available)
        return self._clipboard_manager
    
    def _is_success(self, result: dict) -> bool:
        """Check if AppleScript executor result indicates success."""
        return result.get("status") == ActionStatus.SUCCESS.value
    
    # ========== Platform Detection ==========
    
    def is_available(self) -> bool:
        """Check if running on macOS."""
        return platform.system() == "Darwin"
    
    def get_platform_name(self) -> str:
        """Get platform name."""
        return "macOS"
    
    # ========== Application Management ==========
    
    def open_app(self, app_name: str, timeout: Optional[float] = None) -> SystemBridgeResult:
        """
        Open/launch an application using AppleScript.
        
        Delegates to MacOSAppManager.
        
        Args:
            app_name: Name of the application to open
            timeout: Optional timeout override
            
        Returns:
            SystemBridgeResult with success status
        """
        return self.app_manager.open_app(app_name, timeout)
    
    def close_app(self, app_name: str) -> SystemBridgeResult:
        """
        Close/quit an application using AppleScript.
        
        Delegates to MacOSAppManager.
        
        Args:
            app_name: Name of the application to close
            
        Returns:
            SystemBridgeResult with success status
        """
        return self.app_manager.close_app(app_name)
    
    def get_running_apps(self) -> SystemBridgeResult:
        """
        Get list of currently running applications.
        
        Delegates to MacOSAppManager.
        
        Returns:
            SystemBridgeResult with data["apps"] containing list of app names
        """
        return self.app_manager.get_running_apps()
    
    # ========== Window Management ==========
    
    def get_active_window(self) -> SystemBridgeResult:
        """
        Get information about the currently active window.
        
        Delegates to MacOSWindowManager.
        
        Returns:
            SystemBridgeResult with data["window"] containing WindowInfo
        """
        return self.window_manager.get_active_window()
    
    def list_windows(self) -> SystemBridgeResult:
        """
        Get list of all windows.
        
        Delegates to MacOSWindowManager.
        
        Returns:
            SystemBridgeResult with data["windows"] containing list of WindowInfo
        """
        return self.window_manager.list_windows()
    
    def focus_window(self, app_name: str, timeout: Optional[float] = None) -> SystemBridgeResult:
        """
        Bring a window/application to the foreground.
        
        This is an alias for open_app() on macOS.
        
        Args:
            app_name: Name of the application to focus
            timeout: Optional timeout override
            
        Returns:
            SystemBridgeResult with success status
        """
        return self.open_app(app_name, timeout)
    
    # ========== UI Interactions ==========
    
    def click(self, x: int, y: int, button: str = "left") -> SystemBridgeResult:
        """
        Perform a mouse click at coordinates using System Events.
        
        Args:
            x: X coordinate
            y: Y coordinate
            button: Mouse button (left, right, middle)
            
        Returns:
            SystemBridgeResult with success status
        """
        if not self.is_available():
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="MacOSBridge is only available on macOS"
            )
        
        try:
            # AppleScript for clicking at position
            if button == "right":
                script = f"""
                tell application "System Events"
                    click at {{{x}, {y}}} using control down
                end tell
                """
            else:
                script = f"""
                tell application "System Events"
                    click at {{{x}, {y}}}
                end tell
                """
            
            result = self.applescript_executor.execute(
                script,
                timeout=5.0,
                retries=0,
            )
            
            if self._is_success(result):
                logger.debug(f"Clicked at ({x}, {y}) with {button} button")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"x": x, "y": y, "button": button}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.ERROR,
                    error=f"Failed to click: {result.get('error')}"
                )
                
        except Exception as e:
            logger.error(f"click error: {e}", exc_info=True)
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Exception clicking: {str(e)}"
            )
    
    def type_text(self, text: str) -> SystemBridgeResult:
        """
        Type text using System Events keystroke.
        
        Delegates to MacOSKeyboardManager.
        
        Args:
            text: Text to type
            
        Returns:
            SystemBridgeResult with success status
        """
        return self.keyboard_manager.type_text(text)
    
    def press_key(self, key: str, modifiers: Optional[List[str]] = None) -> SystemBridgeResult:
        """
        Press a key or key combination.
        
        Delegates to MacOSKeyboardManager.
        
        Args:
            key: Key to press (character or special key name)
            modifiers: Optional list of modifiers (command, control, option, shift)
            
        Returns:
            SystemBridgeResult with success status
        """
        return self.keyboard_manager.press_key(key, modifiers)
    
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
        return self.keyboard_manager.send_keys(keys, modifiers)
    
    # ========== Clipboard Operations ==========
    
    def get_clipboard(self) -> SystemBridgeResult:
        """
        Get text from clipboard using pbpaste.
        
        Delegates to MacOSClipboardManager.
        
        Returns:
            SystemBridgeResult with data["text"] containing clipboard text
        """
        return self.clipboard_manager.get_clipboard()
    
    def set_clipboard(self, text: str) -> SystemBridgeResult:
        """
        Set clipboard text using pbcopy.
        
        Delegates to MacOSClipboardManager.
        
        Args:
            text: Text to write to clipboard
            
        Returns:
            SystemBridgeResult with success status
        """
        return self.clipboard_manager.set_clipboard(text)
    
    # ========== System Operations ==========
    
    def show_notification(
        self,
        message: str,
        title: Optional[str] = None
    ) -> SystemBridgeResult:
        """
        Display a macOS notification using AppleScript.
        
        Args:
            message: Notification message
            title: Optional notification title
            
        Returns:
            SystemBridgeResult with success status
        """
        if not self.is_available():
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="MacOSBridge is only available on macOS"
            )
        
        try:
            # Escape message and title for AppleScript
            escaped_message = message.replace('"', '\\"')
            
            if title:
                escaped_title = title.replace('"', '\\"')
                script = f'display notification "{escaped_message}" with title "{escaped_title}"'
            else:
                script = f'display notification "{escaped_message}"'
            
            result = self.applescript_executor.execute(
                script,
                timeout=5.0,
                retries=0,
            )
            
            if self._is_success(result):
                logger.debug(f"Showed notification: {message}")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"message": message, "title": title}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.ERROR,
                    error=f"Failed to show notification: {result.get('error')}"
                )
                
        except Exception as e:
            logger.error(f"show_notification error: {e}", exc_info=True)
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Exception showing notification: {str(e)}"
            )
    
    def run_script(
        self,
        script: str,
        timeout: Optional[float] = None
    ) -> SystemBridgeResult:
        """
        Execute an AppleScript.
        
        TICKET 1 (P0): Check shutdown flag before executing to prevent OS actions after shutdown.
        
        Args:
            script: AppleScript code to execute
            timeout: Optional timeout override
            
        Returns:
            SystemBridgeResult with data["stdout"] and optional data["stderr"]
        """
        if not self.is_available():
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="MacOSBridge is only available on macOS"
            )
        
        # TICKET 1 (P0): Double barrier - check shutdown before any OS automation
        from janus.runtime.shutdown import is_shutdown_requested, get_shutdown_reason
        
        if is_shutdown_requested():
            reason = get_shutdown_reason() or "Unknown reason"
            logger.warning(f"🛑 Aborting AppleScript execution - shutdown requested: {reason}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"AppleScript aborted - shutdown requested: {reason}"
            )
        
        timeout = timeout or self.default_timeout
        
        try:
            result = self.applescript_executor.execute(
                script,
                timeout=timeout,
            )
            
            if self._is_success(result):
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={
                        "stdout": result.get("stdout", ""),
                        "stderr": result.get("stderr", ""),
                    }
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.ERROR,
                    data={
                        "stdout": result.get("stdout", ""),
                        "stderr": result.get("stderr", ""),
                    },
                    error=result.get("error")
                )
                
        except Exception as e:
            logger.error(f"run_script error: {e}", exc_info=True)
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Exception running script: {str(e)}"
            )
    
    # ========== Helper Methods ==========
    
    def _map_app_name(self, app_name: str) -> str:
        """
        Map common app names to official macOS names.
        
        For backward compatibility, delegates to app_manager.
        
        Args:
            app_name: Input app name (may be shorthand)
            
        Returns:
            Official macOS application name
        """
        return self.app_manager.map_app_name(app_name)
    
    # ========== Accessibility API ==========
    
    def get_accessibility_backend(self):
        """
        Get macOS accessibility backend (AXUIElement).
        
        Returns:
            MacOSAccessibility instance or None
        """
        return self._accessibility_backend
    

