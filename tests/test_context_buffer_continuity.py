"""
Tests for Phase 15.3 - Context Buffer Continuity
Ensures no lost/truncated words across segments
"""
import unittest

import numpy as np

from janus.io.stt.context_buffer import ContextBuffer


class TestContextBufferContinuity(unittest.TestCase):
    """Test cases for Context Buffer Manager (Phase 15.3)"""

    def setUp(self):
        """Set up test fixtures"""
        self.buffer = ContextBuffer(
            buffer_duration_sec=2.5, overlap_duration_sec=1.0, sample_rate=16000
        )

    def test_initialization(self):
        """Test buffer initialization"""
        self.assertEqual(self.buffer.buffer_duration_sec, 2.5)
        self.assertEqual(self.buffer.overlap_duration_sec, 1.0)
        self.assertEqual(self.buffer.sample_rate, 16000)
        self.assertEqual(self.buffer.total_segments, 0)

    def test_add_audio_segment(self):
        """Test adding audio segments to buffer"""
        # Create test audio (1 second of data)
        audio = np.random.randint(-1000, 1000, 16000, dtype=np.int16)

        self.buffer.add_audio_segment(audio)

        self.assertEqual(self.buffer.total_segments, 1)
        self.assertEqual(len(self.buffer.audio_buffer), 1)

    def test_get_overlap_audio(self):
        """Test retrieving overlap audio from previous segment"""
        # Add a segment
        audio = np.random.randint(-1000, 1000, 16000, dtype=np.int16)
        self.buffer.add_audio_segment(audio)

        # Get overlap
        overlap = self.buffer.get_overlap_audio()

        self.assertIsNotNone(overlap)
        # Overlap should be 1 second (16000 samples)
        self.assertEqual(len(overlap), 16000)

    def test_get_overlap_empty_buffer(self):
        """Test getting overlap from empty buffer"""
        overlap = self.buffer.get_overlap_audio()
        self.assertIsNone(overlap)

    def test_concatenate_with_overlap(self):
        """Test concatenating new audio with overlap"""
        # Add first segment
        audio1 = np.random.randint(-1000, 1000, 16000, dtype=np.int16)
        self.buffer.add_audio_segment(audio1)

        # Create second segment
        audio2 = np.random.randint(-1000, 1000, 16000, dtype=np.int16)

        # Concatenate with overlap
        concatenated = self.buffer.concatenate_with_overlap(audio2, prepend_overlap=True)

        # Should be: overlap (16000) + new audio (16000) = 32000 samples
        self.assertEqual(len(concatenated), 32000)

    def test_concatenate_without_overlap(self):
        """Test concatenation without overlap"""
        audio = np.random.randint(-1000, 1000, 16000, dtype=np.int16)

        concatenated = self.buffer.concatenate_with_overlap(audio, prepend_overlap=False)

        # Should be same as input
        np.testing.assert_array_equal(concatenated, audio)

    def test_text_checksum(self):
        """Test text checksum computation"""
        text = "Hello World"
        checksum1 = self.buffer.compute_text_checksum(text)
        checksum2 = self.buffer.compute_text_checksum(text)

        # Same text should produce same checksum
        self.assertEqual(checksum1, checksum2)

        # Different text should produce different checksum
        checksum3 = self.buffer.compute_text_checksum("Different text")
        self.assertNotEqual(checksum1, checksum3)

    def test_checksum_normalization(self):
        """Test that checksums normalize text"""
        checksum1 = self.buffer.compute_text_checksum("Hello World")
        checksum2 = self.buffer.compute_text_checksum("hello world")
        checksum3 = self.buffer.compute_text_checksum("  Hello World  ")

        # Should all be equal (case-insensitive, whitespace-trimmed)
        self.assertEqual(checksum1, checksum2)
        self.assertEqual(checksum1, checksum3)

    def test_duplicate_detection(self):
        """Test duplicate text detection"""
        text = "This is a test"

        # First occurrence - not duplicate
        is_dup1 = self.buffer.is_duplicate_text(text)
        self.assertFalse(is_dup1)

        # Second occurrence - is duplicate
        is_dup2 = self.buffer.is_duplicate_text(text)
        self.assertTrue(is_dup2)

        self.assertEqual(self.buffer.duplicates_detected, 1)

    def test_merge_transcriptions_with_overlap(self):
        """Test merging transcriptions with overlapping words"""
        previous = "open the browser"
        current = "the browser window"  # "the browser" overlaps

        merged = self.buffer.merge_transcriptions(previous, current, overlap_words=3)

        # Should remove duplicate "the browser"
        self.assertEqual(merged, "open the browser window")

    def test_merge_transcriptions_no_overlap(self):
        """Test merging transcriptions without overlap"""
        previous = "open the"
        current = "new window"  # No overlap

        merged = self.buffer.merge_transcriptions(previous, current, overlap_words=3)

        # Should concatenate
        self.assertEqual(merged, "open the new window")

    def test_merge_transcriptions_empty_previous(self):
        """Test merging with empty previous text"""
        previous = ""
        current = "hello world"

        merged = self.buffer.merge_transcriptions(previous, current)

        self.assertEqual(merged, "hello world")

    def test_merge_transcriptions_partial_overlap(self):
        """Test merging with partial word overlap"""
        previous = "the quick brown"
        current = "brown fox jumps"  # "brown" overlaps

        merged = self.buffer.merge_transcriptions(previous, current, overlap_words=3)

        # Should remove duplicate "brown"
        self.assertEqual(merged, "the quick brown fox jumps")

    def test_clear_buffer(self):
        """Test clearing all buffers"""
        # Add some data
        audio = np.random.randint(-1000, 1000, 16000, dtype=np.int16)
        self.buffer.add_audio_segment(audio)
        self.buffer.is_duplicate_text("test")

        # Clear
        self.buffer.clear()

        self.assertEqual(len(self.buffer.audio_buffer), 0)
        self.assertEqual(len(self.buffer.text_checksums), 0)
        self.assertEqual(self.buffer.total_segments, 0)
        self.assertEqual(self.buffer.duplicates_detected, 0)

    def test_statistics(self):
        """Test getting buffer statistics"""
        # Add segments
        for _ in range(3):
            audio = np.random.randint(-1000, 1000, 16000, dtype=np.int16)
            self.buffer.add_audio_segment(audio)
            concatenated = self.buffer.concatenate_with_overlap(audio, prepend_overlap=True)

        stats = self.buffer.get_statistics()

        self.assertEqual(stats["total_segments"], 3)
        self.assertEqual(stats["buffer_size"], 3)
        self.assertGreater(stats["avg_overlap_duration_sec"], 0)

    def test_full_buffer_audio(self):
        """Test getting full buffered audio"""
        # Add multiple segments
        for i in range(3):
            audio = np.random.randint(-1000, 1000, 16000, dtype=np.int16)
            self.buffer.add_audio_segment(audio)

        full_audio = self.buffer.get_full_buffer_audio()

        self.assertIsNotNone(full_audio)
        # Should concatenate all segments
        self.assertGreater(len(full_audio), 0)

    def test_latency_estimation(self):
        """Test latency estimation"""
        latency_ms = self.buffer.estimate_latency_ms()

        # Should be under 150ms as per requirements
        self.assertLess(latency_ms, 150)
        self.assertGreater(latency_ms, 0)

    def test_max_buffer_segments(self):
        """Test that buffer respects max_buffer_segments limit"""
        buffer = ContextBuffer(max_buffer_segments=5)

        # Add more segments than max
        for i in range(10):
            audio = np.random.randint(-1000, 1000, 1000, dtype=np.int16)
            buffer.add_audio_segment(audio)

        # Should only keep last 5
        self.assertEqual(len(buffer.audio_buffer), 5)
        self.assertEqual(buffer.total_segments, 10)

    def test_float32_to_int16_conversion(self):
        """Test automatic conversion of float32 audio to int16"""
        # Create float32 audio
        audio_float = np.random.uniform(-1.0, 1.0, 16000).astype(np.float32)

        self.buffer.add_audio_segment(audio_float)

        # Should convert and store
        self.assertEqual(self.buffer.total_segments, 1)

        # Retrieved audio should be int16
        overlap = self.buffer.get_overlap_audio()
        self.assertEqual(overlap.dtype, np.int16)

    def test_no_word_truncation(self):
        """Test that context buffer prevents word truncation"""
        # Simulate scenario where word is split across segments
        previous = "open the brow"  # Truncated "browser"
        current = "browser window"  # Complete word

        # Merge should handle this gracefully
        merged = self.buffer.merge_transcriptions(previous, current, overlap_words=2)

        # Should produce sensible result
        self.assertIn("browser", merged)
        self.assertIn("window", merged)


if __name__ == "__main__":
    unittest.main()
