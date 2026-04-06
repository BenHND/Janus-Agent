"""
Linux Bridge - SystemBridge implementation for Linux.

TICKET-AUDIT-007: Create System Abstraction Layer (SystemBridge)
TICKET-PLATFORM-002: Implement Linux Bridge

This module provides a complete implementation of SystemBridge for Linux.
Uses subprocess and standard Linux tools with graceful fallbacks for maximum
compatibility across different Linux distributions and desktop environments.

Features:
    - Application Management:
        * Launch applications using subprocess
        * Close applications using wmctrl or pkill
        * List running processes using ps
    
    - Window Management (requires wmctrl and/or xdotool):
        * Get active window information
        * List all windows
        * Focus/activate windows by name
    
    - UI Interactions (requires xdotool and/or pyautogui):
        * Mouse clicks (left, right, middle)
        * Keyboard text typing
        * Key combinations with modifiers
    
    - Clipboard Operations (requires xclip and/or xsel):
        * Read clipboard content
        * Write clipboard content
    
    - System Operations:
        * Display notifications using notify-send
        * Execute bash scripts

Dependencies:
    Required:
        - subprocess (Python standard library)
    
    Optional (for enhanced functionality):
        - xdotool: UI automation and window management
          Install: sudo apt-get install xdotool
        
        - wmctrl: Window management
          Install: sudo apt-get install wmctrl
        
        - xclip or xsel: Clipboard operations
          Install: sudo apt-get install xclip
          Or: sudo apt-get install xsel
        
        - pyautogui: Fallback for UI automation
          Install: pip install pyautogui
        
        - notify-send: Desktop notifications (usually pre-installed)

Graceful Degradation:
    The bridge checks for tool availability at initialization and gracefully
    degrades functionality when tools are not available. Operations that
    require missing tools will return SystemBridgeStatus.NOT_AVAILABLE with
    helpful installation instructions in the error message.

Supported Desktop Environments:
    - GNOME
    - KDE Plasma
    - XFCE
    - LXDE
    - i3/Sway (with limitations)
    - Most X11-based environments

Usage Example:
    from janus.platform.os.linux_bridge import LinuxBridge
    
    # Initialize bridge
    bridge = LinuxBridge()
    
    # Check availability
    if not bridge.is_available():
        print("Not running on Linux")
        return
    
    # Launch application
    result = bridge.open_app("firefox")
    if result.success:
        print("Firefox launched successfully")
    
    # Wait for window, then type
    import time
    time.sleep(2)
    result = bridge.type_text("Hello, Linux!")
    
    # Use clipboard
    bridge.set_clipboard("Copied text")
    result = bridge.get_clipboard()
    print(f"Clipboard: {result.data['text']}")
    
    # Show notification
    bridge.show_notification(
        message="Task completed",
        title="Linux Bridge"
    )

Testing:
    Comprehensive tests available in tests/test_linux_bridge.py
    Run with: python -m unittest tests.test_linux_bridge

See Also:
    - janus.os.system_bridge.SystemBridge: Base interface
    - janus.os.macos_bridge.MacOSBridge: macOS implementation
    - janus.os.windows_bridge.WindowsBridge: Windows implementation
"""

import logging
import platform
import subprocess
from typing import List, Optional

from janus.platform.os.system_bridge import (
    SystemBridge,
    SystemBridgeResult,
    SystemBridgeStatus,
    WindowInfo,
)

logger = logging.getLogger(__name__)


class LinuxBridge(SystemBridge):
    """
    Linux implementation of SystemBridge with comprehensive functionality.
    
    This bridge provides a complete implementation of all SystemBridge operations
    for Linux systems, using standard command-line tools and subprocess calls.
    
    Architecture:
        - Uses subprocess for process management and command execution
        - Checks tool availability at initialization
        - Provides fallback mechanisms for better compatibility
        - Returns NOT_AVAILABLE status with helpful messages when tools are missing
    
    Tool Hierarchy (fallback order):
        Window Management:
            1. xdotool (preferred for flexibility)
            2. wmctrl (fallback for basic operations)
        
        UI Interactions:
            1. xdotool (preferred for Linux-native support)
            2. pyautogui (fallback, cross-platform)
        
        Clipboard:
            1. xclip (preferred, widely available)
            2. xsel (alternative)
    
    Methods by Category:
        Platform Detection:
            - is_available(): Check if running on Linux
            - get_platform_name(): Returns "Linux"
        
        Application Management:
            - open_app(app_name): Launch application
            - close_app(app_name): Close application
            - get_running_apps(): List running processes
        
        Window Management (requires wmctrl/xdotool):
            - get_active_window(): Get active window info
            - list_windows(): List all windows
            - focus_window(app_name): Activate window
        
        UI Interactions (requires xdotool/pyautogui):
            - click(x, y, button): Mouse click
            - type_text(text): Type text
            - press_key(key, modifiers): Press key combo
            - send_keys(keys, modifiers): Alias for press_key
        
        Clipboard (requires xclip/xsel):
            - get_clipboard(): Read clipboard
            - set_clipboard(text): Write clipboard
        
        System Operations:
            - show_notification(message, title): Display notification
            - run_script(script): Execute bash script
    
    Attributes:
        _xdotool_available (bool): True if xdotool is installed
        _wmctrl_available (bool): True if wmctrl is installed
        _xclip_available (bool): True if xclip is installed
        _xsel_available (bool): True if xsel is installed
        _pyautogui_available (bool): True if pyautogui is installed
    
    Priority: MEDIUM (see TICKET-AUDIT-007)
    Status: COMPLETE (see TICKET-PLATFORM-002)
    
    Example:
        >>> bridge = LinuxBridge()
        >>> if bridge.is_available():
        ...     result = bridge.open_app("gedit")
        ...     if result.success:
        ...         print("Gedit opened")
        ...     else:
        ...         print(f"Error: {result.error}")
    """
    
    def __init__(self):
        """Initialize Linux bridge."""
        self._xdotool_available = False
        self._wmctrl_available = False
        self._xclip_available = False
        self._xsel_available = False
        self._pyautogui_available = False
        self._check_dependencies()
        
        logger.info(
            f"LinuxBridge initialized "
            f"(xdotool={self._xdotool_available}, wmctrl={self._wmctrl_available}, "
            f"xclip={self._xclip_available}, xsel={self._xsel_available})"
        )
    
    def _check_dependencies(self):
        """Check availability of optional dependencies."""
        # Check for xdotool
        try:
            subprocess.run(["which", "xdotool"], capture_output=True, timeout=1)
            self._xdotool_available = True
        except Exception:
            logger.debug("xdotool not available - UI interactions will be limited")
        
        # Check for wmctrl
        try:
            subprocess.run(["which", "wmctrl"], capture_output=True, timeout=1)
            self._wmctrl_available = True
        except Exception:
            logger.debug("wmctrl not available - window management will be limited")
        
        # Check for xclip
        try:
            subprocess.run(["which", "xclip"], capture_output=True, timeout=1)
            self._xclip_available = True
        except Exception:
            logger.debug("xclip not available")
        
        # Check for xsel
        try:
            subprocess.run(["which", "xsel"], capture_output=True, timeout=1)
            self._xsel_available = True
        except Exception:
            logger.debug("xsel not available")
        
        # Check for pyautogui
        try:
            import pyautogui
            self._pyautogui_available = True
        except ImportError:
            logger.debug("pyautogui not available")
    
    # ========== Platform Detection ==========
    
    def is_available(self) -> bool:
        """Check if running on Linux."""
        return platform.system() == "Linux"
    
    def get_platform_name(self) -> str:
        """Get platform name."""
        return "Linux"
    
    # ========== Application Management ==========
    
    def open_app(self, app_name: str, timeout: Optional[float] = None) -> SystemBridgeResult:
        """
        Open application using subprocess.
        
        Args:
            app_name: Name of application (e.g., "firefox", "gedit")
            timeout: Operation timeout (currently unused)
        
        Returns:
            SystemBridgeResult with success/error status
        """
        try:
            # Try to launch application using subprocess
            subprocess.Popen(
                [app_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            logger.info(f"Launched application: {app_name}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.SUCCESS,
                data={"app_name": app_name}
            )
        except Exception as e:
            logger.error(f"Failed to open app {app_name}: {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to launch application: {str(e)}"
            )
    
    def close_app(self, app_name: str) -> SystemBridgeResult:
        """
        Close application using pkill/wmctrl.
        
        Args:
            app_name: Name of application to close
        
        Returns:
            SystemBridgeResult with success/error status
        """
        try:
            # Try wmctrl first if available
            if self._wmctrl_available:
                subprocess.run(
                    ["wmctrl", "-c", app_name],
                    capture_output=True,
                    timeout=5
                )
            else:
                # Fall back to pkill
                subprocess.run(
                    ["pkill", "-f", app_name],
                    capture_output=True,
                    timeout=5
                )
            
            logger.info(f"Closed application: {app_name}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.SUCCESS,
                data={"app_name": app_name}
            )
        except Exception as e:
            logger.error(f"Failed to close app {app_name}: {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to close application: {str(e)}"
            )
    
    def get_running_apps(self) -> SystemBridgeResult:
        """
        Get running apps using ps command.
        
        Returns:
            SystemBridgeResult with list of running applications
        """
        try:
            result = subprocess.run(
                ["ps", "-eo", "comm", "--no-headers"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse output and get unique process names
                apps = list(set(result.stdout.strip().split('\n')))
                apps = [app for app in apps if app]  # Remove empty strings
                
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"apps": apps}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.ERROR,
                    error="Failed to get running applications"
                )
        except Exception as e:
            logger.error(f"Failed to get running apps: {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to enumerate applications: {str(e)}"
            )
    
    # ========== Window Management ==========
    
    def get_active_window(self) -> SystemBridgeResult:
        """
        Get active window using xdotool or wmctrl.
        
        Returns:
            SystemBridgeResult with window information
        """
        if not (self._xdotool_available or self._wmctrl_available):
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="xdotool or wmctrl required - install with: apt-get install xdotool wmctrl"
            )
        
        try:
            if self._xdotool_available:
                # Get active window ID
                result = subprocess.run(
                    ["xdotool", "getactivewindow"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                window_id = result.stdout.strip()
                
                # Get window name
                result = subprocess.run(
                    ["xdotool", "getwindowname", window_id],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                window_name = result.stdout.strip()
                
                window_info = WindowInfo(
                    title=window_name,
                    app_name="unknown",
                    window_id=window_id,
                    is_active=True
                )
                
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"window": window_info.to_dict()}
                )
            else:
                # Fall back to wmctrl
                result = subprocess.run(
                    ["wmctrl", "-lx"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                # Parse first window (active)
                lines = result.stdout.strip().split('\n')
                if lines and lines[0]:
                    parts = lines[0].split(None, 3)
                    window_info = WindowInfo(
                        title=parts[3] if len(parts) > 3 else "",
                        app_name=parts[2] if len(parts) > 2 else "",
                        window_id=parts[0] if len(parts) > 0 else "",
                        is_active=True
                    )
                    return SystemBridgeResult(
                        status=SystemBridgeStatus.SUCCESS,
                        data={"window": window_info.to_dict()}
                    )
                
                return SystemBridgeResult(
                    status=SystemBridgeStatus.ERROR,
                    error="No active window found"
                )
        except Exception as e:
            logger.error(f"Failed to get active window: {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to get active window: {str(e)}"
            )
    
    def list_windows(self) -> SystemBridgeResult:
        """
        List windows using wmctrl or xdotool.
        
        Returns:
            SystemBridgeResult with list of windows
        """
        if not self._wmctrl_available:
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="wmctrl required - install with: apt-get install wmctrl"
            )
        
        try:
            result = subprocess.run(
                ["wmctrl", "-lx"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            windows = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(None, 3)
                    window_info = WindowInfo(
                        title=parts[3] if len(parts) > 3 else "",
                        app_name=parts[2] if len(parts) > 2 else "",
                        window_id=parts[0] if len(parts) > 0 else "",
                        is_active=False
                    )
                    windows.append(window_info.to_dict())
            
            return SystemBridgeResult(
                status=SystemBridgeStatus.SUCCESS,
                data={"windows": windows}
            )
        except Exception as e:
            logger.error(f"Failed to list windows: {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to list windows: {str(e)}"
            )
    
    def focus_window(self, app_name: str, timeout: Optional[float] = None) -> SystemBridgeResult:
        """
        Focus window using wmctrl or xdotool.
        
        Args:
            app_name: Name of application to focus
            timeout: Operation timeout
        
        Returns:
            SystemBridgeResult with success/error status
        """
        if not (self._wmctrl_available or self._xdotool_available):
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="wmctrl or xdotool required - install with: apt-get install wmctrl xdotool"
            )
        
        try:
            if self._wmctrl_available:
                subprocess.run(
                    ["wmctrl", "-a", app_name],
                    capture_output=True,
                    timeout=timeout or 5
                )
            elif self._xdotool_available:
                # Search for window and activate
                result = subprocess.run(
                    ["xdotool", "search", "--name", app_name],
                    capture_output=True,
                    text=True,
                    timeout=timeout or 5
                )
                window_id = result.stdout.strip().split('\n')[0]
                subprocess.run(
                    ["xdotool", "windowactivate", window_id],
                    capture_output=True,
                    timeout=timeout or 5
                )
            
            logger.info(f"Focused window: {app_name}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.SUCCESS,
                data={"app_name": app_name}
            )
        except Exception as e:
            logger.error(f"Failed to focus window {app_name}: {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to focus window: {str(e)}"
            )
    
    # ========== UI Interactions ==========
    
    def click(self, x: int, y: int, button: str = "left") -> SystemBridgeResult:
        """
        Click at coordinates using xdotool or pyautogui.
        
        Args:
            x: X coordinate
            y: Y coordinate
            button: Mouse button ("left", "right", "middle")
        
        Returns:
            SystemBridgeResult with success/error status
        """
        try:
            if self._xdotool_available:
                # Map button names
                button_map = {"left": "1", "middle": "2", "right": "3"}
                button_num = button_map.get(button, "1")
                
                subprocess.run(
                    ["xdotool", "mousemove", str(x), str(y), "click", button_num],
                    capture_output=True,
                    timeout=5
                )
                logger.info(f"Clicked at ({x}, {y}) with {button} button")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"x": x, "y": y, "button": button}
                )
            elif self._pyautogui_available:
                import pyautogui
                pyautogui.click(x, y, button=button)
                logger.info(f"Clicked at ({x}, {y}) with {button} button")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"x": x, "y": y, "button": button}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.NOT_AVAILABLE,
                    error="xdotool or pyautogui required - install with: apt-get install xdotool"
                )
        except Exception as e:
            logger.error(f"Failed to click at ({x}, {y}): {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to click: {str(e)}"
            )
    
    def type_text(self, text: str) -> SystemBridgeResult:
        """
        Type text using xdotool or pyautogui.
        
        Args:
            text: Text to type
        
        Returns:
            SystemBridgeResult with success/error status
        """
        try:
            if self._xdotool_available:
                subprocess.run(
                    ["xdotool", "type", "--", text],
                    capture_output=True,
                    timeout=30
                )
                logger.info(f"Typed text: {text[:50]}...")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"text": text}
                )
            elif self._pyautogui_available:
                import pyautogui
                pyautogui.write(text, interval=0.01)
                logger.info(f"Typed text: {text[:50]}...")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"text": text}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.NOT_AVAILABLE,
                    error="xdotool or pyautogui required - install with: apt-get install xdotool"
                )
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to type text: {str(e)}"
            )
    
    def press_key(self, key: str, modifiers: Optional[List[str]] = None) -> SystemBridgeResult:
        """
        Press key combination using xdotool or pyautogui.
        
        Args:
            key: Key to press (e.g., "a", "Return", "Escape")
            modifiers: Optional modifier keys (e.g., ["ctrl", "shift"])
        
        Returns:
            SystemBridgeResult with success/error status
        """
        try:
            if self._xdotool_available:
                # Build xdotool key command
                if modifiers:
                    key_combo = "+".join(modifiers + [key])
                else:
                    key_combo = key
                
                subprocess.run(
                    ["xdotool", "key", key_combo],
                    capture_output=True,
                    timeout=5
                )
                logger.info(f"Pressed key: {key} with modifiers {modifiers}")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"key": key, "modifiers": modifiers}
                )
            elif self._pyautogui_available:
                import pyautogui
                if modifiers:
                    pyautogui.hotkey(*modifiers, key)
                else:
                    pyautogui.press(key)
                logger.info(f"Pressed key: {key} with modifiers {modifiers}")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"key": key, "modifiers": modifiers}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.NOT_AVAILABLE,
                    error="xdotool or pyautogui required - install with: apt-get install xdotool"
                )
        except Exception as e:
            logger.error(f"Failed to press key {key}: {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to press key: {str(e)}"
            )
    
    def send_keys(self, keys: str, modifiers: Optional[List[str]] = None) -> SystemBridgeResult:
        """Send keys (alias for press_key)."""
        return self.press_key(keys, modifiers)
    
    # ========== Clipboard Operations ==========
    
    def get_clipboard(self) -> SystemBridgeResult:
        """
        Get clipboard content using xclip or xsel.
        
        Returns:
            SystemBridgeResult with clipboard text
        """
        try:
            if self._xclip_available:
                result = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                clipboard_text = result.stdout
                logger.debug(f"Got clipboard: {clipboard_text[:50]}...")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"text": clipboard_text}
                )
            elif self._xsel_available:
                result = subprocess.run(
                    ["xsel", "--clipboard", "--output"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                clipboard_text = result.stdout
                logger.debug(f"Got clipboard: {clipboard_text[:50]}...")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"text": clipboard_text}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.NOT_AVAILABLE,
                    error="xclip or xsel required - install with: apt-get install xclip"
                )
        except Exception as e:
            logger.error(f"Failed to get clipboard: {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to get clipboard: {str(e)}"
            )
    
    def set_clipboard(self, text: str) -> SystemBridgeResult:
        """
        Set clipboard content using xclip or xsel.
        
        Args:
            text: Text to copy to clipboard
        
        Returns:
            SystemBridgeResult with success/error status
        """
        try:
            if self._xclip_available:
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text.encode(),
                    timeout=5
                )
                logger.debug(f"Set clipboard: {text[:50]}...")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"text": text}
                )
            elif self._xsel_available:
                subprocess.run(
                    ["xsel", "--clipboard", "--input"],
                    input=text.encode(),
                    timeout=5
                )
                logger.debug(f"Set clipboard: {text[:50]}...")
                return SystemBridgeResult(
                    status=SystemBridgeStatus.SUCCESS,
                    data={"text": text}
                )
            else:
                return SystemBridgeResult(
                    status=SystemBridgeStatus.NOT_AVAILABLE,
                    error="xclip or xsel required - install with: apt-get install xclip"
                )
        except Exception as e:
            logger.error(f"Failed to set clipboard: {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to set clipboard: {str(e)}"
            )
    
    # ========== System Operations ==========
    
    def show_notification(
        self,
        message: str,
        title: Optional[str] = None
    ) -> SystemBridgeResult:
        """
        Show notification using notify-send.
        
        Args:
            message: Notification message
            title: Optional notification title
        
        Returns:
            SystemBridgeResult with success/error status
        """
        try:
            title = title or "Janus"
            subprocess.run(
                ["notify-send", title, message],
                capture_output=True,
                timeout=5
            )
            logger.info(f"Showed notification: {title} - {message}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.SUCCESS,
                data={"title": title, "message": message}
            )
        except Exception as e:
            logger.error(f"Failed to show notification: {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to show notification: {str(e)}"
            )
    
    def run_script(
        self,
        script: str,
        timeout: Optional[float] = None
    ) -> SystemBridgeResult:
        """
        Execute bash script.
        
        Args:
            script: Bash script content
            timeout: Operation timeout
        
        Returns:
            SystemBridgeResult with script output
        """
        try:
            result = subprocess.run(
                ["bash", "-c", script],
                capture_output=True,
                text=True,
                timeout=timeout or 30
            )
            
            return SystemBridgeResult(
                status=SystemBridgeStatus.SUCCESS if result.returncode == 0 else SystemBridgeStatus.ERROR,
                data={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                },
                error=result.stderr if result.returncode != 0 else None
            )
        except Exception as e:
            logger.error(f"Failed to run script: {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to run script: {str(e)}"
            )
