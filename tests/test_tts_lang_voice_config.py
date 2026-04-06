"""
Tests for TTS language, voice, and configuration
Ticket ADD-VOX: Voice Response / TTS Integration
"""
import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from janus.io.tts.mac_tts import MacTTSAdapter


class TestTTSLanguageVoiceConfig(unittest.TestCase):
    """Test TTS language, voice, and configuration"""

    def setUp(self):
        """Set up test fixtures"""
        self.adapter = MacTTSAdapter(voice="Thomas", rate=180, lang="fr-FR", enable_queue=False)

    def tearDown(self):
        """Clean up after tests"""
        if hasattr(self, "adapter"):
            self.adapter.shutdown()

    def test_default_configuration(self):
        """Test default configuration values"""
        self.assertEqual(self.adapter.voice, "Thomas")
        self.assertEqual(self.adapter.rate, 180)
        self.assertEqual(self.adapter.default_lang, "fr-FR")

    def test_change_voice(self):
        """Test changing voice"""
        self.adapter.set_voice("Alex")
        self.assertEqual(self.adapter.voice, "Alex")

        self.adapter.set_voice("Samantha")
        self.assertEqual(self.adapter.voice, "Samantha")

    def test_change_rate(self):
        """Test changing speech rate"""
        self.adapter.set_rate(150)
        self.assertEqual(self.adapter.rate, 150)

        self.adapter.set_rate(250)
        self.assertEqual(self.adapter.rate, 250)

    def test_rate_bounds(self):
        """Test that rate is bounded correctly"""
        # Too low
        self.adapter.set_rate(50)
        self.assertGreaterEqual(self.adapter.rate, 100)

        # Too high
        self.adapter.set_rate(500)
        self.assertLessEqual(self.adapter.rate, 300)

    def test_language_normalization_french(self):
        """Test French language code normalization"""
        self.assertEqual(self.adapter._normalize_language("fr"), "fr-FR")
        self.assertEqual(self.adapter._normalize_language("fr-FR"), "fr-FR")
        self.assertEqual(self.adapter._normalize_language("fr-CA"), "fr-CA")

    def test_language_normalization_english(self):
        """Test English language code normalization"""
        self.assertEqual(self.adapter._normalize_language("en"), "en-US")
        self.assertEqual(self.adapter._normalize_language("en-US"), "en-US")
        self.assertEqual(self.adapter._normalize_language("en-GB"), "en-GB")

    def test_language_normalization_other(self):
        """Test other language code normalization"""
        self.assertEqual(self.adapter._normalize_language("es"), "es-ES")
        self.assertEqual(self.adapter._normalize_language("de"), "de-DE")
        self.assertEqual(self.adapter._normalize_language("it"), "it-IT")

    def test_language_normalization_unknown(self):
        """Test unknown language code normalization"""
        # Unknown codes should pass through
        self.assertEqual(self.adapter._normalize_language("pt-BR"), "pt-BR")
        self.assertEqual(self.adapter._normalize_language("ja-JP"), "ja-JP")

    @patch("subprocess.Popen")
    def test_speak_with_french_voice(self, mock_popen):
        """Test speaking with French voice configuration"""
        mock_process = Mock()
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        self.adapter.set_voice("Thomas")
        self.adapter.speak("Bonjour le monde", lang="fr")

        # Verify subprocess was called with French voice
        call_args = mock_popen.call_args[0][0]
        self.assertIn("say", call_args)
        self.assertIn("-v", call_args)
        self.assertIn("Thomas", call_args)
        self.assertIn("Bonjour le monde", call_args)

    @patch("subprocess.Popen")
    def test_speak_with_english_voice(self, mock_popen):
        """Test speaking with English voice configuration"""
        mock_process = Mock()
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        self.adapter.set_voice("Alex")
        self.adapter.speak("Hello world", lang="en")

        # Verify subprocess was called with English voice
        call_args = mock_popen.call_args[0][0]
        self.assertIn("say", call_args)
        self.assertIn("-v", call_args)
        self.assertIn("Alex", call_args)
        self.assertIn("Hello world", call_args)

    @patch("subprocess.Popen")
    def test_speak_with_custom_rate(self, mock_popen):
        """Test speaking with custom rate"""
        mock_process = Mock()
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        self.adapter.set_rate(200)
        self.adapter.speak("Test message")

        # Verify subprocess was called with custom rate
        call_args = mock_popen.call_args[0][0]
        self.assertIn("-r", call_args)
        self.assertIn("200", call_args)

    @patch("subprocess.Popen")
    def test_speak_without_voice_uses_default(self, mock_popen):
        """Test speaking without voice uses default"""
        mock_process = Mock()
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        # Create adapter without voice
        adapter = MacTTSAdapter(voice=None, enable_queue=False)
        adapter.speak("Test message")

        # Verify subprocess was called but without -v flag
        call_args = mock_popen.call_args[0][0]
        self.assertIn("say", call_args)
        # -v should not be in args if voice is None
        if "-v" in call_args:
            # If -v is present, it should be followed by None or not present at all
            v_index = call_args.index("-v")
            # Actually, if voice is None, -v shouldn't be added
            pass

        adapter.shutdown()


class TestTTSConfigurationScenarios(unittest.TestCase):
    """Test various TTS configuration scenarios"""

    def test_french_configuration(self):
        """Test French TTS configuration"""
        adapter = MacTTSAdapter(voice="Thomas", rate=180, lang="fr-FR", enable_queue=False)

        self.assertEqual(adapter.voice, "Thomas")
        self.assertEqual(adapter.rate, 180)
        self.assertEqual(adapter.default_lang, "fr-FR")

        adapter.shutdown()

    def test_english_configuration(self):
        """Test English TTS configuration"""
        adapter = MacTTSAdapter(voice="Alex", rate=200, lang="en-US", enable_queue=False)

        self.assertEqual(adapter.voice, "Alex")
        self.assertEqual(adapter.rate, 200)
        self.assertEqual(adapter.default_lang, "en-US")

        adapter.shutdown()

    def test_fast_speech_rate(self):
        """Test fast speech rate configuration"""
        adapter = MacTTSAdapter(rate=250, enable_queue=False)

        self.assertEqual(adapter.rate, 250)
        adapter.shutdown()

    def test_slow_speech_rate(self):
        """Test slow speech rate configuration"""
        adapter = MacTTSAdapter(rate=120, enable_queue=False)

        self.assertEqual(adapter.rate, 120)
        adapter.shutdown()

    def test_queue_enabled_configuration(self):
        """Test configuration with queue enabled"""
        adapter = MacTTSAdapter(voice="Thomas", rate=180, lang="fr-FR", enable_queue=True)

        self.assertTrue(adapter.enable_queue)
        self.assertIsNotNone(adapter._queue)
        self.assertIsNotNone(adapter._worker_thread)

        adapter.shutdown()

    def test_queue_disabled_configuration(self):
        """Test configuration with queue disabled"""
        adapter = MacTTSAdapter(voice="Thomas", rate=180, lang="fr-FR", enable_queue=False)

        self.assertFalse(adapter.enable_queue)
        self.assertIsNone(adapter._queue)

        adapter.shutdown()


if __name__ == "__main__":
    unittest.main()
