"""
Tests for language enforcement - ensuring only fr/en are supported
"""
import configparser
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Mock missing dependencies before importing Settings
sys.modules["psutil"] = MagicMock()
sys.modules["pyautogui"] = MagicMock()


class TestLanguageEnforcement(unittest.TestCase):
    """Test cases for language enforcement (fr/en only)"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config.ini")

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_config_with_language(self, language: str):
        """Helper to create config.ini with specified language"""
        config = configparser.ConfigParser()
        config["language"] = {"default": language}
        config["whisper"] = {"model_size": "base"}
        config["audio"] = {"sample_rate": "16000"}

        with open(self.config_path, "w") as f:
            config.write(f)

    def test_valid_french_language(self):
        """Test that French (fr) language is accepted"""
        # Import only the settings module to avoid full dependency chain
        from janus.runtime.core.settings import Settings

        self._create_config_with_language("fr")
        settings = Settings(config_path=self.config_path)

        self.assertEqual(settings.language.default, "fr")

    def test_valid_english_language(self):
        """Test that English (en) language is accepted"""
        from janus.runtime.core.settings import Settings

        self._create_config_with_language("en")
        settings = Settings(config_path=self.config_path)

        self.assertEqual(settings.language.default, "en")

    def test_invalid_language_falls_back_to_french(self):
        """Test that invalid languages fall back to French"""
        from janus.runtime.core.settings import Settings

        # Test with Spanish (not supported)
        self._create_config_with_language("es")
        settings = Settings(config_path=self.config_path)

        self.assertEqual(settings.language.default, "fr")

    def test_auto_language_falls_back_to_french(self):
        """Test that 'auto' language falls back to French"""
        from janus.runtime.core.settings import Settings

        self._create_config_with_language("auto")
        settings = Settings(config_path=self.config_path)

        self.assertEqual(settings.language.default, "fr")

    def test_empty_language_falls_back_to_french(self):
        """Test that empty language falls back to French"""
        from janus.runtime.core.settings import Settings

        self._create_config_with_language("")
        settings = Settings(config_path=self.config_path)

        self.assertEqual(settings.language.default, "fr")

    def test_case_insensitive_language(self):
        """Test that language codes are case-insensitive"""
        from janus.runtime.core.settings import Settings

        # Test uppercase
        self._create_config_with_language("EN")
        settings = Settings(config_path=self.config_path)
        self.assertEqual(settings.language.default, "en")

        # Test mixed case
        self._create_config_with_language("Fr")
        settings = Settings(config_path=self.config_path)
        self.assertEqual(settings.language.default, "fr")

    def test_cli_override_valid_language(self):
        """Test that CLI can override config with valid language"""
        from janus.runtime.core.settings import Settings

        self._create_config_with_language("fr")
        settings = Settings(config_path=self.config_path, language="en")

        self.assertEqual(settings.language.default, "en")

    def test_cli_override_invalid_language(self):
        """Test that CLI override with invalid language falls back to French"""
        from janus.runtime.core.settings import Settings

        self._create_config_with_language("fr")
        settings = Settings(config_path=self.config_path, language="de")

        self.assertEqual(settings.language.default, "fr")

    def test_missing_language_section(self):
        """Test that missing language section defaults to French"""
        from janus.runtime.core.settings import Settings

        # Create config without language section
        config = configparser.ConfigParser()
        config["whisper"] = {"model_size": "base"}

        with open(self.config_path, "w") as f:
            config.write(f)

        settings = Settings(config_path=self.config_path)
        self.assertEqual(settings.language.default, "fr")


if __name__ == "__main__":
    unittest.main()
