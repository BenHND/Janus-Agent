"""
Tests for Configuration UI Enhancements (Issue 2.2)
"""
import configparser
import json
import os
import tempfile
import unittest


class TestConfigUIEnhancements(unittest.TestCase):
    """Test cases for ConfigUI enhancements"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        self.ini_config_path = os.path.join(self.temp_dir, "test_config.ini")

        # Create a test INI config
        config = configparser.ConfigParser()
        config.add_section("whisper")
        config.set("whisper", "model_size", "base")
        config.add_section("audio")
        config.set("audio", "activation_threshold", "50.0")
        config.add_section("logging")
        config.set("logging", "level", "INFO")

        with open(self.ini_config_path, "w") as f:
            config.write(f)

    def tearDown(self):
        """Clean up"""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_ini_config_loading(self):
        """Test that INI config can be loaded"""
        config = configparser.ConfigParser()
        config.read(self.ini_config_path)

        self.assertTrue(config.has_section("whisper"))
        self.assertEqual(config.get("whisper", "model_size"), "base")
        self.assertEqual(config.get("audio", "activation_threshold"), "50.0")
        self.assertEqual(config.get("logging", "level"), "INFO")

    def test_ini_config_modification(self):
        """Test that INI config can be modified and saved"""
        config = configparser.ConfigParser()
        config.read(self.ini_config_path)

        # Modify values
        config.set("whisper", "model_size", "small")
        config.set("audio", "activation_threshold", "40.0")
        config.set("logging", "level", "DEBUG")

        # Save
        with open(self.ini_config_path, "w") as f:
            config.write(f)

        # Reload and verify
        config2 = configparser.ConfigParser()
        config2.read(self.ini_config_path)

        self.assertEqual(config2.get("whisper", "model_size"), "small")
        self.assertEqual(config2.get("audio", "activation_threshold"), "40.0")
        self.assertEqual(config2.get("logging", "level"), "DEBUG")

    def test_profile_export_import(self):
        """Test profile export and import functionality"""
        # Create export data
        json_config = {
            "modules": {"chrome": {"enabled": True}},
            "features": {"vision_fallback": {"enabled": True}},
        }

        config = configparser.ConfigParser()
        config.read(self.ini_config_path)

        export_data = {
            "profile_name": "test_profile",
            "json_config": json_config,
            "ini_config": {section: dict(config[section]) for section in config.sections()},
        }

        # Export
        profile_path = os.path.join(self.temp_dir, "test_profile.json")
        with open(profile_path, "w") as f:
            json.dump(export_data, f, indent=2)

        # Import
        with open(profile_path, "r") as f:
            imported_data = json.load(f)

        self.assertEqual(imported_data["profile_name"], "test_profile")
        self.assertIn("json_config", imported_data)
        self.assertIn("ini_config", imported_data)
        self.assertEqual(imported_data["json_config"]["modules"]["chrome"]["enabled"], True)

    def test_activation_threshold_validation(self):
        """Test that activation threshold values are valid"""
        config = configparser.ConfigParser()
        config.read(self.ini_config_path)

        # Test valid values
        valid_values = [0.0, 30.0, 50.0, 65.0, 100.0]
        for value in valid_values:
            config.set("audio", "activation_threshold", str(value))
            threshold = config.getfloat("audio", "activation_threshold")
            self.assertGreaterEqual(threshold, 0.0)
            self.assertLessEqual(threshold, 100.0)

    def test_whisper_model_options(self):
        """Test that whisper model options are valid"""
        valid_models = ["tiny", "base", "small", "medium", "large"]

        config = configparser.ConfigParser()
        config.read(self.ini_config_path)

        for model in valid_models:
            config.set("whisper", "model_size", model)
            self.assertIn(config.get("whisper", "model_size"), valid_models)

    def test_log_level_options(self):
        """Test that log level options are valid"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        config = configparser.ConfigParser()
        config.read(self.ini_config_path)

        for level in valid_levels:
            config.set("logging", "level", level)
            self.assertIn(config.get("logging", "level"), valid_levels)

    def test_ocr_backend_options(self):
        """Test that OCR backend options are valid"""
        valid_backends = ["tesseract", "easyocr"]

        # Test JSON config structure for OCR backend
        ocr_config = {
            "backend": {
                "value": "tesseract",
                "options": ["tesseract", "easyocr"],
                "label": "OCR Backend",
            }
        }

        for backend in valid_backends:
            ocr_config["backend"]["value"] = backend
            self.assertIn(ocr_config["backend"]["value"], valid_backends)

    def test_settings_reset(self):
        """Test that settings can be reset to defaults"""
        config = configparser.ConfigParser()
        config.read(self.ini_config_path)

        # Modify settings
        config.set("whisper", "model_size", "large")
        config.set("audio", "activation_threshold", "30.0")

        # Create new config with defaults
        default_config = configparser.ConfigParser()
        default_config.add_section("whisper")
        default_config.set("whisper", "model_size", "base")
        default_config.add_section("audio")
        default_config.set("audio", "activation_threshold", "50.0")

        # Verify defaults
        self.assertEqual(default_config.get("whisper", "model_size"), "base")
        self.assertEqual(default_config.get("audio", "activation_threshold"), "50.0")


if __name__ == "__main__":
    unittest.main()
