"""
Unit tests for Vision Action Mapper
"""
import unittest
from unittest.mock import MagicMock, Mock, call, patch

# Try to import PIL, mock if not available
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

    # Create a mock Image for testing
    class MockImage:
        Image = type("Image", (), {})

    Image = MockImage()

try:
    from janus.vision.element_locator import ElementMatch
    from janus.vision.vision_action_mapper import (
        ActionResult,
        ElementType,
        VisionActionMapper,
        VisualAttributes,
    )

    MAPPER_AVAILABLE = True
except ImportError as e:
    MAPPER_AVAILABLE = False
    # Skip all tests if dependencies not available
    print(f"Skipping tests: {e}")


@unittest.skipIf(not MAPPER_AVAILABLE, "Vision dependencies not available")
class TestVisionActionMapper(unittest.TestCase):
    """Test cases for VisionActionMapper"""

    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_initialization(self, mock_screenshot, mock_ocr_factory, mock_locator):
        """Test mapper initialization"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        mapper = VisionActionMapper(
            enable_auto_scroll=True,
            enable_auto_retry=True,
            max_retries=3,
            enable_post_action_verification=True,
        )

        self.assertTrue(mapper.enable_auto_scroll)
        self.assertTrue(mapper.enable_auto_retry)
        self.assertEqual(mapper.max_retries, 3)
        self.assertTrue(mapper.enable_post_action_verification)

    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_find_element_by_text_direct_match(self, mock_screenshot, mock_ocr_factory, mock_locator_class):
        """Test finding element by text with direct match"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        # Mock element locator
        mock_locator = Mock()
        mock_element = ElementMatch(
            text="Submit Button", x=100, y=200, width=80, height=40, confidence=95.0
        )
        mock_locator.find_element_by_text.return_value = mock_element
        mock_locator_class.return_value = mock_locator

        mapper = VisionActionMapper()
        result = mapper.find_element_by_text("Submit Button")

        self.assertIsNotNone(result)
        self.assertEqual(result.text, "Submit Button")
        self.assertEqual(result.confidence, 95.0)
        mock_locator.find_element_by_text.assert_called_once()

    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_find_element_by_text_not_found(self, mock_screenshot, mock_ocr_factory, mock_locator_class):
        """Test finding element that doesn't exist"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        # Mock element locator
        mock_locator = Mock()
        mock_locator.find_element_by_text.return_value = None
        mock_locator.get_all_elements.return_value = []
        mock_locator_class.return_value = mock_locator

        mapper = VisionActionMapper(enable_auto_scroll=False)
        result = mapper.find_element_by_text("NonExistent")

        self.assertIsNone(result)

    @patch("pyautogui.scroll")
    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_find_element_with_scroll(
        self, mock_screenshot, mock_ocr_factory, mock_locator_class, mock_scroll
    ):
        """Test finding element with automatic scrolling"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        # Mock element locator
        mock_locator = Mock()
        mock_element = ElementMatch(
            text="Footer Link", x=100, y=800, width=100, height=30, confidence=90.0
        )

        # First call returns None, second call (after scroll) returns element
        mock_locator.find_element_by_text.side_effect = [None, mock_element]
        mock_locator_class.return_value = mock_locator

        mapper = VisionActionMapper(enable_auto_scroll=True)
        result = mapper.find_element_by_text("Footer Link", scroll_if_not_found=True)

        self.assertIsNotNone(result)
        self.assertEqual(result.text, "Footer Link")
        mock_scroll.assert_called()

    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_find_element_by_attributes(self, mock_screenshot_class, mock_ocr_factory, mock_locator_class):
        """Test finding element by visual attributes"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        # Mock screenshot
        mock_img = Mock(spec=Image.Image)
        mock_img.size = (1920, 1080)
        mock_screenshot = Mock()
        mock_screenshot.capture_screen.return_value = mock_img
        mock_screenshot_class.return_value = mock_screenshot

        # Mock element locator
        mock_locator = Mock()
        mock_element = ElementMatch(
            text="Button", x=200, y=300, width=100, height=50, confidence=85.0
        )
        mock_locator.get_all_elements.return_value = [mock_element]
        mock_locator_class.return_value = mock_locator

        mapper = VisionActionMapper()
        attributes = VisualAttributes(
            element_type=ElementType.BUTTON, size=(100, 50), confidence_threshold=80.0
        )
        result = mapper.find_element_by_attributes(attributes, scroll_if_not_found=False)

        self.assertIsNotNone(result)
        self.assertEqual(result.text, "Button")

    @patch("pyautogui.click")
    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_click_viz_success(
        self, mock_screenshot_class, mock_ocr_factory, mock_locator_class, mock_click
    ):
        """Test successful vision-based click"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        # Mock screenshot
        mock_img = Mock(spec=Image.Image)
        mock_screenshot = Mock()
        mock_screenshot.capture_screen.return_value = mock_img
        mock_screenshot_class.return_value = mock_screenshot

        # Mock element locator
        mock_locator = Mock()
        mock_element = ElementMatch(text="OK", x=400, y=500, width=80, height=40, confidence=95.0)
        mock_locator.find_element_by_text.return_value = mock_element
        mock_locator_class.return_value = mock_locator

        mapper = VisionActionMapper(enable_post_action_verification=False)
        result = mapper.click_viz("OK", verify=False)

        self.assertTrue(result.success)
        self.assertEqual(result.action, "click_viz")
        self.assertEqual(result.element.text, "OK")
        mock_click.assert_called_once_with(440, 520)  # center coordinates

    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_click_viz_not_found(self, mock_screenshot, mock_ocr_factory, mock_locator_class):
        """Test vision-based click when element not found"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        # Mock element locator
        mock_locator = Mock()
        mock_locator.find_element_by_text.return_value = None
        mock_locator.get_all_elements.return_value = []
        mock_locator_class.return_value = mock_locator

        mapper = VisionActionMapper(enable_auto_retry=False, enable_auto_scroll=False)
        result = mapper.click_viz("NonExistent", verify=False)

        self.assertFalse(result.success)
        self.assertIn("not found", result.error.lower())

    @patch("pyautogui.click")
    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_click_viz_with_retry(
        self, mock_screenshot_class, mock_ocr_factory, mock_locator_class, mock_click
    ):
        """Test vision-based click with retry on failure"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        # Mock screenshot
        mock_img = Mock(spec=Image.Image)
        mock_screenshot = Mock()
        mock_screenshot.capture_screen.return_value = mock_img
        mock_screenshot_class.return_value = mock_screenshot

        # Mock element locator - fails first, succeeds second
        mock_locator = Mock()
        mock_element = ElementMatch(
            text="Retry Button", x=300, y=400, width=100, height=50, confidence=90.0
        )
        mock_locator.find_element_by_text.side_effect = [None, mock_element]
        mock_locator.get_all_elements.return_value = []
        mock_locator_class.return_value = mock_locator

        mapper = VisionActionMapper(enable_auto_retry=True, max_retries=2, enable_auto_scroll=False)
        result = mapper.click_viz("Retry Button", verify=False)

        self.assertTrue(result.success)
        self.assertEqual(result.retry_count, 1)
        mock_click.assert_called_once()

    @patch("pyautogui.click")
    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_select_viz_success(
        self, mock_screenshot_class, mock_ocr_factory, mock_locator_class, mock_click
    ):
        """Test successful vision-based select"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        # Mock screenshot
        mock_img = Mock(spec=Image.Image)
        mock_screenshot = Mock()
        mock_screenshot.capture_screen.return_value = mock_img
        mock_screenshot_class.return_value = mock_screenshot

        # Mock element locator
        mock_locator = Mock()
        mock_element = ElementMatch(
            text="Text to Select", x=100, y=200, width=150, height=30, confidence=92.0
        )
        mock_locator.find_element_by_text.return_value = mock_element
        mock_locator_class.return_value = mock_locator

        mapper = VisionActionMapper(enable_post_action_verification=False)
        result = mapper.select_viz("Text to Select", verify=False)

        self.assertTrue(result.success)
        self.assertEqual(result.action, "select_viz")
        # Triple-click for selection
        mock_click.assert_called_once_with(175, 215, clicks=3)

    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_extract_viz_success(self, mock_screenshot, mock_ocr_factory, mock_locator_class):
        """Test successful vision-based text extraction"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        # Mock element locator
        mock_locator = Mock()
        mock_element = ElementMatch(
            text="Hello World", x=200, y=300, width=100, height=25, confidence=98.0
        )
        mock_locator.find_element_by_text.return_value = mock_element
        mock_locator_class.return_value = mock_locator

        mapper = VisionActionMapper()
        result = mapper.extract_viz("Hello")

        self.assertTrue(result.success)
        self.assertEqual(result.action, "extract_viz")
        self.assertIn("Hello World", result.message)

    @patch("pyautogui.scroll")
    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_scroll_until_viz_success(
        self, mock_screenshot, mock_ocr_factory, mock_locator_class, mock_scroll
    ):
        """Test successful scroll_until_viz action"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        # Mock element locator
        mock_locator = Mock()
        mock_element = ElementMatch(
            text="Footer Link", x=100, y=800, width=100, height=30, confidence=90.0
        )

        # First call returns None, second call (after scroll) returns element
        mock_locator.find_element_by_text.side_effect = [None, mock_element]
        mock_locator_class.return_value = mock_locator

        mapper = VisionActionMapper()
        result = mapper.scroll_until_viz("Footer Link", max_scrolls=5)

        self.assertTrue(result.success)
        self.assertEqual(result.action, "scroll_until_viz")
        self.assertEqual(result.element.text, "Footer Link")
        self.assertEqual(result.retry_count, 1)
        mock_scroll.assert_called()

    @patch("pyautogui.scroll")
    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_scroll_until_viz_not_found(
        self, mock_screenshot, mock_ocr_factory, mock_locator_class, mock_scroll
    ):
        """Test scroll_until_viz when element not found after max scrolls"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        # Mock element locator - always returns None
        mock_locator = Mock()
        mock_locator.find_element_by_text.return_value = None
        mock_locator_class.return_value = mock_locator

        mapper = VisionActionMapper()
        result = mapper.scroll_until_viz("NonExistent", max_scrolls=3)

        self.assertFalse(result.success)
        self.assertEqual(result.action, "scroll_until_viz")
        self.assertIn("not found", result.error.lower())
        self.assertEqual(result.retry_count, 3)
        # Should have scrolled 3 times
        self.assertEqual(mock_scroll.call_count, 3)

    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_bbox_to_screen_coords(self, mock_screenshot, mock_ocr_factory, mock_locator):
        """Test bounding box to screen coordinates conversion"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        mapper = VisionActionMapper()

        # Without offset
        bbox = (100, 200, 50, 30)
        result = mapper.bbox_to_screen_coords(bbox)
        self.assertEqual(result, (100, 200, 50, 30))

        # With offset
        result_with_offset = mapper.bbox_to_screen_coords(bbox, region_offset=(50, 100))
        self.assertEqual(result_with_offset, (150, 300, 50, 30))

    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_get_element_center(self, mock_screenshot, mock_ocr_factory, mock_locator):
        """Test getting center coordinates of bounding box"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        mapper = VisionActionMapper()

        bbox = (100, 200, 80, 40)
        center = mapper.get_element_center(bbox)

        self.assertEqual(center, (140, 220))

    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_stats_tracking(self, mock_screenshot, mock_ocr_factory, mock_locator_class):
        """Test statistics tracking"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        # Mock element locator
        mock_locator = Mock()
        mock_element = ElementMatch(
            text="Button", x=100, y=200, width=80, height=40, confidence=90.0
        )
        mock_locator.find_element_by_text.return_value = mock_element
        mock_locator_class.return_value = mock_locator

        mapper = VisionActionMapper(enable_post_action_verification=False)

        # Perform some actions
        mapper.extract_viz("Button")

        stats = mapper.get_stats()

        self.assertEqual(stats["total_actions"], 1)
        self.assertEqual(stats["successful_actions"], 1)
        self.assertEqual(stats["failed_actions"], 0)
        self.assertGreater(stats["success_rate"], 0.0)

    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_reset_stats(self, mock_screenshot, mock_ocr_factory, mock_locator_class):
        """Test resetting statistics"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        # Mock element locator
        mock_locator = Mock()
        mock_element = ElementMatch(
            text="Button", x=100, y=200, width=80, height=40, confidence=90.0
        )
        mock_locator.find_element_by_text.return_value = mock_element
        mock_locator_class.return_value = mock_locator

        mapper = VisionActionMapper(enable_post_action_verification=False)

        # Perform action
        mapper.extract_viz("Button")

        # Verify stats were recorded
        stats = mapper.get_stats()
        self.assertEqual(stats["total_actions"], 1)

        # Reset stats
        mapper.reset_stats()

        # Verify stats are cleared
        stats = mapper.get_stats()
        self.assertEqual(stats["total_actions"], 0)
        self.assertEqual(stats["successful_actions"], 0)

    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_fuzzy_find_element(self, mock_screenshot, mock_ocr_factory, mock_locator_class):
        """Test fuzzy element finding"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        # Mock element locator
        mock_locator = Mock()
        mock_locator.find_element_by_text.return_value = None

        # Mock elements for fuzzy matching
        mock_element = ElementMatch(
            text="Submit Button", x=100, y=200, width=80, height=40, confidence=85.0
        )
        mock_locator.get_all_elements.return_value = [mock_element]
        mock_locator_class.return_value = mock_locator

        mapper = VisionActionMapper(enable_auto_scroll=False)

        # Should find "Submit Button" when searching for "Submit"
        result = mapper.find_element_by_text("Submit", fuzzy_match=True)

        self.assertIsNotNone(result)
        self.assertEqual(result.text, "Submit Button")

    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_visual_attributes_dataclass(self, mock_screenshot, mock_ocr_factory, mock_locator):
        """Test VisualAttributes dataclass"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        attrs = VisualAttributes(
            element_type=ElementType.BUTTON,
            color=(255, 0, 0),
            size=(100, 50),
            position=(0, 0, 800, 600),
            confidence_threshold=85.0,
        )

        self.assertEqual(attrs.element_type, ElementType.BUTTON)
        self.assertEqual(attrs.color, (255, 0, 0))
        self.assertEqual(attrs.size, (100, 50))
        self.assertEqual(attrs.confidence_threshold, 85.0)

    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.get_ocr_engine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    def test_action_result_dataclass(self, mock_screenshot, mock_ocr_factory, mock_locator):
        """Test ActionResult dataclass"""
        # Mock the factory to return a mock OCR engine
        mock_ocr_factory.return_value = Mock()
        
        element = ElementMatch(text="Test", x=100, y=200, width=50, height=30, confidence=90.0)

        result = ActionResult(
            success=True,
            action="test_action",
            element=element,
            message="Test message",
            retry_count=2,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.action, "test_action")
        self.assertEqual(result.element.text, "Test")
        self.assertEqual(result.retry_count, 2)


if __name__ == "__main__":
    unittest.main()
