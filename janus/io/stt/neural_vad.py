"""
Neural Voice Activity Detection using Silero VAD
Phase 15.2 - Replaces threshold-based VAD with neural network for precise speech segmentation
"""

import warnings
from typing import List, Optional, Tuple

import numpy as np

from janus.logging import get_logger

try:
    import torch

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    warnings.warn("torch not installed - NeuralVAD will not be available")


class NeuralVAD:
    """
    Neural Voice Activity Detection using Silero VAD model

    Features:
    - Windowed analysis for streaming mode
    - Adaptive threshold adjustment
    - High precision speech/silence boundaries
    - Lower false positive rate than amplitude-based VAD
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 100,
        window_size_samples: int = 512,
    ):
        """
        Initialize Neural VAD

        Args:
            sample_rate: Audio sample rate in Hz (8000 or 16000)
            threshold: Speech probability threshold (0.0 to 1.0)
            min_speech_duration_ms: Minimum speech duration to trigger detection
            min_silence_duration_ms: Minimum silence duration to end speech
            window_size_samples: Window size for analysis (512 or 1536 samples)
        """
        if not HAS_TORCH:
            raise RuntimeError("torch is required for NeuralVAD. Install with: pip install torch")

        self.logger = get_logger("neural_vad")
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms
        self.window_size_samples = window_size_samples

        # Load Silero VAD model
        self.model = None
        self.utils = None
        self._load_model()

        # State tracking for streaming
        self.reset_states()

    def _load_model(self):
        """Load Silero VAD model from torch hub"""
        try:
            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=False,
            )
            self.model = model
            self.utils = utils

            # Extract utility functions
            (
                self.get_speech_timestamps,
                self.save_audio,
                self.read_audio,
                self.VADIterator,
                self.collect_chunks,
            ) = utils

            self.logger.info("Silero VAD model loaded successfully")
        except Exception as e:
            raise RuntimeError(f"Failed to load Silero VAD model: {e}")

    def reset_states(self):
        """Reset internal states for new stream"""
        if self.model is not None:
            self.model.reset_states()
        self.speech_started = False
        self.speech_frames = []
        self.silence_frames = 0

    def is_speech(self, audio_chunk: bytes) -> bool:
        """
        Determine if audio chunk contains speech using neural VAD

        Args:
            audio_chunk: Raw audio bytes (16-bit PCM)

        Returns:
            True if speech is detected, False otherwise
        """
        # Convert bytes to float32 tensor
        audio_int16 = np.frombuffer(audio_chunk, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        audio_tensor = torch.from_numpy(audio_float32)

        # Get speech probability
        speech_prob = self.model(audio_tensor, self.sample_rate).item()

        return speech_prob >= self.threshold

    def get_speech_probability(self, audio_chunk: bytes) -> float:
        """
        Get speech probability for audio chunk

        Args:
            audio_chunk: Raw audio bytes (16-bit PCM)

        Returns:
            Speech probability (0.0 to 1.0)
        """
        # Convert bytes to float32 tensor
        audio_int16 = np.frombuffer(audio_chunk, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        audio_tensor = torch.from_numpy(audio_float32)

        # Get speech probability
        speech_prob = self.model(audio_tensor, self.sample_rate).item()

        return speech_prob

    def detect_speech_segments(
        self, audio_data: np.ndarray, return_seconds: bool = False
    ) -> List[Tuple[int, int]]:
        """
        Detect all speech segments in audio data

        Args:
            audio_data: Audio data as numpy array (float32, range -1 to 1)
            return_seconds: If True, return timestamps in seconds instead of samples

        Returns:
            List of (start, end) tuples for each speech segment
        """
        # Convert to tensor if needed
        if isinstance(audio_data, np.ndarray):
            audio_tensor = torch.from_numpy(audio_data)
        else:
            audio_tensor = audio_data

        # Get speech timestamps
        speech_timestamps = self.get_speech_timestamps(
            audio_tensor,
            self.model,
            sampling_rate=self.sample_rate,
            threshold=self.threshold,
            min_speech_duration_ms=self.min_speech_duration_ms,
            min_silence_duration_ms=self.min_silence_duration_ms,
            window_size_samples=self.window_size_samples,
            return_seconds=return_seconds,
        )

        # Extract start/end pairs
        segments = [(ts["start"], ts["end"]) for ts in speech_timestamps]

        return segments

    def process_streaming_chunk(
        self, audio_chunk: bytes, vad_iterator: Optional[object] = None
    ) -> Tuple[bool, Optional[object]]:
        """
        Process audio chunk in streaming mode with VADIterator

        Args:
            audio_chunk: Raw audio bytes (16-bit PCM)
            vad_iterator: Optional VADIterator instance (will create if None)

        Returns:
            Tuple of (speech_detected, vad_iterator)
        """
        # Create VADIterator if not provided
        if vad_iterator is None:
            vad_iterator = self.VADIterator(
                self.model,
                threshold=self.threshold,
                sampling_rate=self.sample_rate,
                min_silence_duration_ms=self.min_silence_duration_ms,
                speech_pad_ms=30,
            )

        # Convert bytes to float32 tensor
        audio_int16 = np.frombuffer(audio_chunk, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        audio_tensor = torch.from_numpy(audio_float32)

        # Process chunk
        speech_dict = vad_iterator(audio_tensor, return_seconds=False)

        # Check if speech was detected
        speech_detected = speech_dict is not None

        return speech_detected, vad_iterator

    def set_threshold(self, threshold: float):
        """
        Update speech detection threshold

        Args:
            threshold: New threshold (0.0 to 1.0)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        self.threshold = threshold

    def set_aggressiveness(self, aggressiveness: int):
        """
        Set VAD aggressiveness (compatibility method for webrtcvad interface)

        Args:
            aggressiveness: 0-3, higher = more aggressive
                          This maps to threshold: 0→0.3, 1→0.4, 2→0.5, 3→0.6
        """
        threshold_map = {0: 0.3, 1: 0.4, 2: 0.5, 3: 0.6}
        if aggressiveness not in threshold_map:
            raise ValueError("Aggressiveness must be 0-3")
        self.threshold = threshold_map[aggressiveness]

    def get_config(self) -> dict:
        """
        Get current VAD configuration

        Returns:
            Dictionary with current settings
        """
        return {
            "sample_rate": self.sample_rate,
            "threshold": self.threshold,
            "min_speech_duration_ms": self.min_speech_duration_ms,
            "min_silence_duration_ms": self.min_silence_duration_ms,
            "window_size_samples": self.window_size_samples,
            "model_loaded": self.model is not None,
        }


def create_neural_vad(sample_rate: int = 16000, aggressiveness: int = 2) -> NeuralVAD:
    """
    Factory function to create NeuralVAD with webrtcvad-compatible interface

    Args:
        sample_rate: Audio sample rate (8000 or 16000)
        aggressiveness: VAD aggressiveness 0-3

    Returns:
        NeuralVAD instance
    """
    vad = NeuralVAD(sample_rate=sample_rate)
    vad.set_aggressiveness(aggressiveness)
    return vad
