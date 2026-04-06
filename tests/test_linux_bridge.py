"""
Tests for LinuxBridge (TICKET-PLATFORM-002)

Comprehensive tests for Linux platform bridge implementation.
Uses mocks to test all functionality without requiring Linux dependencies.
"""

import platform
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch, call

# Mock Linux-specific dependencies before importing
_mock_modules = {
    'pyautogui': MagicMock(),
    'PIL': MagicMock(),
    'PIL.Image': MagicMock(),
    'cv2': MagicMock(),
    'numpy': MagicMock(),
}
for mod_name, mock in _mock_modules.items():
    if mod_name not in sys.modules:
        sys.modules[mod_name] = mock

from janus.platform.os.linux_bridge import LinuxBridge
from janus.platform.os.system_bridge import SystemBridgeStatus


class TestLinuxBridgeBasics(unittest.TestCase):
    """Test basic LinuxBridge functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = LinuxBridge()
    
    def test_initialization(self):
        """Test bridge initialization."""
        self.assertIsNotNone(self.bridge)
        self.assertIsInstance(self.bridge._xdotool_available, bool)
        self.assertIsInstance(self.bridge._wmctrl_available, bool)
        self.assertIsInstance(self.bridge._xclip_available, bool)
        self.assertIsInstance(self.bridge._xsel_available, bool)
        self.assertIsInstance(self.bridge._pyautogui_available, bool)
    
    def test_is_available_on_linux(self):
        """Test is_available returns True only on Linux."""
        if platform.system() == "Linux":
            self.assertTrue(self.bridge.is_available())
        else:
            self.assertFalse(self.bridge.is_available())
    
    def test_get_platform_name(self):
        """Test platform name is 'Linux'."""
        self.assertEqual(self.bridge.get_platform_name(), "Linux")


class TestLinuxBridgeApplicationManagement(unittest.TestCase):
    """Test application management operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = LinuxBridge()
    
    @patch('subprocess.Popen')
    def test_open_app_success(self, mock_popen):
        """Test successful app opening."""
        mock_popen.return_value = MagicMock()
        
        result = self.bridge.open_app("firefox")
        
        self.assertTrue(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.SUCCESS)
        self.assertEqual(result.data["app_name"], "firefox")
        mock_popen.assert_called_once()
    
    @patch('subprocess.Popen')
    def test_open_app_with_timeout(self, mock_popen):
        """Test app opening with timeout parameter."""
        mock_popen.return_value = MagicMock()
        
        result = self.bridge.open_app("gedit", timeout=5.0)
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["app_name"], "gedit")
    
    @patch('subprocess.Popen', side_effect=Exception("Launch failed"))
    def test_open_app_failure(self, mock_popen):
        """Test failed app opening."""
        result = self.bridge.open_app("nonexistent")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)
        self.assertIn("Failed to launch", result.error)
    
    @patch('subprocess.run')
    def test_close_app_with_wmctrl(self, mock_run):
        """Test successful app closing with wmctrl."""
        self.bridge._wmctrl_available = True
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.bridge.close_app("firefox")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["app_name"], "firefox")
        mock_run.assert_called_once()
        # Verify wmctrl command
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "wmctrl")
        self.assertEqual(args[1], "-c")
        self.assertIn("firefox", args)
    
    @patch('subprocess.run')
    def test_close_app_with_pkill_fallback(self, mock_run):
        """Test app closing falls back to pkill when wmctrl unavailable."""
        self.bridge._wmctrl_available = False
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.bridge.close_app("firefox")
        
        self.assertTrue(result.success)
        # Verify pkill command
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "pkill")
        self.assertIn("firefox", args)
    
    @patch('subprocess.run', side_effect=Exception("Kill failed"))
    def test_close_app_failure(self, mock_run):
        """Test failed app closing."""
        result = self.bridge.close_app("firefox")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)
    
    @patch('subprocess.run')
    def test_get_running_apps_success(self, mock_run):
        """Test successful retrieval of running apps."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "firefox\ngedit\ngnome-terminal\n"
        mock_run.return_value = mock_result
        
        result = self.bridge.get_running_apps()
        
        self.assertTrue(result.success)
        self.assertIn("apps", result.data)
        apps = result.data["apps"]
        self.assertIn("firefox", apps)
        self.assertIn("gedit", apps)
        self.assertIn("gnome-terminal", apps)
    
    @patch('subprocess.run')
    def test_get_running_apps_empty(self, mock_run):
        """Test getting running apps when output is empty."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run.return_value = mock_result
        
        result = self.bridge.get_running_apps()
        
        self.assertTrue(result.success)
        # Should have empty list (empty strings filtered out)
        self.assertEqual(len([app for app in result.data["apps"] if app]), 0)
    
    @patch('subprocess.run', side_effect=Exception("ps command failed"))
    def test_get_running_apps_failure(self, mock_run):
        """Test failed retrieval of running apps."""
        result = self.bridge.get_running_apps()
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)


class TestLinuxBridgeWindowManagement(unittest.TestCase):
    """Test window management operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = LinuxBridge()
    
    def test_get_active_window_without_tools(self):
        """Test get_active_window returns NOT_AVAILABLE without xdotool/wmctrl."""
        self.bridge._xdotool_available = False
        self.bridge._wmctrl_available = False
        
        result = self.bridge.get_active_window()
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        self.assertIn("xdotool or wmctrl required", result.error)
    
    @patch('subprocess.run')
    def test_get_active_window_with_xdotool(self, mock_run):
        """Test get_active_window with xdotool."""
        self.bridge._xdotool_available = True
        
        # Mock xdotool commands
        def run_side_effect(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            if "getactivewindow" in cmd:
                result.stdout = "12345678"
            elif "getwindowname" in cmd:
                result.stdout = "Firefox - Test Page"
            return result
        
        mock_run.side_effect = run_side_effect
        
        result = self.bridge.get_active_window()
        
        self.assertTrue(result.success)
        window = result.data["window"]
        self.assertEqual(window["title"], "Firefox - Test Page")
        self.assertEqual(window["window_id"], "12345678")
        self.assertTrue(window["is_active"])
    
    @patch('subprocess.run')
    def test_get_active_window_with_wmctrl_fallback(self, mock_run):
        """Test get_active_window falls back to wmctrl."""
        self.bridge._xdotool_available = False
        self.bridge._wmctrl_available = True
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "0x01234567  0 firefox.Firefox  test-pc Firefox - Test Page\n"
        mock_run.return_value = mock_result
        
        result = self.bridge.get_active_window()
        
        self.assertTrue(result.success)
        window = result.data["window"]
        self.assertEqual(window["window_id"], "0x01234567")
        self.assertIn("Firefox", window["title"])
    
    @patch('subprocess.run', side_effect=Exception("Command failed"))
    def test_get_active_window_failure(self, mock_run):
        """Test get_active_window handles errors."""
        self.bridge._xdotool_available = True
        
        result = self.bridge.get_active_window()
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)
    
    def test_list_windows_without_wmctrl(self):
        """Test list_windows returns NOT_AVAILABLE without wmctrl."""
        self.bridge._wmctrl_available = False
        
        result = self.bridge.list_windows()
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        self.assertIn("wmctrl required", result.error)
    
    @patch('subprocess.run')
    def test_list_windows_success(self, mock_run):
        """Test successful window listing."""
        self.bridge._wmctrl_available = True
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = """0x01234567  0 firefox.Firefox  test-pc Firefox - Test Page
0x02345678  0 gedit.Gedit      test-pc Untitled Document 1 - gedit
0x03456789  0 terminal.Gnome-terminal test-pc Terminal
"""
        mock_run.return_value = mock_result
        
        result = self.bridge.list_windows()
        
        self.assertTrue(result.success)
        windows = result.data["windows"]
        self.assertEqual(len(windows), 3)
        self.assertEqual(windows[0]["window_id"], "0x01234567")
        self.assertIn("Firefox", windows[0]["title"])
    
    @patch('subprocess.run', side_effect=Exception("wmctrl failed"))
    def test_list_windows_failure(self, mock_run):
        """Test list_windows handles errors."""
        self.bridge._wmctrl_available = True
        
        result = self.bridge.list_windows()
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)
    
    def test_focus_window_without_tools(self):
        """Test focus_window returns NOT_AVAILABLE without wmctrl/xdotool."""
        self.bridge._wmctrl_available = False
        self.bridge._xdotool_available = False
        
        result = self.bridge.focus_window("firefox")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
    
    @patch('subprocess.run')
    def test_focus_window_with_wmctrl(self, mock_run):
        """Test successful window focusing with wmctrl."""
        self.bridge._wmctrl_available = True
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.bridge.focus_window("firefox")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["app_name"], "firefox")
        # Verify wmctrl -a command
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "wmctrl")
        self.assertEqual(args[1], "-a")
        self.assertIn("firefox", args)
    
    @patch('subprocess.run')
    def test_focus_window_with_xdotool_fallback(self, mock_run):
        """Test window focusing falls back to xdotool."""
        self.bridge._wmctrl_available = False
        self.bridge._xdotool_available = True
        
        # Mock xdotool search and windowactivate
        def run_side_effect(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            if "search" in cmd:
                result.stdout = "12345678\n"
            return result
        
        mock_run.side_effect = run_side_effect
        
        result = self.bridge.focus_window("firefox")
        
        self.assertTrue(result.success)
        self.assertEqual(mock_run.call_count, 2)  # search + windowactivate


class TestLinuxBridgeUIInteractions(unittest.TestCase):
    """Test UI interaction operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = LinuxBridge()
    
    def test_click_without_tools(self):
        """Test click returns NOT_AVAILABLE without xdotool/pyautogui."""
        self.bridge._xdotool_available = False
        self.bridge._pyautogui_available = False
        
        result = self.bridge.click(100, 200)
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        self.assertIn("xdotool or pyautogui required", result.error)
    
    @patch('subprocess.run')
    def test_click_with_xdotool(self, mock_run):
        """Test successful click with xdotool."""
        self.bridge._xdotool_available = True
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.bridge.click(150, 250, button="left")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["x"], 150)
        self.assertEqual(result.data["y"], 250)
        self.assertEqual(result.data["button"], "left")
        # Verify xdotool command
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "xdotool")
        self.assertIn("mousemove", args)
        self.assertIn("150", args)
        self.assertIn("250", args)
        self.assertIn("click", args)
    
    @patch('subprocess.run')
    def test_click_right_button(self, mock_run):
        """Test right-click operation."""
        self.bridge._xdotool_available = True
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.bridge.click(100, 100, button="right")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["button"], "right")
        # Verify button number 3 for right click
        args = mock_run.call_args[0][0]
        self.assertIn("3", args)  # right button
    
    @patch('pyautogui.click')
    def test_click_with_pyautogui_fallback(self, mock_click):
        """Test click falls back to pyautogui."""
        self.bridge._xdotool_available = False
        self.bridge._pyautogui_available = True
        
        result = self.bridge.click(200, 300, button="middle")
        
        self.assertTrue(result.success)
        mock_click.assert_called_once_with(200, 300, button="middle")
    
    def test_type_text_without_tools(self):
        """Test type_text returns NOT_AVAILABLE without tools."""
        self.bridge._xdotool_available = False
        self.bridge._pyautogui_available = False
        
        result = self.bridge.type_text("Hello")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
    
    @patch('subprocess.run')
    def test_type_text_with_xdotool(self, mock_run):
        """Test successful text typing with xdotool."""
        self.bridge._xdotool_available = True
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.bridge.type_text("Hello, World!")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["text"], "Hello, World!")
        # Verify xdotool type command
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "xdotool")
        self.assertEqual(args[1], "type")
        self.assertEqual(args[2], "--")
        self.assertEqual(args[3], "Hello, World!")
    
    @patch('pyautogui.write')
    def test_type_text_with_pyautogui_fallback(self, mock_write):
        """Test type_text falls back to pyautogui."""
        self.bridge._xdotool_available = False
        self.bridge._pyautogui_available = True
        
        result = self.bridge.type_text("Test text")
        
        self.assertTrue(result.success)
        mock_write.assert_called_once_with("Test text", interval=0.01)
    
    def test_press_key_without_tools(self):
        """Test press_key returns NOT_AVAILABLE without tools."""
        self.bridge._xdotool_available = False
        self.bridge._pyautogui_available = False
        
        result = self.bridge.press_key("a")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
    
    @patch('subprocess.run')
    def test_press_key_without_modifiers(self, mock_run):
        """Test pressing a key without modifiers."""
        self.bridge._xdotool_available = True
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.bridge.press_key("Return")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["key"], "Return")
        self.assertIsNone(result.data["modifiers"])
        # Verify xdotool key command
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "xdotool")
        self.assertEqual(args[1], "key")
        self.assertEqual(args[2], "Return")
    
    @patch('subprocess.run')
    def test_press_key_with_modifiers(self, mock_run):
        """Test pressing a key with modifiers."""
        self.bridge._xdotool_available = True
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.bridge.press_key("c", modifiers=["ctrl", "shift"])
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["key"], "c")
        self.assertEqual(result.data["modifiers"], ["ctrl", "shift"])
        # Verify key combo format
        args = mock_run.call_args[0][0]
        self.assertEqual(args[2], "ctrl+shift+c")
    
    @patch('pyautogui.hotkey')
    def test_press_key_with_pyautogui_and_modifiers(self, mock_hotkey):
        """Test pressing key with modifiers using pyautogui."""
        self.bridge._xdotool_available = False
        self.bridge._pyautogui_available = True
        
        result = self.bridge.press_key("v", modifiers=["ctrl"])
        
        self.assertTrue(result.success)
        mock_hotkey.assert_called_once_with("ctrl", "v")
    
    @patch('subprocess.run')
    def test_send_keys_alias(self, mock_run):
        """Test send_keys is an alias for press_key."""
        self.bridge._xdotool_available = True
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.bridge.send_keys("Escape")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["key"], "Escape")


class TestLinuxBridgeClipboard(unittest.TestCase):
    """Test clipboard operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = LinuxBridge()
    
    def test_get_clipboard_without_tools(self):
        """Test get_clipboard returns NOT_AVAILABLE without xclip/xsel."""
        self.bridge._xclip_available = False
        self.bridge._xsel_available = False
        
        result = self.bridge.get_clipboard()
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        self.assertIn("xclip or xsel required", result.error)
    
    @patch('subprocess.run')
    def test_get_clipboard_with_xclip(self, mock_run):
        """Test successful clipboard retrieval with xclip."""
        self.bridge._xclip_available = True
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Test clipboard content"
        mock_run.return_value = mock_result
        
        result = self.bridge.get_clipboard()
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["text"], "Test clipboard content")
        # Verify xclip command
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "xclip")
        self.assertIn("-selection", args)
        self.assertIn("clipboard", args)
        self.assertIn("-o", args)
    
    @patch('subprocess.run')
    def test_get_clipboard_with_xsel_fallback(self, mock_run):
        """Test clipboard retrieval falls back to xsel."""
        self.bridge._xclip_available = False
        self.bridge._xsel_available = True
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "xsel clipboard content"
        mock_run.return_value = mock_result
        
        result = self.bridge.get_clipboard()
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["text"], "xsel clipboard content")
        # Verify xsel command
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "xsel")
        self.assertIn("--clipboard", args)
        self.assertIn("--output", args)
    
    @patch('subprocess.run', side_effect=Exception("Clipboard error"))
    def test_get_clipboard_failure(self, mock_run):
        """Test failed clipboard retrieval."""
        self.bridge._xclip_available = True
        
        result = self.bridge.get_clipboard()
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)
    
    def test_set_clipboard_without_tools(self):
        """Test set_clipboard returns NOT_AVAILABLE without xclip/xsel."""
        self.bridge._xclip_available = False
        self.bridge._xsel_available = False
        
        result = self.bridge.set_clipboard("test")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
    
    @patch('subprocess.run')
    def test_set_clipboard_with_xclip(self, mock_run):
        """Test successful clipboard setting with xclip."""
        self.bridge._xclip_available = True
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.bridge.set_clipboard("New clipboard text")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["text"], "New clipboard text")
        # Verify xclip command and input
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "xclip")
        self.assertIn("-selection", args)
        self.assertIn("clipboard", args)
        # Verify text was passed as input
        kwargs = mock_run.call_args[1]
        self.assertEqual(kwargs["input"], b"New clipboard text")
    
    @patch('subprocess.run')
    def test_set_clipboard_with_xsel_fallback(self, mock_run):
        """Test clipboard setting falls back to xsel."""
        self.bridge._xclip_available = False
        self.bridge._xsel_available = True
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.bridge.set_clipboard("xsel text")
        
        self.assertTrue(result.success)
        # Verify xsel command
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "xsel")
        self.assertIn("--clipboard", args)
        self.assertIn("--input", args)
    
    @patch('subprocess.run', side_effect=Exception("Clipboard write failed"))
    def test_set_clipboard_failure(self, mock_run):
        """Test failed clipboard setting."""
        self.bridge._xclip_available = True
        
        result = self.bridge.set_clipboard("Text")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)


class TestLinuxBridgeSystemOperations(unittest.TestCase):
    """Test system-level operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = LinuxBridge()
    
    @patch('subprocess.run')
    def test_show_notification_success(self, mock_run):
        """Test successful notification display."""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.bridge.show_notification("Test message", "Test Title")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["message"], "Test message")
        self.assertEqual(result.data["title"], "Test Title")
        # Verify notify-send was called
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "notify-send")
        self.assertEqual(args[1], "Test Title")
        self.assertEqual(args[2], "Test message")
    
    @patch('subprocess.run')
    def test_show_notification_default_title(self, mock_run):
        """Test notification with default title."""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.bridge.show_notification("Test message")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["title"], "Janus")
    
    @patch('subprocess.run', side_effect=Exception("notify-send error"))
    def test_show_notification_failure(self, mock_run):
        """Test failed notification display."""
        result = self.bridge.show_notification("Test")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)
    
    @patch('subprocess.run')
    def test_run_script_success(self, mock_run):
        """Test successful bash script execution."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Script output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = self.bridge.run_script("echo 'Hello, World!'")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["stdout"], "Script output")
        self.assertEqual(result.data["returncode"], 0)
        # Verify bash was called
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "bash")
        self.assertEqual(args[1], "-c")
        self.assertEqual(args[2], "echo 'Hello, World!'")
    
    @patch('subprocess.run')
    def test_run_script_with_timeout(self, mock_run):
        """Test script execution with custom timeout."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = self.bridge.run_script("sleep 1 && echo done", timeout=10.0)
        
        self.assertTrue(result.success)
        # Verify timeout was passed
        self.assertEqual(mock_run.call_args[1]["timeout"], 10.0)
    
    @patch('subprocess.run')
    def test_run_script_with_error(self, mock_run):
        """Test script execution with non-zero exit code."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Command not found"
        mock_run.return_value = mock_result
        
        result = self.bridge.run_script("invalid-command")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)
        self.assertEqual(result.data["returncode"], 1)
        self.assertEqual(result.error, "Command not found")
    
    @patch('subprocess.run', side_effect=Exception("Execution failed"))
    def test_run_script_exception(self, mock_run):
        """Test script execution with exception."""
        result = self.bridge.run_script("test")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)
        self.assertIn("Failed to run script", result.error)


class TestLinuxBridgeDependencyChecks(unittest.TestCase):
    """Test dependency checking logic."""
    
    def test_check_dependencies_flags_exist(self):
        """Test that all dependency flags are initialized."""
        bridge = LinuxBridge()
        self.assertIsInstance(bridge._xdotool_available, bool)
        self.assertIsInstance(bridge._wmctrl_available, bool)
        self.assertIsInstance(bridge._xclip_available, bool)
        self.assertIsInstance(bridge._xsel_available, bool)
        self.assertIsInstance(bridge._pyautogui_available, bool)
    
    def test_dependency_graceful_degradation(self):
        """Test operations gracefully degrade without dependencies."""
        bridge = LinuxBridge()
        bridge._xdotool_available = False
        bridge._wmctrl_available = False
        bridge._xclip_available = False
        bridge._xsel_available = False
        bridge._pyautogui_available = False
        
        # UI operations should return NOT_AVAILABLE
        result = bridge.click(100, 100)
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        
        result = bridge.type_text("test")
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        
        result = bridge.press_key("a")
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        
        # Window operations should return NOT_AVAILABLE
        result = bridge.get_active_window()
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        
        result = bridge.list_windows()
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        
        result = bridge.focus_window("test")
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        
        # Clipboard operations should return NOT_AVAILABLE
        result = bridge.get_clipboard()
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        
        result = bridge.set_clipboard("test")
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)


class TestLinuxBridgeIntegration(unittest.TestCase):
    """Test integration scenarios."""
    
    @patch('subprocess.Popen')
    @patch('subprocess.run')
    def test_app_lifecycle(self, mock_run, mock_popen):
        """Test complete app lifecycle: open -> close."""
        bridge = LinuxBridge()
        bridge._wmctrl_available = True
        mock_popen.return_value = MagicMock()
        mock_run.return_value = MagicMock(returncode=0)
        
        # Open app
        result = bridge.open_app("firefox")
        self.assertTrue(result.success)
        
        # Close app
        result = bridge.close_app("firefox")
        self.assertTrue(result.success)
    
    @patch('subprocess.run')
    def test_clipboard_roundtrip(self, mock_run):
        """Test clipboard set and get roundtrip."""
        bridge = LinuxBridge()
        bridge._xclip_available = True
        
        test_text = "Test clipboard content"
        
        # Set clipboard
        mock_run.return_value = MagicMock(returncode=0)
        result = bridge.set_clipboard(test_text)
        self.assertTrue(result.success)
        
        # Get clipboard
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = test_text
        mock_run.return_value = mock_result
        result = bridge.get_clipboard()
        self.assertTrue(result.success)
        self.assertEqual(result.data["text"], test_text)
    
    @patch('subprocess.run')
    def test_window_focus_workflow(self, mock_run):
        """Test window focus workflow."""
        bridge = LinuxBridge()
        bridge._wmctrl_available = True
        mock_run.return_value = MagicMock(returncode=0)
        
        # List windows
        mock_run.return_value.stdout = "0x01234567  0 firefox.Firefox  test-pc Firefox\n"
        result = bridge.list_windows()
        self.assertTrue(result.success)
        
        # Focus window
        mock_run.return_value = MagicMock(returncode=0)
        result = bridge.focus_window("firefox")
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
