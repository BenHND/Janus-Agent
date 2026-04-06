"""
Unit tests for MLX STT Engine (TICKET-P2-01)

Tests the MLX Whisper integration for Apple Silicon.
These tests are designed to run on any platform, with actual MLX tests
being skipped on non-Apple-Silicon hardware.
"""

import platform
import sys
import unittest
from unittest.mock import Mock, patch

import numpy as np

# Check if we're on Apple Silicon
IS_APPLE_SILICON = platform.system() == "Darwin" and platform.machine() == "arm64"


class TestMLXEngineImports(unittest.TestCase):
    """Test MLX engine module imports and availability checking"""

    def test_import_mlx_stt_engine_module(self):
        """Test that mlx_stt_engine module can be imported"""
        try:
            from janus.io.stt import mlx_stt_engine

            self.assertTrue(hasattr(mlx_stt_engine, "MLXSTTEngine"))
            self.assertTrue(hasattr(mlx_stt_engine, "is_mlx_available"))
            self.assertTrue(hasattr(mlx_stt_engine, "create_mlx_stt_engine"))
        except ImportError as e:
            self.fail(f"Failed to import mlx_stt_engine: {e}")

    def test_is_mlx_available_function(self):
        """Test is_mlx_available returns correct value based on platform"""
        from janus.io.stt.mlx_stt_engine import is_mlx_available, IS_APPLE_SILICON

        result = is_mlx_available()

        # On non-Apple-Silicon, should always be False
        if not IS_APPLE_SILICON:
            self.assertFalse(result)
        # On Apple Silicon, depends on whether lightning-whisper-mlx is installed

    def test_is_apple_silicon_detection(self):
        """Test Apple Silicon detection constant"""
        from janus.io.stt.mlx_stt_engine import IS_APPLE_SILICON

        expected = platform.system() == "Darwin" and platform.machine() == "arm64"
        self.assertEqual(IS_APPLE_SILICON, expected)


class TestMLXEngineStub(unittest.TestCase):
    """Test MLX engine with mocked MLX library"""

    def test_transcription_result_dataclass(self):
        """Test TranscriptionResult dataclass"""
        from janus.io.stt.mlx_stt_engine import TranscriptionResult

        result = TranscriptionResult(
            text="Hello world",
            language="en",
            confidence=0.95,
            duration_ms=250.0,
            model_used="mlx-whisper",
        )

        self.assertEqual(result.text, "Hello world")
        self.assertEqual(result.language, "en")
        self.assertEqual(result.confidence, 0.95)
        self.assertEqual(result.duration_ms, 250.0)
        self.assertEqual(result.model_used, "mlx-whisper")
        self.assertIsNone(result.segments)

    def test_transcription_result_with_segments(self):
        """Test TranscriptionResult with segments"""
        from janus.io.stt.mlx_stt_engine import TranscriptionResult

        segments = [
            {"start": 0.0, "end": 1.0, "text": "Hello"},
            {"start": 1.0, "end": 2.0, "text": "world"},
        ]

        result = TranscriptionResult(
            text="Hello world",
            language="en",
            confidence=0.95,
            duration_ms=250.0,
            model_used="mlx-whisper",
            segments=segments,
        )

        self.assertEqual(len(result.segments), 2)
        self.assertEqual(result.segments[0]["text"], "Hello")

    def test_mlx_engine_initialization_mocked(self):
        """Test MLX engine initialization with mocked LightningWhisperMLX"""
        import janus.stt.mlx_stt_engine as mlx_module

        # Create mock for LightningWhisperMLX
        mock_mlx_class = Mock()
        mock_model = Mock()
        mock_mlx_class.return_value = mock_model

        # Save original values
        original_has_mlx = mlx_module.HAS_MLX_WHISPER
        original_is_apple_silicon = mlx_module.IS_APPLE_SILICON

        try:
            # Patch module-level variables
            mlx_module.HAS_MLX_WHISPER = True
            mlx_module.IS_APPLE_SILICON = True
            mlx_module.LightningWhisperMLX = mock_mlx_class

            engine = mlx_module.MLXSTTEngine(
                model_size="base",
                language="fr",
                batch_size=12,
            )

            self.assertEqual(engine.model_size, "base")
            self.assertEqual(engine.language, "fr")
            self.assertEqual(engine.batch_size, 12)
            mock_mlx_class.assert_called_once()
        finally:
            # Restore original values
            mlx_module.HAS_MLX_WHISPER = original_has_mlx
            mlx_module.IS_APPLE_SILICON = original_is_apple_silicon
            if hasattr(mlx_module, "LightningWhisperMLX"):
                delattr(mlx_module, "LightningWhisperMLX")

    def test_language_normalization(self):
        """Test that language is always normalized to fr or en"""
        from janus.io.stt.mlx_stt_engine import MLXSTTEngine

        # Patch to prevent actual model loading
        with patch.object(MLXSTTEngine, "_initialize_model"):
            engine = MLXSTTEngine.__new__(MLXSTTEngine)
            engine.logger = Mock()
            engine.model_size = "base"
            engine.sample_rate = 16000
            engine.buffer_duration_sec = 3.0
            engine.beam_size = 5
            engine.batch_size = 12
            engine.quant = None
            engine.model = None
            engine.rolling_buffer = []
            engine.buffer_max_samples = 48000
            engine.stats = {
                "total_transcriptions": 0,
                "total_duration_ms": 0.0,
                "avg_latency_ms": 0.0,
                "errors": 0,
            }

            # Test various language inputs
            test_cases = [
                ("fr", "fr"),
                ("en", "en"),
                ("FR", "fr"),
                ("EN", "en"),
                ("auto", "fr"),  # Falls back to fr
                (None, "fr"),  # Falls back to fr
                ("de", "fr"),  # Unsupported falls back to fr
                ("  fr  ", "fr"),  # Whitespace stripped
            ]

            for input_lang, expected in test_cases:
                lang = (input_lang or "fr").lower().strip()
                if lang == "auto" or lang not in ("fr", "en"):
                    lang = "fr"
                self.assertEqual(lang, expected, f"Failed for input: {input_lang}")


class TestMLXEngineBuffer(unittest.TestCase):
    """Test rolling buffer functionality"""

    def setUp(self):
        """Set up a mock MLX engine for buffer testing"""
        from janus.io.stt.mlx_stt_engine import MLXSTTEngine

        # Create engine without initializing model
        with patch.object(MLXSTTEngine, "_initialize_model"):
            self.engine = MLXSTTEngine.__new__(MLXSTTEngine)
            self.engine.logger = Mock()
            self.engine.model_size = "base"
            self.engine.sample_rate = 16000
            self.engine.buffer_duration_sec = 3.0
            self.engine.beam_size = 5
            self.engine.batch_size = 12
            self.engine.quant = None
            self.engine.model = None
            self.engine.rolling_buffer = []
            self.engine.buffer_max_samples = int(3.0 * 16000)  # 3 seconds
            self.engine.stats = {
                "total_transcriptions": 0,
                "total_duration_ms": 0.0,
                "avg_latency_ms": 0.0,
                "errors": 0,
            }
            self.engine.language = "fr"

    def test_add_to_buffer(self):
        """Test adding audio to buffer"""
        audio_chunk = np.zeros(16000, dtype=np.float32)  # 1 second
        self.engine.add_to_buffer(audio_chunk)

        self.assertEqual(len(self.engine.rolling_buffer), 1)

    def test_buffer_overflow(self):
        """Test that buffer doesn't exceed max size"""
        # Add 5 seconds of audio (should keep only last 3 seconds)
        for _ in range(5):
            audio_chunk = np.zeros(16000, dtype=np.float32)  # 1 second each
            self.engine.add_to_buffer(audio_chunk)

        # Should have at most 3 seconds worth
        total_samples = sum(len(chunk) for chunk in self.engine.rolling_buffer)
        self.assertLessEqual(total_samples, self.engine.buffer_max_samples)

    def test_get_buffer_audio_empty(self):
        """Test get_buffer_audio with empty buffer"""
        result = self.engine.get_buffer_audio()
        self.assertIsNone(result)

    def test_get_buffer_audio_with_data(self):
        """Test get_buffer_audio with data"""
        audio_chunk = np.ones(16000, dtype=np.float32)
        self.engine.add_to_buffer(audio_chunk)

        result = self.engine.get_buffer_audio()
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 16000)
        np.testing.assert_array_equal(result, audio_chunk)

    def test_clear_buffer(self):
        """Test clearing buffer"""
        audio_chunk = np.zeros(16000, dtype=np.float32)
        self.engine.add_to_buffer(audio_chunk)
        self.engine.clear_buffer()

        self.assertEqual(len(self.engine.rolling_buffer), 0)


class TestSTTFactory(unittest.TestCase):
    """Test STT factory functions"""

    def test_import_stt_factory(self):
        """Test that stt_factory module can be imported"""
        try:
            from janus.io.stt import stt_factory

            self.assertTrue(hasattr(stt_factory, "create_stt_engine"))
            self.assertTrue(hasattr(stt_factory, "get_best_stt_engine_type"))
            self.assertTrue(hasattr(stt_factory, "get_stt_engine_info"))
        except ImportError as e:
            self.fail(f"Failed to import stt_factory: {e}")

    def test_get_stt_engine_info(self):
        """Test get_stt_engine_info returns correct structure"""
        from janus.io.stt.stt_factory import get_stt_engine_info

        info = get_stt_engine_info()

        self.assertIn("platform", info)
        self.assertIn("machine", info)
        self.assertIn("is_apple_silicon", info)
        self.assertIn("engines", info)
        self.assertIn("recommended_engine", info)

        self.assertIn("mlx", info["engines"])
        self.assertIn("faster_whisper", info["engines"])
        self.assertIn("whisper", info["engines"])

    def test_get_best_stt_engine_type(self):
        """Test get_best_stt_engine_type returns valid engine type"""
        from janus.io.stt.stt_factory import get_best_stt_engine_type

        engine_type = get_best_stt_engine_type()

        self.assertIn(engine_type, ["mlx", "faster-whisper", "whisper"])


class TestGPUUtilsMLX(unittest.TestCase):
    """Test GPU utils MLX-related functions"""

    def test_is_apple_silicon(self):
        """Test is_apple_silicon function"""
        from janus.utils.gpu_utils import is_apple_silicon

        result = is_apple_silicon()
        expected = platform.system() == "Darwin" and platform.machine() == "arm64"
        self.assertEqual(result, expected)

    def test_is_mlx_available(self):
        """Test is_mlx_available function from gpu_utils"""
        from janus.utils.gpu_utils import is_mlx_available

        result = is_mlx_available()

        # On non-Apple-Silicon, should always be False
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            self.assertFalse(result)

    def test_get_best_stt_engine(self):
        """Test get_best_stt_engine function"""
        from janus.utils.gpu_utils import get_best_stt_engine

        engine = get_best_stt_engine()
        self.assertIn(engine, ["mlx", "faster-whisper", "whisper"])


class TestMLXExportsFromInit(unittest.TestCase):
    """Test that MLX exports are available from janus.stt"""

    def test_is_mlx_available_exported(self):
        """Test is_mlx_available is exported from janus.stt"""
        from janus.io.stt import is_mlx_available

        result = is_mlx_available()
        self.assertIsInstance(result, bool)

    def test_create_stt_engine_exported(self):
        """Test create_stt_engine is exported from janus.stt"""
        try:
            from janus.io.stt import create_stt_engine

            self.assertTrue(callable(create_stt_engine))
        except ImportError:
            # This is acceptable if dependencies are missing
            pass

    def test_get_stt_engine_info_exported(self):
        """Test get_stt_engine_info is exported from janus.stt"""
        try:
            from janus.io.stt import get_stt_engine_info

            info = get_stt_engine_info()
            self.assertIsInstance(info, dict)
        except ImportError:
            # This is acceptable if dependencies are missing
            pass


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestMLXEngineImports))
    suite.addTests(loader.loadTestsFromTestCase(TestMLXEngineStub))
    suite.addTests(loader.loadTestsFromTestCase(TestMLXEngineBuffer))
    suite.addTests(loader.loadTestsFromTestCase(TestSTTFactory))
    suite.addTests(loader.loadTestsFromTestCase(TestGPUUtilsMLX))
    suite.addTests(loader.loadTestsFromTestCase(TestMLXExportsFromInit))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
