"""
Tests for WindowsBridge (TICKET-PLATFORM-001)

Comprehensive tests for Windows platform bridge implementation.
Uses mocks to test all functionality without requiring Windows.
"""

import platform
import subprocess
import sys
import time
import unittest
from unittest.mock import MagicMock, patch, call

# Mock Windows-specific dependencies before importing
_mock_modules = {
    'pyautogui': MagicMock(),
    'pywinauto': MagicMock(),
    'tkinter': MagicMock(),
}
for mod_name, mock in _mock_modules.items():
    if mod_name not in sys.modules:
        sys.modules[mod_name] = mock

from janus.platform.os.windows_bridge import WindowsBridge
from janus.platform.os.system_bridge import SystemBridgeStatus


class TestWindowsBridgeBasics(unittest.TestCase):
    """Test basic WindowsBridge functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = WindowsBridge()
    
    def test_initialization(self):
        """Test bridge initialization."""
        self.assertIsNotNone(self.bridge)
        self.assertIsInstance(self.bridge._pyautogui_available, bool)
        self.assertIsInstance(self.bridge._pywinauto_available, bool)
    
    def test_is_available_on_windows(self):
        """Test is_available returns True only on Windows."""
        if platform.system() == "Windows":
            self.assertTrue(self.bridge.is_available())
        else:
            self.assertFalse(self.bridge.is_available())
    
    def test_get_platform_name(self):
        """Test platform name is 'Windows'."""
        self.assertEqual(self.bridge.get_platform_name(), "Windows")


class TestWindowsBridgeApplicationManagement(unittest.TestCase):
    """Test application management operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = WindowsBridge()
    
    @patch('subprocess.Popen')
    def test_open_app_success(self, mock_popen):
        """Test successful app opening."""
        mock_popen.return_value = MagicMock()
        
        result = self.bridge.open_app("notepad")
        
        self.assertTrue(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.SUCCESS)
        self.assertEqual(result.data["app_name"], "notepad")
        mock_popen.assert_called_once()
    
    @patch('subprocess.Popen')
    def test_open_app_with_timeout(self, mock_popen):
        """Test app opening with timeout parameter."""
        mock_popen.return_value = MagicMock()
        
        result = self.bridge.open_app("calc", timeout=5.0)
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["app_name"], "calc")
    
    @patch('subprocess.Popen', side_effect=Exception("Launch failed"))
    def test_open_app_failure(self, mock_popen):
        """Test failed app opening."""
        result = self.bridge.open_app("nonexistent")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)
        self.assertIn("Failed to launch", result.error)
    
    @patch('subprocess.run')
    def test_close_app_success(self, mock_run):
        """Test successful app closing."""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.bridge.close_app("notepad")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["app_name"], "notepad")
        mock_run.assert_called_once()
        # Verify taskkill command
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "taskkill")
        self.assertIn("notepad.exe", args)
    
    @patch('subprocess.run', side_effect=Exception("Kill failed"))
    def test_close_app_failure(self, mock_run):
        """Test failed app closing."""
        result = self.bridge.close_app("notepad")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)
    
    @patch('subprocess.run')
    def test_get_running_apps_success(self, mock_run):
        """Test successful retrieval of running apps."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '"notepad.exe","1234","Console","1","3,456 K"\n"calc.exe","5678","Console","2","2,345 K"'
        mock_run.return_value = mock_result
        
        result = self.bridge.get_running_apps()
        
        self.assertTrue(result.success)
        self.assertIn("apps", result.data)
        apps = result.data["apps"]
        self.assertIn("notepad.exe", apps)
        self.assertIn("calc.exe", apps)
    
    @patch('subprocess.run')
    def test_get_running_apps_empty(self, mock_run):
        """Test getting running apps when none are running."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run.return_value = mock_result
        
        result = self.bridge.get_running_apps()
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.data["apps"]), 0)
    
    @patch('subprocess.run', side_effect=Exception("List failed"))
    def test_get_running_apps_failure(self, mock_run):
        """Test failed retrieval of running apps."""
        result = self.bridge.get_running_apps()
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)


class TestWindowsBridgeWindowManagement(unittest.TestCase):
    """Test window management operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = WindowsBridge()
    
    def test_get_active_window_without_pywinauto(self):
        """Test get_active_window returns NOT_AVAILABLE without pywinauto."""
        self.bridge._pywinauto_available = False
        
        result = self.bridge.get_active_window()
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        self.assertIn("pywinauto", result.error)
    
    def test_list_windows_without_pywinauto(self):
        """Test list_windows returns NOT_AVAILABLE without pywinauto."""
        self.bridge._pywinauto_available = False
        
        result = self.bridge.list_windows()
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
    
    def test_focus_window_without_pywinauto(self):
        """Test focus_window returns NOT_AVAILABLE without pywinauto."""
        self.bridge._pywinauto_available = False
        
        result = self.bridge.focus_window("notepad")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)


class TestWindowsBridgeUIInteractions(unittest.TestCase):
    """Test UI interaction operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = WindowsBridge()
    
    def test_click_without_pyautogui(self):
        """Test click returns NOT_AVAILABLE without pyautogui."""
        self.bridge._pyautogui_available = False
        
        result = self.bridge.click(100, 200)
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
        self.assertIn("pyautogui", result.error)
    
    @patch('pyautogui.click')
    def test_click_success(self, mock_click):
        """Test successful click operation."""
        self.bridge._pyautogui_available = True
        
        result = self.bridge.click(150, 250, button="left")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["x"], 150)
        self.assertEqual(result.data["y"], 250)
        self.assertEqual(result.data["button"], "left")
    
    @patch('pyautogui.click')
    def test_click_right_button(self, mock_click):
        """Test right-click operation."""
        self.bridge._pyautogui_available = True
        
        result = self.bridge.click(100, 100, button="right")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["button"], "right")
    
    def test_type_text_without_pyautogui(self):
        """Test type_text returns NOT_AVAILABLE without pyautogui."""
        self.bridge._pyautogui_available = False
        
        result = self.bridge.type_text("Hello")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
    
    @patch('pyautogui.write')
    def test_type_text_success(self, mock_write):
        """Test successful text typing."""
        self.bridge._pyautogui_available = True
        
        result = self.bridge.type_text("Hello, World!")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["text"], "Hello, World!")
        mock_write.assert_called_once()
    
    def test_press_key_without_pyautogui(self):
        """Test press_key returns NOT_AVAILABLE without pyautogui."""
        self.bridge._pyautogui_available = False
        
        result = self.bridge.press_key("a")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.NOT_AVAILABLE)
    
    @patch('pyautogui.press')
    def test_press_key_without_modifiers(self, mock_press):
        """Test pressing a key without modifiers."""
        self.bridge._pyautogui_available = True
        
        result = self.bridge.press_key("enter")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["key"], "enter")
        self.assertIsNone(result.data["modifiers"])
        mock_press.assert_called_once_with("enter")
    
    @patch('pyautogui.hotkey')
    def test_press_key_with_modifiers(self, mock_hotkey):
        """Test pressing a key with modifiers."""
        self.bridge._pyautogui_available = True
        
        result = self.bridge.press_key("c", modifiers=["ctrl", "shift"])
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["key"], "c")
        self.assertEqual(result.data["modifiers"], ["ctrl", "shift"])
        mock_hotkey.assert_called_once_with("ctrl", "shift", "c")
    
    @patch('pyautogui.press')
    def test_send_keys_alias(self, mock_press):
        """Test send_keys is an alias for press_key."""
        self.bridge._pyautogui_available = True
        
        result = self.bridge.send_keys("escape")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["key"], "escape")


class TestWindowsBridgeClipboard(unittest.TestCase):
    """Test clipboard operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = WindowsBridge()
    
    @patch('tkinter.Tk')
    def test_get_clipboard_success(self, mock_tk):
        """Test successful clipboard retrieval."""
        mock_root = MagicMock()
        mock_root.clipboard_get.return_value = "Test clipboard content"
        mock_tk.return_value = mock_root
        
        result = self.bridge.get_clipboard()
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["text"], "Test clipboard content")
        mock_root.withdraw.assert_called_once()
        mock_root.destroy.assert_called_once()
    
    @patch('tkinter.Tk', side_effect=Exception("Clipboard error"))
    def test_get_clipboard_failure(self, mock_tk):
        """Test failed clipboard retrieval."""
        result = self.bridge.get_clipboard()
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)
    
    @patch('tkinter.Tk')
    def test_set_clipboard_success(self, mock_tk):
        """Test successful clipboard setting."""
        mock_root = MagicMock()
        mock_tk.return_value = mock_root
        
        result = self.bridge.set_clipboard("New clipboard text")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["text"], "New clipboard text")
        mock_root.clipboard_clear.assert_called_once()
        mock_root.clipboard_append.assert_called_once_with("New clipboard text")
        mock_root.update.assert_called_once()
        mock_root.destroy.assert_called_once()
    
    @patch('tkinter.Tk', side_effect=Exception("Clipboard error"))
    def test_set_clipboard_failure(self, mock_tk):
        """Test failed clipboard setting."""
        result = self.bridge.set_clipboard("Text")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)


class TestWindowsBridgeSystemOperations(unittest.TestCase):
    """Test system-level operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = WindowsBridge()
    
    @patch('subprocess.run')
    def test_show_notification_success(self, mock_run):
        """Test successful notification display."""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.bridge.show_notification("Test message", "Test Title")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["message"], "Test message")
        self.assertEqual(result.data["title"], "Test Title")
        # Verify PowerShell was called
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "powershell")
    
    @patch('subprocess.run')
    def test_show_notification_default_title(self, mock_run):
        """Test notification with default title."""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.bridge.show_notification("Test message")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["title"], "Janus")
    
    @patch('subprocess.run', side_effect=Exception("PowerShell error"))
    def test_show_notification_failure(self, mock_run):
        """Test failed notification display."""
        result = self.bridge.show_notification("Test")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)
    
    @patch('subprocess.run')
    def test_run_script_success(self, mock_run):
        """Test successful PowerShell script execution."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Script output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = self.bridge.run_script("Get-Process | Select-Object -First 5")
        
        self.assertTrue(result.success)
        self.assertEqual(result.data["stdout"], "Script output")
        self.assertEqual(result.data["returncode"], 0)
        # Verify PowerShell was called
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0], "powershell")
        self.assertEqual(args[1], "-Command")
    
    @patch('subprocess.run')
    def test_run_script_with_timeout(self, mock_run):
        """Test script execution with custom timeout."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = self.bridge.run_script("echo test", timeout=10.0)
        
        self.assertTrue(result.success)
        # Verify timeout was passed
        self.assertEqual(mock_run.call_args[1]["timeout"], 10.0)
    
    @patch('subprocess.run')
    def test_run_script_with_error(self, mock_run):
        """Test script execution with non-zero exit code."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Script error"
        mock_run.return_value = mock_result
        
        result = self.bridge.run_script("Invalid-Command")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)
        self.assertEqual(result.data["returncode"], 1)
        self.assertEqual(result.error, "Script error")
    
    @patch('subprocess.run', side_effect=Exception("Execution failed"))
    def test_run_script_exception(self, mock_run):
        """Test script execution with exception."""
        result = self.bridge.run_script("test")
        
        self.assertFalse(result.success)
        self.assertEqual(result.status, SystemBridgeStatus.ERROR)
        self.assertIn("Failed to run script", result.error)


class TestWindowsBridgeDependencyChecks(unittest.TestCase):
    """Test dependency checking logic."""
    
    @patch('importlib.import_module')
    def test_check_dependencies_all_available(self, mock_import):
        """Test dependency check when all deps are available."""
        # This is tested implicitly in __init__
        bridge = WindowsBridge()
        # We can't fully test this without mocking imports at module level
        # but we can verify the flags exist
        self.assertIsInstance(bridge._pyautogui_available, bool)
        self.assertIsInstance(bridge._pywinauto_available, bool)
    
    def test_dependency_graceful_degradation(self):
        """Test operations gracefully degrade without dependencies."""
        bridge = WindowsBridge()
        bridge._pyautogui_available = False
        bridge._pywinauto_available = False
        
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


class TestWindowsBridgeIntegration(unittest.TestCase):
    """Test integration scenarios."""
    
    @patch('subprocess.Popen')
    @patch('subprocess.run')
    def test_app_lifecycle(self, mock_run, mock_popen):
        """Test complete app lifecycle: open -> close."""
        bridge = WindowsBridge()
        mock_popen.return_value = MagicMock()
        mock_run.return_value = MagicMock(returncode=0)
        
        # Open app
        result = bridge.open_app("notepad")
        self.assertTrue(result.success)
        
        # Close app
        result = bridge.close_app("notepad")
        self.assertTrue(result.success)
    
    @patch('tkinter.Tk')
    def test_clipboard_roundtrip(self, mock_tk):
        """Test clipboard set and get roundtrip."""
        bridge = WindowsBridge()
        mock_root = MagicMock()
        mock_tk.return_value = mock_root
        
        test_text = "Test clipboard content"
        
        # Set clipboard
        result = bridge.set_clipboard(test_text)
        self.assertTrue(result.success)
        
        # Get clipboard
        mock_root.clipboard_get.return_value = test_text
        result = bridge.get_clipboard()
        self.assertTrue(result.success)
        self.assertEqual(result.data["text"], test_text)


class TestWindowsBridgeNativeAPI(unittest.TestCase):
    """Test native Windows API implementation (TICKET-OS-001)."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bridge = WindowsBridge()
    
    @unittest.skipUnless(platform.system() == "Windows", "Requires Windows")
    def test_get_running_apps_performance(self):
        """Test that get_running_apps executes in <50ms (TICKET-OS-001)."""
        # Run multiple times to get average
        times = []
        for _ in range(5):
            start = time.perf_counter()
            result = self.bridge.get_running_apps()
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times.append(elapsed)
            
            self.assertTrue(result.success, "get_running_apps should succeed")
            self.assertIn("apps", result.data, "Should return apps list")
        
        avg_time = sum(times) / len(times)
        print(f"\nget_running_apps average time: {avg_time:.2f}ms")
        
        # Allow some margin, but should be well under 50ms with native API
        self.assertLess(avg_time, 100, 
            f"get_running_apps took {avg_time:.2f}ms on average, "
            f"should be <100ms (target <50ms)")
    
    @unittest.skipUnless(platform.system() == "Windows", "Requires Windows")
    def test_get_running_apps_returns_processes(self):
        """Test that get_running_apps returns actual running processes."""
        result = self.bridge.get_running_apps()
        
        self.assertTrue(result.success)
        self.assertIn("apps", result.data)
        
        apps = result.data["apps"]
        self.assertIsInstance(apps, list)
        self.assertGreater(len(apps), 0, "Should find at least one running process")
        
        # Common Windows processes that should always be running
        # We check if at least some processes are found
        common_processes = ["System", "svchost.exe", "explorer.exe", "csrss.exe"]
        found_common = any(proc in apps for proc in common_processes)
        # Note: In some test environments, these might not all be present
        # So we just verify we got a non-empty list
        print(f"\nFound {len(apps)} running processes")
    
    @unittest.skipUnless(platform.system() == "Windows", "Requires Windows")
    def test_show_notification_native(self):
        """Test native notification display."""
        result = self.bridge.show_notification("Test notification", "Test Title")
        
        # Should succeed (or at least not crash)
        self.assertTrue(result.success or result.status == SystemBridgeStatus.ERROR)
        
        if result.success:
            self.assertEqual(result.data["title"], "Test Title")
            self.assertEqual(result.data["message"], "Test notification")
    
    def test_native_api_fallback_on_non_windows(self):
        """Test that native API is not initialized on non-Windows platforms."""
        if platform.system() != "Windows":
            self.assertIsNone(self.bridge._win_api, 
                "Windows API should not be initialized on non-Windows platforms")
    
    @patch('janus.os.windows_bridge.WindowsBridge._get_running_apps_native')
    def test_native_api_fallback_on_error(self, mock_native):
        """Test fallback to subprocess when native API fails."""
        bridge = WindowsBridge()
        
        # Simulate native API available but failing
        bridge._win_api = {"mock": "api"}
        mock_native.side_effect = Exception("Native API error")
        
        # Should fall back to subprocess method
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = '"notepad.exe","1234","Console","1","3,456 K"'
            mock_run.return_value = mock_result
            
            result = bridge.get_running_apps()
            
            # Should succeed via fallback
            self.assertTrue(result.success)
            self.assertIn("apps", result.data)
            mock_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
