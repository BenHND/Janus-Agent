"""
Windows Bridge - SystemBridge implementation for Windows.

TICKET-AUDIT-007: Create System Abstraction Layer (SystemBridge)
TICKET-OS-001: Native Windows Bridge Rewrite

This module provides a native implementation of SystemBridge for Windows.
Uses ctypes to call Windows API directly for performance and language-independence.

Features:
    - Native process enumeration using Windows API (EnumProcesses + GetModuleBaseName)
    - Native notifications using Shell_NotifyIcon
    - Application launch using subprocess
    - Window management using pywinauto (if available)
    - UI interactions using pyautogui (if available)
    - Clipboard operations using standard libraries

Performance:
    - get_running_apps(): <50ms (vs >200ms with subprocess)
    - Language-independent: Works on any Windows language configuration

Usage:
    from janus.platform.os.windows_bridge import WindowsBridge
    
    bridge = WindowsBridge()
    if bridge.is_available():
        bridge.open_app("notepad")
"""

import ctypes
import logging
import platform
import subprocess
import time
from ctypes import wintypes
from typing import List, Optional

from janus.platform.os.system_bridge import (
    SystemBridge,
    SystemBridgeResult,
    SystemBridgeStatus,
    WindowInfo,
)

logger = logging.getLogger(__name__)


# ========== Windows API Definitions ==========
# These are only loaded on Windows platform to avoid import errors on other platforms

def _setup_windows_api():
    """
    Setup Windows API function signatures for ctypes.
    Only called when running on Windows platform.
    Returns a dict of API functions or None if not on Windows.
    """
    if platform.system() != "Windows":
        return None
    
    try:
        # Load Windows DLLs
        psapi = ctypes.windll.psapi
        kernel32 = ctypes.windll.kernel32
        shell32 = ctypes.windll.shell32
        user32 = ctypes.windll.user32
        
        # Define constants
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010
        MAX_PATH = 260
        
        # Shell_NotifyIcon constants
        NIM_ADD = 0x00000000
        NIM_MODIFY = 0x00000001
        NIM_DELETE = 0x00000002
        NIF_MESSAGE = 0x00000001
        NIF_ICON = 0x00000002
        NIF_TIP = 0x00000004
        NIF_INFO = 0x00000010
        NIIF_INFO = 0x00000001
        NIIF_WARNING = 0x00000002
        NIIF_ERROR = 0x00000003
        
        # Icon constants
        IDI_APPLICATION = 32512  # Default application icon
        
        # Define NOTIFYICONDATA structure
        class NOTIFYICONDATA(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("hWnd", wintypes.HWND),
                ("uID", wintypes.UINT),
                ("uFlags", wintypes.UINT),
                ("uCallbackMessage", wintypes.UINT),
                ("hIcon", wintypes.HICON),
                ("szTip", wintypes.WCHAR * 128),
                ("dwState", wintypes.DWORD),
                ("dwStateMask", wintypes.DWORD),
                ("szInfo", wintypes.WCHAR * 256),
                ("uVersion", wintypes.UINT),
                ("szInfoTitle", wintypes.WCHAR * 64),
                ("dwInfoFlags", wintypes.DWORD),
            ]
        
        # Setup function signatures
        psapi.EnumProcesses.argtypes = [
            ctypes.POINTER(wintypes.DWORD),
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD)
        ]
        psapi.EnumProcesses.restype = wintypes.BOOL
        
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        
        psapi.GetModuleBaseNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.HMODULE,
            wintypes.LPWSTR,
            wintypes.DWORD
        ]
        psapi.GetModuleBaseNameW.restype = wintypes.DWORD
        
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        
        shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATA)]
        shell32.Shell_NotifyIconW.restype = wintypes.BOOL
        
        user32.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
        user32.LoadIconW.restype = wintypes.HICON
        
        return {
            'psapi': psapi,
            'kernel32': kernel32,
            'shell32': shell32,
            'user32': user32,
            'PROCESS_QUERY_INFORMATION': PROCESS_QUERY_INFORMATION,
            'PROCESS_VM_READ': PROCESS_VM_READ,
            'MAX_PATH': MAX_PATH,
            'NOTIFYICONDATA': NOTIFYICONDATA,
            'NIM_ADD': NIM_ADD,
            'NIM_MODIFY': NIM_MODIFY,
            'NIM_DELETE': NIM_DELETE,
            'NIF_MESSAGE': NIF_MESSAGE,
            'NIF_ICON': NIF_ICON,
            'NIF_TIP': NIF_TIP,
            'NIF_INFO': NIF_INFO,
            'NIIF_INFO': NIIF_INFO,
            'NIIF_WARNING': NIIF_WARNING,
            'NIIF_ERROR': NIIF_ERROR,
            'IDI_APPLICATION': IDI_APPLICATION,
        }
    except Exception as e:
        logger.warning(f"Failed to setup Windows API: {e}")
        return None


class WindowsBridge(SystemBridge):
    """
    Windows implementation of SystemBridge with basic functionality.
    
    Provides essential system operations with graceful degradation:
        - Application launch via subprocess
        - Window management via pywinauto (optional)
        - UI interactions via pyautogui (optional)
        - Clipboard operations via tkinter
        - Basic notifications
        - Accessibility API via UIAutomation
    
    Priority: MEDIUM (see TICKET-AUDIT-007)
    Dependencies: pyautogui (optional), pywinauto (optional)
    """
    
    def __init__(self):
        """Initialize Windows bridge."""
        self._pyautogui_available = False
        self._pywinauto_available = False
        self._win_api = None
        self._accessibility_backend = None
        self._check_dependencies()
        
        # Setup Windows API on Windows platform
        if platform.system() == "Windows":
            self._win_api = _setup_windows_api()
            # Initialize accessibility backend
            self._init_accessibility()
        
        logger.info(
            f"WindowsBridge initialized "
            f"(pyautogui={self._pyautogui_available}, pywinauto={self._pywinauto_available}, "
            f"native_api={self._win_api is not None}, "
            f"accessibility={self._accessibility_backend is not None})"
        )
    
    def _init_accessibility(self):
        """Initialize accessibility backend."""
        try:
            from janus.platform.accessibility.windows_accessibility import WindowsAccessibility
            self._accessibility_backend = WindowsAccessibility()
            if self._accessibility_backend.is_available():
                logger.debug("Windows accessibility backend initialized")
        except Exception as e:
            logger.debug(f"Failed to initialize accessibility backend: {e}")
    
    def _check_dependencies(self):
        """Check availability of optional dependencies."""
        try:
            import pyautogui
            self._pyautogui_available = True
        except ImportError:
            logger.debug("pyautogui not available - UI interactions will be limited")
        
        try:
            import pywinauto
            self._pywinauto_available = True
        except ImportError:
            logger.debug("pywinauto not available - window management will be limited")
    
    # ========== Platform Detection ==========
    
    def is_available(self) -> bool:
        """Check if running on Windows."""
        return platform.system() == "Windows"
    
    def get_platform_name(self) -> str:
        """Get platform name."""
        return "Windows"
    
    # ========== Application Management ==========
    
    def open_app(self, app_name: str, timeout: Optional[float] = None) -> SystemBridgeResult:
        """
        Open application using Windows system commands.
        
        Args:
            app_name: Name of application (e.g., "notepad", "calc")
            timeout: Operation timeout (currently unused)
        
        Returns:
            SystemBridgeResult with success/error status
        """
        try:
            # Try to launch application using subprocess
            subprocess.Popen([app_name], shell=True, 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
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
        Close application using taskkill command.
        
        Args:
            app_name: Name of application to close
        
        Returns:
            SystemBridgeResult with success/error status
        """
        try:
            # Use taskkill to terminate the process
            subprocess.run(
                ["taskkill", "/F", "/IM", f"{app_name}.exe"],
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
        Get running apps using native Windows API (EnumProcesses + GetModuleBaseName).
        
        This is a language-independent implementation that works on any Windows locale.
        Performance: <50ms (vs >200ms with subprocess/tasklist).
        
        Returns:
            SystemBridgeResult with list of running applications
        """
        # Use native API if available, fallback to subprocess
        if self._win_api:
            try:
                return self._get_running_apps_native()
            except Exception as e:
                logger.warning(f"Native API failed, falling back to subprocess: {e}")
                # Fall through to subprocess fallback
        
        # Fallback to subprocess method
        return self._get_running_apps_subprocess()
    
    def _get_running_apps_native(self) -> SystemBridgeResult:
        """
        Get running apps using native Windows API.
        
        Uses EnumProcesses to get all PIDs, then GetModuleBaseName to get executable names.
        This is language-independent and much faster than parsing tasklist output.
        """
        try:
            api = self._win_api
            psapi = api['psapi']
            kernel32 = api['kernel32']
            
            # Allocate buffer for process IDs (up to 1024 processes)
            max_processes = 1024
            pids = (wintypes.DWORD * max_processes)()
            cb_needed = wintypes.DWORD()
            
            # Enumerate all processes
            if not psapi.EnumProcesses(
                ctypes.byref(pids),
                ctypes.sizeof(pids),
                ctypes.byref(cb_needed)
            ):
                raise ctypes.WinError()
            
            # Calculate number of processes returned
            num_processes = cb_needed.value // ctypes.sizeof(wintypes.DWORD)
            
            # Get process names
            apps = []
            seen = set()
            
            for i in range(num_processes):
                pid = pids[i]
                if pid == 0:
                    continue
                
                # Open process with query rights
                h_process = kernel32.OpenProcess(
                    api['PROCESS_QUERY_INFORMATION'] | api['PROCESS_VM_READ'],
                    False,
                    pid
                )
                
                if h_process:
                    try:
                        # Get module base name (executable name)
                        process_name = ctypes.create_unicode_buffer(api['MAX_PATH'])
                        if psapi.GetModuleBaseNameW(
                            h_process,
                            None,
                            process_name,
                            api['MAX_PATH']
                        ):
                            name = process_name.value
                            if name and name not in seen:
                                apps.append(name)
                                seen.add(name)
                    finally:
                        kernel32.CloseHandle(h_process)
            
            return SystemBridgeResult(
                status=SystemBridgeStatus.SUCCESS,
                data={"apps": apps}
            )
        except Exception as e:
            logger.error(f"Failed to get running apps (native): {e}")
            raise
    
    def _get_running_apps_subprocess(self) -> SystemBridgeResult:
        """
        Fallback method using subprocess and tasklist.
        
        This is the old implementation kept for compatibility.
        """
        try:
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Parse CSV output and extract unique app names
                apps = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        # Extract first field (app name) from CSV
                        app = line.split(',')[0].strip('"')
                        if app and app not in apps:
                            apps.append(app)
                
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
            logger.error(f"Failed to get running apps (subprocess): {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to enumerate applications: {str(e)}"
            )
    
    # ========== Window Management ==========
    
    def get_active_window(self) -> SystemBridgeResult:
        """
        Get active window (requires pywinauto).
        
        Returns:
            SystemBridgeResult with window information
        """
        if not self._pywinauto_available:
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="pywinauto not available - install with: pip install pywinauto"
            )
        
        try:
            from pywinauto import Desktop
            window = Desktop(backend="uia").windows()[0]
            
            window_info = WindowInfo(
                title=window.window_text(),
                app_name=window.process_id(),
                window_id=str(window.handle),
                is_active=True
            )
            
            return SystemBridgeResult(
                status=SystemBridgeStatus.SUCCESS,
                data={"window": window_info.to_dict()}
            )
        except Exception as e:
            logger.error(f"Failed to get active window: {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to get active window: {str(e)}"
            )
    
    def list_windows(self) -> SystemBridgeResult:
        """
        List windows (requires pywinauto).
        
        Returns:
            SystemBridgeResult with list of windows
        """
        if not self._pywinauto_available:
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="pywinauto not available - install with: pip install pywinauto"
            )
        
        try:
            from pywinauto import Desktop
            desktop = Desktop(backend="uia")
            windows = []
            
            for window in desktop.windows():
                if window.is_visible():
                    window_info = WindowInfo(
                        title=window.window_text(),
                        app_name=str(window.process_id()),
                        window_id=str(window.handle),
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
        Focus window (requires pywinauto).
        
        Args:
            app_name: Name of application to focus
            timeout: Operation timeout
        
        Returns:
            SystemBridgeResult with success/error status
        """
        if not self._pywinauto_available:
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="pywinauto not available - install with: pip install pywinauto"
            )
        
        try:
            from pywinauto import Application
            app = Application().connect(title_re=f".*{app_name}.*", timeout=timeout or 5)
            app.top_window().set_focus()
            
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
        Click at coordinates using pyautogui.
        
        Args:
            x: X coordinate
            y: Y coordinate  
            button: Mouse button ("left", "right", "middle")
        
        Returns:
            SystemBridgeResult with success/error status
        """
        if not self._pyautogui_available:
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="pyautogui not available - install with: pip install pyautogui"
            )
        
        try:
            import pyautogui
            pyautogui.click(x, y, button=button)
            logger.info(f"Clicked at ({x}, {y}) with {button} button")
            return SystemBridgeResult(
                status=SystemBridgeStatus.SUCCESS,
                data={"x": x, "y": y, "button": button}
            )
        except Exception as e:
            logger.error(f"Failed to click at ({x}, {y}): {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to click: {str(e)}"
            )
    
    def type_text(self, text: str) -> SystemBridgeResult:
        """
        Type text using pyautogui.
        
        Args:
            text: Text to type
        
        Returns:
            SystemBridgeResult with success/error status
        """
        if not self._pyautogui_available:
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="pyautogui not available - install with: pip install pyautogui"
            )
        
        try:
            import pyautogui
            pyautogui.write(text, interval=0.01)
            logger.info(f"Typed text: {text[:50]}...")
            return SystemBridgeResult(
                status=SystemBridgeStatus.SUCCESS,
                data={"text": text}
            )
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to type text: {str(e)}"
            )
    
    def press_key(self, key: str, modifiers: Optional[List[str]] = None) -> SystemBridgeResult:
        """
        Press key combination using pyautogui.
        
        Args:
            key: Key to press (e.g., "a", "enter", "escape")
            modifiers: Optional modifier keys (e.g., ["ctrl", "shift"])
        
        Returns:
            SystemBridgeResult with success/error status
        """
        if not self._pyautogui_available:
            return SystemBridgeResult(
                status=SystemBridgeStatus.NOT_AVAILABLE,
                error="pyautogui not available - install with: pip install pyautogui"
            )
        
        try:
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
        Get clipboard content using tkinter.
        
        Returns:
            SystemBridgeResult with clipboard text
        """
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            clipboard_text = root.clipboard_get()
            root.destroy()
            
            logger.debug(f"Got clipboard: {clipboard_text[:50]}...")
            return SystemBridgeResult(
                status=SystemBridgeStatus.SUCCESS,
                data={"text": clipboard_text}
            )
        except Exception as e:
            logger.error(f"Failed to get clipboard: {e}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.ERROR,
                error=f"Failed to get clipboard: {str(e)}"
            )
    
    def set_clipboard(self, text: str) -> SystemBridgeResult:
        """
        Set clipboard content using tkinter.
        
        Args:
            text: Text to copy to clipboard
        
        Returns:
            SystemBridgeResult with success/error status
        """
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()  # Keep clipboard content after destroy
            root.destroy()
            
            logger.debug(f"Set clipboard: {text[:50]}...")
            return SystemBridgeResult(
                status=SystemBridgeStatus.SUCCESS,
                data={"text": text}
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
        Show notification using native Windows API (Shell_NotifyIcon).
        
        This is a language-independent implementation using the Windows shell API.
        Falls back to PowerShell if native API is not available.
        
        Args:
            message: Notification message
            title: Optional notification title
        
        Returns:
            SystemBridgeResult with success/error status
        """
        # Use native API if available, fallback to PowerShell
        if self._win_api:
            try:
                return self._show_notification_native(message, title)
            except Exception as e:
                logger.warning(f"Native notification failed, falling back to PowerShell: {e}")
                # Fall through to PowerShell fallback
        
        # Fallback to PowerShell method
        return self._show_notification_powershell(message, title)
    
    def _show_notification_native(
        self,
        message: str,
        title: Optional[str] = None
    ) -> SystemBridgeResult:
        """
        Show notification using native Shell_NotifyIcon API.
        
        This creates a temporary notification icon in the system tray.
        """
        try:
            api = self._win_api
            shell32 = api['shell32']
            user32 = api['user32']
            
            title = title or "Janus"
            
            # Create NOTIFYICONDATA structure
            nid = api['NOTIFYICONDATA']()
            nid.cbSize = ctypes.sizeof(api['NOTIFYICONDATA'])
            nid.hWnd = None  # No window handle needed for simple notification
            nid.uID = 1
            nid.uFlags = api['NIF_INFO'] | api['NIF_ICON']
            
            # Load default application icon
            nid.hIcon = user32.LoadIconW(None, api['IDI_APPLICATION'])
            
            # Set notification text (limited to 256 chars)
            nid.szInfo = message[:255]
            nid.szInfoTitle = title[:63]
            nid.dwInfoFlags = api['NIIF_INFO']
            
            # Add notification icon
            if not shell32.Shell_NotifyIconW(api['NIM_ADD'], ctypes.byref(nid)):
                # If NIM_ADD fails, try NIM_MODIFY (in case icon already exists)
                if not shell32.Shell_NotifyIconW(api['NIM_MODIFY'], ctypes.byref(nid)):
                    raise ctypes.WinError()
            
            # Keep notification visible briefly, then remove
            time.sleep(0.1)
            shell32.Shell_NotifyIconW(api['NIM_DELETE'], ctypes.byref(nid))
            
            logger.info(f"Showed notification (native): {title} - {message}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.SUCCESS,
                data={"title": title, "message": message}
            )
        except Exception as e:
            logger.error(f"Failed to show notification (native): {e}")
            raise
    
    def _show_notification_powershell(
        self,
        message: str,
        title: Optional[str] = None
    ) -> SystemBridgeResult:
        """
        Fallback method using PowerShell for notifications.
        
        This is the old implementation kept for compatibility.
        """
        try:
            title = title or "Janus"
            # Use PowerShell to show a balloon notification
            ps_script = f"""
            $notify = New-Object System.Windows.Forms.NotifyIcon
            $notify.Icon = [System.Drawing.SystemIcons]::Information
            $notify.Visible = $true
            $notify.ShowBalloonTip(5000, "{title}", "{message}", [System.Windows.Forms.ToolTipIcon]::Info)
            Start-Sleep -Seconds 1
            $notify.Dispose()
            """
            
            subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                timeout=10
            )
            
            logger.info(f"Showed notification (PowerShell): {title} - {message}")
            return SystemBridgeResult(
                status=SystemBridgeStatus.SUCCESS,
                data={"title": title, "message": message}
            )
        except Exception as e:
            logger.error(f"Failed to show notification (PowerShell): {e}")
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
        Execute PowerShell script.
        
        Args:
            script: PowerShell script content
            timeout: Operation timeout
        
        Returns:
            SystemBridgeResult with script output
        """
        try:
            result = subprocess.run(
                ["powershell", "-Command", script],
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
    
    # ========== Accessibility API ==========
    
    def get_accessibility_backend(self):
        """
        Get Windows accessibility backend (UIAutomation).
        
        Returns:
            WindowsAccessibility instance or None
        """
        return self._accessibility_backend
