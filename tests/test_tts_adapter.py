"""
Unit tests for TTS adapters
Ticket ADD-VOX: Voice Response / TTS Integration
"""
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from janus.io.tts.adapter import TTSAdapter
from janus.io.tts.mac_tts import MacTTSAdapter, TTSMessage


class TestTTSAdapter(unittest.TestCase):
    """Test TTS adapter interface"""

    def test_tts_adapter_is_abstract(self):
        """Test that TTSAdapter cannot be instantiated directly"""
        with self.assertRaises(TypeError):
            TTSAdapter()


class TestMacTTSAdapter(unittest.TestCase):
    """Test macOS TTS adapter"""

    def setUp(self):
        """Set up test fixtures"""
        # Create adapter without queue for synchronous testing
        self.adapter = MacTTSAdapter(voice="Thomas", rate=180, lang="fr-FR", enable_queue=False)

    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, "adapter"):
            self.adapter.shutdown()

    def test_initialization(self):
        """Test adapter initialization"""
        self.assertEqual(self.adapter.voice, "Thomas")
        self.assertEqual(self.adapter.rate, 180)
        self.assertEqual(self.adapter.default_lang, "fr-FR")
        self.assertFalse(self.adapter.enable_queue)

    def test_initialization_with_queue(self):
        """Test adapter initialization with queue enabled"""
        adapter = MacTTSAdapter(enable_queue=True)
        self.assertTrue(adapter.enable_queue)
        self.assertIsNotNone(adapter._queue)
        self.assertIsNotNone(adapter._worker_thread)
        adapter.shutdown()

    def test_set_voice(self):
        """Test setting voice"""
        self.adapter.set_voice("Alex")
        self.assertEqual(self.adapter.voice, "Alex")

    def test_set_rate(self):
        """Test setting speech rate"""
        self.adapter.set_rate(200)
        self.assertEqual(self.adapter.rate, 200)

    def test_set_rate_clamping(self):
        """Test that speech rate is clamped to reasonable range"""
        self.adapter.set_rate(50)  # Too low
        self.assertEqual(self.adapter.rate, 100)

        self.adapter.set_rate(500)  # Too high
        self.assertEqual(self.adapter.rate, 300)

    def test_normalize_language(self):
        """Test language code normalization"""
        self.assertEqual(self.adapter._normalize_language("fr"), "fr-FR")
        self.assertEqual(self.adapter._normalize_language("en"), "en-US")
        self.assertEqual(self.adapter._normalize_language("fr-FR"), "fr-FR")
        self.assertEqual(self.adapter._normalize_language("en-GB"), "en-GB")

    def test_is_speaking_initially_false(self):
        """Test that is_speaking is initially False"""
        self.assertFalse(self.adapter.is_speaking())

    @patch("subprocess.Popen")
    def test_speak_sync(self, mock_popen):
        """Test synchronous speech"""
        # Mock process
        mock_process = MagicMock()
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        # Speak text
        self.adapter._speak_sync("Hello", "en-US")

        # Verify subprocess was called
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        self.assertIn("say", call_args)
        self.assertIn("Hello", call_args)
        self.assertIn("-v", call_args)
        self.assertIn("Thomas", call_args)
        self.assertIn("-r", call_args)
        self.assertIn("180", call_args)

    @patch("subprocess.Popen")
    def test_speak(self, mock_popen):
        """Test speak method"""
        # Mock process
        mock_process = MagicMock()
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        # Speak text
        result = self.adapter.speak("Bonjour", lang="fr")

        # Should succeed
        self.assertTrue(result)
        mock_popen.assert_called_once()

    def test_speak_empty_text(self):
        """Test speaking empty text"""
        result = self.adapter.speak("")
        self.assertFalse(result)

        result = self.adapter.speak("   ")
        self.assertFalse(result)

    @patch("subprocess.Popen")
    def test_stop(self, mock_popen):
        """Test stopping speech"""
        # Mock process
        mock_process = MagicMock()
        mock_process.wait.side_effect = lambda: time.sleep(0.1)
        mock_process.terminate.return_value = None
        mock_popen.return_value = mock_process

        # Start speaking in background thread
        import threading

        thread = threading.Thread(target=lambda: self.adapter._speak_sync("Test", "en"))
        thread.start()

        # Give it time to start
        time.sleep(0.05)

        # Stop speech
        self.adapter.stop()

        # Verify terminate was called
        mock_process.terminate.assert_called()

        # Wait for thread to finish
        thread.join(timeout=1.0)

    @patch("subprocess.run")
    def test_get_available_voices(self, mock_run):
        """Test getting available voices"""
        # Mock voice list output
        mock_result = MagicMock()
        mock_result.stdout = "Alex en-US    Most people recognize me by my voice.\nThomas fr-FR    Bonjour, je m'appelle Thomas.\n"
        mock_run.return_value = mock_result

        voices = self.adapter.get_available_voices()

        self.assertIn("Alex", voices)
        self.assertIn("Thomas", voices)

    def test_tts_message_dataclass(self):
        """Test TTSMessage dataclass"""
        msg = TTSMessage(priority=5, timestamp=time.time(), text="Test", lang="en-US")

        self.assertEqual(msg.text, "Test")
        self.assertEqual(msg.lang, "en-US")
        self.assertEqual(msg.priority, 5)
        self.assertIsInstance(msg.timestamp, float)


class TestMacTTSAdapterWithQueue(unittest.TestCase):
    """Test macOS TTS adapter with queue enabled"""

    def setUp(self):
        """Set up test fixtures"""
        self.adapter = MacTTSAdapter(voice="Thomas", rate=180, lang="fr-FR", enable_queue=True)

    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, "adapter"):
            self.adapter.shutdown()

    def test_queue_enabled(self):
        """Test that queue is enabled"""
        self.assertTrue(self.adapter.enable_queue)
        self.assertIsNotNone(self.adapter._queue)

    def test_speak_queues_message(self):
        """Test that speak queues message"""
        result = self.adapter.speak("Test message", priority=5)
        self.assertTrue(result)

        # Check queue has message
        self.assertFalse(self.adapter._queue.empty())

    def test_priority_handling(self):
        """Test message priority handling"""
        # Queue low priority messages
        self.adapter.speak("Low priority 1", priority=1)
        self.adapter.speak("Low priority 2", priority=2)

        # Queue high priority message
        self.adapter.speak("High priority", priority=10)

        # High priority should be processed first (after current message)
        # Note: Priority queue uses negative priority, so -10 < -2 < -1
        time.sleep(0.1)  # Give worker time to process

    def test_clear_low_priority_messages(self):
        """Test clearing low-priority messages"""
        # Queue several low priority messages
        for i in range(5):
            self.adapter.speak(f"Low priority {i}", priority=i)

        # Clear low priority
        self.adapter._clear_low_priority_messages()

        # Only high-priority messages should remain
        # (priority > 5, i.e., negative priority < -5)
        remaining = self.adapter._queue.qsize()
        self.assertEqual(remaining, 0)  # All were low priority

    def test_shutdown_clears_queue(self):
        """Test that shutdown clears queue"""
        # Queue messages
        self.adapter.speak("Message 1")
        self.adapter.speak("Message 2")

        # Shutdown
        self.adapter.shutdown()

        # Queue should be cleared
        self.assertTrue(self.adapter._queue.empty())


if __name__ == "__main__":
    unittest.main()
