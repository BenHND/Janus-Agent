"""
Tests for PERF-FOUNDATION-001: Vision policy flags
Tests vision_decision_enabled, vision_verification_enabled, trace_screenshots_enabled
"""
import configparser
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.runtime.core import Settings
from janus.runtime.core.contracts import ActionResult, ExecutionResult, Intent


class TestVisionPolicyFlags(unittest.TestCase):
    """Test vision policy flags functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_config_with_vision_flags(self, 
                                       vision_decision_enabled=True,
                                       vision_verification_enabled=True,
                                       trace_screenshots_enabled=False):
        """Helper to create config with specific vision flag values"""
        config_path = os.path.join(self.temp_dir, "test_config.ini")
        config = configparser.ConfigParser()

        config.add_section("features")
        config.set("features", "enable_llm_reasoning", "true")
        config.set("features", "enable_vision", "true")
        config.set("features", "enable_learning", "true")
        config.set("features", "enable_semantic_correction", "true")
        config.set("features", "vision_decision_enabled", str(vision_decision_enabled).lower())
        config.set("features", "vision_verification_enabled", str(vision_verification_enabled).lower())
        config.set("features", "trace_screenshots_enabled", str(trace_screenshots_enabled).lower())

        with open(config_path, "w") as f:
            config.write(f)

        return config_path

    def test_default_vision_flags(self):
        """Test that vision flags have correct defaults"""
        # Create config without vision flags - should use defaults
        config_path = os.path.join(self.temp_dir, "default_config.ini")
        config = configparser.ConfigParser()
        config.add_section("features")
        config.set("features", "enable_vision", "true")

        with open(config_path, "w") as f:
            config.write(f)

        settings = Settings(config_path=config_path)

        # Check defaults
        self.assertTrue(settings.features.vision_decision_enabled)  # Default: true
        self.assertTrue(settings.features.vision_verification_enabled)  # Default: true
        self.assertFalse(settings.features.trace_screenshots_enabled)  # Default: false

    def test_vision_decision_disabled(self):
        """Test vision_decision_enabled = false"""
        config_path = self.create_config_with_vision_flags(
            vision_decision_enabled=False,
            vision_verification_enabled=True,
            trace_screenshots_enabled=False
        )

        settings = Settings(config_path=config_path)

        self.assertFalse(settings.features.vision_decision_enabled)
        self.assertTrue(settings.features.vision_verification_enabled)
        self.assertFalse(settings.features.trace_screenshots_enabled)

    def test_vision_verification_disabled(self):
        """Test vision_verification_enabled = false (FAST mode)"""
        config_path = self.create_config_with_vision_flags(
            vision_decision_enabled=True,
            vision_verification_enabled=False,  # FAST mode
            trace_screenshots_enabled=False
        )

        settings = Settings(config_path=config_path)

        self.assertTrue(settings.features.vision_decision_enabled)
        self.assertFalse(settings.features.vision_verification_enabled)
        self.assertFalse(settings.features.trace_screenshots_enabled)

    def test_trace_screenshots_enabled(self):
        """Test trace_screenshots_enabled = true (AUDIT mode)"""
        config_path = self.create_config_with_vision_flags(
            vision_decision_enabled=True,
            vision_verification_enabled=True,
            trace_screenshots_enabled=True  # AUDIT mode
        )

        settings = Settings(config_path=config_path)

        self.assertTrue(settings.features.vision_decision_enabled)
        self.assertTrue(settings.features.vision_verification_enabled)
        self.assertTrue(settings.features.trace_screenshots_enabled)

    def test_all_vision_flags_disabled(self):
        """Test all vision flags disabled (minimal vision mode)"""
        config_path = self.create_config_with_vision_flags(
            vision_decision_enabled=False,
            vision_verification_enabled=False,
            trace_screenshots_enabled=False
        )

        settings = Settings(config_path=config_path)

        self.assertFalse(settings.features.vision_decision_enabled)
        self.assertFalse(settings.features.vision_verification_enabled)
        self.assertFalse(settings.features.trace_screenshots_enabled)

    def test_vision_service_should_verify_action_logic(self):
        """Test VisionService._should_verify_action logic"""
        from janus.services.vision_service import VisionService

        # Create mock settings
        config_path = self.create_config_with_vision_flags(
            vision_decision_enabled=True,
            vision_verification_enabled=True,
            trace_screenshots_enabled=False
        )
        settings = Settings(config_path=config_path)

        vision_service = VisionService(settings=settings, enabled=True)

        # Test 1: Successful non-risky action - should NOT verify
        action_result = ActionResult(
            action_type="browser.navigate",
            success=True,
            message="Navigated successfully",
            recoverable=False  # Not a recoverable error
        )
        self.assertFalse(vision_service._should_verify_action(action_result))

        # Test 2: Failed action - should verify
        action_result = ActionResult(
            action_type="browser.navigate",
            success=False,
            message="Navigation failed",
            recoverable=False
        )
        self.assertTrue(vision_service._should_verify_action(action_result))

        # Test 3: Recoverable error - should verify
        action_result = ActionResult(
            action_type="browser.navigate",
            success=True,
            message="Success",
            recoverable=True
        )
        self.assertTrue(vision_service._should_verify_action(action_result))

        # Test 4: Risky UI action (ui.click) - should verify
        action_result = ActionResult(
            action_type="ui.click",
            success=True,
            message="Clicked element",
            recoverable=False
        )
        self.assertTrue(vision_service._should_verify_action(action_result))

        # Test 5: Risky UI action (ui.type) - should verify
        action_result = ActionResult(
            action_type="ui.type",
            success=True,
            message="Typed text",
            recoverable=False
        )
        self.assertTrue(vision_service._should_verify_action(action_result))

        # Test 6: Non-risky UI action (ui.wait) - should NOT verify
        action_result = ActionResult(
            action_type="ui.wait",
            success=True,
            message="Waited successfully",
            recoverable=False
        )
        self.assertFalse(vision_service._should_verify_action(action_result))

    def test_vision_verification_respects_flag(self):
        """Test that verify_with_vision respects vision_verification_enabled flag"""
        from janus.services.vision_service import VisionService

        # Test with flag enabled
        config_path = self.create_config_with_vision_flags(
            vision_verification_enabled=True
        )
        settings = Settings(config_path=config_path)
        vision_service = VisionService(settings=settings, enabled=True)

        # Mock vision_runner
        vision_service._vision_runner = MagicMock()
        vision_service._vision_runner.verify_action_result = MagicMock(return_value=True)

        # Create execution result with successful action
        intent = Intent(action="test", confidence=1.0, raw_command="test")
        result = ExecutionResult(intent=intent, success=True, session_id="test", request_id="test")
        result.action_results.append(ActionResult(
            action_type="browser.navigate",
            success=True,
            message="Success",
            recoverable=False  # Not a recoverable error, so shouldn't verify
        ))

        # Should skip verification for successful non-risky action
        vision_service.verify_with_vision(result, "test", None)
        vision_service._vision_runner.verify_action_result.assert_not_called()

    def test_action_coordinator_respects_vision_decision_flag(self):
        """Test that ActionCoordinator respects vision_decision_enabled flag"""
        from janus.runtime.core.action_coordinator import ActionCoordinator

        # Create settings with vision_decision_enabled = False
        config_path = self.create_config_with_vision_flags(
            vision_decision_enabled=False
        )
        settings = Settings(config_path=config_path)

        # Create coordinator with settings
        coordinator = ActionCoordinator(settings=settings)

        # Verify settings are stored
        self.assertFalse(coordinator.settings.features.vision_decision_enabled)
        self.assertTrue(coordinator.settings.features.enable_vision)  # Vision enabled overall


class TestVisionPolicyIntegration(unittest.TestCase):
    """Integration tests for vision policy flags"""

    def test_fast_mode_configuration(self):
        """Test FAST mode configuration (minimal vision)"""
        temp_dir = tempfile.mkdtemp()
        try:
            config_path = os.path.join(temp_dir, "fast_mode.ini")
            config = configparser.ConfigParser()

            config.add_section("features")
            config.set("features", "enable_vision", "true")
            config.set("features", "vision_decision_enabled", "true")
            config.set("features", "vision_verification_enabled", "false")  # FAST: no verification
            config.set("features", "trace_screenshots_enabled", "false")  # FAST: no tracing

            with open(config_path, "w") as f:
                config.write(f)

            settings = Settings(config_path=config_path)

            # FAST mode: Vision for decision, but no verification/trace
            self.assertTrue(settings.features.enable_vision)
            self.assertTrue(settings.features.vision_decision_enabled)
            self.assertFalse(settings.features.vision_verification_enabled)
            self.assertFalse(settings.features.trace_screenshots_enabled)
        finally:
            import shutil
            shutil.rmtree(temp_dir)

    def test_audit_mode_configuration(self):
        """Test AUDIT mode configuration (full vision)"""
        temp_dir = tempfile.mkdtemp()
        try:
            config_path = os.path.join(temp_dir, "audit_mode.ini")
            config = configparser.ConfigParser()

            config.add_section("features")
            config.set("features", "enable_vision", "true")
            config.set("features", "vision_decision_enabled", "true")
            config.set("features", "vision_verification_enabled", "true")  # AUDIT: full verification
            config.set("features", "trace_screenshots_enabled", "true")  # AUDIT: full tracing

            with open(config_path, "w") as f:
                config.write(f)

            settings = Settings(config_path=config_path)

            # AUDIT mode: All vision features enabled
            self.assertTrue(settings.features.enable_vision)
            self.assertTrue(settings.features.vision_decision_enabled)
            self.assertTrue(settings.features.vision_verification_enabled)
            self.assertTrue(settings.features.trace_screenshots_enabled)
        finally:
            import shutil
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    unittest.main()
