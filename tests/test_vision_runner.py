"""
Unit tests for Vision Runner
"""
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

# Mock all required modules before importing
sys.modules["pyautogui"] = Mock()
sys.modules["PIL"] = Mock()
sys.modules["PIL.Image"] = Mock()
sys.modules["mss"] = Mock()

from janus.vision.vision_runner import VisionRunner


class TestVisionRunner(unittest.TestCase):
    """Test cases for VisionRunner"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock the vision modules
        self.mock_screenshot_engine = Mock()
        self.mock_ocr_engine = Mock()
        self.mock_element_locator = Mock()

        self.vision_runner = VisionRunner(
            screenshot_engine=self.mock_screenshot_engine,
            ocr_engine=self.mock_ocr_engine,
            element_locator=self.mock_element_locator,
        )

    def test_initialization_with_mocks(self):
        """Test initialization with mock engines"""
        self.assertTrue(self.vision_runner.is_available())
        self.assertIsNotNone(self.vision_runner.screenshot_engine)
        self.assertIsNotNone(self.vision_runner.ocr_engine)
        self.assertIsNotNone(self.vision_runner.element_locator)

    def test_screenshot_full_screen(self):
        """Test capturing full screen screenshot"""
        mock_image = Mock()
        self.mock_screenshot_engine.capture_screen.return_value = mock_image

        result = self.vision_runner.screenshot()

        self.assertEqual(result, mock_image)
        self.mock_screenshot_engine.capture_screen.assert_called_once()

    def test_screenshot_region(self):
        """Test capturing region screenshot"""
        mock_image = Mock()
        self.mock_screenshot_engine.capture_region.return_value = mock_image

        region = (100, 100, 200, 200)
        result = self.vision_runner.screenshot(region=region)

        self.assertEqual(result, mock_image)
        self.mock_screenshot_engine.capture_region.assert_called_once_with(*region)

    def test_ocr_with_image(self):
        """Test OCR with provided image"""
        mock_image = Mock()
        mock_result = {
            "texts": ["Hello", "World"],
            "boxes": [(10, 10, 50, 20), (60, 10, 50, 20)],
            "confidence": [0.9, 0.95],
        }
        self.mock_ocr_engine.extract_text.return_value = mock_result

        result = self.vision_runner.ocr(image=mock_image)

        self.assertEqual(len(result["texts"]), 2)
        self.assertEqual(result["texts"][0], "Hello")
        self.mock_ocr_engine.extract_text.assert_called_once_with(mock_image)

    def test_ocr_without_image(self):
        """Test OCR without image (captures screen)"""
        mock_image = Mock()
        self.mock_screenshot_engine.capture_screen.return_value = mock_image

        mock_result = {
            "texts": ["Test"],
            "boxes": [(10, 10, 50, 20)],
            "confidence": [0.9],
        }
        self.mock_ocr_engine.extract_text.return_value = mock_result

        result = self.vision_runner.ocr()

        self.assertEqual(len(result["texts"]), 1)
        self.mock_screenshot_engine.capture_screen.assert_called_once()
        self.mock_ocr_engine.extract_text.assert_called_once()

    def test_find_text_success(self):
        """Test finding text successfully"""
        bbox = (100, 100, 50, 30)
        self.mock_element_locator.find_element_by_text.return_value = {
            "found": True,
            "bbox": bbox,
        }

        result = self.vision_runner.find_text("Submit")

        self.assertEqual(result, bbox)
        self.mock_element_locator.find_element_by_text.assert_called_once()

    def test_find_text_not_found(self):
        """Test finding text that doesn't exist"""
        self.mock_element_locator.find_element_by_text.return_value = {
            "found": False,
        }

        result = self.vision_runner.find_text("NonExistent")

        self.assertIsNone(result)

    def test_template_match_success(self):
        """Test template matching successfully"""
        bbox = (200, 150, 100, 80)
        self.mock_element_locator.find_element_by_image.return_value = {
            "found": True,
            "bbox": bbox,
        }

        result = self.vision_runner.template_match("/path/to/template.png")

        self.assertEqual(result, bbox)
        self.mock_element_locator.find_element_by_image.assert_called_once()

    def test_template_match_not_found(self):
        """Test template matching failure"""
        self.mock_element_locator.find_element_by_image.return_value = {
            "found": False,
        }

        result = self.vision_runner.template_match("/path/to/template.png")

        self.assertIsNone(result)

    @patch("pyautogui.click")
    def test_click_at_bbox(self, mock_click):
        """Test clicking at bounding box"""
        bbox = (100, 100, 50, 30)

        result = self.vision_runner.click_at_bbox(bbox)

        self.assertTrue(result)
        # Should click at center: (100 + 50//2, 100 + 30//2) = (125, 115)
        mock_click.assert_called_once_with(125, 115)

    @patch("pyautogui.click")
    def test_click_at_bbox_exception(self, mock_click):
        """Test clicking with exception"""
        mock_click.side_effect = Exception("Test error")
        bbox = (100, 100, 50, 30)

        result = self.vision_runner.click_at_bbox(bbox)

        self.assertFalse(result)

    @patch("pyautogui.write")
    @patch("pyautogui.click")
    @patch("time.sleep")
    def test_type_at_bbox(self, mock_sleep, mock_click, mock_write):
        """Test typing at bounding box"""
        bbox = (100, 100, 50, 30)
        text = "Hello World"

        result = self.vision_runner.type_at_bbox(bbox, text)

        self.assertTrue(result)
        mock_click.assert_called_once()
        mock_write.assert_called_once_with(text, interval=0.05)

    def test_get_statistics(self):
        """Test getting statistics"""
        stats = self.vision_runner.get_statistics()

        self.assertIn("available", stats)
        self.assertIn("has_screenshot", stats)
        self.assertIn("has_ocr", stats)
        self.assertIn("has_locator", stats)

        self.assertTrue(stats["available"])
        self.assertTrue(stats["has_screenshot"])
        self.assertTrue(stats["has_ocr"])
        self.assertTrue(stats["has_locator"])


if __name__ == "__main__":
    unittest.main()
