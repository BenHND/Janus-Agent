"""
Tests for Zero-Latency Audio Pipeline (TICKET: Refonte Complète Pipeline Audio)

Tests cover:
- A. STT eager initialization (no lazy loading)
- B. Neural Gatekeeper (anti-echo)
- C. Barge-in (interruption)
- D. Tuned VAD (faster response)
"""
import inspect
import unittest
from unittest.mock import MagicMock, Mock, patch


class TestSTTEagerInitialization(unittest.TestCase):
    """Test STT eager initialization for zero-latency"""

    @patch("janus.io.stt.whisper_stt.WhisperSTT.__init__", return_value=None)
    @patch("janus.io.stt.whisper_stt.WhisperRecorder")
    @patch("janus.io.stt.whisper_stt.WhisperTranscriber")
    @patch("janus.io.stt.whisper_stt.WhisperPostProcessor")
    def test_stt_service_eager_initialization_when_enabled(
        self, mock_post, mock_trans, mock_rec, mock_init
    ):
        """Test that STT service initializes engine immediately when enabled"""
        # Import here to avoid import errors
        import sys
        from unittest.mock import MagicMock

        # Mock the entire module chain to avoid PIL import
        sys.modules["janus.logging.trace_recorder"] = MagicMock()

        from janus.services.stt_service import STTService

        # Mock settings
        mock_settings = Mock()
        mock_settings.features.enable_semantic_correction = False
        mock_settings.whisper.semantic_correction_model_path = None
        mock_settings.whisper.enable_context_buffer = False
        mock_settings.whisper.enable_corrections = True
        mock_settings.whisper.models_dir = "/tmp/models"
        mock_settings.language.default = "en"

        # Patch the initialization method to track calls
        with patch.object(
            STTService, "_initialize_engine"
        ) as mock_initialize:
            service = STTService(
                settings=mock_settings, enabled=True, unified_llm_client=None
            )

            # Verify _initialize_engine was called during __init__
            mock_initialize.assert_called_once()

    def test_stt_service_has_warmup_thread_method(self):
        """Test that STTService has warmup thread method"""
        from janus.services.stt_service import STTService

        # Check method exists
        self.assertTrue(hasattr(STTService, "_start_warmup_thread"))
        self.assertTrue(callable(STTService._start_warmup_thread))


class TestNeuralGatekeeper(unittest.TestCase):
    """Test Neural Gatekeeper (anti-echo) functionality"""

    def test_tts_service_has_is_speaking_method(self):
        """Test that TTSService has is_speaking method"""
        # Check method signature without importing (avoids PIL dependency)
        import janus.services.tts_service as tts_module

        # Verify the class and method exist
        self.assertTrue(hasattr(tts_module, "TTSService"))
        TTSService = getattr(tts_module, "TTSService")
        self.assertTrue(hasattr(TTSService, "is_speaking"))

    def test_tts_service_has_stop_immediately_method(self):
        """Test that TTSService has stop_speaking_immediately method"""
        import janus.services.tts_service as tts_module

        TTSService = getattr(tts_module, "TTSService")
        self.assertTrue(hasattr(TTSService, "stop_speaking_immediately"))
        self.assertTrue(callable(TTSService.stop_speaking_immediately))

    def test_whisper_recorder_accepts_tts_service(self):
        """Test that WhisperRecorder accepts tts_service parameter"""
        from janus.io.stt.whisper_recorder import WhisperRecorder

        # Check that tts_service parameter exists in __init__ signature
        sig = inspect.signature(WhisperRecorder.__init__)
        params = sig.parameters
        self.assertIn("tts_service", params)

    def test_whisper_stt_accepts_tts_service(self):
        """Test that WhisperSTT accepts tts_service parameter"""
        from janus.io.stt.whisper_stt import WhisperSTT

        # Check that tts_service parameter exists in __init__ signature
        sig = inspect.signature(WhisperSTT.__init__)
        params = sig.parameters
        self.assertIn("tts_service", params)


class TestBargeIn(unittest.TestCase):
    """Test barge-in (interruption) functionality"""

    def test_tts_service_has_barge_in_method(self):
        """Test that TTSService has stop_speaking_immediately for barge-in"""
        import janus.services.tts_service as tts_module

        TTSService = getattr(tts_module, "TTSService")

        # Verify method exists and is callable
        self.assertTrue(hasattr(TTSService, "stop_speaking_immediately"))
        self.assertTrue(callable(TTSService.stop_speaking_immediately))

        # Check method signature
        sig = inspect.signature(TTSService.stop_speaking_immediately)
        # Method should only take self (no other parameters)
        params = list(sig.parameters.keys())
        self.assertEqual(params, ["self"])


class TestTunedVAD(unittest.TestCase):
    """Test tuned VAD for faster response"""

    def test_default_silence_threshold_reduced(self):
        """Test that default silence_threshold is reduced to 30 chunks"""
        from janus.io.stt.whisper_stt import WhisperSTT

        # Check default parameter value
        sig = inspect.signature(WhisperSTT.__init__)
        silence_threshold_param = sig.parameters["silence_threshold"]

        # Verify default is 30 (not 60) - reduced for faster response
        self.assertEqual(silence_threshold_param.default, 30)

    def test_whisper_recorder_silence_threshold(self):
        """Test WhisperRecorder accepts and stores silence_threshold"""
        from janus.io.stt.whisper_recorder import WhisperRecorder

        # Check parameter exists
        sig = inspect.signature(WhisperRecorder.__init__)
        params = sig.parameters
        self.assertIn("silence_threshold", params)


class TestDocumentation(unittest.TestCase):
    """Test that changes are properly documented"""

    def test_stt_service_docstring_mentions_eager_loading(self):
        """Test that STTService docstring mentions eager loading"""
        from janus.services.stt_service import STTService

        docstring = STTService.__doc__
        self.assertIsNotNone(docstring)
        # Check for keywords related to eager loading
        self.assertTrue(
            "eager" in docstring.lower() or "zero-latency" in docstring.lower()
        )

    def test_tts_service_docstring_mentions_anti_echo(self):
        """Test that TTSService docstring mentions anti-echo"""
        from janus.services.tts_service import TTSService

        docstring = TTSService.__doc__
        self.assertIsNotNone(docstring)
        # Check for keywords related to anti-echo
        self.assertTrue(
            "anti-echo" in docstring.lower()
            or "neural gatekeeper" in docstring.lower()
            or "observable" in docstring.lower()
        )

    def test_whisper_recorder_docstring_mentions_gating(self):
        """Test that WhisperRecorder docstring mentions TTS gating"""
        from janus.io.stt.whisper_recorder import WhisperRecorder

        docstring = WhisperRecorder.__doc__
        self.assertIsNotNone(docstring)
        # Check for keywords related to gating
        docstring_lower = docstring.lower()
        self.assertTrue(
            "gating" in docstring_lower
            or "neural gatekeeper" in docstring_lower
            or "anti-echo" in docstring_lower
        )


if __name__ == "__main__":
    unittest.main()

