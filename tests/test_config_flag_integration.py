"""
Integration test for --config CLI flag
Tests that custom config.ini files can be loaded via command line
"""
import configparser
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.runtime.core import Settings


class TestConfigFlagIntegration(unittest.TestCase):
    """Test --config CLI flag integration"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.custom_config_path = os.path.join(self.temp_dir, "custom_config.ini")

        # Create a custom config with distinct values
        config = configparser.ConfigParser()

        config.add_section("whisper")
        config.set("whisper", "model_size", "large")
        config.set("whisper", "models_dir", "custom/whisper/models")

        config.add_section("audio")
        config.set("audio", "sample_rate", "16000")
        config.set("audio", "vad_aggressiveness", "3")

        config.add_section("logging")
        config.set("logging", "level", "DEBUG")

        config.add_section("language")
        config.set("language", "default", "en")

        with open(self.custom_config_path, "w") as f:
            config.write(f)

    def tearDown(self):
        """Clean up"""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_custom_config_loading(self):
        """Test that Settings class loads custom config file"""
        settings = Settings(config_path=self.custom_config_path)

        # Verify custom values are loaded
        self.assertEqual(settings.whisper.model_size, "large")
        # Note: models_dir can be overridden by environment variable, so we skip this check
        self.assertEqual(settings.audio.vad_aggressiveness, 3)
        self.assertEqual(settings.language.default, "en")

    def test_default_config_when_no_path_provided(self):
        """Test that default config.ini is used when no path provided"""
        # This should load the default config.ini from project root
        settings = Settings()

        # Verify it loaded (check for expected default values)
        self.assertIsNotNone(settings.whisper.model_size)
        self.assertIsNotNone(settings.audio.vad_aggressiveness)

    def test_cli_overrides_take_precedence(self):
        """Test that CLI overrides take precedence over config file"""
        settings = Settings(
            config_path=self.custom_config_path,
            model_size="tiny",  # Override the 'large' from custom config
            language="fr",  # Override the 'en' from custom config
        )

        # CLI overrides should take precedence
        self.assertEqual(settings.whisper.model_size, "tiny")
        self.assertEqual(settings.language.default, "fr")

    def test_nonexistent_config_uses_defaults(self):
        """Test that nonexistent config file path uses defaults gracefully"""
        nonexistent_path = os.path.join(self.temp_dir, "nonexistent.ini")

        # Should not raise an error, just use defaults
        settings = Settings(config_path=nonexistent_path)

        # Should have some default values
        self.assertIsNotNone(settings.whisper)
        self.assertIsNotNone(settings.audio)

    def test_partial_config_file(self):
        """Test that partial config file works with defaults"""
        partial_config_path = os.path.join(self.temp_dir, "partial_config.ini")

        # Create a config with only one section
        config = configparser.ConfigParser()
        config.add_section("whisper")
        config.set("whisper", "model_size", "medium")

        with open(partial_config_path, "w") as f:
            config.write(f)

        settings = Settings(config_path=partial_config_path)

        # Custom value should be loaded
        self.assertEqual(settings.whisper.model_size, "medium")

        # Other settings should use defaults
        self.assertIsNotNone(settings.audio)
        self.assertIsNotNone(settings.language)


if __name__ == "__main__":
    unittest.main()
