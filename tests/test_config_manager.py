"""
Tests for Configuration Manager (Ticket 10.2)
"""
import os
import tempfile
import unittest

from janus.ui.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager"""

    def setUp(self):
        """Set up test fixtures"""
        # Use temporary file for testing
        self.temp_config = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        self.temp_config.close()
        self.config_path = self.temp_config.name
        self.manager = ConfigManager(config_path=self.config_path, auto_save=False)

    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.config_path):
            os.unlink(self.config_path)

    def test_initialization(self):
        """Test manager initialization"""
        self.assertIsNotNone(self.manager.config)
        self.assertIn("modules", self.manager.config)
        self.assertIn("features", self.manager.config)
        self.assertIn("ui", self.manager.config)

    def test_save_and_load(self):
        """Test saving and loading configuration"""
        # Modify configuration
        self.manager.enable_module("chrome")
        self.assertTrue(self.manager.save())

        # Create new manager with same config file
        new_manager = ConfigManager(config_path=self.config_path)
        self.assertTrue(new_manager.is_module_enabled("chrome"))

    def test_module_enable_disable(self):
        """Test enabling and disabling modules"""
        # Enable module
        self.assertTrue(self.manager.enable_module("chrome"))
        self.assertTrue(self.manager.is_module_enabled("chrome"))

        # Disable module
        self.assertTrue(self.manager.disable_module("chrome"))
        self.assertFalse(self.manager.is_module_enabled("chrome"))

    def test_set_module_state(self):
        """Test setting module state directly"""
        self.assertTrue(self.manager.set_module_state("vscode", True))
        self.assertTrue(self.manager.is_module_enabled("vscode"))

        self.assertTrue(self.manager.set_module_state("vscode", False))
        self.assertFalse(self.manager.is_module_enabled("vscode"))

    def test_get_enabled_modules(self):
        """Test getting list of enabled modules"""
        self.manager.enable_module("chrome")
        self.manager.enable_module("vscode")
        self.manager.disable_module("terminal")

        enabled = self.manager.get_enabled_modules()
        self.assertIn("chrome", enabled)
        self.assertIn("vscode", enabled)
        self.assertNotIn("terminal", enabled)

    def test_feature_enable_disable(self):
        """Test enabling and disabling features"""
        self.assertTrue(self.manager.enable_feature("vision_fallback"))
        self.assertTrue(self.manager.is_feature_enabled("vision_fallback"))

        self.assertTrue(self.manager.disable_feature("vision_fallback"))
        self.assertFalse(self.manager.is_feature_enabled("vision_fallback"))

    def test_set_feature_state(self):
        """Test setting feature state directly"""
        self.assertTrue(self.manager.set_feature_state("llm_integration", True))
        self.assertTrue(self.manager.is_feature_enabled("llm_integration"))

        self.assertTrue(self.manager.set_feature_state("llm_integration", False))
        self.assertFalse(self.manager.is_feature_enabled("llm_integration"))

    def test_get_setting(self):
        """Test getting setting values"""
        # Test with existing setting
        position = self.manager.get_setting("ui", "overlay_position")
        self.assertIsNotNone(position)

        # Test with default value
        nonexistent = self.manager.get_setting("ui", "nonexistent", "default")
        self.assertEqual(nonexistent, "default")

    def test_set_setting(self):
        """Test setting values"""
        self.assertTrue(self.manager.set_setting("ui", "overlay_duration", 5000))
        value = self.manager.get_setting("ui", "overlay_duration")
        self.assertEqual(value, 5000)

    def test_ui_setting_helpers(self):
        """Test UI setting helper methods"""
        self.assertTrue(self.manager.set_ui_setting("show_coordinates", True))
        self.assertTrue(self.manager.get_ui_setting("show_coordinates"))

        self.assertTrue(self.manager.set_ui_setting("highlight_color", "#00FF00"))
        self.assertEqual(self.manager.get_ui_setting("highlight_color"), "#00FF00")

    def test_performance_setting_helpers(self):
        """Test performance setting helper methods"""
        self.assertTrue(self.manager.set_performance_setting("safety_delay", 1.0))
        self.assertEqual(self.manager.get_performance_setting("safety_delay"), 1.0)

        self.assertTrue(self.manager.set_performance_setting("update_throttle_ms", 100))
        self.assertEqual(self.manager.get_performance_setting("update_throttle_ms"), 100)

    def test_get_section(self):
        """Test getting entire configuration section"""
        modules = self.manager.get_section("modules")
        self.assertIsInstance(modules, dict)
        self.assertIn("chrome", modules)

    def test_set_section(self):
        """Test setting entire configuration section"""
        new_modules = {"chrome": {"enabled": True}, "firefox": {"enabled": True}}
        self.assertTrue(self.manager.set_section("modules", new_modules))

        modules = self.manager.get_section("modules")
        self.assertIn("firefox", modules)

    def test_reset_to_defaults(self):
        """Test resetting to default configuration"""
        # Modify configuration
        self.manager.enable_module("chrome")
        self.manager.set_ui_setting("overlay_duration", 9999)

        # Reset to defaults
        self.assertTrue(self.manager.reset_to_defaults())

        # Check defaults are restored
        config = self.manager.get_config()
        self.assertIsNotNone(config)

    def test_reload(self):
        """Test reloading configuration"""
        # Save current config
        self.manager.enable_module("chrome")
        self.manager.save()

        # Modify in memory
        self.manager.disable_module("chrome")

        # Reload from file
        self.assertTrue(self.manager.reload())
        self.assertTrue(self.manager.is_module_enabled("chrome"))

    def test_update_multiple(self):
        """Test updating multiple settings at once"""
        updates = {
            "ui": {"overlay_duration": 4000, "highlight_color": "#0000FF"},
            "performance": {"safety_delay": 0.8},
        }

        self.assertTrue(self.manager.update_multiple(updates))
        self.assertEqual(self.manager.get_ui_setting("overlay_duration"), 4000)
        self.assertEqual(self.manager.get_ui_setting("highlight_color"), "#0000FF")
        self.assertEqual(self.manager.get_performance_setting("safety_delay"), 0.8)

    def test_auto_save(self):
        """Test auto-save functionality"""
        manager = ConfigManager(config_path=self.config_path, auto_save=True)
        manager.enable_module("chrome")

        # Should have auto-saved
        new_manager = ConfigManager(config_path=self.config_path)
        self.assertTrue(new_manager.is_module_enabled("chrome"))

    def test_listeners(self):
        """Test configuration change listeners"""
        callback_called = []

        def callback(config):
            callback_called.append(True)

        self.manager.add_listener(callback)
        self.manager.enable_module("chrome")
        self.assertTrue(len(callback_called) > 0)

        # Remove listener
        self.manager.remove_listener(callback)
        callback_called.clear()
        self.manager.enable_module("vscode")
        self.assertEqual(len(callback_called), 0)

    def test_listener_errors(self):
        """Test that listener errors don't break the manager"""

        def bad_callback(config):
            raise Exception("Test error")

        self.manager.add_listener(bad_callback)
        # Should not raise exception
        self.manager.enable_module("chrome")

    def test_thread_safety(self):
        """Test basic thread safety"""
        import threading

        def modify_config():
            for i in range(10):
                self.manager.enable_module("chrome")
                self.manager.disable_module("chrome")

        threads = [threading.Thread(target=modify_config) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should complete without errors
        self.assertIsNotNone(self.manager.config)

    def test_new_module(self):
        """Test adding a new module not in defaults"""
        self.assertTrue(self.manager.enable_module("new_module"))
        self.assertTrue(self.manager.is_module_enabled("new_module"))

    def test_new_feature(self):
        """Test adding a new feature not in defaults"""
        self.assertTrue(self.manager.enable_feature("new_feature"))
        self.assertTrue(self.manager.is_feature_enabled("new_feature"))


if __name__ == "__main__":
    unittest.main()
