"""
Unit tests for Vision Auto-Integration
Tests automatic vision verification in ActionExecutor
"""
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

from PIL import Image

# Mock pyautogui before importing ActionExecutor
sys.modules["pyautogui"] = MagicMock()

from janus.automation.action_executor import ActionExecutor, ExecutionStatus


class TestVisionAutoIntegration(unittest.TestCase):
    """Test cases for vision cognitive auto-integration"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_image = Image.new("RGB", (100, 100), color="white")

    def test_initialization_without_vision(self):
        """Test initialization with vision disabled"""
        executor = ActionExecutor(safety_delay=0.1, enable_vision_verification=False)

        self.assertIsNotNone(executor)
        self.assertFalse(executor.enable_vision_verification)
        self.assertIsNone(executor._vision_engine)

    def test_initialization_with_vision_enabled(self):
        """Test initialization with vision enabled"""
        with patch("janus.vision.vision_cognitive_engine.VisionCognitiveEngine") as mock_engine:
            with patch("janus.vision.screenshot_engine.ScreenshotEngine"):
                with patch("janus.vision.visual_error_detector.VisualErrorDetector"):
                    executor = ActionExecutor(safety_delay=0.1, enable_vision_verification=True)

                    self.assertTrue(executor.enable_vision_verification)

    def test_load_vision_preference(self):
        """Test loading vision preference from config"""
        executor = ActionExecutor(safety_delay=0.1)

        # Should return bool
        preference = executor._load_vision_preference()
        self.assertIsInstance(preference, bool)

    def test_get_vision_info_disabled(self):
        """Test vision info when disabled"""
        executor = ActionExecutor(enable_vision_verification=False)

        info = executor.get_vision_info()

        self.assertIn("enabled", info)
        self.assertFalse(info["enabled"])
        self.assertIn("engine_available", info)
        self.assertIn("models_loaded", info)

    def test_execute_action_without_verification(self):
        """Test action execution without verification"""
        executor = ActionExecutor(enable_vision_verification=False)

        action = {"action": "open_url", "url": "https://example.com"}

        with patch("webbrowser.open"):
            result = executor.execute_action_with_verification(action, verify=False)

        # Should not have verification
        self.assertNotIn("verification", result)
        self.assertEqual(result["status"], ExecutionStatus.SUCCESS.value)

    @patch("janus.vision.visual_error_detector.VisualErrorDetector")
    @patch("janus.vision.screenshot_engine.ScreenshotEngine")
    @patch("janus.vision.vision_cognitive_engine.VisionCognitiveEngine")
    def test_execute_action_with_verification(self, mock_engine, mock_screenshot, mock_detector):
        """Test action execution with verification"""
        # Setup mocks
        mock_vision = MagicMock()
        mock_vision.is_available.return_value = True
        mock_vision.verify_action_result.return_value = {
            "verified": True,
            "confidence": 0.9,
            "reason": "Action verified",
            "method": "blip2",
        }
        mock_engine.return_value = mock_vision

        mock_screenshot_engine = MagicMock()
        mock_screenshot_engine.capture_screen.return_value = self.test_image
        mock_screenshot.return_value = mock_screenshot_engine

        mock_error_detector = MagicMock()
        mock_error_detector.detect.return_value = {"has_error": False}
        mock_detector.return_value = mock_error_detector

        # Create executor with vision enabled
        executor = ActionExecutor(safety_delay=0.1, enable_vision_verification=True)

        action = {"action": "open_url", "url": "https://example.com"}

        with patch("webbrowser.open"):
            result = executor.execute_action_with_verification(action, verify=True)

        # Should have verification
        self.assertIn("verification", result)
        self.assertTrue(result["verification"]["verified"])
        self.assertEqual(result["status"], ExecutionStatus.SUCCESS.value)

    @patch("janus.vision.visual_error_detector.VisualErrorDetector")
    @patch("janus.vision.screenshot_engine.ScreenshotEngine")
    @patch("janus.vision.vision_cognitive_engine.VisionCognitiveEngine")
    def test_verification_detects_error(self, mock_engine, mock_screenshot, mock_detector):
        """Test that verification detects errors"""
        # Setup mocks
        mock_vision = MagicMock()
        mock_vision.is_available.return_value = True
        mock_engine.return_value = mock_vision

        mock_screenshot_engine = MagicMock()
        mock_screenshot_engine.capture_screen.return_value = self.test_image
        mock_screenshot.return_value = mock_screenshot_engine

        # Mock error detection
        mock_error_detector = MagicMock()
        mock_error_detector.detect.return_value = {
            "has_error": True,
            "error_type": "404",
            "confidence": 0.95,
        }
        mock_detector.return_value = mock_error_detector

        # Create executor
        executor = ActionExecutor(safety_delay=0.1, enable_vision_verification=True)

        action = {"action": "open_url", "url": "https://example.com/missing"}

        with patch("webbrowser.open"):
            result = executor.execute_action_with_verification(action, verify=True)

        # Should detect error
        self.assertIn("verification", result)
        self.assertFalse(result["verification"]["verified"])
        self.assertIn("404", result["verification"]["reason"])

        # Status should be PARTIAL due to failed verification
        self.assertEqual(result["status"], ExecutionStatus.PARTIAL.value)

    def test_verify_action_with_vision_disabled(self):
        """Test verification when vision is disabled"""
        executor = ActionExecutor(enable_vision_verification=False)

        action = {"action": "open_url", "url": "https://example.com"}
        result = executor._verify_action_with_vision(action)

        self.assertEqual(result["method"], "none")
        self.assertTrue(result["verified"])
        self.assertEqual(result["confidence"], 0.0)

    @patch("janus.vision.visual_error_detector.VisualErrorDetector")
    @patch("janus.vision.screenshot_engine.ScreenshotEngine")
    @patch("janus.vision.vision_cognitive_engine.VisionCognitiveEngine")
    def test_verification_screenshot_failure(self, mock_engine, mock_screenshot, mock_detector):
        """Test verification when screenshot capture fails"""
        # Setup mocks
        mock_vision = MagicMock()
        mock_vision.is_available.return_value = True
        mock_engine.return_value = mock_vision

        # Mock screenshot failure
        mock_screenshot_engine = MagicMock()
        mock_screenshot_engine.capture_screen.return_value = None
        mock_screenshot.return_value = mock_screenshot_engine

        mock_detector.return_value = MagicMock()

        # Create executor
        executor = ActionExecutor(safety_delay=0.1, enable_vision_verification=True)

        action = {"action": "click", "target": "button"}
        result = executor._verify_action_with_vision(action)

        # Should fallback gracefully
        self.assertEqual(result["method"], "fallback")
        self.assertTrue(result["verified"])
        self.assertIn("Could not capture screenshot", result["reason"])

    @patch("janus.vision.visual_error_detector.VisualErrorDetector")
    @patch("janus.vision.screenshot_engine.ScreenshotEngine")
    @patch("janus.vision.vision_cognitive_engine.VisionCognitiveEngine")
    def test_verification_exception_handling(self, mock_engine, mock_screenshot, mock_detector):
        """Test verification handles exceptions gracefully"""
        # Setup mocks to raise exception
        mock_vision = MagicMock()
        mock_vision.is_available.return_value = True
        mock_vision.verify_action_result.side_effect = Exception("Test error")
        mock_engine.return_value = mock_vision

        mock_screenshot_engine = MagicMock()
        mock_screenshot_engine.capture_screen.return_value = self.test_image
        mock_screenshot.return_value = mock_screenshot_engine

        mock_error_detector = MagicMock()
        mock_error_detector.detect.return_value = {"has_error": False}
        mock_detector.return_value = mock_error_detector

        # Create executor
        executor = ActionExecutor(safety_delay=0.1, enable_vision_verification=True)

        action = {"action": "click"}
        result = executor._verify_action_with_vision(action)

        # Should handle error gracefully
        self.assertEqual(result["method"], "error")
        self.assertTrue(result["verified"])  # Defaults to true on error
        self.assertIn("Verification error", result["reason"])

    def test_execute_plan_standard_behavior(self):
        """Test that execute_plan still works as before"""
        executor = ActionExecutor(safety_delay=0.1, enable_vision_verification=False)

        actions = [{"action": "open_url", "url": "https://example.com"}]

        with patch("webbrowser.open"):
            results = executor.execute_plan(actions)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], ExecutionStatus.SUCCESS.value)

    @patch("janus.vision.visual_error_detector.VisualErrorDetector")
    @patch("janus.vision.screenshot_engine.ScreenshotEngine")
    @patch("janus.vision.vision_cognitive_engine.VisionCognitiveEngine")
    def test_vision_config_passed_to_engine(self, mock_engine, mock_screenshot, mock_detector):
        """Test that vision config is passed to engine"""
        vision_config = {"device": "cpu", "model_type": "blip2", "enable_cache": True}

        executor = ActionExecutor(
            safety_delay=0.1, enable_vision_verification=True, vision_config=vision_config
        )

        # Check that engine was called with correct config
        if executor._vision_engine:
            mock_engine.assert_called_once()
            call_kwargs = mock_engine.call_args[1]
            self.assertEqual(call_kwargs["device"], "cpu")
            self.assertEqual(call_kwargs["model_type"], "blip2")
            self.assertEqual(call_kwargs["enable_cache"], True)


class TestVisionConfigIntegration(unittest.TestCase):
    """Test integration with vision config"""

    def test_load_config_from_wizard(self):
        """Test loading config from wizard"""
        with patch("janus.vision.vision_config_wizard.VisionConfigWizard") as mock_wizard:
            mock_config = Mock()
            mock_config.enabled = True
            mock_config.auto_verify_actions = True

            mock_wizard_instance = Mock()
            mock_wizard_instance.get_config.return_value = mock_config
            mock_wizard.return_value = mock_wizard_instance

            executor = ActionExecutor(safety_delay=0.1)

            # Should have loaded preference
            preference = executor._load_vision_preference()
            self.assertTrue(preference)


if __name__ == "__main__":
    unittest.main()
