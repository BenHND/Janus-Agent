"""
Tests for WhisperSTT enable/disable listening (TICKET A6)

Tests cover:
- enable_listening and disable_listening methods
- Async versions of these methods
- Integration with stop_listening flag
"""
import asyncio

# Mock imports that may not be available in test environment
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

# Mock heavy dependencies
sys.modules["pyaudio"] = MagicMock()
sys.modules["webrtcvad"] = MagicMock()
sys.modules["whisper"] = MagicMock()

from janus.io.stt.whisper_stt import WhisperSTT


class TestWhisperSTTListeningControl(unittest.TestCase):
    """Test WhisperSTT listening control methods for TICKET A6"""

    def setUp(self):
        """Set up test fixtures"""
        # Create WhisperSTT instance with lazy loading
        # This prevents actual model loading during tests
        with patch("janus.stt.whisper_stt.pyaudio.PyAudio"):
            with patch("janus.stt.whisper_stt.webrtcvad.Vad"):
                self.stt = WhisperSTT(
                    model_size="tiny",
                    lazy_load=True,  # Don't load model during tests
                    enable_logging=False,  # Disable logging
                    enable_corrections=False,  # Disable corrections
                    enable_normalization=False,  # Disable normalization
                )

    def test_enable_listening(self):
        """Test enable_listening sets flag correctly"""
        # Set flag to True (stopped)
        self.stt._stop_listening = True

        # Enable listening
        self.stt.enable_listening()

        # Verify flag is cleared
        self.assertFalse(self.stt._stop_listening)

    def test_disable_listening(self):
        """Test disable_listening sets flag correctly"""
        # Set flag to False (listening)
        self.stt._stop_listening = False

        # Disable listening
        self.stt.disable_listening()

        # Verify flag is set
        self.assertTrue(self.stt._stop_listening)

    def test_start_listening_alias(self):
        """Test start_listening (original method) works"""
        self.stt._stop_listening = True
        self.stt.start_listening()
        self.assertFalse(self.stt._stop_listening)

    def test_stop_listening_alias(self):
        """Test stop_listening (original method) works"""
        self.stt._stop_listening = False
        self.stt.stop_listening()
        self.assertTrue(self.stt._stop_listening)

    def test_enable_listening_async(self):
        """Test async version of enable_listening"""
        self.stt._stop_listening = True

        # Run async method
        asyncio.run(self.stt.enable_listening_async())

        # Verify flag is cleared
        self.assertFalse(self.stt._stop_listening)

    def test_disable_listening_async(self):
        """Test async version of disable_listening"""
        self.stt._stop_listening = False

        # Run async method
        asyncio.run(self.stt.disable_listening_async())

        # Verify flag is set
        self.assertTrue(self.stt._stop_listening)

    def test_multiple_enable_disable_cycles(self):
        """Test multiple enable/disable cycles"""
        # Cycle 1
        self.stt.enable_listening()
        self.assertFalse(self.stt._stop_listening)

        self.stt.disable_listening()
        self.assertTrue(self.stt._stop_listening)

        # Cycle 2
        self.stt.enable_listening()
        self.assertFalse(self.stt._stop_listening)

        self.stt.disable_listening()
        self.assertTrue(self.stt._stop_listening)

        # Cycle 3
        self.stt.enable_listening()
        self.assertFalse(self.stt._stop_listening)

    def test_idempotent_enable(self):
        """Test enabling when already enabled is safe"""
        self.stt._stop_listening = False

        # Enable when already enabled
        self.stt.enable_listening()
        self.assertFalse(self.stt._stop_listening)

        self.stt.enable_listening()
        self.assertFalse(self.stt._stop_listening)

    def test_idempotent_disable(self):
        """Test disabling when already disabled is safe"""
        self.stt._stop_listening = True

        # Disable when already disabled
        self.stt.disable_listening()
        self.assertTrue(self.stt._stop_listening)

        self.stt.disable_listening()
        self.assertTrue(self.stt._stop_listening)

    def test_async_methods_complete_quickly(self):
        """Test async methods complete without blocking"""
        import time

        # Measure time for async operations
        start = time.time()

        asyncio.run(self.stt.enable_listening_async())
        asyncio.run(self.stt.disable_listening_async())

        elapsed = time.time() - start

        # Should complete almost instantly (< 100ms)
        self.assertLess(elapsed, 0.1)

    def test_initial_state(self):
        """Test initial listening state is enabled"""
        with patch("janus.stt.whisper_stt.pyaudio.PyAudio"):
            with patch("janus.stt.whisper_stt.webrtcvad.Vad"):
                stt = WhisperSTT(
                    model_size="tiny",
                    lazy_load=True,
                    enable_logging=False,
                    enable_corrections=False,
                    enable_normalization=False,
                )

        # Initial state should be False (not stopped, i.e., listening)
        self.assertFalse(stt._stop_listening)


class TestWhisperSTTIntegrationA6(unittest.TestCase):
    """Test integration scenarios for TICKET A6"""

    def setUp(self):
        """Set up test fixtures"""
        with patch("janus.stt.whisper_stt.pyaudio.PyAudio"):
            with patch("janus.stt.whisper_stt.webrtcvad.Vad"):
                self.stt = WhisperSTT(
                    model_size="tiny",
                    lazy_load=True,
                    enable_logging=False,
                    enable_corrections=False,
                    enable_normalization=False,
                )

    def test_tts_integration_scenario(self):
        """Test typical TTS integration scenario"""
        # 1. User is listening
        self.stt.enable_listening()
        self.assertFalse(self.stt._stop_listening)

        # 2. TTS starts speaking - disable mic
        self.stt.disable_listening()
        self.assertTrue(self.stt._stop_listening)

        # 3. TTS finishes - re-enable mic
        self.stt.enable_listening()
        self.assertFalse(self.stt._stop_listening)

    def test_async_tts_integration_scenario(self):
        """Test async TTS integration scenario"""

        async def integration_flow():
            # Enable listening
            await self.stt.enable_listening_async()
            self.assertFalse(self.stt._stop_listening)

            # Simulate TTS speaking
            await asyncio.sleep(0.01)
            await self.stt.disable_listening_async()
            self.assertTrue(self.stt._stop_listening)

            # Re-enable after TTS
            await asyncio.sleep(0.01)
            await self.stt.enable_listening_async()
            self.assertFalse(self.stt._stop_listening)

        asyncio.run(integration_flow())


if __name__ == "__main__":
    unittest.main()
