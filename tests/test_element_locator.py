"""
Unit tests for Element Locator
"""
import unittest
from unittest.mock import MagicMock, Mock, patch

from PIL import Image

from janus.vision.element_locator import ElementLocator, ElementMatch
from janus.vision.native_ocr_adapter import OCRResult


class TestElementMatch(unittest.TestCase):
    """Test cases for ElementMatch"""

    def test_element_match_initialization(self):
        """Test ElementMatch initialization"""
        match = ElementMatch("Button", 100, 200, 50, 30, 95.0)

        self.assertEqual(match.text, "Button")
        self.assertEqual(match.x, 100)
        self.assertEqual(match.y, 200)
        self.assertEqual(match.width, 50)
        self.assertEqual(match.height, 30)
        self.assertEqual(match.confidence, 95.0)

        # Center should be calculated
        self.assertEqual(match.center_x, 125)  # 100 + 50/2
        self.assertEqual(match.center_y, 215)  # 200 + 30/2

    def test_element_match_to_dict(self):
        """Test ElementMatch to_dict conversion"""
        match = ElementMatch("Submit", 50, 100, 80, 40, 90.0)

        result_dict = match.to_dict()

        self.assertEqual(result_dict["text"], "Submit")
        self.assertEqual(result_dict["x"], 50)
        self.assertEqual(result_dict["y"], 100)
        self.assertEqual(result_dict["center_x"], 90)
        self.assertEqual(result_dict["center_y"], 120)


class TestElementLocator(unittest.TestCase):
    """Test cases for ElementLocator"""

    def setUp(self):
        """Set up test fixtures"""
        with patch("janus.vision.element_locator.ScreenshotEngine"), patch(
            "janus.vision.element_locator.OCREngine"
        ):
            self.locator = ElementLocator()

    @patch("janus.vision.element_locator.ScreenshotEngine")
    @patch("janus.vision.element_locator.OCREngine")
    def test_find_element_by_text(self, mock_ocr_class, mock_screenshot_class):
        """Test finding an element by text"""
        # Mock screenshot engine
        mock_screenshot = Mock()
        mock_image = MagicMock(spec=Image.Image)
        mock_screenshot.capture_screen.return_value = mock_image
        mock_screenshot_class.return_value = mock_screenshot

        # Mock OCR engine
        mock_ocr = Mock()
        ocr_result = OCRResult("Button", 95.0, (100, 200, 50, 30))
        mock_ocr.find_text.return_value = [ocr_result]
        mock_ocr_class.return_value = mock_ocr

        locator = ElementLocator()
        result = locator.find_element_by_text("Button")

        self.assertIsNotNone(result)
        self.assertEqual(result.text, "Button")
        self.assertEqual(result.x, 100)
        self.assertEqual(result.y, 200)

    @patch("janus.vision.element_locator.ScreenshotEngine")
    @patch("janus.vision.element_locator.OCREngine")
    def test_find_element_not_found(self, mock_ocr_class, mock_screenshot_class):
        """Test when element is not found"""
        mock_screenshot = Mock()
        mock_image = MagicMock(spec=Image.Image)
        mock_screenshot.capture_screen.return_value = mock_image
        mock_screenshot_class.return_value = mock_screenshot

        mock_ocr = Mock()
        mock_ocr.find_text.return_value = []
        mock_ocr_class.return_value = mock_ocr

        locator = ElementLocator()
        result = locator.find_element_by_text("NonExistent")

        self.assertIsNone(result)

    @patch("janus.vision.element_locator.ScreenshotEngine")
    @patch("janus.vision.element_locator.OCREngine")
    def test_find_all_elements_by_text(self, mock_ocr_class, mock_screenshot_class):
        """Test finding all elements matching text"""
        mock_screenshot = Mock()
        mock_image = MagicMock(spec=Image.Image)
        mock_screenshot.capture_screen.return_value = mock_image
        mock_screenshot_class.return_value = mock_screenshot

        mock_ocr = Mock()
        ocr_results = [
            OCRResult("Button1", 95.0, (100, 200, 50, 30)),
            OCRResult("Button2", 90.0, (200, 300, 50, 30)),
        ]
        mock_ocr.find_text.return_value = ocr_results
        mock_ocr_class.return_value = mock_ocr

        locator = ElementLocator()
        results = locator.find_all_elements_by_text("Button")

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].text, "Button1")
        self.assertEqual(results[1].text, "Button2")

    @patch("janus.vision.element_locator.ScreenshotEngine")
    @patch("janus.vision.element_locator.OCREngine")
    @patch("pyautogui.click")
    def test_click_element(self, mock_click, mock_ocr_class, mock_screenshot_class):
        """Test clicking an element"""
        mock_screenshot = Mock()
        mock_image = MagicMock(spec=Image.Image)
        mock_screenshot.capture_screen.return_value = mock_image
        mock_screenshot_class.return_value = mock_screenshot

        mock_ocr = Mock()
        ocr_result = OCRResult("Submit", 95.0, (100, 200, 80, 40))
        mock_ocr.find_text.return_value = [ocr_result]
        mock_ocr_class.return_value = mock_ocr

        locator = ElementLocator()
        result = locator.click_element("Submit")

        self.assertEqual(result["status"], "success")
        # Center should be 140, 220 (100+40, 200+20)
        mock_click.assert_called_once_with(140, 220, button="left")

    @patch("janus.vision.element_locator.ScreenshotEngine")
    @patch("janus.vision.element_locator.OCREngine")
    def test_click_element_not_found(self, mock_ocr_class, mock_screenshot_class):
        """Test clicking when element is not found"""
        mock_screenshot = Mock()
        mock_image = MagicMock(spec=Image.Image)
        mock_screenshot.capture_screen.return_value = mock_image
        mock_screenshot_class.return_value = mock_screenshot

        mock_ocr = Mock()
        mock_ocr.find_text.return_value = []
        mock_ocr_class.return_value = mock_ocr

        locator = ElementLocator()
        result = locator.click_element("NonExistent")

        self.assertEqual(result["status"], "failed")
        self.assertIn("not found", result["error"])

    @patch("janus.vision.element_locator.ScreenshotEngine")
    @patch("janus.vision.element_locator.OCREngine")
    @patch("pyautogui.moveTo")
    def test_hover_element(self, mock_moveto, mock_ocr_class, mock_screenshot_class):
        """Test hovering over an element"""
        mock_screenshot = Mock()
        mock_image = MagicMock(spec=Image.Image)
        mock_screenshot.capture_screen.return_value = mock_image
        mock_screenshot_class.return_value = mock_screenshot

        mock_ocr = Mock()
        ocr_result = OCRResult("Link", 95.0, (150, 250, 60, 20))
        mock_ocr.find_text.return_value = [ocr_result]
        mock_ocr_class.return_value = mock_ocr

        locator = ElementLocator()
        result = locator.hover_element("Link")

        self.assertEqual(result["status"], "success")
        # Center should be 180, 260 (150+30, 250+10)
        mock_moveto.assert_called_once_with(180, 260)

    @patch("janus.vision.element_locator.ScreenshotEngine")
    @patch("janus.vision.element_locator.OCREngine")
    def test_get_element_coordinates(self, mock_ocr_class, mock_screenshot_class):
        """Test getting element coordinates"""
        mock_screenshot = Mock()
        mock_image = MagicMock(spec=Image.Image)
        mock_screenshot.capture_screen.return_value = mock_image
        mock_screenshot_class.return_value = mock_screenshot

        mock_ocr = Mock()
        ocr_result = OCRResult("Title", 95.0, (50, 100, 200, 40))
        mock_ocr.find_text.return_value = [ocr_result]
        mock_ocr_class.return_value = mock_ocr

        locator = ElementLocator()
        coords = locator.get_element_coordinates("Title")

        self.assertIsNotNone(coords)
        self.assertEqual(coords["x"], 50)
        self.assertEqual(coords["y"], 100)
        self.assertEqual(coords["center_x"], 150)  # 50 + 200/2
        self.assertEqual(coords["center_y"], 120)  # 100 + 40/2

    @patch("janus.vision.element_locator.ScreenshotEngine")
    @patch("janus.vision.element_locator.OCREngine")
    def test_find_element_with_region(self, mock_ocr_class, mock_screenshot_class):
        """Test finding element in a specific region"""
        mock_screenshot = Mock()
        mock_image = MagicMock(spec=Image.Image)
        mock_screenshot.capture_region.return_value = mock_image
        mock_screenshot_class.return_value = mock_screenshot

        mock_ocr = Mock()
        # OCR returns coordinates relative to region
        ocr_result = OCRResult("Button", 95.0, (10, 20, 50, 30))
        mock_ocr.find_text.return_value = [ocr_result]
        mock_ocr_class.return_value = mock_ocr

        locator = ElementLocator()
        region = (100, 100, 500, 500)
        result = locator.find_element_by_text("Button", region=region)

        # Coordinates should be adjusted for region offset
        self.assertIsNotNone(result)
        self.assertEqual(result.x, 110)  # 10 + 100
        self.assertEqual(result.y, 120)  # 20 + 100

    @patch("janus.vision.element_locator.ScreenshotEngine")
    @patch("janus.vision.element_locator.OCREngine")
    @patch("pyperclip.copy")
    def test_copy_element_text(self, mock_copy, mock_ocr_class, mock_screenshot_class):
        """Test copying element text to clipboard"""
        mock_screenshot = Mock()
        mock_image = MagicMock(spec=Image.Image)
        mock_screenshot.capture_screen.return_value = mock_image
        mock_screenshot_class.return_value = mock_screenshot

        mock_ocr = Mock()
        ocr_result = OCRResult("Important Text", 95.0, (100, 200, 150, 30))
        mock_ocr.find_text.return_value = [ocr_result]
        mock_ocr_class.return_value = mock_ocr

        locator = ElementLocator()
        result = locator.copy_element_text("Important")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["copied_text"], "Important Text")
        mock_copy.assert_called_once_with("Important Text")

    @patch("janus.vision.element_locator.ScreenshotEngine")
    @patch("janus.vision.element_locator.OCREngine")
    def test_get_all_elements(self, mock_ocr_class, mock_screenshot_class):
        """Test getting all elements on screen"""
        mock_screenshot = Mock()
        mock_image = MagicMock(spec=Image.Image)
        mock_screenshot.capture_screen.return_value = mock_image
        mock_screenshot_class.return_value = mock_screenshot

        mock_ocr = Mock()
        ocr_results = [
            OCRResult("Button", 95.0, (100, 200, 50, 30)),
            OCRResult("Link", 90.0, (200, 300, 60, 25)),
            OCRResult("Title", 92.0, (300, 100, 100, 40)),
        ]
        mock_ocr.get_all_text_with_boxes.return_value = ocr_results
        mock_ocr_class.return_value = mock_ocr

        locator = ElementLocator()
        results = locator.get_all_elements()

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].text, "Button")
        self.assertEqual(results[1].text, "Link")
        self.assertEqual(results[2].text, "Title")

    @patch("janus.vision.element_locator.ScreenshotEngine")
    @patch("janus.vision.element_locator.OCREngine")
    def test_min_confidence_threshold(self, mock_ocr_class, mock_screenshot_class):
        """Test that low confidence results are filtered"""
        mock_screenshot = Mock()
        mock_image = MagicMock(spec=Image.Image)
        mock_screenshot.capture_screen.return_value = mock_image
        mock_screenshot_class.return_value = mock_screenshot

        mock_ocr = Mock()
        # One result below default 50% confidence threshold
        ocr_results = [
            OCRResult("LowConf", 40.0, (100, 200, 50, 30)),
            OCRResult("HighConf", 95.0, (200, 300, 50, 30)),
        ]
        mock_ocr.find_text.return_value = ocr_results
        mock_ocr_class.return_value = mock_ocr

        locator = ElementLocator(min_confidence=50.0)
        results = locator.find_all_elements_by_text("test")

        # Only high confidence result should be included
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].text, "HighConf")


if __name__ == "__main__":
    unittest.main()
