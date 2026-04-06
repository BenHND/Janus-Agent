"""
Unit tests for speaker verification module (TICKET-STT-002)
Tests voice fingerprinting and speaker recognition functionality
"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# Mock resemblyzer module before importing speaker_verifier
sys.modules['resemblyzer'] = MagicMock()

from janus.io.stt.speaker_verifier import SpeakerVerifier


class TestSpeakerVerifier(unittest.TestCase):
    """Test cases for speaker verification"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.embedding_path = os.path.join(self.temp_dir, "test_voice.npy")

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', False)
    def test_initialization_without_resemblyzer(self):
        """Test initialization when resemblyzer is not available"""
        verifier = SpeakerVerifier()
        self.assertFalse(verifier.is_available())

    @patch('resemblyzer.VoiceEncoder')
    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    def test_initialization_with_resemblyzer(self, mock_encoder_class):
        """Test initialization when resemblyzer is available"""
        mock_encoder_class.return_value = Mock()
        verifier = SpeakerVerifier()
        self.assertTrue(verifier.is_available())
        mock_encoder_class.assert_called_once()

    @patch('resemblyzer.VoiceEncoder')
    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    def test_save_and_load_embedding(self, mock_encoder_class):
        """Test saving and loading voice embeddings"""
        mock_encoder_class.return_value = Mock()
        verifier = SpeakerVerifier()

        # Create a dummy embedding
        test_embedding = np.random.rand(256).astype(np.float32)

        # Save embedding
        success = verifier.save_user_embedding(test_embedding, self.embedding_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(self.embedding_path))

        # Create new verifier and load embedding
        verifier2 = SpeakerVerifier(embedding_path=self.embedding_path)
        self.assertIsNotNone(verifier2.user_embedding)
        np.testing.assert_array_equal(verifier2.user_embedding, test_embedding)

    @patch('resemblyzer.preprocess_wav')
    @patch('resemblyzer.VoiceEncoder')
    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    def test_extract_embedding(self, mock_encoder_class, mock_preprocess):
        """Test voice embedding extraction from audio"""
        # Mock encoder
        mock_encoder_instance = Mock()
        mock_embedding = np.random.rand(256).astype(np.float32)
        mock_encoder_instance.embed_utterance.return_value = mock_embedding
        mock_encoder_class.return_value = mock_encoder_instance

        # Mock preprocessing
        mock_preprocess.return_value = np.random.rand(16000).astype(np.float32)

        verifier = SpeakerVerifier()

        # Test with int16 audio
        audio_data = np.random.randint(-32768, 32767, 16000, dtype=np.int16)
        embedding = verifier.extract_embedding(audio_data)

        self.assertIsNotNone(embedding)
        np.testing.assert_array_equal(embedding, mock_embedding)
        mock_encoder_instance.embed_utterance.assert_called_once()

    def test_cosine_similarity(self):
        """Test cosine similarity calculation"""
        verifier = SpeakerVerifier()

        # Test identical vectors
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        similarity = verifier._cosine_similarity(vec1, vec2)
        self.assertAlmostEqual(similarity, 1.0, places=5)

        # Test orthogonal vectors (should be 0.0)
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        similarity = verifier._cosine_similarity(vec1, vec2)
        self.assertAlmostEqual(similarity, 0.0, places=5)

        # Test opposite vectors (should be -1.0)
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([-1.0, 0.0, 0.0])
        similarity = verifier._cosine_similarity(vec1, vec2)
        self.assertAlmostEqual(similarity, -1.0, places=5)

    @patch('resemblyzer.VoiceEncoder')
    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    def test_verify_speaker_without_enrollment(self, mock_encoder_class):
        """Test speaker verification without enrolled user"""
        mock_encoder_class.return_value = Mock()
        verifier = SpeakerVerifier()

        # Without user embedding, should accept by default
        audio_data = np.random.rand(16000).astype(np.float32)
        is_verified, similarity = verifier.verify_speaker(audio_data)

        self.assertTrue(is_verified)
        self.assertEqual(similarity, 1.0)

    @patch('resemblyzer.preprocess_wav')
    @patch('resemblyzer.VoiceEncoder')
    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    def test_verify_speaker_with_enrollment(self, mock_encoder_class, mock_preprocess):
        """Test speaker verification with enrolled user"""
        # Mock encoder
        mock_encoder_instance = Mock()
        user_embedding = np.random.rand(256).astype(np.float32)
        mock_encoder_instance.embed_utterance.return_value = user_embedding
        mock_encoder_class.return_value = mock_encoder_instance

        # Mock preprocessing
        mock_preprocess.return_value = np.random.rand(16000).astype(np.float32)

        verifier = SpeakerVerifier(similarity_threshold=0.75)
        verifier.user_embedding = user_embedding

        # Test with same embedding (should verify)
        audio_data = np.random.rand(16000).astype(np.float32)
        is_verified, similarity = verifier.verify_speaker(audio_data)

        self.assertTrue(is_verified)
        self.assertGreater(similarity, 0.75)

    @patch('resemblyzer.preprocess_wav')
    @patch('resemblyzer.VoiceEncoder')
    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    def test_verify_speaker_rejection(self, mock_encoder_class, mock_preprocess):
        """Test speaker rejection when similarity is below threshold"""
        # Mock encoder to return orthogonal embeddings (similarity = 0.0)
        mock_encoder_instance = Mock()
        # Create orthogonal unit vectors
        user_embedding = np.zeros(256, dtype=np.float32)
        user_embedding[0] = 1.0  # [1, 0, 0, ...]
        
        different_embedding = np.zeros(256, dtype=np.float32)
        different_embedding[1] = 1.0  # [0, 1, 0, ...]
        
        mock_encoder_instance.embed_utterance.return_value = different_embedding
        mock_encoder_class.return_value = mock_encoder_instance

        # Mock preprocessing
        mock_preprocess.return_value = np.random.rand(16000).astype(np.float32)

        verifier = SpeakerVerifier(similarity_threshold=0.75)
        verifier.user_embedding = user_embedding

        # Test with orthogonal embedding (similarity = 0.0, should reject)
        audio_data = np.random.rand(16000).astype(np.float32)
        is_verified, similarity = verifier.verify_speaker(audio_data)

        self.assertFalse(is_verified)
        self.assertLess(similarity, 0.75)
        self.assertAlmostEqual(similarity, 0.0, places=5)

    @patch('resemblyzer.preprocess_wav')
    @patch('resemblyzer.VoiceEncoder')
    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    def test_enroll_user_with_multiple_samples(self, mock_encoder_class, mock_preprocess):
        """Test user enrollment with multiple audio samples"""
        # Mock encoder
        mock_encoder_instance = Mock()
        embeddings = [
            np.random.rand(256).astype(np.float32),
            np.random.rand(256).astype(np.float32),
            np.random.rand(256).astype(np.float32),
        ]
        mock_encoder_instance.embed_utterance.side_effect = embeddings
        mock_encoder_class.return_value = mock_encoder_instance

        # Mock preprocessing
        mock_preprocess.return_value = np.random.rand(16000).astype(np.float32)

        verifier = SpeakerVerifier()

        # Enroll with 3 samples
        audio_samples = [
            np.random.rand(16000).astype(np.float32),
            np.random.rand(16000).astype(np.float32),
            np.random.rand(16000).astype(np.float32),
        ]

        user_embedding = verifier.enroll_user(audio_samples)

        self.assertIsNotNone(user_embedding)
        self.assertEqual(len(user_embedding), 256)
        # Should be average of the embeddings
        expected = np.mean(embeddings, axis=0)
        np.testing.assert_array_almost_equal(user_embedding, expected, decimal=5)

    @patch('resemblyzer.VoiceEncoder')
    @patch('janus.stt.speaker_verifier.HAS_RESEMBLYZER', True)
    def test_enroll_user_insufficient_samples(self, mock_encoder_class):
        """Test enrollment failure with insufficient samples"""
        mock_encoder_class.return_value = Mock()
        verifier = SpeakerVerifier()

        # Try to enroll with only 1 sample
        audio_samples = [np.random.rand(16000).astype(np.float32)]
        user_embedding = verifier.enroll_user(audio_samples)

        self.assertIsNone(user_embedding)


if __name__ == "__main__":
    unittest.main()
