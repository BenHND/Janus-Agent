"""
Tests for Configuration UI (Ticket 6.4)
"""
import json
import os
import tempfile
import unittest

from janus.ui.config_ui import ConfigUI


class TestConfigUI(unittest.TestCase):
    """Test cases for ConfigUI"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary config file
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        self.config_ui = ConfigUI(config_path=self.config_path)

    def tearDown(self):
        """Clean up"""
        # Remove temp files
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        os.rmdir(self.temp_dir)

    def test_initialization(self):
        """Test config UI initialization"""
        self.assertEqual(self.config_ui.config_path, self.config_path)
        self.assertIsInstance(self.config_ui.config, dict)
        self.assertIn("modules", self.config_ui.config)
        self.assertIn("features", self.config_ui.config)

    def test_default_config(self):
        """Test default configuration"""
        config = self.config_ui.config

        # Check modules
        self.assertIn("chrome", config["modules"])
        self.assertIn("vscode", config["modules"])
        self.assertIn("terminal", config["modules"])

        # Check features
        self.assertIn("vision_fallback", config["features"])
        self.assertIn("action_history", config["features"])

        # Check UI settings
        self.assertIn("show_overlay", config["ui"])
        self.assertIn("confirmation_dialogs", config["ui"])

    def test_save_config(self):
        """Test saving configuration"""
        # Modify config
        self.config_ui.config["modules"]["chrome"]["enabled"] = False

        # Save
        success = self.config_ui._save_config()
        self.assertTrue(success)

        # Verify file exists
        self.assertTrue(os.path.exists(self.config_path))

        # Load and verify
        with open(self.config_path, "r") as f:
            saved_config = json.load(f)

        self.assertFalse(saved_config["modules"]["chrome"]["enabled"])

    def test_load_config(self):
        """Test loading existing configuration"""
        # Create config file
        test_config = {"modules": {"chrome": {"enabled": False}, "vscode": {"enabled": True}}}

        with open(self.config_path, "w") as f:
            json.dump(test_config, f)

        # Load config
        config_ui = ConfigUI(config_path=self.config_path)

        # Verify loaded
        self.assertFalse(config_ui.config["modules"]["chrome"]["enabled"])
        self.assertTrue(config_ui.config["modules"]["vscode"]["enabled"])

    def test_is_module_enabled(self):
        """Test checking if module is enabled"""
        # Chrome should be enabled by default
        self.assertTrue(self.config_ui.is_module_enabled("chrome"))

        # Disable chrome
        self.config_ui.config["modules"]["chrome"]["enabled"] = False

        # Should now be disabled
        self.assertFalse(self.config_ui.is_module_enabled("chrome"))

    def test_is_feature_enabled(self):
        """Test checking if feature is enabled"""
        # Vision fallback should be enabled by default
        self.assertTrue(self.config_ui.is_feature_enabled("vision_fallback"))

        # Disable it
        self.config_ui.config["features"]["vision_fallback"]["enabled"] = False

        # Should now be disabled
        self.assertFalse(self.config_ui.is_feature_enabled("vision_fallback"))

    def test_get_ui_setting(self):
        """Test getting UI settings"""
        # Boolean setting
        show_overlay = self.config_ui.get_ui_setting("show_overlay")
        self.assertIsInstance(show_overlay, bool)

        # Value setting
        overlay_position = self.config_ui.get_ui_setting("overlay_position")
        self.assertIn(overlay_position, ["top-right", "top-left", "bottom-right", "bottom-left"])

    def test_get_config(self):
        """Test getting full configuration"""
        config = self.config_ui.get_config()

        self.assertIsInstance(config, dict)
        self.assertIn("modules", config)
        self.assertIn("features", config)
        self.assertIn("ui", config)

    def test_save_callback(self):
        """Test save callback"""
        callback_called = [False]
        saved_config = [None]

        def callback(config):
            callback_called[0] = True
            saved_config[0] = config

        config_ui = ConfigUI(config_path=self.config_path, on_save=callback)
        config_ui._save_config()

        self.assertTrue(callback_called[0])
        self.assertIsNotNone(saved_config[0])

    def test_module_list(self):
        """Test that all expected modules are in config"""
        expected_modules = ["chrome", "vscode", "terminal", "finder", "slack"]

        for module in expected_modules:
            self.assertIn(module, self.config_ui.config["modules"])

    def test_feature_list(self):
        """Test that all expected features are in config"""
        expected_features = [
            "vision_fallback",
            "llm_integration",
            "action_history",
            "undo_redo",
            "workflow_persistence",
        ]

        for feature in expected_features:
            self.assertIn(feature, self.config_ui.config["features"])


if __name__ == "__main__":
    unittest.main()
