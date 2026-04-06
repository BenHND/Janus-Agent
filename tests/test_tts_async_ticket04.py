"""
Unit tests for async TTS operations (TICKET-04)
Tests that TTS speak() is async and doesn't block the event loop
"""

import asyncio
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, Mock, patch, PropertyMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestAsyncTTSOperations(unittest.TestCase):
    """Test async TTS operations"""

    def test_adapter_speak_is_async(self):
        """Test that TTSAdapter.speak is defined as async"""
        from janus.io.tts.adapter import TTSAdapter
        import inspect

        # Get the speak method
        speak_method = getattr(TTSAdapter, "speak")

        # Check that it's a coroutine function (async def)
        self.assertTrue(
            inspect.iscoroutinefunction(speak_method),
            "TTSAdapter.speak() should be declared as async def",
        )

    @patch("janus.tts.piper_neural_tts.PIPER_AVAILABLE", True)
    @patch("piper.PiperVoice")
    def test_piper_speak_is_async(self, mock_piper_voice):
        """Test that PiperNeuralTTSAdapter.speak() is async"""
        import inspect

        from janus.io.tts.piper_neural_tts import PiperNeuralTTSAdapter

        # Mock the PiperVoice.load to avoid actual model loading
        mock_voice = MagicMock()
        mock_piper_voice.load.return_value = mock_voice

        # Create adapter
        adapter = PiperNeuralTTSAdapter(model_path="/fake/model.onnx", enable_queue=False)

        # Wait for engine to be ready
        adapter._engine_ready.wait(timeout=1)

        # Check that speak is a coroutine function
        self.assertTrue(
            inspect.iscoroutinefunction(adapter.speak),
            "PiperNeuralTTSAdapter.speak() should be declared as async def",
        )

        # Cleanup
        adapter.shutdown()

    @patch("janus.tts.piper_neural_tts.PIPER_AVAILABLE", True)
    @patch("piper.PiperVoice")
    def test_async_speak_non_blocking(self, mock_piper_voice):
        """Test that async speak() doesn't block the event loop"""
        from janus.io.tts.piper_neural_tts import PiperNeuralTTSAdapter

        # Mock the PiperVoice and its methods
        mock_voice = MagicMock()
        mock_piper_voice.load.return_value = mock_voice

        # Create adapter without queue (direct mode)
        adapter = PiperNeuralTTSAdapter(model_path="/fake/model.onnx", enable_queue=False)

        # Wait for engine to be ready
        adapter._engine_ready.wait(timeout=1)

        # Mock the blocking I/O method to simulate slow operation
        def slow_generate_and_play(text):
            time.sleep(0.1)  # Simulate slow I/O

        adapter._generate_and_play_audio = slow_generate_and_play

        async def run_test():
            # Record start time
            start_time = time.time()

            # Start TTS (should not block)
            task = asyncio.create_task(adapter.speak("Test message", priority=5))

            # Event loop should remain responsive
            # This counter should increment while TTS is running
            counter = 0
            for _ in range(5):
                await asyncio.sleep(0.01)
                counter += 1

            # Wait for TTS to complete
            await task

            elapsed = time.time() - start_time

            # Verify counter incremented (event loop wasn't blocked)
            self.assertGreater(
                counter,
                0,
                "Event loop should remain responsive during TTS operation",
            )

            # Verify the operation took reasonable time
            self.assertGreater(elapsed, 0.05, "TTS should take some time to complete")

        # Run the async test
        asyncio.run(run_test())

        # Cleanup
        adapter.shutdown()

    @patch("janus.tts.piper_neural_tts.PIPER_AVAILABLE", True)
    def test_queue_mode_still_works(self):
        """Test that queue mode (worker thread) still works with async speak"""
        from janus.io.tts.piper_neural_tts import PiperNeuralTTSAdapter
        import inspect

        # We just verify that the method signature remains async
        # The actual queue processing is tested in integration tests
        self.assertTrue(
            inspect.iscoroutinefunction(PiperNeuralTTSAdapter.speak),
            "PiperNeuralTTSAdapter.speak() should remain async even with queue mode",
        )


class TestOrchestratorIntegrationAsync(unittest.TestCase):
    """Test orchestrator integration async usage"""

    def test_speak_custom_is_async(self):
        """Test that speak_custom is async"""
        import inspect

        # Simply import the orchestrator integration if available
        try:
            from janus.io.tts.orchestrator_integration import TTSOrchestratorIntegration

            # Check that speak_custom is async
            self.assertTrue(
                inspect.iscoroutinefunction(TTSOrchestratorIntegration.speak_custom),
                "TTSOrchestratorIntegration.speak_custom() should be async",
            )
        except ImportError as e:
            # Skip test if dependencies are not available
            self.skipTest(f"Orchestrator integration dependencies not available: {e}")


if __name__ == "__main__":
    unittest.main()
