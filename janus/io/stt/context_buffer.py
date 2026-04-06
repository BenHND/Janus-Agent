"""
Context Buffer Manager for continuous transcription
Phase 15.3 - Maintains rolling audio buffer to prevent truncated words across segments
"""

import hashlib
from collections import deque
from typing import List, Optional, Tuple

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class ContextBuffer:
    """
    Manages rolling audio buffer for continuous transcription

    Features:
    - Maintains 2-3 second rolling buffer of past audio
    - Concatenates overlap to prevent word truncation
    - Checksum-based duplicate detection
    - Minimal latency overhead (< 150ms target)
    """

    def __init__(
        self,
        buffer_duration_sec: float = 2.5,
        overlap_duration_sec: float = 1.0,
        sample_rate: int = 16000,
        max_buffer_segments: int = 10,
    ):
        """
        Initialize Context Buffer

        Args:
            buffer_duration_sec: Duration of rolling buffer in seconds (2-3s recommended)
            overlap_duration_sec: Duration of overlap to concatenate between segments
            sample_rate: Audio sample rate in Hz
            max_buffer_segments: Maximum number of segments to keep in buffer
        """
        self.buffer_duration_sec = buffer_duration_sec
        self.overlap_duration_sec = overlap_duration_sec
        self.sample_rate = sample_rate
        self.max_buffer_segments = max_buffer_segments

        # Calculate buffer sizes
        self.buffer_size_samples = int(buffer_duration_sec * sample_rate)
        self.overlap_size_samples = int(overlap_duration_sec * sample_rate)

        # Rolling buffer (stores raw audio data)
        self.audio_buffer = deque(maxlen=max_buffer_segments)

        # Text checksums to prevent duplicates
        self.text_checksums = set()

        # Statistics
        self.total_segments = 0
        self.duplicates_detected = 0
        self.total_overlap_samples = 0

    def add_audio_segment(self, audio_data: "np.ndarray") -> None:
        """
        Add audio segment to rolling buffer

        Args:
            audio_data: Audio data as numpy array (int16 or float32)
        """
        if not HAS_NUMPY:
            raise RuntimeError("numpy is required for ContextBuffer audio operations")

        import numpy as np

        # Convert to int16 if needed
        if audio_data.dtype == np.float32:
            audio_data = (audio_data * 32768).astype(np.int16)
        elif audio_data.dtype != np.int16:
            audio_data = audio_data.astype(np.int16)

        # Add to buffer
        self.audio_buffer.append(audio_data.copy())
        self.total_segments += 1

    def get_overlap_audio(self) -> Optional["np.ndarray"]:
        """
        Get overlap audio from previous segment

        Returns:
            Overlap audio as numpy array, or None if buffer is empty
        """
        if not self.audio_buffer:
            return None

        # Get last segment
        last_segment = self.audio_buffer[-1]

        # Extract overlap portion (last N seconds)
        if len(last_segment) <= self.overlap_size_samples:
            # Entire segment is shorter than overlap - use all of it
            return last_segment.copy()
        else:
            # Extract last N seconds
            overlap = last_segment[-self.overlap_size_samples :].copy()
            return overlap

    def concatenate_with_overlap(
        self, new_audio: "np.ndarray", prepend_overlap: bool = True
    ) -> "np.ndarray":
        """
        Concatenate new audio with overlap from previous segment

        Args:
            new_audio: New audio data to process
            prepend_overlap: If True, prepend overlap to new audio

        Returns:
            Concatenated audio with overlap
        """
        if not HAS_NUMPY:
            raise RuntimeError("numpy is required for ContextBuffer audio operations")

        import numpy as np

        if not prepend_overlap or not self.audio_buffer:
            # No overlap needed
            return new_audio

        # Get overlap from previous segment
        overlap = self.get_overlap_audio()
        if overlap is None:
            return new_audio

        # Concatenate overlap + new audio
        concatenated = np.concatenate([overlap, new_audio])
        self.total_overlap_samples += len(overlap)

        return concatenated

    def compute_text_checksum(self, text: str) -> str:
        """
        Compute checksum for text to detect duplicates

        Args:
            text: Text to checksum

        Returns:
            Checksum string
        """
        # Normalize text (lowercase, strip whitespace)
        normalized = text.lower().strip()

        # Compute SHA256 hash
        checksum = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

        return checksum

    def is_duplicate_text(self, text: str) -> bool:
        """
        Check if text is a duplicate based on checksum

        Args:
            text: Text to check

        Returns:
            True if duplicate, False otherwise
        """
        checksum = self.compute_text_checksum(text)

        if checksum in self.text_checksums:
            self.duplicates_detected += 1
            return True

        # Add to checksums
        self.text_checksums.add(checksum)

        # Limit checksum history to prevent memory growth
        if len(self.text_checksums) > 100:
            # Remove oldest checksums (approximate LRU)
            oldest = list(self.text_checksums)[:20]
            self.text_checksums -= set(oldest)

        return False

    def merge_transcriptions(
        self, previous_text: str, current_text: str, overlap_words: int = 3
    ) -> str:
        """
        Merge transcriptions, removing duplicate words at overlap boundary

        Args:
            previous_text: Previous transcription
            current_text: Current transcription (with overlap)
            overlap_words: Number of words to check for overlap

        Returns:
            Merged transcription
        """
        if not previous_text:
            return current_text

        # Split into words
        prev_words = previous_text.split()
        curr_words = current_text.split()

        if not prev_words or not curr_words:
            return previous_text + " " + current_text

        # Check for overlap at word level
        best_match_idx = 0
        max_match_len = 0

        # Look for longest matching sequence
        for i in range(min(overlap_words, len(prev_words))):
            suffix = prev_words[-overlap_words + i :]

            # Try to find this suffix at start of current text
            match_len = 0
            for j, word in enumerate(suffix):
                if j < len(curr_words) and curr_words[j].lower() == word.lower():
                    match_len += 1
                else:
                    break

            if match_len > max_match_len:
                max_match_len = match_len
                best_match_idx = len(suffix) - match_len

        # Merge, removing duplicate words
        if max_match_len > 0:
            # Skip the duplicate words in current text
            merged = previous_text + " " + " ".join(curr_words[max_match_len:])
        else:
            # No overlap found, simple concatenation
            merged = previous_text + " " + current_text

        return merged.strip()

    def clear(self):
        """Clear all buffers and reset state"""
        self.audio_buffer.clear()
        self.text_checksums.clear()
        self.total_segments = 0
        self.duplicates_detected = 0
        self.total_overlap_samples = 0

    def get_statistics(self) -> dict:
        """
        Get buffer statistics

        Returns:
            Dictionary with statistics
        """
        avg_overlap_duration = 0.0
        if self.total_segments > 0:
            avg_overlap_duration = (
                self.total_overlap_samples / self.sample_rate / max(1, self.total_segments - 1)
            )

        return {
            "total_segments": self.total_segments,
            "duplicates_detected": self.duplicates_detected,
            "buffer_size": len(self.audio_buffer),
            "buffer_duration_sec": self.buffer_duration_sec,
            "overlap_duration_sec": self.overlap_duration_sec,
            "avg_overlap_duration_sec": avg_overlap_duration,
            "checksums_stored": len(self.text_checksums),
        }

    def get_full_buffer_audio(self) -> Optional["np.ndarray"]:
        """
        Get entire buffered audio as single array

        Returns:
            Concatenated audio buffer, or None if empty
        """
        if not HAS_NUMPY:
            raise RuntimeError("numpy is required for ContextBuffer audio operations")

        import numpy as np

        if not self.audio_buffer:
            return None

        # Concatenate all segments
        full_audio = np.concatenate(list(self.audio_buffer))

        # Limit to buffer duration
        if len(full_audio) > self.buffer_size_samples:
            full_audio = full_audio[-self.buffer_size_samples :]

        return full_audio

    def estimate_latency_ms(self) -> float:
        """
        Estimate latency overhead introduced by buffering

        Returns:
            Estimated latency in milliseconds
        """
        # Latency from overlap processing
        overlap_latency_ms = (self.overlap_duration_sec * 1000) / 10  # ~10% overhead

        # Latency from concatenation
        concat_latency_ms = 5.0  # Fixed overhead for array operations

        # Total estimated latency
        total_latency_ms = overlap_latency_ms + concat_latency_ms

        return total_latency_ms
