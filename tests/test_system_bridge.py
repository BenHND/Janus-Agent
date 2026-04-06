"""
Tests for SystemBridge (TICKET-AUDIT-007)

Tests the SystemBridge abstraction layer and platform implementations.

This test module uses mocked imports to avoid triggering
heavy dependencies in headless CI environments.
"""

import platform
import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock heavy dependencies before importing
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

# Now safe to import from janus.platform.os
from janus.platform.os import (
    SystemBridge,
    SystemBridgeResult,
    SystemBridgeStatus,
    WindowInfo,
    get_system_bridge,
    create_system_bridge,
    reset_system_bridge,
)
from janus.platform.os.macos_bridge import MacOSBridge
from janus.platform.os.windows_bridge import WindowsBridge
from janus.platform.os.linux_bridge import LinuxBridge
from janus.platform.os.mock_bridge import MockSystemBridge


class TestWindowInfo(unittest.TestCase):
    """Test WindowInfo dataclass."""
    
    def test_window_info_creation(self):
        """Test WindowInfo creation."""
        window = WindowInfo(
            title="Safari Window",
            app_name="Safari",
            window_id="123",
            is_active=True,
            bounds={"x": 0, "y": 0, "width": 800, "height": 600},
        )
        
        self.assertEqual(window.title, "Safari Window")
        self.assertEqual(window.app_name, "Safari")
        self.assertEqual(window.window_id, "123")
        self.assertTrue(window.is_active)
        self.assertIsNotNone(window.bounds)
    
    def test_window_info_to_dict(self):
        """Test WindowInfo to_dict conversion."""
        window = WindowInfo(
            title="Test",
            app_name="TestApp",
        )
        
        d = window.to_dict()
        self.assertEqual(d["title"], "Test")
        self.assertEqual(d["app_name"], "TestApp")
        self.assertIn("is_active", d)


class TestSystemBridgeResult(unittest.TestCase):
    """Test SystemBridgeResult container."""
    
    def test_success_result(self):
        """Test successful result creation."""
        result = SystemBridgeResult(
            status=SystemBridgeStatus.SUCCESS,
            data={"app_name": "Safari"},
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.SUCCESS)
        self.assertEqual(result.data["app_name"], "Safari")
        self.assertIsNone(result.error)
    
    def test_error_result(self):
        """Test error result creation."""
        result = SystemBridgeResult(
            status=SystemBridgeStatus.ERROR,
            error="Operation failed",
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)
        self.assertEqual(result.error, "Operation failed")
    
    def test_not_available_result(self):
        """Test not available result."""
        result = SystemBridgeResult(
            status=SystemBridgeStatus.NOT_AVAILABLE,
            error="Platform not supported",
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
    
    def test_to_dict_success(self):
        """Test to_dict for successful result."""
        result = SystemBridgeResult(
            status=SystemBridgeStatus.SUCCESS,
            data={"text": "Hello"},
        )
        
        d = result.to_dict()
        self.assertEqual(d["status"], "success")
        self.assertEqual(d["data"]["text"], "Hello")
        self.assertNotIn("error", d)
    
    def test_to_dict_error(self):
        """Test to_dict for error result."""
        result = SystemBridgeResult(
            status=SystemBridgeStatus.ERROR,
            error="Failed",
        )
        
        d = result.to_dict()
        self.assertEqual(d["status"], "error")
        self.assertEqual(d["error"], "Failed")


class TestMacOSBridge(unittest.TestCase):
    """Test MacOSBridge implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = MacOSBridge()
    
    def test_is_available_on_mac(self):
        """Test is_available returns True on macOS."""
        if platform.system() == "Darwin":
            self.assertTrue(self.bridge.is_available())
        else:
            self.assertFalse(self.bridge.is_available())
    
    def test_get_platform_name(self):
        """Test platform name."""
        self.assertEqual(self.bridge.get_platform_name(), "macOS")
    
    def test_open_app_not_on_mac(self):
        """Test open_app returns error when not on macOS."""
        if platform.system() != "Darwin":
            result = self.bridge.open_app("Safari")
            self.assertFalse(result.success)
            self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
            self.assertIn("only available on macOS", result.error)
    
    def test_close_app_not_on_mac(self):
        """Test close_app returns error when not on macOS."""
        if platform.system() != "Darwin":
            result = self.bridge.close_app("Safari")
            self.assertFalse(result.success)
            self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
    
    def test_get_running_apps_not_on_mac(self):
        """Test get_running_apps returns error when not on macOS."""
        if platform.system() != "Darwin":
            result = self.bridge.get_running_apps()
            self.assertFalse(result.success)
    
    def test_get_active_window_not_on_mac(self):
        """Test get_active_window returns error when not on macOS."""
        if platform.system() != "Darwin":
            result = self.bridge.get_active_window()
            self.assertFalse(result.success)
    
    def test_click_not_on_mac(self):
        """Test click returns error when not on macOS."""
        if platform.system() != "Darwin":
            result = self.bridge.click(100, 200)
            self.assertFalse(result.success)
    
    def test_type_text_not_on_mac(self):
        """Test type_text returns error when not on macOS."""
        if platform.system() != "Darwin":
            result = self.bridge.type_text("hello")
            self.assertFalse(result.success)
    
    def test_app_name_mapping(self):
        """Test app name mapping."""
        self.assertEqual(self.bridge._map_app_name("chrome"), "Google Chrome")
        self.assertEqual(self.bridge._map_app_name("vscode"), "Visual Studio Code")
        self.assertEqual(self.bridge._map_app_name("safari"), "Safari")
        self.assertEqual(self.bridge._map_app_name("UnknownApp"), "UnknownApp")


class TestMacOSBridgeWithMocks(unittest.TestCase):
    """Test MacOSBridge with mocked AppleScript executor."""
    
    def setUp(self):
        """Set up test fixtures with mocked executor."""
        self.bridge = MacOSBridge()
        self.mock_executor = MagicMock()
        self.bridge._applescript_executor = self.mock_executor
    
    @patch('platform.system', return_value='Darwin')
    def test_open_app_success(self, mock_platform):
        """Test successful open_app call."""
        self.mock_executor.execute.return_value = {
            "status": "success",
            "stdout": "",
        }
        
        result = self.bridge.open_app("Safari")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["app_name"], "Safari")
        self.mock_executor.execute.assert_called_once()
    
    @patch('platform.system', return_value='Darwin')
    def test_close_app_success(self, mock_platform):
        """Test successful close_app call."""
        self.mock_executor.execute.return_value = {
            "status": "success",
            "stdout": "",
        }
        
        result = self.bridge.close_app("Safari")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["app_name"], "Safari")
    
    @patch('platform.system', return_value='Darwin')
    def test_get_running_apps_success(self, mock_platform):
        """Test successful get_running_apps call."""
        self.mock_executor.execute.return_value = {
            "status": "success",
            "stdout": "Finder, Safari, Terminal",
        }
        
        result = self.bridge.get_running_apps()
        
        self.assertTrue(result.success)
        self.assertIn("apps", result.data)
        self.assertEqual(len(result.data["apps"]), 3)
        self.assertIn("Safari", result.data["apps"])
    
    @patch('platform.system', return_value='Darwin')
    def test_get_active_window_success(self, mock_platform):
        """Test successful get_active_window call."""
        self.mock_executor.execute.return_value = {
            "status": "success",
            "stdout": "Safari|Example Page",
        }
        
        result = self.bridge.get_active_window()
        
        self.assertTrue(result.success)
        window = result.data["window"]
        self.assertEqual(window.app_name, "Safari")
        self.assertEqual(window.title, "Example Page")
        self.assertTrue(window.is_active)
    
    @patch('platform.system', return_value='Darwin')
    def test_press_key_with_modifiers(self, mock_platform):
        """Test press_key with modifier keys."""
        self.mock_executor.execute.return_value = {
            "status": "success",
            "stdout": "",
        }
        
        result = self.bridge.press_key("c", modifiers=["command"])
        
        self.assertTrue(result.success)
        # Check that the script included modifier
        call_args = self.mock_executor.execute.call_args[0][0]
        self.assertIn("command down", call_args)
    
    @patch('platform.system', return_value='Darwin')
    def test_type_text_with_special_chars(self, mock_platform):
        """Test type_text with special characters."""
        self.mock_executor.execute.return_value = {
            "status": "success",
            "stdout": "",
        }
        
        result = self.bridge.type_text('Hello "World"')
        
        self.assertTrue(result.success)
        # Check that quotes were escaped
        call_args = self.mock_executor.execute.call_args[0][0]
        self.assertIn('\\"', call_args)


class TestWindowsBridge(unittest.TestCase):
    """Test WindowsBridge stub."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = WindowsBridge()
    
    def test_is_available(self):
        """Test is_available."""
        if platform.system() == "Windows":
            self.assertTrue(self.bridge.is_available())
        else:
            self.assertFalse(self.bridge.is_available())
    
    def test_get_platform_name(self):
        """Test platform name."""
        self.assertEqual(self.bridge.get_platform_name(), "Windows")
    
    def test_open_app_implemented(self):
        """Test open_app is now implemented."""
        # Note: This will fail if actually run on Windows without the app
        # but it should no longer return NOT_AVAILABLE
        result = self.bridge.open_app("notepad")
        # On Linux (CI environment), this will return ERROR status
        # On Windows, it might succeed or error depending on the app
        self.assertIn(result.status, [SystemBridgeStatus.SUCCESS, SystemBridgeStatus.ERROR])
    
    def test_some_operations_require_dependencies(self):
        """Test operations that require optional dependencies."""
        # These operations require pywinauto which may not be installed
        result = self.bridge.get_active_window()
        if not self.bridge._pywinauto_available:
            self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        else:
            self.assertIn(result.status, [SystemBridgeStatus.SUCCESS, SystemBridgeStatus.ERROR])
        
        result = self.bridge.list_windows()
        if not self.bridge._pywinauto_available:
            self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        else:
            self.assertIn(result.status, [SystemBridgeStatus.SUCCESS, SystemBridgeStatus.ERROR])
    
    def test_clipboard_implemented(self):
        """Test clipboard operations are implemented."""
        # Clipboard uses tkinter which should be available
        result = self.bridge.set_clipboard("test")
        # May succeed or error, but not NOT_AVAILABLE
        self.assertIn(result.status, [SystemBridgeStatus.SUCCESS, SystemBridgeStatus.ERROR])
        
        result = self.bridge.get_clipboard()
        self.assertIn(result.status, [SystemBridgeStatus.SUCCESS, SystemBridgeStatus.ERROR])


class TestLinuxBridge(unittest.TestCase):
    """Test LinuxBridge stub."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = LinuxBridge()
    
    def test_is_available(self):
        """Test is_available."""
        if platform.system() == "Linux":
            self.assertTrue(self.bridge.is_available())
        else:
            self.assertFalse(self.bridge.is_available())
    
    def test_get_platform_name(self):
        """Test platform name."""
        self.assertEqual(self.bridge.get_platform_name(), "Linux")
    
    def test_some_operations_implemented(self):
        """Test that some operations are now implemented."""
        # Basic operations like app launch should work
        result = self.bridge.open_app("app")
        # Will error on Linux CI but not return NOT_AVAILABLE
        self.assertIn(result.status, [SystemBridgeStatus.SUCCESS, SystemBridgeStatus.ERROR])
        
        result = self.bridge.close_app("app")
        self.assertIn(result.status, [SystemBridgeStatus.SUCCESS, SystemBridgeStatus.ERROR])
        
        result = self.bridge.get_running_apps()
        self.assertIn(result.status, [SystemBridgeStatus.SUCCESS, SystemBridgeStatus.ERROR])
        
        result = self.bridge.show_notification("msg")
        self.assertIn(result.status, [SystemBridgeStatus.SUCCESS, SystemBridgeStatus.ERROR])
        
        result = self.bridge.run_script("echo test")
        self.assertIn(result.status, [SystemBridgeStatus.SUCCESS, SystemBridgeStatus.ERROR])
    
    def test_some_operations_require_dependencies(self):
        """Test operations that require optional dependencies."""
        # These operations require xdotool/wmctrl/xclip which may not be installed
        result = self.bridge.get_active_window()
        if not (self.bridge._xdotool_available or self.bridge._wmctrl_available):
            self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        
        result = self.bridge.list_windows()
        if not self.bridge._wmctrl_available:
            self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        
        result = self.bridge.click(100, 200)
        if not (self.bridge._xdotool_available or self.bridge._pyautogui_available):
            self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        
        result = self.bridge.get_clipboard()
        if not (self.bridge._xclip_available or self.bridge._xsel_available):
            self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)


class TestMockSystemBridge(unittest.TestCase):
    """Test MockSystemBridge for testing."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = MockSystemBridge()
    
    def test_is_always_available(self):
        """Test mock is always available."""
        self.assertTrue(self.bridge.is_available())
    
    def test_get_platform_name(self):
        """Test platform name."""
        self.assertEqual(self.bridge.get_platform_name(), "Mock")
    
    def test_open_app_success(self):
        """Test open_app succeeds by default."""
        result = self.bridge.open_app("TestApp")
        self.assertTrue(result.success)
        self.assertEqual(result.data["app_name"], "TestApp")
    
    def test_close_app_success(self):
        """Test close_app succeeds by default."""
        self.bridge.open_app("TestApp")
        result = self.bridge.close_app("TestApp")
        self.assertTrue(result.success)
    
    def test_get_running_apps(self):
        """Test get_running_apps returns mock apps."""
        result = self.bridge.get_running_apps()
        self.assertTrue(result.success)
        self.assertIn("apps", result.data)
        self.assertGreater(len(result.data["apps"]), 0)
    
    def test_get_active_window(self):
        """Test get_active_window returns mock window."""
        result = self.bridge.get_active_window()
        self.assertTrue(result.success)
        window = result.data["window"]
        self.assertIsInstance(window, WindowInfo)
        self.assertTrue(window.is_active)
    
    def test_clipboard_operations(self):
        """Test clipboard get/set."""
        # Set clipboard
        result = self.bridge.set_clipboard("Test content")
        self.assertTrue(result.success)
        
        # Get clipboard
        result = self.bridge.get_clipboard()
        self.assertTrue(result.success)
        self.assertEqual(result.data["text"], "Test content")
    
    def test_call_logging(self):
        """Test call logging functionality."""
        self.bridge.open_app("App1")
        self.bridge.click(100, 200)
        self.bridge.type_text("Hello")
        
        self.assertEqual(len(self.bridge.call_log), 3)
        self.assertTrue(self.bridge.was_called("open_app"))
        self.assertTrue(self.bridge.was_called("click"))
        self.assertTrue(self.bridge.was_called("type_text"))
        self.assertEqual(self.bridge.get_call_count("open_app"), 1)
    
    def test_should_fail_mode(self):
        """Test should_fail mode."""
        bridge = MockSystemBridge(should_fail=True)
        
        result = bridge.open_app("App")
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)
    
    def test_reset_call_log(self):
        """Test call log reset."""
        self.bridge.open_app("App")
        self.assertEqual(len(self.bridge.call_log), 1)
        
        self.bridge.reset_call_log()
        self.assertEqual(len(self.bridge.call_log), 0)


class TestFactory(unittest.TestCase):
    """Test factory functions."""
    
    def setUp(self):
        """Reset singleton before each test."""
        reset_system_bridge()
    
    def tearDown(self):
        """Reset singleton after each test."""
        reset_system_bridge()
    
    def test_get_system_bridge_returns_bridge(self):
        """Test get_system_bridge returns a SystemBridge."""
        bridge = get_system_bridge()
        self.assertIsInstance(bridge, SystemBridge)
    
    def test_get_system_bridge_is_singleton(self):
        """Test get_system_bridge returns the same instance."""
        bridge1 = get_system_bridge()
        bridge2 = get_system_bridge()
        self.assertIs(bridge1, bridge2)
    
    def test_create_system_bridge_creates_new_instance(self):
        """Test create_system_bridge always creates new instance."""
        bridge1 = create_system_bridge()
        bridge2 = create_system_bridge()
        self.assertIsNot(bridge1, bridge2)
    
    def test_reset_system_bridge(self):
        """Test reset_system_bridge clears singleton."""
        bridge1 = get_system_bridge()
        reset_system_bridge()
        bridge2 = get_system_bridge()
        # After reset, should get a new instance
        self.assertIsNot(bridge1, bridge2)
    
    @patch('platform.system', return_value='Darwin')
    def test_factory_creates_macos_bridge(self, mock_platform):
        """Test factory creates MacOSBridge on macOS."""
        reset_system_bridge()
        bridge = create_system_bridge()
        self.assertIsInstance(bridge, MacOSBridge)
    
    @patch('platform.system', return_value='Windows')
    def test_factory_creates_windows_bridge(self, mock_platform):
        """Test factory creates WindowsBridge on Windows."""
        reset_system_bridge()
        bridge = create_system_bridge()
        self.assertIsInstance(bridge, WindowsBridge)
    
    @patch('platform.system', return_value='Linux')
    def test_factory_creates_linux_bridge(self, mock_platform):
        """Test factory creates LinuxBridge on Linux."""
        reset_system_bridge()
        bridge = create_system_bridge()
        self.assertIsInstance(bridge, LinuxBridge)


if __name__ == "__main__":
    unittest.main()
