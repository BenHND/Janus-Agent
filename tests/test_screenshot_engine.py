"""
Unit tests for Screenshot Engine
"""

import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from janus.vision.screenshot_engine import ScreenshotEngine


class TestScreenshotEngine(unittest.TestCase):
    """Test cases for ScreenshotEngine"""

    def setUp(self):
        """Set up test fixtures"""
        # Create engine with a mock backend
        mock_backend = MagicMock()
        mock_backend.name = "mock"
        mock_backend.get_scale_factor.return_value = 1.0
        mock_backend.get_last_capture_time.return_value = 0.05
        mock_backend.get_screen_size.return_value = (1920, 1080)

        self.mock_backend = mock_backend
        self.engine = ScreenshotEngine(backend=mock_backend)

    def test_capture_screen(self):
        """Test capturing the entire screen"""
        # Mock backend capture
        mock_image = Image.new("RGB", (1920, 1080))
        self.mock_backend.capture_screen.return_value = mock_image

        result = self.engine.capture_screen()

        self.assertIsInstance(result, Image.Image)
        self.mock_backend.capture_screen.assert_called_once()

    def test_capture_screen_with_downsampling(self):
        """Test screen capture with downsampling"""
        # Create engine with max_width
        engine = ScreenshotEngine(backend=self.mock_backend, max_width=800)

        # Mock large image
        large_image = Image.new("RGB", (1920, 1080))
        self.mock_backend.capture_screen.return_value = large_image

        result = engine.capture_screen()

        # Should be downsampled to max_width
        self.assertEqual(result.width, 800)
        self.assertEqual(result.height, 450)  # Maintains aspect ratio

    def test_capture_screen_no_downsampling_when_smaller(self):
        """Test that small images are not upsampled"""
        engine = ScreenshotEngine(backend=self.mock_backend, max_width=2000)

        small_image = Image.new("RGB", (800, 600))
        self.mock_backend.capture_screen.return_value = small_image

        result = engine.capture_screen()

        # Should not be modified
        self.assertEqual(result.size, (800, 600))

    def test_capture_screen_no_downsampling_when_disabled(self):
        """Test capture without downsampling when max_width is None"""
        engine = ScreenshotEngine(backend=self.mock_backend, max_width=None)

        large_image = Image.new("RGB", (3840, 2160))
        self.mock_backend.capture_screen.return_value = large_image

        result = engine.capture_screen()

        # Should not be modified
        self.assertEqual(result.size, (3840, 2160))

    def test_capture_region(self):
        """Test capturing a specific region"""
        mock_image = Image.new("RGB", (300, 400))
        self.mock_backend.capture_region.return_value = mock_image

        x, y, width, height = 100, 200, 300, 400
        result = self.engine.capture_region(x, y, width, height)

        self.assertEqual(result, mock_image)
        self.mock_backend.capture_region.assert_called_once_with(x, y, width, height)

    def test_capture_screen_failure(self):
        """Test handling of screenshot failure"""
        self.mock_backend.capture_screen.side_effect = Exception("Screenshot failed")

        with self.assertRaises(RuntimeError) as context:
            self.engine.capture_screen()

        self.assertIn("Failed to capture screen", str(context.exception))

    def test_get_screen_size(self):
        """Test getting screen size"""
        result = self.engine._get_screen_size()

        self.assertEqual(result["x"], 0)
        self.assertEqual(result["y"], 0)
        self.assertEqual(result["width"], 1920)
        self.assertEqual(result["height"], 1080)
        self.mock_backend.get_screen_size.assert_called_once()

    def test_save_screenshot(self):
        """Test saving a screenshot"""
        mock_image = MagicMock(spec=Image.Image)
        file_path = "/tmp/test_screenshot.png"

        self.engine.save_screenshot(mock_image, file_path)

        mock_image.save.assert_called_once_with(file_path)

    def test_save_screenshot_failure(self):
        """Test handling of save failure"""
        mock_image = MagicMock(spec=Image.Image)
        mock_image.save.side_effect = Exception("Save failed")
        file_path = "/tmp/test_screenshot.png"

        with self.assertRaises(RuntimeError) as context:
            self.engine.save_screenshot(mock_image, file_path)

        self.assertIn("Failed to save screenshot", str(context.exception))

    def test_get_screenshot_bytes(self):
        """Test converting screenshot to bytes"""
        # Create a simple test image
        mock_image = Image.new("RGB", (100, 100), color="red")

        result = self.engine.get_screenshot_bytes(mock_image, format="PNG")

        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)

    def test_capture_window_mac_fallback(self):
        """Test window capture falls back to full screen on error"""
        # Mock platform check
        self.engine.is_mac = True

        # Mock subprocess to fail
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.side_effect = Exception("AppleScript failed")

            # Mock full screen capture
            mock_image = Image.new("RGB", (1920, 1080))
            self.mock_backend.capture_screen.return_value = mock_image

            result_image, result_bounds = self.engine.capture_window("Safari")

            self.assertIsInstance(result_image, Image.Image)
            self.assertEqual(result_bounds["width"], 1920)

    def test_pii_masking_disabled_by_default(self):
        """Test that PII masking is disabled by default"""
        self.assertFalse(self.engine.enable_pii_masking)

    def test_pii_masking_enabled(self):
        """Test enabling PII masking"""
        engine = ScreenshotEngine(backend=self.mock_backend, enable_pii_masking=True)
        self.assertTrue(engine.enable_pii_masking)

    def test_save_screenshot_with_pii_masking_disabled(self):
        """Test saving without PII masking (default)"""
        mock_image = MagicMock(spec=Image.Image)
        file_path = "/tmp/test_screenshot.png"

        self.engine.save_screenshot(mock_image, file_path)

        # Should save the original image directly
        mock_image.save.assert_called_once_with(file_path)

    def test_save_screenshot_with_pii_masking_enabled(self):
        """Test saving with PII masking enabled"""
        engine = ScreenshotEngine(backend=self.mock_backend, enable_pii_masking=True)

        # Create a real image for testing
        mock_image = Image.new("RGB", (100, 100), color="red")
        file_path = "/tmp/test_masked_screenshot.png"

        # Mock the OCR and masker
        with patch.object(engine, "_get_ocr_engine") as mock_get_ocr:
            with patch.object(engine, "_get_pii_masker") as mock_get_masker:
                mock_ocr_engine = MagicMock()
                mock_ocr_engine.get_all_text_with_boxes.return_value = []
                mock_get_ocr.return_value = mock_ocr_engine

                mock_masker = MagicMock()
                mock_masker.mask_pii_in_image.return_value = mock_image
                mock_get_masker.return_value = mock_masker

                engine.save_screenshot(mock_image, file_path)

                # Should call OCR and masker
                mock_get_ocr.assert_called_once()
                mock_get_masker.assert_called_once()
                mock_masker.mask_pii_in_image.assert_called_once()

    def test_save_screenshot_with_override_masking(self):
        """Test overriding PII masking setting"""
        # Engine has masking disabled
        self.assertFalse(self.engine.enable_pii_masking)

        mock_image = Image.new("RGB", (100, 100), color="blue")
        file_path = "/tmp/test_override_screenshot.png"

        # Override to enable masking
        with patch.object(self.engine, "_apply_pii_masking") as mock_apply:
            mock_apply.return_value = mock_image
            self.engine.save_screenshot(mock_image, file_path, mask_pii=True)

            # Should call masking even though engine default is False
            mock_apply.assert_called_once()

    def test_save_screenshot_with_provided_ocr_results(self):
        """Test saving with pre-computed OCR results"""
        engine = ScreenshotEngine(backend=self.mock_backend, enable_pii_masking=True)

        mock_image = Image.new("RGB", (100, 100), color="green")
        file_path = "/tmp/test_ocr_results_screenshot.png"

        # Mock OCR results
        mock_ocr_result = MagicMock()
        mock_ocr_result.text = "test@example.com"
        mock_ocr_result.bbox = (10, 10, 100, 20)
        ocr_results = [mock_ocr_result]

        with patch.object(engine, "_get_pii_masker") as mock_get_masker:
            mock_masker = MagicMock()
            mock_masker.mask_pii_in_image.return_value = mock_image
            mock_get_masker.return_value = mock_masker

            engine.save_screenshot(mock_image, file_path, ocr_results=ocr_results)

            # Should use provided OCR results
            mock_masker.mask_pii_in_image.assert_called_once_with(mock_image, ocr_results)

    def test_get_backend_info(self):
        """Test getting backend information"""
        info = self.engine.get_backend_info()

        self.assertEqual(info["name"], "mock")
        self.assertEqual(info["scale_factor"], 1.0)
        self.assertIn("last_capture_time_ms", info)

    def test_backend_auto_detection(self):
        """Test that backend is auto-detected when not provided"""
        # Create engine without backend parameter
        with patch("janus.vision.screenshot_engine.get_best_backend") as mock_get:
            mock_backend = MagicMock()
            mock_backend.name = "auto"
            mock_backend.get_scale_factor.return_value = 1.0
            mock_get.return_value = mock_backend

            engine = ScreenshotEngine()

            mock_get.assert_called_once()
            self.assertEqual(engine._backend, mock_backend)


if __name__ == "__main__":
    unittest.main()
