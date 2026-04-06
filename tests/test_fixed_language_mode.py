"""
Tests for Phase 15.1 - Fixed Language Profiles
Validates stable transcription when forcing FR/EN
"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch

# Mock dependencies before importing
sys.modules["whisper"] = MagicMock()
sys.modules["pyaudio"] = MagicMock()
sys.modules["webrtcvad"] = MagicMock()


class TestFixedLanguageMode(unittest.TestCase):
    """Test cases for fixed language profile mode (Phase 15.1)"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fixed_language_from_profile(self):
        """Test that profile language is used instead of auto-detection"""
        # Import and patch in the right order
        import janus.stt.whisper_stt as whisper_stt_module

        with patch.object(whisper_stt_module, "whisper") as mock_whisper, patch.object(
            whisper_stt_module, "pyaudio"
        ) as mock_pyaudio_module:
            from janus.io.stt.calibration_manager import CalibrationManager
            from janus.io.stt.whisper_stt import WhisperSTT

            # Mock Whisper model
            mock_model = Mock()
            mock_model.transcribe.return_value = {"text": "bonjour"}
            mock_whisper.load_model.return_value = mock_model
            mock_pyaudio_module.PyAudio.return_value = Mock()

            # Create a calibration profile with fixed language
            manager = CalibrationManager(profile_dir=self.temp_dir)
            profile = manager._create_default_profile("test_user", "fr")
            manager.save_profile(profile)

            # Initialize WhisperSTT with the profile
            stt = WhisperSTT(
                model_size="base",
                enable_logging=False,
                user_id="test_user",
            )
            # Override profile directory to use test directory
            stt.calibration_manager.profile_dir = manager.profile_dir
            stt.calibration_profile = manager.load_profile("test_user")

            # Create a dummy audio file
            audio_path = os.path.join(self.temp_dir, "test.wav")
            with open(audio_path, "wb") as f:
                f.write(b"\x00" * 1000)

            # Transcribe - should use profile language "fr"
            result = stt.transcribe(audio_path)

            # Verify transcribe was called with language="fr"
            call_kwargs = mock_model.transcribe.call_args[1]
            self.assertEqual(call_kwargs.get("language"), "fr")
            self.assertEqual(result["language"], "fr")

    def test_auto_language_mode_preserved(self):
        """Test that language='auto' is converted to explicit language (TICKET-1)"""
        with patch("janus.stt.whisper_stt.whisper.load_model") as mock_load_model, patch(
            "janus.stt.whisper_stt.pyaudio.PyAudio"
        ) as mock_pyaudio:
            from janus.io.stt.whisper_stt import WhisperSTT

            # Mock Whisper model
            mock_model = Mock()
            mock_model.transcribe.return_value = {"text": "hello"}
            mock_load_model.return_value = mock_model
            mock_pyaudio.return_value = Mock()

            stt = WhisperSTT(
                model_size="base",
                language="en",  # TICKET-1: Explicit default language
                enable_logging=False,
                user_id="test_user",
            )

            # Create a dummy audio file
            audio_path = os.path.join(self.temp_dir, "test.wav")
            with open(audio_path, "wb") as f:
                f.write(b"\x00" * 1000)

            # Transcribe with auto (TICKET-1: should use effective_language, not None)
            result = stt.transcribe(audio_path, language="auto")

            # TICKET-1: Verify transcribe was called with explicit language (not None)
            call_kwargs = mock_model.transcribe.call_args[1]
            self.assertIn("language", call_kwargs)
            self.assertEqual(call_kwargs.get("language"), "en")
            self.assertTrue(result["success"])

    def test_explicit_language_override(self):
        """Test that explicit language parameter is used (TICKET-1)"""
        with patch("janus.stt.whisper_stt.whisper.load_model") as mock_load_model, patch(
            "janus.stt.whisper_stt.pyaudio.PyAudio"
        ) as mock_pyaudio:
            from janus.io.stt.calibration_manager import CalibrationManager
            from janus.io.stt.whisper_stt import WhisperSTT

            # Mock Whisper model
            mock_model = Mock()
            mock_model.transcribe.return_value = {"text": "hello"}
            mock_load_model.return_value = mock_model
            mock_pyaudio.return_value = Mock()

            # Create a calibration profile with French
            manager = CalibrationManager(profile_dir=self.temp_dir)
            profile = manager._create_default_profile("test_user", "fr")
            manager.save_profile(profile)

            stt = WhisperSTT(
                model_size="base",
                language="fr",  # TICKET-1: Default language
                enable_logging=False,
                user_id="test_user",
            )
            stt.calibration_manager.profile_dir = manager.profile_dir
            stt.calibration_profile = manager.load_profile("test_user")

            # Create a dummy audio file
            audio_path = os.path.join(self.temp_dir, "test.wav")
            with open(audio_path, "wb") as f:
                f.write(b"\x00" * 1000)

            # TICKET-1: Transcribe with explicit English (should override profile)
            result = stt.transcribe(audio_path, language="en")

            # TICKET-1: Explicit parameter overrides profile
            call_kwargs = mock_model.transcribe.call_args[1]
            self.assertEqual(call_kwargs.get("language"), "en")

    def test_backward_compatibility_no_profile(self):
        """Test backward compatibility when no profile exists"""
        with patch("janus.stt.whisper_stt.whisper.load_model") as mock_load_model, patch(
            "janus.stt.whisper_stt.pyaudio.PyAudio"
        ) as mock_pyaudio:
            from janus.io.stt.whisper_stt import WhisperSTT

            # Mock Whisper model
            mock_model = Mock()
            mock_model.transcribe.return_value = {"text": "test"}
            mock_load_model.return_value = mock_model
            mock_pyaudio.return_value = Mock()

            stt = WhisperSTT(
                model_size="base",
                enable_logging=False,
            )

            # Create a dummy audio file
            audio_path = os.path.join(self.temp_dir, "test.wav")
            with open(audio_path, "wb") as f:
                f.write(b"\x00" * 1000)

            # Transcribe with default language
            result = stt.transcribe(audio_path, language="en")

            # Should use provided language
            call_kwargs = mock_model.transcribe.call_args[1]
            self.assertEqual(call_kwargs.get("language"), "en")


if __name__ == "__main__":
    unittest.main()
