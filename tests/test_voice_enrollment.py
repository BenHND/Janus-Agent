"""
Unit tests for voice enrollment module (TICKET-STT-002)
Tests the enrollment process for speaker verification
"""
import os
import shutil
import sys
import tempfile
import unittest
import wave
from unittest.mock import Mock, patch, MagicMock, call
import numpy as np

# Mock resemblyzer module before importing
sys.modules['resemblyzer'] = MagicMock()

from janus.io.stt.voice_enrollment import VoiceEnrollmentManager, ENROLLMENT_PROMPTS
from janus.io.stt.speaker_verifier import SpeakerVerifier


class TestVoiceEnrollmentManager(unittest.TestCase):
    """Test cases for voice enrollment manager"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.embedding_path = os.path.join(self.temp_dir, "user_voice.npy")

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_enrollment_prompts_exist(self):
        """Test that enrollment prompts are defined"""
        self.assertIsNotNone(ENROLLMENT_PROMPTS)
        self.assertEqual(len(ENROLLMENT_PROMPTS), 3)
        for prompt in ENROLLMENT_PROMPTS:
            self.assertIsInstance(prompt, str)
            self.assertGreater(len(prompt), 0)

    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    @patch('janus.stt.speaker_verifier.VoiceEncoder')
    def test_initialization(self, mock_encoder):
        """Test enrollment manager initialization"""
        mock_encoder.return_value = Mock()
        verifier = SpeakerVerifier()
        recorder = Mock()

        manager = VoiceEnrollmentManager(
            verifier=verifier,
            recorder=recorder,
            embedding_path=self.embedding_path
        )

        self.assertEqual(manager.verifier, verifier)
        self.assertEqual(manager.recorder, recorder)
        self.assertEqual(manager.embedding_path, self.embedding_path)

    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    @patch('janus.stt.speaker_verifier.VoiceEncoder')
    def test_is_enrolled(self, mock_encoder):
        """Test enrollment status check"""
        mock_encoder.return_value = Mock()
        verifier = SpeakerVerifier()
        manager = VoiceEnrollmentManager(
            verifier=verifier,
            recorder=None,
            embedding_path=self.embedding_path
        )

        # Initially not enrolled
        self.assertFalse(manager.is_enrolled())

        # Create dummy embedding file
        np.save(self.embedding_path, np.random.rand(256))

        # Now should be enrolled
        self.assertTrue(manager.is_enrolled())

    def create_test_wav(self, path, duration_sec=1, sample_rate=16000):
        """Helper to create a test WAV file"""
        # Generate sine wave
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec))
        audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)

        with wave.open(path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())

    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    @patch('janus.stt.speaker_verifier.VoiceEncoder')
    def test_load_audio_from_wav(self, mock_encoder):
        """Test loading audio from WAV file"""
        mock_encoder.return_value = Mock()
        verifier = SpeakerVerifier()
        manager = VoiceEnrollmentManager(
            verifier=verifier,
            recorder=None,
            embedding_path=self.embedding_path
        )

        # Create test WAV file
        wav_path = os.path.join(self.temp_dir, "test.wav")
        self.create_test_wav(wav_path, duration_sec=2)

        # Load audio
        audio_data = manager.load_audio_from_wav(wav_path)

        self.assertIsNotNone(audio_data)
        self.assertEqual(audio_data.dtype, np.float32)
        self.assertGreater(len(audio_data), 0)
        # Check audio is normalized to [-1, 1]
        self.assertLessEqual(np.max(np.abs(audio_data)), 1.0)

    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    @patch('janus.stt.speaker_verifier.VoiceEncoder')
    def test_load_audio_from_nonexistent_file(self, mock_encoder):
        """Test loading audio from non-existent file"""
        mock_encoder.return_value = Mock()
        verifier = SpeakerVerifier()
        manager = VoiceEnrollmentManager(
            verifier=verifier,
            recorder=None,
            embedding_path=self.embedding_path
        )

        # Try to load non-existent file
        audio_data = manager.load_audio_from_wav("nonexistent.wav")
        self.assertIsNone(audio_data)

    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    @patch('janus.stt.speaker_verifier.VoiceEncoder')
    def test_record_sample(self, mock_encoder):
        """Test recording a single voice sample"""
        mock_encoder.return_value = Mock()
        verifier = SpeakerVerifier()

        # Mock recorder
        mock_recorder = Mock()
        wav_path = os.path.join(self.temp_dir, "recorded.wav")
        self.create_test_wav(wav_path, duration_sec=2)
        mock_recorder.record_audio.return_value = (wav_path, None)

        manager = VoiceEnrollmentManager(
            verifier=verifier,
            recorder=mock_recorder,
            embedding_path=self.embedding_path
        )

        # Record sample
        audio_data, error = manager.record_sample(prompt_number=0)

        self.assertIsNone(error)
        self.assertIsNotNone(audio_data)
        self.assertGreater(len(audio_data), verifier.sample_rate)  # At least 1 second
        mock_recorder.record_audio.assert_called_once()

    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    @patch('janus.stt.speaker_verifier.VoiceEncoder')
    def test_record_sample_too_short(self, mock_encoder):
        """Test recording rejection when audio is too short"""
        mock_encoder.return_value = Mock()
        verifier = SpeakerVerifier()

        # Mock recorder
        mock_recorder = Mock()
        wav_path = os.path.join(self.temp_dir, "recorded.wav")
        self.create_test_wav(wav_path, duration_sec=0.5)  # Too short
        mock_recorder.record_audio.return_value = (wav_path, None)

        manager = VoiceEnrollmentManager(
            verifier=verifier,
            recorder=mock_recorder,
            embedding_path=self.embedding_path
        )

        # Record sample
        audio_data, error = manager.record_sample(prompt_number=0)

        self.assertIsNone(audio_data)
        self.assertIsNotNone(error)
        self.assertIn("too short", error.lower())

    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    @patch('janus.stt.speaker_verifier.VoiceEncoder')
    def test_record_sample_recording_failed(self, mock_encoder):
        """Test handling of recording failure"""
        mock_encoder.return_value = Mock()
        verifier = SpeakerVerifier()

        # Mock recorder that fails
        mock_recorder = Mock()
        mock_recorder.record_audio.return_value = (None, "Recording failed")

        manager = VoiceEnrollmentManager(
            verifier=verifier,
            recorder=mock_recorder,
            embedding_path=self.embedding_path
        )

        # Try to record sample
        audio_data, error = manager.record_sample(prompt_number=0)

        self.assertIsNone(audio_data)
        self.assertEqual(error, "Recording failed")

    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    @patch('janus.stt.speaker_verifier.VoiceEncoder')
    @patch('janus.stt.speaker_verifier.preprocess_wav')
    def test_enroll_user_interactive_success(self, mock_preprocess, mock_encoder):
        """Test successful interactive enrollment"""
        # Mock encoder
        mock_encoder_instance = Mock()
        embeddings = [
            np.random.rand(256).astype(np.float32),
            np.random.rand(256).astype(np.float32),
            np.random.rand(256).astype(np.float32),
        ]
        mock_encoder_instance.embed_utterance.side_effect = embeddings
        mock_encoder.return_value = mock_encoder_instance

        # Mock preprocessing
        mock_preprocess.return_value = np.random.rand(16000).astype(np.float32)

        verifier = SpeakerVerifier()

        # Mock recorder
        mock_recorder = Mock()

        def mock_record(max_duration=8, on_audio_chunk=None):
            wav_path = os.path.join(self.temp_dir, f"recorded_{mock_recorder.record_audio.call_count}.wav")
            self.create_test_wav(wav_path, duration_sec=2)
            return (wav_path, None)

        mock_recorder.record_audio.side_effect = mock_record

        manager = VoiceEnrollmentManager(
            verifier=verifier,
            recorder=mock_recorder,
            embedding_path=self.embedding_path
        )

        # Track progress
        progress_calls = []

        def progress_callback(step, total, message):
            progress_calls.append((step, total, message))

        # Enroll user
        success, message = manager.enroll_user_interactive(on_progress=progress_callback)

        self.assertTrue(success)
        self.assertIn("success", message.lower())
        self.assertEqual(mock_recorder.record_audio.call_count, 3)
        self.assertTrue(os.path.exists(self.embedding_path))
        # Check progress was reported
        self.assertEqual(len(progress_calls), 4)  # 3 recordings + 1 processing

    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', False)
    def test_enroll_user_interactive_no_resemblyzer(self):
        """Test enrollment failure when resemblyzer is not available"""
        verifier = SpeakerVerifier()
        mock_recorder = Mock()

        manager = VoiceEnrollmentManager(
            verifier=verifier,
            recorder=mock_recorder,
            embedding_path=self.embedding_path
        )

        success, message = manager.enroll_user_interactive()

        self.assertFalse(success)
        self.assertIn("not available", message.lower())

    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    @patch('janus.stt.speaker_verifier.VoiceEncoder')
    def test_enroll_user_interactive_recording_failure(self, mock_encoder):
        """Test enrollment failure when recording fails"""
        mock_encoder.return_value = Mock()
        verifier = SpeakerVerifier()

        # Mock recorder that fails
        mock_recorder = Mock()
        mock_recorder.record_audio.return_value = (None, "Microphone error")

        manager = VoiceEnrollmentManager(
            verifier=verifier,
            recorder=mock_recorder,
            embedding_path=self.embedding_path
        )

        success, message = manager.enroll_user_interactive()

        self.assertFalse(success)
        self.assertIn("Failed to record", message)

    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    @patch('janus.stt.speaker_verifier.VoiceEncoder')
    def test_get_enrollment_prompts(self, mock_encoder):
        """Test getting enrollment prompts"""
        mock_encoder.return_value = Mock()
        verifier = SpeakerVerifier()
        manager = VoiceEnrollmentManager(
            verifier=verifier,
            recorder=None,
            embedding_path=self.embedding_path
        )

        prompts = manager.get_enrollment_prompts()

        self.assertEqual(len(prompts), 3)
        self.assertEqual(prompts, ENROLLMENT_PROMPTS)
        # Ensure we get a copy, not the original
        self.assertIsNot(prompts, ENROLLMENT_PROMPTS)


if __name__ == "__main__":
    unittest.main()
