"""
Unit tests for Screenshot Backends
VISION-FOUNDATION-002
"""

import platform
import unittest
from unittest.mock import MagicMock, Mock, patch

from PIL import Image

from janus.vision.screenshot_backend import (
    MSSBackend,
    PyAutoGUIBackend,
    ScreenshotBackend,
    get_best_backend,
)


class TestScreenshotBackend(unittest.TestCase):
    """Test cases for ScreenshotBackend base class"""

    def test_abstract_backend_cannot_instantiate(self):
        """Test that abstract backend cannot be instantiated directly"""
        # This should fail since ScreenshotBackend is abstract
        with self.assertRaises(TypeError):
            ScreenshotBackend()

    def test_backend_measure_capture(self):
        """Test capture time measurement"""

        # Create a concrete implementation for testing
        class TestBackend(ScreenshotBackend):
            def capture_screen(self):
                return Image.new("RGB", (100, 100))

            def capture_region(self, x, y, w, h):
                return Image.new("RGB", (w, h))

            def get_screen_size(self):
                return (1920, 1080)

        backend = TestBackend()
        backend.capture_screen()

        # Check that capture time was measured
        self.assertGreater(backend.get_last_capture_time(), 0)
        self.assertLess(backend.get_last_capture_time(), 1.0)  # Should be very fast


class TestMSSBackend(unittest.TestCase):
    """Test cases for MSSBackend"""

    @patch("janus.vision.screenshot_backend.mss")
    def test_mss_backend_initialization(self, mock_mss_module):
        """Test MSSBackend initialization"""
        # Mock mss.mss() constructor
        mock_sct = MagicMock()
        mock_sct.monitors = [
            {},  # Index 0: all monitors
            {"width": 1920, "height": 1080, "left": 0, "top": 0},  # Primary monitor
        ]
        mock_mss_module.mss.return_value = mock_sct

        backend = MSSBackend()

        self.assertEqual(backend.name, "mss")
        self.assertIsNotNone(backend._sct)

    @patch("janus.vision.screenshot_backend.mss")
    def test_mss_capture_screen(self, mock_mss_module):
        """Test screen capture with MSS"""
        # Mock mss screenshot
        mock_sct = MagicMock()
        mock_grab_result = MagicMock()
        mock_grab_result.size = (1920, 1080)
        mock_grab_result.bgra = b"\x00" * (1920 * 1080 * 4)

        mock_sct.monitors = [
            {},
            {"width": 1920, "height": 1080, "left": 0, "top": 0},
        ]
        mock_sct.grab.return_value = mock_grab_result
        mock_mss_module.mss.return_value = mock_sct

        backend = MSSBackend()
        image = backend.capture_screen()

        self.assertIsInstance(image, Image.Image)
        self.assertEqual(image.size, (1920, 1080))

    @patch("janus.vision.screenshot_backend.mss")
    def test_mss_capture_region(self, mock_mss_module):
        """Test region capture with MSS"""
        mock_sct = MagicMock()
        mock_grab_result = MagicMock()
        mock_grab_result.size = (800, 600)
        mock_grab_result.bgra = b"\x00" * (800 * 600 * 4)

        mock_sct.monitors = [{}, {"width": 1920, "height": 1080}]
        mock_sct.grab.return_value = mock_grab_result
        mock_mss_module.mss.return_value = mock_sct

        backend = MSSBackend()
        image = backend.capture_region(100, 100, 800, 600)

        self.assertIsInstance(image, Image.Image)
        self.assertEqual(image.size, (800, 600))

    @patch("janus.vision.screenshot_backend.mss")
    def test_mss_get_screen_size(self, mock_mss_module):
        """Test getting screen size with MSS"""
        mock_sct = MagicMock()
        mock_sct.monitors = [{}, {"width": 2560, "height": 1440}]
        mock_mss_module.mss.return_value = mock_sct

        backend = MSSBackend()
        size = backend.get_screen_size()

        self.assertEqual(size, (2560, 1440))


class TestPyAutoGUIBackend(unittest.TestCase):
    """Test cases for PyAutoGUIBackend"""

    @patch("janus.vision.screenshot_backend.pyautogui")
    def test_pyautogui_backend_initialization(self, mock_pyautogui):
        """Test PyAutoGUIBackend initialization"""
        backend = PyAutoGUIBackend()

        self.assertEqual(backend.name, "pyautogui")
        self.assertEqual(backend.get_scale_factor(), 1.0)

    @patch("janus.vision.screenshot_backend.pyautogui")
    def test_pyautogui_capture_screen(self, mock_pyautogui):
        """Test screen capture with PyAutoGUI"""
        mock_image = Image.new("RGB", (1920, 1080))
        mock_pyautogui.screenshot.return_value = mock_image

        backend = PyAutoGUIBackend()
        image = backend.capture_screen()

        self.assertEqual(image, mock_image)
        mock_pyautogui.screenshot.assert_called_once()

    @patch("janus.vision.screenshot_backend.pyautogui")
    def test_pyautogui_capture_region(self, mock_pyautogui):
        """Test region capture with PyAutoGUI"""
        mock_image = Image.new("RGB", (800, 600))
        mock_pyautogui.screenshot.return_value = mock_image

        backend = PyAutoGUIBackend()
        image = backend.capture_region(100, 100, 800, 600)

        self.assertEqual(image, mock_image)
        mock_pyautogui.screenshot.assert_called_once_with(region=(100, 100, 800, 600))

    @patch("janus.vision.screenshot_backend.pyautogui")
    def test_pyautogui_get_screen_size(self, mock_pyautogui):
        """Test getting screen size with PyAutoGUI"""
        mock_pyautogui.size.return_value = (1920, 1080)

        backend = PyAutoGUIBackend()
        size = backend.get_screen_size()

        self.assertEqual(size, (1920, 1080))


class TestMacOSQuartzBackend(unittest.TestCase):
    """Test cases for MacOSQuartzBackend"""

    @unittest.skipUnless(platform.system() == "Darwin", "macOS only test")
    def test_macos_backend_available_on_mac(self):
        """Test that Quartz backend can be loaded on macOS"""
        try:
            from janus.vision.screenshot_backend import MacOSQuartzBackend

            backend = MacOSQuartzBackend()
            self.assertEqual(backend.name, "macos_quartz")
        except RuntimeError:
            # If Quartz is not available, skip the test
            self.skipTest("Quartz framework not available")


class TestGetBestBackend(unittest.TestCase):
    """Test cases for get_best_backend function"""

    @patch("janus.vision.screenshot_backend.platform.system")
    @patch("janus.vision.screenshot_backend.MacOSQuartzBackend")
    def test_get_best_backend_macos(self, mock_quartz_class, mock_system):
        """Test that macOS gets Quartz backend"""
        mock_system.return_value = "Darwin"
        mock_backend = MagicMock()
        mock_quartz_class.return_value = mock_backend

        backend = get_best_backend()

        self.assertEqual(backend, mock_backend)
        mock_quartz_class.assert_called_once()

    @patch("janus.vision.screenshot_backend.platform.system")
    @patch("janus.vision.screenshot_backend.MSSBackend")
    def test_get_best_backend_windows(self, mock_mss_class, mock_system):
        """Test that Windows gets MSS backend"""
        mock_system.return_value = "Windows"
        mock_backend = MagicMock()
        mock_mss_class.return_value = mock_backend

        backend = get_best_backend()

        self.assertEqual(backend, mock_backend)
        mock_mss_class.assert_called_once()

    @patch("janus.vision.screenshot_backend.platform.system")
    @patch("janus.vision.screenshot_backend.MSSBackend")
    def test_get_best_backend_linux(self, mock_mss_class, mock_system):
        """Test that Linux gets MSS backend"""
        mock_system.return_value = "Linux"
        mock_backend = MagicMock()
        mock_mss_class.return_value = mock_backend

        backend = get_best_backend()

        self.assertEqual(backend, mock_backend)
        mock_mss_class.assert_called_once()

    @patch("janus.vision.screenshot_backend.platform.system")
    @patch("janus.vision.screenshot_backend.MacOSQuartzBackend")
    @patch("janus.vision.screenshot_backend.PyAutoGUIBackend")
    def test_get_best_backend_fallback(
        self, mock_pyautogui_class, mock_quartz_class, mock_system
    ):
        """Test fallback to PyAutoGUI when preferred backend fails"""
        mock_system.return_value = "Darwin"
        # Quartz fails
        mock_quartz_class.side_effect = RuntimeError("Quartz not available")
        # PyAutoGUI succeeds
        mock_backend = MagicMock()
        mock_pyautogui_class.return_value = mock_backend

        backend = get_best_backend()

        self.assertEqual(backend, mock_backend)
        mock_pyautogui_class.assert_called_once()

    @patch("janus.vision.screenshot_backend.platform.system")
    @patch("janus.vision.screenshot_backend.MacOSQuartzBackend")
    @patch("janus.vision.screenshot_backend.MSSBackend")
    @patch("janus.vision.screenshot_backend.PyAutoGUIBackend")
    def test_get_best_backend_all_fail(
        self, mock_pyautogui, mock_mss, mock_quartz, mock_system
    ):
        """Test error when all backends fail"""
        mock_system.return_value = "Darwin"
        mock_quartz.side_effect = RuntimeError("Failed")
        mock_mss.side_effect = RuntimeError("Failed")
        mock_pyautogui.side_effect = RuntimeError("Failed")

        with self.assertRaises(RuntimeError) as context:
            get_best_backend()

        self.assertIn("No screenshot backend available", str(context.exception))


if __name__ == "__main__":
    unittest.main()
