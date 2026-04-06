"""
Integration tests for enhanced WhisperSTT
Tests the integration of all new features
"""
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch

from janus.io.stt.whisper_stt import WhisperSTT


class TestWhisperSTTIntegration(unittest.TestCase):
    """Integration test cases for enhanced WhisperSTT"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("janus.stt.whisper_stt.whisper.load_model")
    @patch("janus.stt.whisper_stt.pyaudio.PyAudio")
    def test_initialization_with_all_features(self, mock_pyaudio, mock_load_model):
        """Test initialization with all features enabled"""
        mock_load_model.return_value = Mock()
        mock_pyaudio.return_value = Mock()

        stt = WhisperSTT(
            model_size="base",
            enable_corrections=True,
            enable_normalization=True,
            enable_logging=True,
            log_dir=self.temp_dir,
            user_id="test_user",
        )

        self.assertIsNotNone(stt.correction_dict)
        self.assertIsNotNone(stt.normalizer)
        self.assertIsNotNone(stt.logger)
        self.assertIsNotNone(stt.calibration_manager)
        self.assertIsNotNone(stt.calibration_profile)

    @patch("janus.stt.whisper_stt.whisper.load_model")
    @patch("janus.stt.whisper_stt.pyaudio.PyAudio")
    def test_initialization_with_features_disabled(self, mock_pyaudio, mock_load_model):
        """Test initialization with features disabled"""
        mock_load_model.return_value = Mock()
        mock_pyaudio.return_value = Mock()

        stt = WhisperSTT(
            model_size="base",
            enable_corrections=False,
            enable_normalization=False,
            enable_logging=False,
            log_dir=self.temp_dir,
            user_id="test_user",
        )

        self.assertIsNone(stt.correction_dict)
        self.assertIsNone(stt.normalizer)
        self.assertIsNone(stt.logger)

    @patch("janus.stt.whisper_stt.whisper.load_model")
    @patch("janus.stt.whisper_stt.pyaudio.PyAudio")
    def test_transcribe_with_corrections(self, mock_pyaudio, mock_load_model):
        """Test transcription with correction dictionary"""
        # Mock Whisper model
        mock_model = Mock()
        mock_model.transcribe.return_value = {"text": "ouvre vs code"}
        mock_load_model.return_value = mock_model
        mock_pyaudio.return_value = Mock()

        stt = WhisperSTT(
            model_size="base",
            enable_corrections=True,
            enable_normalization=False,
            enable_logging=False,
            log_dir=self.temp_dir,
            user_id="test_user",
        )

        # Create a dummy audio file
        audio_path = os.path.join(self.temp_dir, "test.wav")
        with open(audio_path, "wb") as f:
            f.write(b"\x00" * 1000)

        result = stt.transcribe(audio_path, "fr")

        self.assertTrue(result["success"])
        self.assertEqual(result["raw"], "ouvre vs code")
        self.assertIn("vscode", result["corrected"].lower())

    @patch("janus.stt.whisper_stt.whisper.load_model")
    @patch("janus.stt.whisper_stt.pyaudio.PyAudio")
    def test_transcribe_with_normalization(self, mock_pyaudio, mock_load_model):
        """Test transcription with text normalization"""
        # Mock Whisper model
        mock_model = Mock()
        mock_model.transcribe.return_value = {"text": "euh ouvre le navigateur"}
        mock_load_model.return_value = mock_model
        mock_pyaudio.return_value = Mock()

        stt = WhisperSTT(
            model_size="base",
            enable_corrections=False,
            enable_normalization=True,
            enable_logging=False,
            log_dir=self.temp_dir,
            user_id="test_user",
        )

        # Create a dummy audio file
        audio_path = os.path.join(self.temp_dir, "test.wav")
        with open(audio_path, "wb") as f:
            f.write(b"\x00" * 1000)

        result = stt.transcribe(audio_path, "fr")

        self.assertTrue(result["success"])
        self.assertEqual(result["raw"], "euh ouvre le navigateur")
        # Normalized should not contain "euh"
        self.assertNotIn("euh", result["normalized"].lower())

    @patch("janus.stt.whisper_stt.whisper.load_model")
    @patch("janus.stt.whisper_stt.pyaudio.PyAudio")
    def test_transcribe_full_pipeline(self, mock_pyaudio, mock_load_model):
        """Test transcription with full pipeline (corrections + normalization)"""
        # Mock Whisper model
        mock_model = Mock()
        mock_model.transcribe.return_value = {"text": "euh ouvre vs code"}
        mock_load_model.return_value = mock_model
        mock_pyaudio.return_value = Mock()

        stt = WhisperSTT(
            model_size="base",
            enable_corrections=True,
            enable_normalization=True,
            enable_logging=False,
            log_dir=self.temp_dir,
            user_id="test_user",
        )

        # Create a dummy audio file
        audio_path = os.path.join(self.temp_dir, "test.wav")
        with open(audio_path, "wb") as f:
            f.write(b"\x00" * 1000)

        result = stt.transcribe(audio_path, "fr")

        self.assertTrue(result["success"])
        self.assertEqual(result["raw"], "euh ouvre vs code")
        self.assertIn("vscode", result["final"].lower())
        self.assertNotIn("euh", result["final"].lower())

    @patch("janus.stt.whisper_stt.whisper.load_model")
    @patch("janus.stt.whisper_stt.pyaudio.PyAudio")
    def test_transcribe_with_logging(self, mock_pyaudio, mock_load_model):
        """Test transcription with logging enabled"""
        # Mock Whisper model
        mock_model = Mock()
        mock_model.transcribe.return_value = {"text": "test transcription"}
        mock_load_model.return_value = mock_model
        mock_pyaudio.return_value = Mock()

        stt = WhisperSTT(
            model_size="base",
            enable_corrections=False,
            enable_normalization=False,
            enable_logging=True,
            log_dir=self.temp_dir,
            user_id="test_user",
        )

        # Create a dummy audio file
        audio_path = os.path.join(self.temp_dir, "test.wav")
        with open(audio_path, "wb") as f:
            f.write(b"\x00" * 1000)

        result = stt.transcribe(audio_path, "fr")

        self.assertTrue(result["success"])

        # Verify log was created
        logs = stt.get_recent_logs(count=1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["raw_transcription"], "test transcription")

    @patch("janus.stt.whisper_stt.whisper.load_model")
    @patch("janus.stt.whisper_stt.pyaudio.PyAudio")
    def test_transcribe_error_handling(self, mock_pyaudio, mock_load_model):
        """Test error handling in transcription"""
        # Mock Whisper model to raise error
        mock_model = Mock()
        mock_model.transcribe.side_effect = Exception("Test error")
        mock_load_model.return_value = mock_model
        mock_pyaudio.return_value = Mock()

        stt = WhisperSTT(
            model_size="base", enable_logging=True, log_dir=self.temp_dir, user_id="test_user"
        )

        # Create a dummy audio file
        audio_path = os.path.join(self.temp_dir, "test.wav")
        with open(audio_path, "wb") as f:
            f.write(b"\x00" * 1000)

        result = stt.transcribe(audio_path, "fr")

        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["final"], "")

    @patch("janus.stt.whisper_stt.whisper.load_model")
    @patch("janus.stt.whisper_stt.pyaudio.PyAudio")
    def test_add_custom_correction(self, mock_pyaudio, mock_load_model):
        """Test adding custom corrections"""
        mock_load_model.return_value = Mock()
        mock_pyaudio.return_value = Mock()

        stt = WhisperSTT(
            model_size="base",
            enable_corrections=True,
            enable_logging=False,
            log_dir=self.temp_dir,
            user_id="test_user",
        )

        # Add custom correction
        stt.add_custom_correction("git lab", "gitlab")

        # Verify it's in the dictionary
        corrections = stt.correction_dict.get_corrections()
        self.assertIn("git lab", corrections)

    @patch("janus.stt.whisper_stt.whisper.load_model")
    @patch("janus.stt.whisper_stt.pyaudio.PyAudio")
    def test_get_logger_stats(self, mock_pyaudio, mock_load_model):
        """Test getting logger statistics"""
        mock_model = Mock()
        mock_model.transcribe.return_value = {"text": "test"}
        mock_load_model.return_value = mock_model
        mock_pyaudio.return_value = Mock()

        stt = WhisperSTT(
            model_size="base", enable_logging=True, log_dir=self.temp_dir, user_id="test_user"
        )

        # Create a dummy audio file and transcribe
        audio_path = os.path.join(self.temp_dir, "test.wav")
        with open(audio_path, "wb") as f:
            f.write(b"\x00" * 1000)

        stt.transcribe(audio_path, "fr")

        # Get stats
        stats = stt.get_logger_stats()

        self.assertIsNotNone(stats)
        self.assertEqual(stats["total_logs"], 1)

    @patch("janus.stt.whisper_stt.whisper.load_model")
    @patch("janus.stt.whisper_stt.pyaudio.PyAudio")
    def test_calibration_profile_loaded(self, mock_pyaudio, mock_load_model):
        """Test that calibration profile is loaded on init"""
        mock_load_model.return_value = Mock()
        mock_pyaudio.return_value = Mock()

        stt = WhisperSTT(model_size="base", log_dir=self.temp_dir, user_id="test_user")

        # Should have a calibration profile
        self.assertIsNotNone(stt.calibration_profile)
        self.assertEqual(stt.calibration_profile.user_id, "test_user")


if __name__ == "__main__":
    unittest.main()
