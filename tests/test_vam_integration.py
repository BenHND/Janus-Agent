"""
Integration tests for Vision-to-Action Mapping (VAM) with ActionExecutor
Tests the complete flow from ActionExecutor to VisionActionMapper
"""
import unittest
from unittest.mock import MagicMock, Mock, patch

try:
    from janus.automation.action_executor import ActionExecutor, ExecutionStatus
    from janus.vision.element_locator import ElementMatch
    from janus.vision.vision_action_mapper import ActionResult

    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    ActionResult = None  # Define for type checking
    print(f"Skipping VAM integration tests: {e}")


@unittest.skipIf(not IMPORTS_AVAILABLE, "Required dependencies not available")
class TestVAMIntegration(unittest.TestCase):
    """Test VAM integration with ActionExecutor"""

    @patch("janus.automation.action_executor.LightVisionEngine")
    @patch("janus.automation.action_executor.ScreenshotEngine")
    def test_action_executor_has_vision_mapper(self, mock_screenshot, mock_light_vision):
        """Test that ActionExecutor can access vision action mapper"""
        executor = ActionExecutor()

        # Vision action mapper should be lazy-loaded
        self.assertIsNotNone(executor._vision_action_mapper)

        # Access the property to trigger initialization
        mapper = executor.vision_action_mapper

        # Should be initialized (or None if dependencies missing)
        # In test environment, it might be None, but property should work
        self.assertTrue(hasattr(executor, "vision_action_mapper"))

    @patch("janus.automation.action_executor.VisionActionMapper")
    @patch("janus.automation.action_executor.LightVisionEngine")
    @patch("janus.automation.action_executor.ScreenshotEngine")
    def test_click_viz_action(self, mock_screenshot, mock_light_vision, mock_vam_class):
        """Test click_viz action through ActionExecutor"""
        # Mock VisionActionMapper
        mock_vam = Mock()
        mock_element = ElementMatch(
            text="Submit", x=100, y=200, width=80, height=40, confidence=95.0
        )

        # Mock ActionResult
        mock_result = ActionResult(
            success=True,
            action="click_viz",
            element=mock_element,
            message="Clicked on Submit",
            retry_count=0,
        )
        mock_vam.click_viz.return_value = mock_result
        mock_vam_class.return_value = mock_vam

        # Create executor
        executor = ActionExecutor()
        executor._vision_action_mapper = mock_vam

        # Execute click_viz action
        action = {"action": "click_viz", "target": "Submit"}
        result = executor.execute_action(action)

        # Verify
        self.assertEqual(result["status"], ExecutionStatus.SUCCESS.value)
        self.assertEqual(result["action"], "click_viz")
        self.assertIn("element", result)
        mock_vam.click_viz.assert_called_once()

    @patch("janus.automation.action_executor.VisionActionMapper")
    @patch("janus.automation.action_executor.LightVisionEngine")
    @patch("janus.automation.action_executor.ScreenshotEngine")
    def test_select_viz_action(self, mock_screenshot, mock_light_vision, mock_vam_class):
        """Test select_viz action through ActionExecutor"""
        # Mock VisionActionMapper
        mock_vam = Mock()
        mock_element = ElementMatch(
            text="Email Field", x=200, y=300, width=150, height=30, confidence=92.0
        )

        mock_result = ActionResult(
            success=True,
            action="select_viz",
            element=mock_element,
            message="Selected Email Field",
        )
        mock_vam.select_viz.return_value = mock_result
        mock_vam_class.return_value = mock_vam

        executor = ActionExecutor()
        executor._vision_action_mapper = mock_vam

        action = {"action": "select_viz", "target": "Email Field"}
        result = executor.execute_action(action)

        self.assertEqual(result["status"], ExecutionStatus.SUCCESS.value)
        self.assertEqual(result["action"], "select_viz")
        mock_vam.select_viz.assert_called_once()

    @patch("janus.automation.action_executor.VisionActionMapper")
    @patch("janus.automation.action_executor.LightVisionEngine")
    @patch("janus.automation.action_executor.ScreenshotEngine")
    def test_extract_viz_action(self, mock_screenshot, mock_light_vision, mock_vam_class):
        """Test extract_viz action through ActionExecutor"""
        mock_vam = Mock()
        mock_element = ElementMatch(
            text="Error: Invalid input", x=100, y=100, width=200, height=50, confidence=98.0
        )

        mock_result = ActionResult(
            success=True,
            action="extract_viz",
            element=mock_element,
            message="Extracted text: Error: Invalid input",
        )
        mock_vam.extract_viz.return_value = mock_result
        mock_vam_class.return_value = mock_vam

        executor = ActionExecutor()
        executor._vision_action_mapper = mock_vam

        action = {"action": "extract_viz", "target": "Error"}
        result = executor.execute_action(action)

        self.assertEqual(result["status"], ExecutionStatus.SUCCESS.value)
        self.assertEqual(result["action"], "extract_viz")
        self.assertIn("extracted_text", result)
        self.assertEqual(result["extracted_text"], "Error: Invalid input")

    @patch("janus.automation.action_executor.VisionActionMapper")
    @patch("janus.automation.action_executor.LightVisionEngine")
    @patch("janus.automation.action_executor.ScreenshotEngine")
    def test_scroll_until_viz_action(self, mock_screenshot, mock_light_vision, mock_vam_class):
        """Test scroll_until_viz action through ActionExecutor"""
        mock_vam = Mock()
        mock_element = ElementMatch(
            text="Footer", x=100, y=800, width=100, height=30, confidence=90.0
        )

        mock_result = ActionResult(
            success=True,
            action="scroll_until_viz",
            element=mock_element,
            message="Found Footer after 3 scroll(s)",
            retry_count=3,
        )
        mock_vam.scroll_until_viz.return_value = mock_result
        mock_vam_class.return_value = mock_vam

        executor = ActionExecutor()
        executor._vision_action_mapper = mock_vam

        action = {"action": "scroll_until_viz", "target": "Footer", "max_scrolls": 10}
        result = executor.execute_action(action)

        self.assertEqual(result["status"], ExecutionStatus.SUCCESS.value)
        self.assertEqual(result["action"], "scroll_until_viz")
        self.assertEqual(result["scrolls_performed"], 3)

    @patch("janus.automation.action_executor.VisionActionMapper")
    @patch("janus.automation.action_executor.LightVisionEngine")
    @patch("janus.automation.action_executor.ScreenshotEngine")
    def test_click_with_vision_method(self, mock_screenshot, mock_light_vision, mock_vam_class):
        """Test regular click action with method='vision' routes to click_viz"""
        mock_vam = Mock()
        mock_element = ElementMatch(text="OK", x=400, y=500, width=80, height=40, confidence=95.0)

        mock_result = ActionResult(
            success=True,
            action="click_viz",
            element=mock_element,
            message="Clicked on OK",
        )
        mock_vam.click_viz.return_value = mock_result
        mock_vam_class.return_value = mock_vam

        executor = ActionExecutor()
        executor._vision_action_mapper = mock_vam

        # Test with method='vision'
        action = {"action": "click", "target": "OK", "method": "vision"}
        result = executor.execute_action(action)

        self.assertEqual(result["status"], ExecutionStatus.SUCCESS.value)
        mock_vam.click_viz.assert_called_once_with("OK")

    @patch("janus.automation.action_executor.VisionActionMapper")
    @patch("janus.automation.action_executor.LightVisionEngine")
    @patch("janus.automation.action_executor.ScreenshotEngine")
    def test_get_vision_info_includes_vam(self, mock_screenshot, mock_light_vision, mock_vam_class):
        """Test that get_vision_info includes VAM statistics"""
        mock_vam = Mock()
        mock_vam.get_stats.return_value = {
            "total_actions": 10,
            "successful_actions": 9,
            "failed_actions": 1,
            "success_rate": 0.9,
            "scrolls_performed": 5,
        }
        mock_vam_class.return_value = mock_vam

        mock_light = Mock()
        mock_light.is_available.return_value = True
        mock_light.get_stats.return_value = {"verifications": 10}
        mock_light_vision.return_value = mock_light

        executor = ActionExecutor()
        executor._vision_action_mapper = mock_vam

        info = executor.get_vision_info()

        self.assertTrue(info["enabled"])
        self.assertTrue(info["vam_available"])
        self.assertIn("vam_stats", info)
        self.assertEqual(info["vam_stats"]["total_actions"], 10)
        self.assertEqual(info["vam_stats"]["success_rate"], 0.9)

    @patch("janus.automation.action_executor.VisionActionMapper")
    @patch("janus.automation.action_executor.LightVisionEngine")
    @patch("janus.automation.action_executor.ScreenshotEngine")
    def test_vision_action_failure_handling(self, mock_screenshot, mock_light_vision, mock_vam_class):
        """Test proper handling of vision action failures"""
        mock_vam = Mock()

        mock_result = ActionResult(
            success=False,
            action="click_viz",
            message="Element not found",
            error="Element 'NonExistent' not found",
        )
        mock_vam.click_viz.return_value = mock_result
        mock_vam_class.return_value = mock_vam

        executor = ActionExecutor()
        executor._vision_action_mapper = mock_vam

        action = {"action": "click_viz", "target": "NonExistent"}
        result = executor.execute_action(action)

        self.assertEqual(result["status"], ExecutionStatus.FAILED.value)
        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())


if __name__ == "__main__":
    unittest.main()
