"""
TTS (Text-to-Speech) Module
Provides high-quality neural text-to-speech with Piper TTS.
100% offline, cross-platform, natural voices.
"""

from .adapter import TTSAdapter
from .piper_neural_tts import PiperNeuralTTSAdapter

# Use PiperNeuralTTSAdapter as the default TTS implementation
DefaultTTSAdapter = PiperNeuralTTSAdapter

__all__ = ["TTSAdapter", "PiperNeuralTTSAdapter", "DefaultTTSAdapter"]
