"""
Tests for Persistent Overlay (Ticket #UI-001)
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch


class TestPersistentOverlay(unittest.TestCase):
    """Test cases for PersistentOverlay"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock tkinter to avoid GUI dependencies in tests
        self.tk_mock = MagicMock()
        self.patcher = patch.dict(
            "sys.modules",
            {
                "tkinter": self.tk_mock,
                "tkinter.ttk": self.tk_mock,
            },
        )
        self.patcher.start()

        # Now import after mocking
        from janus.ui.persistent_overlay import PersistentOverlay

        # Create temp config file
        self.temp_config = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        self.temp_config.close()

        # Create overlay with temp config
        self.overlay = PersistentOverlay(
            on_start=Mock(),
            on_stop=Mock(),
            on_config=Mock(),
            on_clear=Mock(),
            config_path=self.temp_config.name,
        )

    def tearDown(self):
        """Clean up"""
        self.patcher.stop()
        # Clean up temp file
        try:
            Path(self.temp_config.name).unlink()
        except:
            pass

    def test_initialization(self):
        """Test overlay initialization"""
        self.assertIsNotNone(self.overlay.on_start)
        self.assertIsNotNone(self.overlay.on_stop)
        self.assertIsNotNone(self.overlay.on_config)
        self.assertIsNotNone(self.overlay.on_clear)
        self.assertFalse(self.overlay.is_running)
        self.assertFalse(self.overlay.is_listening)

    def test_load_default_position(self):
        """Test loading default position when no saved position exists"""
        pos = self.overlay._load_position()
        self.assertIsNone(pos["x"])
        self.assertIsNone(pos["y"])

    def test_save_and_load_position(self):
        """Test saving and loading window position"""
        # Save position
        test_pos = {"x": 100, "y": 200}
        with open(self.temp_config.name, "w") as f:
            json.dump(test_pos, f)

        # Load position
        pos = self.overlay._load_position()
        self.assertEqual(pos["x"], 100)
        self.assertEqual(pos["y"], 200)

    def test_update_transcription_queue(self):
        """Test that transcription updates are queued"""
        self.overlay.update_transcription("Test transcription")
        self.assertFalse(self.overlay.message_queue.empty())

        msg_type, msg_data = self.overlay.message_queue.get()
        self.assertEqual(msg_type, "transcription")
        self.assertEqual(msg_data, "Test transcription")

    def test_update_status_queue(self):
        """Test that status updates are queued"""
        self.overlay.update_status("Test status")
        self.assertFalse(self.overlay.message_queue.empty())

        msg_type, msg_data = self.overlay.message_queue.get()
        self.assertEqual(msg_type, "status")
        self.assertEqual(msg_data, "Test status")

    def test_clear_transcription_queue(self):
        """Test that clear requests are queued"""
        self.overlay.clear_transcription()
        self.assertFalse(self.overlay.message_queue.empty())

        msg_type, msg_data = self.overlay.message_queue.get()
        self.assertEqual(msg_type, "clear")
        self.assertIsNone(msg_data)

    def test_multiple_updates(self):
        """Test multiple updates are queued in order"""
        self.overlay.update_transcription("First")
        self.overlay.update_status("Status")
        self.overlay.update_transcription("Second")

        # Check first message
        msg_type, msg_data = self.overlay.message_queue.get()
        self.assertEqual(msg_type, "transcription")
        self.assertEqual(msg_data, "First")

        # Check second message
        msg_type, msg_data = self.overlay.message_queue.get()
        self.assertEqual(msg_type, "status")
        self.assertEqual(msg_data, "Status")

        # Check third message
        msg_type, msg_data = self.overlay.message_queue.get()
        self.assertEqual(msg_type, "transcription")
        self.assertEqual(msg_data, "Second")

    def test_callbacks_exist(self):
        """Test that callbacks are properly set"""
        self.assertTrue(callable(self.overlay.on_start))
        self.assertTrue(callable(self.overlay.on_stop))
        self.assertTrue(callable(self.overlay.on_config))
        self.assertTrue(callable(self.overlay.on_clear))


if __name__ == "__main__":
    unittest.main()
