"""
Unit tests for ForegroundAppSync - Foreground App Synchronization Layer

Tests the critical functionality that keeps agent's context in sync with OS reality.
"""

import platform
import unittest
from unittest.mock import MagicMock, Mock, patch

from janus.constants import ActionStatus
from janus.platform.os.foreground_app_sync import (
    ForegroundAppSync,
    ensure_frontmost,
    get_active_app,
    wait_until_frontmost,
)


class TestForegroundAppSync(unittest.TestCase):
    """Test cases for ForegroundAppSync class"""

    def setUp(self):
        """Set up test fixtures"""
        self.sync = ForegroundAppSync(
            default_timeout=3.0, poll_interval=0.1, enable_auto_sync=True
        )
        # Mock the applescript_executor property for testing
        self.sync._applescript_executor = Mock()

    def test_initialization(self):
        """Test ForegroundAppSync initialization"""
        # Don't use self.sync which has mocked _applescript_executor in setUp
        fresh_sync = ForegroundAppSync(
            default_timeout=3.0, poll_interval=0.1, enable_auto_sync=True
        )
        self.assertEqual(fresh_sync.default_timeout, 3.0)
        self.assertEqual(fresh_sync.poll_interval, 0.1)
        self.assertTrue(fresh_sync.enable_auto_sync)
        self.assertIsNone(fresh_sync._applescript_executor)  # Should be lazy-loaded

    @patch("platform.system")
    def test_initialization_non_mac(self, mock_platform):
        """Test initialization on non-macOS platform"""
        mock_platform.return_value = "Linux"
        sync = ForegroundAppSync()
        self.assertFalse(sync.is_mac)

    @patch("platform.system", return_value="Darwin")
    def test_get_active_app_success(self, mock_platform):
        """Test successfully getting active app on macOS"""
        # Create sync after patching platform
        sync = ForegroundAppSync()
        sync._applescript_executor = Mock()

        # Mock AppleScript executor
        mock_result = {
            "status": ActionStatus.SUCCESS.value,
            "stdout": "Google Chrome",
            "stderr": "",
        }
        sync._applescript_executor.execute = Mock(return_value=mock_result)

        app = sync.get_active_app()
        self.assertEqual(app, "Google Chrome")

    @patch("platform.system", return_value="Darwin")
    def test_get_active_app_failure(self, mock_platform):
        """Test get_active_app when AppleScript fails"""
        # Create sync after patching platform
        sync = ForegroundAppSync()
        sync._applescript_executor = Mock()

        # Mock failed AppleScript execution
        mock_result = {
            "status": ActionStatus.FAILED.value,
            "stdout": "",
            "stderr": "error",
            "error": "AppleScript execution failed",
        }
        sync._applescript_executor.execute = Mock(return_value=mock_result)

        app = sync.get_active_app()
        self.assertIsNone(app)

    @patch("platform.system")
    def test_get_active_app_non_mac(self, mock_platform):
        """Test get_active_app on non-macOS platform"""
        mock_platform.return_value = "Linux"
        sync = ForegroundAppSync()

        app = sync.get_active_app()
        self.assertIsNone(app)

    @patch("platform.system", return_value="Darwin")
    def test_ensure_frontmost_success(self, mock_platform):
        """Test successfully ensuring app is frontmost"""
        # Create sync after patching platform
        sync = ForegroundAppSync()
        sync._applescript_executor = Mock()

        # Mock AppleScript success for activation
        mock_result = {"status": ActionStatus.SUCCESS.value, "stdout": "", "stderr": ""}
        sync._applescript_executor.execute = Mock(return_value=mock_result)

        # Mock get_active_app to return the target app (simulating success)
        sync.get_active_app = Mock(return_value="Safari")

        success = sync.ensure_frontmost("Safari")
        self.assertTrue(success)

    @patch("platform.system", return_value="Darwin")
    def test_ensure_frontmost_failure(self, mock_platform):
        """Test ensure_frontmost when activation fails"""
        # Create sync after patching platform
        sync = ForegroundAppSync()
        sync._applescript_executor = Mock()

        # Mock AppleScript failure
        mock_result = {
            "status": ActionStatus.FAILED.value,
            "stdout": "",
            "stderr": "error",
            "error": "Failed to activate",
        }
        sync._applescript_executor.execute = Mock(return_value=mock_result)

        success = sync.ensure_frontmost("Safari")
        self.assertFalse(success)

    @patch("platform.system", return_value="Darwin")
    def test_ensure_frontmost_with_mapping(self, mock_platform):
        """Test ensure_frontmost with app name mapping"""
        # Create sync after patching platform
        sync = ForegroundAppSync()
        sync._applescript_executor = Mock()

        # Mock AppleScript success
        mock_result = {"status": ActionStatus.SUCCESS.value, "stdout": "", "stderr": ""}
        sync._applescript_executor.execute = Mock(return_value=mock_result)

        # Mock get_active_app to return mapped name
        sync.get_active_app = Mock(return_value="Google Chrome")

        # Use shorthand name
        success = sync.ensure_frontmost("chrome")
        self.assertTrue(success)

        # Verify mapping was applied
        sync.get_active_app.assert_called()

    @patch("time.sleep")
    @patch("platform.system", return_value="Darwin")
    def test_wait_until_frontmost_success(self, mock_platform, mock_sleep):
        """Test wait_until_frontmost succeeds when app becomes frontmost"""
        # Create sync after patching platform
        sync = ForegroundAppSync()

        # Simulate app becoming frontmost after second check
        # Need enough values for the wait loop
        sync.get_active_app = Mock(side_effect=["Terminal", "Safari"])

        success = sync.wait_until_frontmost("Safari", timeout=1.0)
        self.assertTrue(success)

    @patch("time.sleep")
    @patch("platform.system", return_value="Darwin")
    def test_wait_until_frontmost_timeout(self, mock_platform, mock_sleep):
        """Test wait_until_frontmost timeout when app never becomes frontmost"""
        # Create sync after patching platform
        sync = ForegroundAppSync(poll_interval=0.1)

        # Mock app never becoming frontmost
        sync.get_active_app = Mock(return_value="Terminal")

        # Use a small timeout and let it naturally timeout
        success = sync.wait_until_frontmost("Safari", timeout=0.2)
        self.assertFalse(success)

    @patch("platform.system", return_value="Darwin")
    def test_sync_with_context_no_mismatch(self, mock_platform):
        """Test sync_with_context when apps match"""
        # Create sync after patching platform
        sync = ForegroundAppSync()

        context = {"active_app": "Google Chrome"}
        sync.get_active_app = Mock(return_value="Google Chrome")

        result = sync.sync_with_context(context)

        self.assertFalse(result["synced"])
        self.assertFalse(result["mismatch_detected"])
        self.assertEqual(result["action_taken"], "none")

    @patch("platform.system", return_value="Darwin")
    def test_sync_with_context_initialize(self, mock_platform):
        """Test sync_with_context initializes active_app when not set"""
        # Create sync after patching platform
        sync = ForegroundAppSync()

        context = {}  # No active_app
        sync.get_active_app = Mock(return_value="Safari")

        result = sync.sync_with_context(context)

        self.assertTrue(result["synced"])
        self.assertFalse(result["mismatch_detected"])
        self.assertEqual(result["action_taken"], "initialized")
        self.assertEqual(context["active_app"], "Safari")

    @patch("platform.system", return_value="Darwin")
    def test_sync_with_context_mismatch_forced(self, mock_platform):
        """Test sync_with_context forces context app to foreground on mismatch"""
        # Create sync after patching platform
        sync = ForegroundAppSync()

        context = {"active_app": "Safari"}
        sync.get_active_app = Mock(return_value="Google Chrome")

        # Mock successful force to foreground
        sync.ensure_frontmost = Mock(return_value=True)

        result = sync.sync_with_context(context)

        self.assertTrue(result["synced"])
        self.assertTrue(result["mismatch_detected"])
        self.assertEqual(result["action_taken"], "forced_foreground")
        self.assertEqual(result["old_app"], "Google Chrome")
        self.assertEqual(result["new_app"], "Safari")

        # Verify ensure_frontmost was called
        sync.ensure_frontmost.assert_called_once_with("Safari", timeout=2.0)

    @patch("platform.system", return_value="Darwin")
    def test_sync_with_context_mismatch_updated(self, mock_platform):
        """Test sync_with_context updates context when forcing fails"""
        # Create sync after patching platform
        sync = ForegroundAppSync()

        context = {"active_app": "Safari"}
        sync.get_active_app = Mock(return_value="Google Chrome")

        # Mock failed force to foreground
        sync.ensure_frontmost = Mock(return_value=False)

        result = sync.sync_with_context(context)

        self.assertTrue(result["synced"])
        self.assertTrue(result["mismatch_detected"])
        self.assertEqual(result["action_taken"], "updated_context")
        self.assertEqual(result["old_app"], "Safari")
        self.assertEqual(result["new_app"], "Google Chrome")
        self.assertEqual(context["active_app"], "Google Chrome")

    @patch("platform.system", return_value="Darwin")
    def test_sync_with_context_auto_sync_disabled(self, mock_platform):
        """Test sync_with_context with auto_sync disabled"""
        # Create sync after patching platform
        sync = ForegroundAppSync(enable_auto_sync=False)
        
        context = {"active_app": "Safari"}
        sync.get_active_app = Mock(return_value="Google Chrome")

        result = sync.sync_with_context(context)

        self.assertTrue(result["synced"])
        self.assertTrue(result["mismatch_detected"])
        self.assertEqual(result["action_taken"], "updated_context")
        self.assertEqual(context["active_app"], "Google Chrome")

    @patch("platform.system", return_value="Darwin")
    def test_sync_with_context_detection_failed(self, mock_platform):
        """Test sync_with_context when app detection fails"""
        # Create sync after patching platform
        sync = ForegroundAppSync()

        context = {"active_app": "Safari"}
        sync.get_active_app = Mock(return_value=None)

        result = sync.sync_with_context(context)

        self.assertFalse(result["synced"])
        self.assertFalse(result["mismatch_detected"])
        self.assertEqual(result["action_taken"], "detection_failed")

    def test_map_app_name(self):
        """Test app name mapping"""
        # Test common mappings
        self.assertEqual(self.sync._map_app_name("chrome"), "Google Chrome")
        self.assertEqual(self.sync._map_app_name("vscode"), "Visual Studio Code")
        self.assertEqual(self.sync._map_app_name("vs code"), "Visual Studio Code")
        self.assertEqual(self.sync._map_app_name("safari"), "Safari")
        self.assertEqual(self.sync._map_app_name("terminal"), "Terminal")

        # Test case insensitivity
        self.assertEqual(self.sync._map_app_name("CHROME"), "Google Chrome")

        # Test unmapped names (returned as-is)
        self.assertEqual(self.sync._map_app_name("Custom App"), "Custom App")

    @patch("platform.system", return_value="Darwin")
    def test_sync_with_context_case_insensitive(self, mock_platform):
        """Test sync_with_context is case-insensitive"""
        # Create sync after patching platform
        sync = ForegroundAppSync()

        # Different case but same app
        context = {"active_app": "google chrome"}
        sync.get_active_app = Mock(return_value="Google Chrome")

        result = sync.sync_with_context(context)

        # Should not detect mismatch due to case difference
        self.assertFalse(result["mismatch_detected"])
        self.assertEqual(result["action_taken"], "none")


class TestConvenienceFunctions(unittest.TestCase):
    """Test module-level convenience functions"""

    @patch("janus.os.foreground_app_sync.ForegroundAppSync")
    def test_get_active_app_convenience(self, mock_sync_class):
        """Test get_active_app convenience function"""
        mock_instance = Mock()
        mock_instance.get_active_app.return_value = "Safari"
        mock_sync_class.return_value = mock_instance

        # Clear default instance to force new creation
        import janus.os.foreground_app_sync as fgs

        fgs._default_sync = None

        app = get_active_app()
        self.assertEqual(app, "Safari")

    @patch("janus.os.foreground_app_sync.ForegroundAppSync")
    def test_ensure_frontmost_convenience(self, mock_sync_class):
        """Test ensure_frontmost convenience function"""
        mock_instance = Mock()
        mock_instance.ensure_frontmost.return_value = True
        mock_sync_class.return_value = mock_instance

        # Clear default instance
        import janus.os.foreground_app_sync as fgs

        fgs._default_sync = None

        success = ensure_frontmost("Safari")
        self.assertTrue(success)

    @patch("janus.os.foreground_app_sync.ForegroundAppSync")
    def test_wait_until_frontmost_convenience(self, mock_sync_class):
        """Test wait_until_frontmost convenience function"""
        mock_instance = Mock()
        mock_instance.wait_until_frontmost.return_value = True
        mock_sync_class.return_value = mock_instance

        # Clear default instance
        import janus.os.foreground_app_sync as fgs

        fgs._default_sync = None

        success = wait_until_frontmost("Safari", timeout=5.0)
        self.assertTrue(success)


@unittest.skipIf(platform.system() != "Darwin", "Integration tests require macOS")
class TestForegroundAppSyncIntegration(unittest.TestCase):
    """
    Integration tests for ForegroundAppSync.
    These tests run on macOS only and interact with real apps.
    """

    def setUp(self):
        """Set up integration test fixtures"""
        self.sync = ForegroundAppSync()

    def test_get_active_app_real(self):
        """Test getting real active app (integration test)"""
        app = self.sync.get_active_app()

        # Should return a non-empty string on macOS
        self.assertIsNotNone(app)
        self.assertIsInstance(app, str)
        self.assertGreater(len(app), 0)

    def test_ensure_frontmost_finder_real(self):
        """Test bringing Finder to foreground (integration test)"""
        # Finder should always be available on macOS
        success = self.sync.ensure_frontmost("Finder", timeout=5.0)

        if success:
            # If successful, Finder should now be frontmost
            current_app = self.sync.get_active_app()
            self.assertEqual(current_app, "Finder")

    def test_wait_until_frontmost_current_app_real(self):
        """Test waiting for currently frontmost app (integration test)"""
        current_app = self.sync.get_active_app()

        if current_app:
            # Should immediately succeed since app is already frontmost
            success = self.sync.wait_until_frontmost(current_app, timeout=1.0)
            self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
