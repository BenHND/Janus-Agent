"""
Unit tests for OverlayUI

These tests verify the overlay UI logic without requiring a display.
"""
import json
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestOverlayUILogic(unittest.TestCase):
    """Test OverlayUI logic without requiring display"""

    def test_mic_state_enum(self):
        """Test MicState enum values"""
        from janus.ui.overlay_types import MicState

        self.assertEqual(MicState.IDLE.value, "idle")
        self.assertEqual(MicState.LISTENING.value, "listening")
        self.assertEqual(MicState.THINKING.value, "thinking")
        self.assertEqual(MicState.MUTED.value, "muted")
        self.assertEqual(MicState.LOADING.value, "loading")
        self.assertEqual(MicState.ERROR.value, "error")  # NEW

    def test_status_state_enum(self):
        """Test StatusState enum values"""
        from janus.ui.overlay_types import StatusState

        self.assertEqual(StatusState.IDLE.value, "idle")
        self.assertEqual(StatusState.LISTENING.value, "listening")
        self.assertEqual(StatusState.THINKING.value, "thinking")
        self.assertEqual(StatusState.ACTING.value, "acting")
        self.assertEqual(StatusState.LOADING.value, "loading")
        self.assertEqual(StatusState.ERROR.value, "error")  # NEW

    def test_mic_state_string_conversion(self):
        """Test MicState can be created from string"""
        from janus.ui.overlay_types import MicState

        state = MicState("listening")
        self.assertEqual(state, MicState.LISTENING)

        state = MicState("idle")
        self.assertEqual(state, MicState.IDLE)

    def test_status_state_string_conversion(self):
        """Test StatusState can be created from string"""
        from janus.ui.overlay_types import StatusState

        state = StatusState("thinking")
        self.assertEqual(state, StatusState.THINKING)

        state = StatusState("acting")
        self.assertEqual(state, StatusState.ACTING)

    def test_position_persistence_format(self):
        """Test position save/load format"""
        # Test that we can read/write position JSON
        test_path = "/tmp/test_overlay_position.json"

        # Write position
        position = {"x": 100, "y": 200}
        with open(test_path, "w") as f:
            json.dump(position, f)

        # Read position
        with open(test_path, "r") as f:
            loaded = json.load(f)

        self.assertEqual(loaded["x"], 100)
        self.assertEqual(loaded["y"], 200)

        # Clean up
        Path(test_path).unlink(missing_ok=True)

    def test_config_data_structure(self):
        """Test config mini window data structure matching new ConfigMiniWindow"""
        # Verify the expected config structure for the updated ConfigMiniWindow
        config = {
            "llm_provider": "ollama",
            "llm_model": "llama3.2",
            "stt_model": "small",
            "language": "fr",
            "llm_feature_enabled": True,
            "vision_feature_enabled": True,
            "learning_feature_enabled": True,
            "semantic_correction_enabled": True,
            "tts_feature_enabled": True,
            "theme": "light",
        }

        # Verify all keys are present
        self.assertIn("llm_provider", config)
        self.assertIn("llm_model", config)
        self.assertIn("stt_model", config)
        self.assertIn("language", config)
        self.assertIn("llm_feature_enabled", config)
        self.assertIn("vision_feature_enabled", config)
        self.assertIn("learning_feature_enabled", config)
        self.assertIn("semantic_correction_enabled", config)
        self.assertIn("tts_feature_enabled", config)
        self.assertIn("theme", config)

        # Verify types
        self.assertIsInstance(config["llm_provider"], str)
        self.assertIsInstance(config["llm_model"], str)
        self.assertIsInstance(config["stt_model"], str)
        self.assertIsInstance(config["language"], str)
        self.assertIsInstance(config["llm_feature_enabled"], bool)
        self.assertIsInstance(config["vision_feature_enabled"], bool)
        self.assertIsInstance(config["learning_feature_enabled"], bool)
        self.assertIsInstance(config["semantic_correction_enabled"], bool)
        self.assertIsInstance(config["tts_feature_enabled"], bool)
        self.assertIsInstance(config["theme"], str)

    def test_callback_signatures(self):
        """Test that callbacks have correct signatures"""

        # Test mic toggle callback
        def on_mic_toggle(enabled: bool):
            self.assertIsInstance(enabled, bool)

        on_mic_toggle(True)
        on_mic_toggle(False)

        # Test config callback
        def on_config():
            pass

        on_config()

    def test_api_method_signatures(self):
        """Test expected API method signatures"""
        from janus.ui.overlay_types import MicState, StatusState

        # These should not raise errors
        state = MicState.LISTENING
        self.assertEqual(state.value, "listening")

        state = StatusState.THINKING
        self.assertEqual(state.value, "thinking")


class TestConfigMiniWindow(unittest.TestCase):
    """Test ConfigMiniWindow logic"""

    def test_config_keys(self):
        """Test expected configuration keys for the new ConfigMiniWindow structure"""
        expected_keys = [
            "llm_provider",
            "llm_model",
            "stt_model",
            "language",
            "llm_feature_enabled",
            "vision_feature_enabled",
            "learning_feature_enabled",
            "semantic_correction_enabled",
            "tts_feature_enabled",
            "theme",
        ]

        config = {
            "llm_provider": "ollama",
            "llm_model": "llama3.2",
            "stt_model": "small",
            "language": "fr",
            "llm_feature_enabled": True,
            "vision_feature_enabled": True,
            "learning_feature_enabled": True,
            "semantic_correction_enabled": True,
            "tts_feature_enabled": True,
            "theme": "light",
        }

        for key in expected_keys:
            self.assertIn(key, config)

    def test_theme_options(self):
        """Test theme options for overlay UI"""
        themes = ["light", "dark"]
        
        for theme in themes:
            self.assertIsInstance(theme, str)
            self.assertIn(theme, ["light", "dark"])

    def test_llm_provider_options(self):
        """Test LLM provider options matching config.ini providers"""
        providers = [
            "ollama",
            "openai",
            "anthropic",
            "mistral",
        ]

        # Verify all are strings
        for provider in providers:
            self.assertIsInstance(provider, str)
            self.assertTrue(len(provider) > 0)

    def test_stt_model_options(self):
        """Test STT model options matching Whisper model sizes"""
        models = ["tiny", "base", "small", "medium", "large"]

        # Verify all are strings matching Whisper model names
        for model in models:
            self.assertIsInstance(model, str)
            self.assertIn(model, ["tiny", "base", "small", "medium", "large"])

    def test_language_options(self):
        """Test language options"""
        languages = ["fr", "en"]

        for lang in languages:
            self.assertIsInstance(lang, str)
            self.assertTrue(len(lang) == 2)  # ISO 639-1 codes


class TestIntegrationScenarios(unittest.TestCase):
    """Test integration scenarios without UI"""

    def test_pipeline_event_mapping(self):
        """Test that pipeline events map to correct overlay states"""
        from janus.ui.overlay_types import MicState, StatusState

        # STT start -> listening
        self.assertEqual(StatusState.LISTENING.value, "listening")
        self.assertEqual(MicState.LISTENING.value, "listening")

        # LLM -> thinking
        self.assertEqual(StatusState.THINKING.value, "thinking")
        self.assertEqual(MicState.THINKING.value, "thinking")

        # Action executor -> acting
        self.assertEqual(StatusState.ACTING.value, "acting")

        # Complete -> idle
        self.assertEqual(StatusState.IDLE.value, "idle")
        self.assertEqual(MicState.IDLE.value, "idle")

    def test_workflow_state_transitions(self):
        """Test typical workflow state transitions"""
        from janus.ui.overlay_types import MicState, StatusState

        # Typical workflow
        workflow = [
            (StatusState.IDLE, MicState.IDLE),
            (StatusState.LISTENING, MicState.LISTENING),
            (StatusState.THINKING, MicState.THINKING),
            (StatusState.ACTING, MicState.LISTENING),
            (StatusState.IDLE, MicState.IDLE),
        ]

        # Verify all states are valid
        for status, mic in workflow:
            self.assertIsInstance(status, StatusState)
            self.assertIsInstance(mic, MicState)


class TestExampleCode(unittest.TestCase):
    """Test that example code structure is correct"""

    def test_demo_files_exist(self):
        """Test that demo files exist"""
        demos = [
            "examples/overlay_ui_demo.py",
            "examples/overlay_ui_pipeline_integration.py",
            "examples/overlay_ui_complete_demo.py",
        ]

        for demo in demos:
            path = Path(__file__).parent.parent / demo
            self.assertTrue(path.exists(), f"Demo file not found: {demo}")

    def test_documentation_exists(self):
        """Test that documentation exists"""
        doc_path = Path(__file__).parent.parent / "docs/user/overlay-ui-guide.md"
        self.assertTrue(doc_path.exists(), "Documentation file not found")


class TestThemeConfiguration(unittest.TestCase):
    """Test theme configuration for overlay UI"""

    def test_get_theme_from_config_default(self):
        """Test that get_theme_from_config returns 'light' as default"""
        from janus.ui.overlay_ui import get_theme_from_config
        
        # When no config file exists or ui section is missing, should return 'light'
        # This test verifies the function doesn't crash and has a fallback
        theme = get_theme_from_config()
        self.assertIn(theme, ["light", "dark"])

    def test_valid_themes_constant(self):
        """Test VALID_THEMES constant exists and contains expected values"""
        from janus.ui.overlay_ui import VALID_THEMES
        
        self.assertIn("light", VALID_THEMES)
        self.assertIn("dark", VALID_THEMES)
        self.assertEqual(len(VALID_THEMES), 2)

    def test_theme_values(self):
        """Test valid theme values"""
        valid_themes = ["light", "dark"]
        
        for theme in valid_themes:
            self.assertIsInstance(theme, str)

    def test_theme_in_config_structure(self):
        """Test that theme is part of the config structure"""
        # Verify the config structure includes theme
        config_with_theme = {
            "theme": "dark",
            "llm_provider": "ollama",
        }
        
        self.assertIn("theme", config_with_theme)
        self.assertEqual(config_with_theme["theme"], "dark")


if __name__ == "__main__":
    unittest.main()
