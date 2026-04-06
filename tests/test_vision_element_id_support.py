"""
Unit tests for Vision Element ID Support (VISION-FOUNDATION-001)

Tests the end-to-end element_id (SOM) support:
- ElementFinder.find_element_by_id()
- ActionExecutor click/select/extract with element_id
- Integration with SetOfMarksEngine
"""
import unittest
from unittest.mock import MagicMock, Mock, patch

try:
    from janus.vision.element_finder import ElementFinder
    from janus.vision.action_executor import ActionExecutor
    from janus.vision.element_locator import ElementMatch
    from janus.vision.set_of_marks import InteractiveElement, SetOfMarksEngine
    from janus.vision.vision_action_mapper import VisionActionMapper

    VISION_AVAILABLE = True
except ImportError as e:
    VISION_AVAILABLE = False
    print(f"Skipping tests: {e}")


@unittest.skipIf(not VISION_AVAILABLE, "Vision dependencies not available")
class TestElementFinderWithID(unittest.TestCase):
    """Test ElementFinder.find_element_by_id()"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a mock SOM engine
        self.mock_som = Mock(spec=SetOfMarksEngine)
        self.mock_som.is_available.return_value = True

        # Create mock components
        self.mock_screenshot = Mock()
        self.mock_ocr = Mock()
        self.mock_locator = Mock()

    def test_find_element_by_id_success(self):
        """Test finding element by ID successfully"""
        # Create a mock InteractiveElement
        mock_element = InteractiveElement(
            element_id="button_5",
            element_type="button",
            text="Submit",
            bbox=(100, 200, 80, 40),  # x, y, width, height
            confidence=0.95,
        )

        self.mock_som.get_element_by_id.return_value = mock_element

        # Create ElementFinder with SOM engine
        finder = ElementFinder(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            element_locator=self.mock_locator,
            som_engine=self.mock_som,
        )

        # Find element by ID
        result = finder.find_element_by_id("button_5")

        # Verify
        self.assertIsNotNone(result)
        self.assertIsInstance(result, ElementMatch)
        self.assertEqual(result.text, "Submit")
        self.assertEqual(result.x, 100)
        self.assertEqual(result.y, 200)
        self.assertEqual(result.width, 80)
        self.assertEqual(result.height, 40)
        self.assertEqual(result.confidence, 0.95)
        self.assertEqual(result.center_x, 140)  # 100 + 80/2
        self.assertEqual(result.center_y, 220)  # 200 + 40/2

        # Verify SOM engine was called
        self.mock_som.get_element_by_id.assert_called_once_with("button_5")

    def test_find_element_by_id_not_found(self):
        """Test finding element by ID that doesn't exist"""
        self.mock_som.get_element_by_id.return_value = None

        finder = ElementFinder(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            element_locator=self.mock_locator,
            som_engine=self.mock_som,
        )

        result = finder.find_element_by_id("nonexistent_99")

        self.assertIsNone(result)
        self.mock_som.get_element_by_id.assert_called_once_with("nonexistent_99")

    def test_find_element_by_id_no_som_engine(self):
        """Test finding element by ID when SOM engine not available"""
        finder = ElementFinder(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            element_locator=self.mock_locator,
            som_engine=None,  # No SOM engine
        )

        result = finder.find_element_by_id("button_5")

        self.assertIsNone(result)

    def test_find_element_by_id_som_not_available(self):
        """Test finding element by ID when SOM engine exists but not available"""
        self.mock_som.is_available.return_value = False

        finder = ElementFinder(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            element_locator=self.mock_locator,
            som_engine=self.mock_som,
        )

        result = finder.find_element_by_id("button_5")

        self.assertIsNone(result)

    def test_find_element_by_id_with_exception(self):
        """Test finding element by ID when SOM engine raises exception"""
        self.mock_som.get_element_by_id.side_effect = Exception("SOM error")

        finder = ElementFinder(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            element_locator=self.mock_locator,
            som_engine=self.mock_som,
        )

        result = finder.find_element_by_id("button_5")

        self.assertIsNone(result)

    def test_find_element_by_id_no_text(self):
        """Test finding element by ID when element has no text"""
        mock_element = InteractiveElement(
            element_id="icon_3",
            element_type="icon",
            text="",  # No text
            bbox=(50, 100, 30, 30),
            confidence=0.85,
        )

        self.mock_som.get_element_by_id.return_value = mock_element

        finder = ElementFinder(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            element_locator=self.mock_locator,
            som_engine=self.mock_som,
        )

        result = finder.find_element_by_id("icon_3")

        # Should use element_id as text fallback
        self.assertIsNotNone(result)
        self.assertEqual(result.text, "icon_3")


@unittest.skipIf(not VISION_AVAILABLE, "Vision dependencies not available")
class TestActionExecutorWithID(unittest.TestCase):
    """Test ActionExecutor with element_id support"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a mock SOM engine
        self.mock_som = Mock(spec=SetOfMarksEngine)
        self.mock_som.is_available.return_value = True

        # Create mock components
        self.mock_finder = Mock(spec=ElementFinder)
        self.mock_verifier = Mock()

    @patch("pyautogui.click")
    def test_click_viz_with_explicit_element_id(self, mock_click):
        """Test click_viz with explicit element_id parameter"""
        mock_element = ElementMatch(
            text="Submit", x=100, y=200, width=80, height=40, confidence=95.0
        )
        self.mock_finder.find_element_by_id.return_value = mock_element

        executor = ActionExecutor(
            element_finder=self.mock_finder,
            action_verifier=self.mock_verifier,
            enable_auto_retry=False,
        )

        result = executor.click_viz(
            target="button_5", element_id="button_5", verify=False
        )

        # Verify
        self.assertTrue(result.success)
        self.assertEqual(result.element.text, "Submit")

        # Should call find_element_by_id
        self.mock_finder.find_element_by_id.assert_called_once_with("button_5", None)
        self.mock_finder.find_element_by_text.assert_not_called()

        # Should click at center
        mock_click.assert_called_once_with(140, 220)

    @patch("pyautogui.click")
    def test_click_viz_with_id_pattern_in_target(self, mock_click):
        """Test click_viz detecting element_id pattern in target"""
        mock_element = ElementMatch(
            text="Click me", x=50, y=100, width=100, height=50, confidence=90.0
        )
        self.mock_finder.find_element_by_id.return_value = mock_element

        executor = ActionExecutor(
            element_finder=self.mock_finder,
            action_verifier=self.mock_verifier,
            enable_auto_retry=False,
        )

        result = executor.click_viz(target="text_22", verify=False)

        # Verify
        self.assertTrue(result.success)

        # Should try find_element_by_id first because target matches pattern
        self.mock_finder.find_element_by_id.assert_called_once_with("text_22", None)
        self.mock_finder.find_element_by_text.assert_not_called()

        mock_click.assert_called_once_with(100, 125)

    @patch("pyautogui.click")
    def test_click_viz_id_pattern_fallback_to_text(self, mock_click):
        """Test click_viz falls back to text search when ID not found"""
        mock_element = ElementMatch(
            text="text_22", x=50, y=100, width=100, height=50, confidence=90.0
        )

        # ID lookup fails, text search succeeds
        self.mock_finder.find_element_by_id.return_value = None
        self.mock_finder.find_element_by_text.return_value = mock_element

        executor = ActionExecutor(
            element_finder=self.mock_finder,
            action_verifier=self.mock_verifier,
            enable_auto_retry=False,
        )

        result = executor.click_viz(target="text_22", verify=False)

        # Verify
        self.assertTrue(result.success)

        # Should try ID first, then fallback to text
        self.mock_finder.find_element_by_id.assert_called_once_with("text_22", None)
        self.mock_finder.find_element_by_text.assert_called_once()

        mock_click.assert_called_once_with(100, 125)

    @patch("pyautogui.click")
    def test_click_viz_regular_text(self, mock_click):
        """Test click_viz with regular text (not an ID pattern)"""
        mock_element = ElementMatch(
            text="Submit Button", x=100, y=200, width=80, height=40, confidence=95.0
        )
        self.mock_finder.find_element_by_text.return_value = mock_element

        executor = ActionExecutor(
            element_finder=self.mock_finder,
            action_verifier=self.mock_verifier,
            enable_auto_retry=False,
        )

        result = executor.click_viz(target="Submit Button", verify=False)

        # Verify
        self.assertTrue(result.success)

        # Should use find_element_by_text directly
        self.mock_finder.find_element_by_text.assert_called_once()
        self.mock_finder.find_element_by_id.assert_not_called()

        mock_click.assert_called_once_with(140, 220)

    @patch("pyautogui.click")
    def test_select_viz_with_element_id(self, mock_click):
        """Test select_viz with element_id"""
        mock_element = ElementMatch(
            text="Text to select", x=100, y=200, width=120, height=30, confidence=92.0
        )
        self.mock_finder.find_element_by_id.return_value = mock_element

        executor = ActionExecutor(
            element_finder=self.mock_finder,
            action_verifier=self.mock_verifier,
            enable_auto_retry=False,
        )

        result = executor.select_viz(
            target="text_12", element_id="text_12", verify=False
        )

        # Verify
        self.assertTrue(result.success)
        self.mock_finder.find_element_by_id.assert_called_once_with("text_12", None)

        # Triple-click for selection
        mock_click.assert_called_once_with(160, 215, clicks=3)

    def test_extract_viz_with_element_id(self):
        """Test extract_viz with element_id"""
        mock_element = ElementMatch(
            text="Extracted text", x=100, y=200, width=120, height=30, confidence=92.0
        )
        self.mock_finder.find_element_by_id.return_value = mock_element

        executor = ActionExecutor(
            element_finder=self.mock_finder,
            action_verifier=self.mock_verifier,
            enable_auto_retry=False,
        )

        result = executor.extract_viz(target="text_15", element_id="text_15")

        # Verify
        self.assertTrue(result.success)
        self.assertIn("Extracted text", result.message)
        self.mock_finder.find_element_by_id.assert_called_once_with("text_15", None)


@unittest.skipIf(not VISION_AVAILABLE, "Vision dependencies not available")
class TestVisionActionMapperWithID(unittest.TestCase):
    """Test VisionActionMapper with element_id support"""

    @patch("janus.vision.vision_action_mapper.ElementLocator")
    @patch("janus.vision.vision_action_mapper.OCREngine")
    @patch("janus.vision.vision_action_mapper.ScreenshotEngine")
    @patch("pyautogui.click")
    def test_mapper_click_with_som_engine(
        self, mock_click, mock_screenshot_class, mock_ocr_class, mock_locator_class
    ):
        """Test VisionActionMapper with SOM engine integration"""
        # Create mock SOM engine
        mock_som = Mock(spec=SetOfMarksEngine)
        mock_som.is_available.return_value = True

        mock_element_data = InteractiveElement(
            element_id="button_7",
            element_type="button",
            text="Login",
            bbox=(200, 300, 100, 50),
            confidence=0.95,
        )
        mock_som.get_element_by_id.return_value = mock_element_data

        # Create mapper with SOM engine
        mapper = VisionActionMapper(
            som_engine=mock_som, enable_post_action_verification=False
        )

        # Click using element_id
        result = mapper.click_viz(
            target="button_7", element_id="button_7", verify=False
        )

        # Verify
        self.assertTrue(result.success)
        mock_click.assert_called_once_with(250, 325)  # Center of bbox


@unittest.skipIf(not VISION_AVAILABLE, "Vision dependencies not available")
class TestIDPatternDetection(unittest.TestCase):
    """Test element_id pattern detection logic"""

    def test_id_pattern_detection(self):
        """Test various ID patterns are correctly detected"""
        # These should be detected as IDs
        id_patterns = [
            "text_22",
            "button_5",
            "icon_3",
            "link_100",
            "input_1",
        ]

        # These should NOT be detected as IDs
        non_id_patterns = [
            "Submit Button",
            "Click here",
            "text",  # No number
            "button",  # No number
            "22_text",  # Number before underscore (edge case)
        ]

        for pattern in id_patterns:
            # Check if pattern matches: has underscore and last part after underscore has digits
            has_underscore = "_" in pattern
            last_part_has_digit = any(c.isdigit() for c in pattern.split("_")[-1])
            self.assertTrue(
                has_underscore and last_part_has_digit,
                f"Pattern '{pattern}' should be detected as ID",
            )

        for pattern in non_id_patterns:
            has_underscore = "_" in pattern
            last_part_has_digit = (
                any(c.isdigit() for c in pattern.split("_")[-1]) if has_underscore else False
            )
            result = has_underscore and last_part_has_digit
            self.assertFalse(
                result, f"Pattern '{pattern}' should NOT be detected as ID"
            )


if __name__ == "__main__":
    unittest.main()
