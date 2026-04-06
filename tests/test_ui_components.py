"""
Tests for new UI components - LogsViewer, StatsPanel, Dashboard
Tests TICKET-012 implementation
"""
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

# Try to import UI components, skip tests if tkinter not available
try:
    import tkinter

    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

if TKINTER_AVAILABLE:
    from janus.ui.logs_viewer import LogsViewer
    from janus.ui.stats_panel import StatsPanel
    from janus.ui.dashboard import Dashboard

from janus.persistence.action_history import ActionHistory


@unittest.skipIf(not TKINTER_AVAILABLE, "tkinter not available")
class TestLogsViewer(unittest.TestCase):
    """Test cases for LogsViewer"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary log directory
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = Path(self.temp_dir) / "logs"
        self.log_dir.mkdir(exist_ok=True)

        # Create sample log files
        self._create_sample_logs()

        # Create LogsViewer instance (without showing UI)
        self.viewer = LogsViewer(log_dir=str(self.log_dir), auto_refresh=False)

    def tearDown(self):
        """Clean up"""
        # Remove temp files
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_sample_logs(self):
        """Create sample log files for testing"""
        # JSON format log
        json_log = self.log_dir / "test.json"
        with open(json_log, "w") as f:
            f.write(
                json.dumps(
                    {
                        "timestamp": "2024-01-01T10:00:00",
                        "level": "INFO",
                        "module": "test_module",
                        "message": "Test message 1",
                    }
                )
                + "\n"
            )
            f.write(
                json.dumps(
                    {
                        "timestamp": "2024-01-01T10:01:00",
                        "level": "ERROR",
                        "module": "test_module",
                        "message": "Test error message",
                    }
                )
                + "\n"
            )

        # Plain text log
        text_log = self.log_dir / "test.log"
        with open(text_log, "w") as f:
            f.write("2024-01-01 10:00:00 INFO test_module Test message 2\n")
            f.write("2024-01-01 10:01:00 WARNING test_module Test warning\n")

    def test_initialization(self):
        """Test LogsViewer initialization"""
        self.assertEqual(self.viewer.log_dir, Path(self.log_dir))
        self.assertFalse(self.viewer.auto_refresh)
        self.assertEqual(self.viewer.theme, "light")
        self.assertIsNone(self.viewer.window)
        self.assertFalse(self.viewer.is_showing)

    def test_load_logs(self):
        """Test loading logs from files"""
        self.viewer._load_logs()

        # Should have loaded entries
        self.assertGreater(len(self.viewer.log_entries), 0)

        # Check that entries have required fields
        for entry in self.viewer.log_entries:
            self.assertIn("timestamp", entry)
            self.assertIn("level", entry)
            self.assertIn("message", entry)

    def test_filter_by_level(self):
        """Test filtering logs by level"""
        self.viewer._load_logs()

        # Filter by ERROR level
        self.viewer.filter_level = "ERROR"
        self.viewer._apply_filters()

        # All filtered entries should be ERROR level
        for entry in self.viewer.filtered_entries:
            self.assertEqual(entry.get("level"), "ERROR")

    def test_filter_by_text(self):
        """Test filtering logs by text search"""
        self.viewer._load_logs()

        # Search for "error"
        self.viewer.filter_text = "error"
        self.viewer._apply_filters()

        # All filtered entries should contain "error" in message
        for entry in self.viewer.filtered_entries:
            self.assertIn("error", entry.get("message", "").lower())

    def test_theme_colors(self):
        """Test theme color configurations"""
        # Test light theme
        self.viewer.set_theme("light")
        self.assertEqual(self.viewer.theme, "light")
        self.assertIn("bg", self.viewer.colors)
        self.assertIn("fg", self.viewer.colors)

        # Test dark theme
        self.viewer.set_theme("dark")
        self.assertEqual(self.viewer.theme, "dark")
        self.assertIn("bg", self.viewer.colors)
        self.assertIn("fg", self.viewer.colors)

    def test_parse_text_log_line(self):
        """Test parsing plain text log lines"""
        line = "2024-01-01 10:00:00 INFO test_module Test message"
        entry = self.viewer._parse_text_log_line(line)

        self.assertIsNotNone(entry)
        self.assertIn("timestamp", entry)
        self.assertIn("level", entry)
        self.assertIn("module", entry)
        self.assertIn("message", entry)


@unittest.skipIf(not TKINTER_AVAILABLE, "tkinter not available")
class TestStatsPanel(unittest.TestCase):
    """Test cases for StatsPanel"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_actions.db")

        # Create ActionHistory instance
        self.action_history = ActionHistory(db_path=self.db_path)

        # Add sample actions
        self._create_sample_actions()

        # Create StatsPanel instance (without showing UI)
        self.panel = StatsPanel(action_history=self.action_history, auto_refresh=False)

    def tearDown(self):
        """Clean up"""
        # Remove temp files
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_sample_actions(self):
        """Create sample actions for testing"""
        # Successful actions
        for i in range(10):
            self.action_history.record_action(
                action_type="click",
                action_data={"x": 100, "y": 200},
                status="success",
                duration_ms=100 + i * 10,
                module="test_module",
            )

        # Failed actions
        for i in range(3):
            self.action_history.record_action(
                action_type="type_text",
                action_data={"text": "test"},
                status="failed",
                duration_ms=50,
                module="test_module",
                error="Test error",
            )

    def test_initialization(self):
        """Test StatsPanel initialization"""
        self.assertIsNotNone(self.panel.action_history)
        self.assertFalse(self.panel.auto_refresh)
        self.assertEqual(self.panel.theme, "light")
        self.assertIsNone(self.panel.window)
        self.assertFalse(self.panel.is_showing)

    def test_get_date_range(self):
        """Test date range calculation"""
        # Test "all" period
        self.panel.period = "all"
        self.panel.period_var = type("obj", (object,), {"get": lambda: "all"})()
        start_date, end_date = self.panel._get_date_range()
        self.assertIsNone(start_date)
        self.assertIsNone(end_date)

        # Test "today" period
        self.panel.period_var = type("obj", (object,), {"get": lambda: "today"})()
        start_date, end_date = self.panel._get_date_range()
        self.assertIsNotNone(start_date)
        self.assertIsNotNone(end_date)

    def test_theme_colors(self):
        """Test theme color configurations"""
        # Test light theme
        self.panel.set_theme("light")
        self.assertEqual(self.panel.theme, "light")
        self.assertIn("bg", self.panel.colors)
        self.assertIn("fg", self.panel.colors)

        # Test dark theme
        self.panel.set_theme("dark")
        self.assertEqual(self.panel.theme, "dark")
        self.assertIn("bg", self.panel.colors)
        self.assertIn("fg", self.panel.colors)


@unittest.skipIf(not TKINTER_AVAILABLE, "tkinter not available")
class TestDashboard(unittest.TestCase):
    """Test cases for Dashboard"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database and config
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_actions.db")
        self.config_path = os.path.join(self.temp_dir, "test_config.json")

        # Create ActionHistory instance
        self.action_history = ActionHistory(db_path=self.db_path)

        # Add sample actions
        self._create_sample_actions()

        # Create Dashboard instance (without showing UI)
        self.dashboard = Dashboard(action_history=self.action_history, config_path=self.config_path)

    def tearDown(self):
        """Clean up"""
        # Remove temp files
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_sample_actions(self):
        """Create sample actions for testing"""
        # Successful actions
        for i in range(5):
            self.action_history.record_action(
                action_type="click",
                action_data={"x": 100, "y": 200},
                status="success",
                duration_ms=100 + i * 10,
                module="test_module",
            )

        # Failed action
        self.action_history.record_action(
            action_type="type_text",
            action_data={"text": "test"},
            status="failed",
            duration_ms=50,
            module="test_module",
            error="Test error",
        )

    def test_initialization(self):
        """Test Dashboard initialization"""
        self.assertIsNotNone(self.dashboard.action_history)
        self.assertEqual(self.dashboard.config_path, self.config_path)
        self.assertEqual(self.dashboard.theme, "light")
        self.assertIsNone(self.dashboard.window)
        self.assertFalse(self.dashboard.is_showing)

    def test_dashboard_has_action_history(self):
        """Test that dashboard can access action history"""
        stats = self.dashboard.action_history.get_statistics()

        self.assertIsInstance(stats, dict)
        self.assertIn("total_actions", stats)
        self.assertGreater(stats["total_actions"], 0)


@unittest.skipIf(not TKINTER_AVAILABLE, "tkinter not available")
class TestConfigUIEnhancements(unittest.TestCase):
    """Test cases for ConfigUI enhancements (shortcuts and theme)"""

    def setUp(self):
        """Set up test fixtures"""
        from janus.ui.config_ui import ConfigUI

        # Create temporary config file
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        self.config_ui = ConfigUI(config_path=self.config_path)

    def tearDown(self):
        """Clean up"""
        # Remove temp files
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_shortcuts_in_config(self):
        """Test that shortcuts are in configuration"""
        config = self.config_ui.config

        self.assertIn("shortcuts", config)

        # Check expected shortcuts
        expected_shortcuts = [
            "show_dashboard",
            "show_logs",
            "show_stats",
            "show_config",
            "pause_listening",
            "cancel_action",
        ]

        for shortcut in expected_shortcuts:
            self.assertIn(shortcut, config["shortcuts"])
            self.assertIn("value", config["shortcuts"][shortcut])
            self.assertIn("label", config["shortcuts"][shortcut])

    def test_theme_in_ui_config(self):
        """Test that theme is in UI configuration"""
        config = self.config_ui.config

        self.assertIn("ui", config)
        self.assertIn("theme", config["ui"])
        self.assertIn("value", config["ui"]["theme"])
        self.assertIn("options", config["ui"]["theme"])

        # Check theme options
        theme_options = config["ui"]["theme"]["options"]
        self.assertIn("light", theme_options)
        self.assertIn("dark", theme_options)

    def test_default_shortcuts(self):
        """Test default shortcut values"""
        shortcuts = self.config_ui.config["shortcuts"]

        # Check some default shortcuts
        self.assertEqual(shortcuts["show_dashboard"]["value"], "Ctrl+Shift+D")
        self.assertEqual(shortcuts["show_logs"]["value"], "Ctrl+Shift+L")
        self.assertEqual(shortcuts["show_stats"]["value"], "Ctrl+Shift+S")
        self.assertEqual(shortcuts["cancel_action"]["value"], "Escape")


class TestUIIntegration(unittest.TestCase):
    """Integration tests for UI components"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up"""
        # Remove temp files
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @unittest.skipIf(not TKINTER_AVAILABLE, "tkinter not available")
    def test_ui_module_imports(self):
        """Test that all UI components can be imported"""
        from janus.ui import (
            ActionOverlay,
            ConfigUI,
            Dashboard,
            EnhancedOverlay,
            LearningDashboard,
            LogsViewer,
            StatsPanel,
        )

        # All components should be available (even if None when tkinter not available)
        # This test just ensures the imports work
        self.assertTrue(True)

    def test_ui_module_all_exports(self):
        """Test that __all__ includes new components"""
        import janus.ui

        self.assertIn("LogsViewer", janus.ui.__all__)
        self.assertIn("StatsPanel", janus.ui.__all__)
        self.assertIn("Dashboard", janus.ui.__all__)


if __name__ == "__main__":
    unittest.main()
