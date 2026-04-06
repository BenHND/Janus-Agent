"""
Unit tests for TTS enhanced controls
Ticket TICKET-MAC-03: TTS Activation and Stabilization
"""
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from janus.io.tts.mac_tts import MacTTSAdapter


class TestMacTTSVolumeControl(unittest.TestCase):
    """Test volume control functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.adapter = MacTTSAdapter(
            voice="Thomas", rate=180, volume=0.7, lang="fr-FR", enable_queue=False
        )

    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, "adapter"):
            self.adapter.shutdown()

    def test_initial_volume(self):
        """Test initial volume setting"""
        self.assertEqual(self.adapter.get_volume(), 0.7)

    def test_set_volume(self):
        """Test setting volume"""
        self.adapter.set_volume(0.5)
        self.assertEqual(self.adapter.get_volume(), 0.5)

    def test_volume_clamping(self):
        """Test volume is clamped to valid range"""
        self.adapter.set_volume(-0.5)
        self.assertEqual(self.adapter.get_volume(), 0.0)

        self.adapter.set_volume(1.5)
        self.assertEqual(self.adapter.get_volume(), 1.0)

    @patch("subprocess.Popen")
    def test_volume_in_say_command(self, mock_popen):
        """Test that volume is passed to say command"""
        mock_process = MagicMock()
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        self.adapter.set_volume(0.8)
        self.adapter.speak("Test", lang="fr")

        # Check that --volume flag was used
        call_args = mock_popen.call_args[0][0]
        self.assertIn("--volume", call_args)
        # Volume should be converted to 0-100 scale
        volume_index = call_args.index("--volume")
        self.assertEqual(call_args[volume_index + 1], "80")


class TestMacTTSMuteControl(unittest.TestCase):
    """Test mute/unmute functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.adapter = MacTTSAdapter(
            voice="Thomas", rate=180, volume=0.7, lang="fr-FR", enable_queue=False
        )

    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, "adapter"):
            self.adapter.shutdown()

    def test_initial_mute_state(self):
        """Test initial mute state is False"""
        self.assertFalse(self.adapter.is_muted())

    def test_mute(self):
        """Test muting"""
        self.adapter.mute()
        self.assertTrue(self.adapter.is_muted())

    def test_unmute(self):
        """Test unmuting"""
        self.adapter.mute()
        self.assertTrue(self.adapter.is_muted())

        self.adapter.unmute()
        self.assertFalse(self.adapter.is_muted())

    def test_mute_preserves_volume(self):
        """Test that mute preserves volume setting"""
        original_volume = 0.7
        self.adapter.set_volume(original_volume)

        self.adapter.mute()
        self.adapter.unmute()

        self.assertEqual(self.adapter.get_volume(), original_volume)

    @patch("subprocess.Popen")
    def test_muted_speak_does_not_execute(self, mock_popen):
        """Test that speak does not execute when muted"""
        self.adapter.mute()
        result = self.adapter.speak("Test", lang="fr")

        # Should return False and not call subprocess
        self.assertFalse(result)
        mock_popen.assert_not_called()

    def test_mute_stops_current_speech(self):
        """Test that mute stops current speech"""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.wait.side_effect = lambda: time.sleep(0.2)
            mock_process.terminate.return_value = None
            mock_popen.return_value = mock_process

            # Start speaking in background
            import threading

            thread = threading.Thread(target=lambda: self.adapter._speak_sync("Test", "en"))
            thread.start()

            time.sleep(0.05)

            # Mute should stop speech
            self.adapter.mute()

            # Verify terminate was called
            mock_process.terminate.assert_called()

            thread.join(timeout=1.0)


class TestMacTTSTimingTracking(unittest.TestCase):
    """Test timing and duration tracking"""

    def setUp(self):
        """Set up test fixtures"""
        self.adapter = MacTTSAdapter(
            voice="Thomas", rate=180, volume=0.7, lang="fr-FR", enable_queue=False
        )

    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, "adapter"):
            self.adapter.shutdown()

    def test_initial_timing_stats(self):
        """Test initial timing statistics"""
        stats = self.adapter.get_timing_stats()

        self.assertEqual(stats["total_speech_time"], 0.0)
        self.assertEqual(stats["speech_count"], 0)
        self.assertEqual(stats["average_duration"], 0.0)
        self.assertFalse(stats["is_speaking"])

    @patch("subprocess.Popen")
    def test_timing_tracked_after_speech(self, mock_popen):
        """Test that timing is tracked after speech"""
        mock_process = MagicMock()
        mock_process.wait.side_effect = lambda: time.sleep(0.1)
        mock_popen.return_value = mock_process

        self.adapter.speak("Test", lang="fr")
        time.sleep(0.2)

        stats = self.adapter.get_timing_stats()

        # Should have recorded one speech
        self.assertEqual(stats["speech_count"], 1)
        self.assertGreater(stats["total_speech_time"], 0.0)
        self.assertGreater(stats["average_duration"], 0.0)

    @patch("subprocess.Popen")
    def test_multiple_speeches_tracked(self, mock_popen):
        """Test that multiple speeches are tracked"""
        mock_process = MagicMock()
        mock_process.wait.side_effect = lambda: time.sleep(0.05)
        mock_popen.return_value = mock_process

        # Speak multiple times
        for i in range(3):
            self.adapter.speak(f"Test {i}", lang="fr")
            time.sleep(0.1)

        stats = self.adapter.get_timing_stats()

        # Should have recorded three speeches
        self.assertEqual(stats["speech_count"], 3)
        self.assertGreater(stats["total_speech_time"], 0.0)
        self.assertGreater(stats["average_duration"], 0.0)


class TestMacTTSQueueWithMute(unittest.TestCase):
    """Test queue behavior with mute"""

    def setUp(self):
        """Set up test fixtures"""
        self.adapter = MacTTSAdapter(
            voice="Thomas", rate=180, volume=0.7, lang="fr-FR", enable_queue=True
        )

    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, "adapter"):
            self.adapter.shutdown()

    def test_muted_queue_does_not_add_messages(self):
        """Test that messages are not queued when muted"""
        self.adapter.mute()

        result = self.adapter.speak("Test", priority=5)

        # Should return False and not queue
        self.assertFalse(result)
        self.assertTrue(self.adapter._queue.empty())

    def test_unmute_allows_queueing(self):
        """Test that unmute allows queueing again"""
        self.adapter.mute()
        self.adapter.speak("Test1")  # Should not queue

        self.adapter.unmute()
        result = self.adapter.speak("Test2")  # Should queue

        self.assertTrue(result)
        self.assertFalse(self.adapter._queue.empty())


class TestMacTTSIntegrationWithSettings(unittest.TestCase):
    """Test TTS integration with settings"""

    @patch("subprocess.Popen")
    def test_adapter_uses_volume_from_init(self, mock_popen):
        """Test that adapter uses volume from initialization"""
        mock_process = MagicMock()
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        adapter = MacTTSAdapter(
            voice="Thomas", rate=180, volume=0.6, lang="fr-FR", enable_queue=False
        )

        adapter.speak("Test", lang="fr")

        # Check volume in command
        call_args = mock_popen.call_args[0][0]
        volume_index = call_args.index("--volume")
        self.assertEqual(call_args[volume_index + 1], "60")

        adapter.shutdown()


if __name__ == "__main__":
    unittest.main()
