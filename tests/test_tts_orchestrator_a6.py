"""
Tests for TTS Orchestrator Integration enhancements (TICKET A6)

Tests cover:
- ask_clarification method
- Microphone re-enable callback
- STT enable callback integration
"""
import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from janus.io.tts.adapter import TTSAdapter
from janus.io.tts.orchestrator_integration import TTSOrchestratorIntegration


class TestTTSOrchestratorIntegrationA6(unittest.TestCase):
    """Test TTS orchestrator integration TICKET A6 enhancements"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mock TTS adapter
        self.mock_tts = Mock(spec=TTSAdapter)
        self.mock_tts.speak = Mock(return_value=True)

        # Create orchestrator integration
        self.integration = TTSOrchestratorIntegration(
            tts_adapter=self.mock_tts,
            enable_tts=True,
            auto_confirmations=True,
            verbosity="compact",
            lang="fr-FR",
        )

    def test_ask_clarification_basic(self):
        """Test ask_clarification speaks the question"""
        question = "Quel fichier voulez-vous ouvrir ?"

        # Run ask_clarification
        result = asyncio.run(self.integration.ask_clarification(question))

        # Verify TTS was called
        self.assertTrue(result)
        self.mock_tts.speak.assert_called_once()
        call_args = self.mock_tts.speak.call_args
        self.assertEqual(call_args[0][0], question)
        self.assertEqual(call_args[1]["lang"], "fr-FR")
        self.assertEqual(call_args[1]["priority"], 8)

    def test_ask_clarification_with_callback(self):
        """Test ask_clarification calls STT enable callback"""
        # Create mock callback
        mock_callback = AsyncMock()
        self.integration.set_stt_enable_callback(mock_callback)

        question = "Test question?"

        # Run ask_clarification
        result = asyncio.run(self.integration.ask_clarification(question))

        # Verify callback was called
        self.assertTrue(result)
        mock_callback.assert_called_once()

    def test_ask_clarification_no_auto_enable(self):
        """Test ask_clarification without auto-enable"""
        mock_callback = AsyncMock()
        self.integration.set_stt_enable_callback(mock_callback)

        question = "Test question?"

        # Run with auto_enable_mic=False
        result = asyncio.run(self.integration.ask_clarification(question, auto_enable_mic=False))

        # Verify callback was NOT called
        self.assertTrue(result)
        mock_callback.assert_not_called()

    def test_ask_clarification_tts_disabled(self):
        """Test ask_clarification when TTS is disabled"""
        self.integration.set_enabled(False)

        mock_callback = AsyncMock()
        self.integration.set_stt_enable_callback(mock_callback)

        question = "Test question?"

        # Run ask_clarification
        result = asyncio.run(self.integration.ask_clarification(question))

        # Should return False, TTS not called
        self.assertFalse(result)
        self.mock_tts.speak.assert_not_called()
        mock_callback.assert_not_called()

    def test_set_stt_enable_callback(self):
        """Test setting STT enable callback"""
        callback1 = AsyncMock()

        # Set callback
        self.integration.set_stt_enable_callback(callback1)
        self.assertEqual(self.integration.stt_enable_callback, callback1)

        # Clear callback
        self.integration.set_stt_enable_callback(None)
        self.assertIsNone(self.integration.stt_enable_callback)

    def test_ask_clarification_callback_error_handling(self):
        """Test ask_clarification handles callback errors gracefully"""

        # Create callback that raises an error
        async def failing_callback():
            raise RuntimeError("Callback error")

        self.integration.set_stt_enable_callback(failing_callback)

        question = "Test question?"

        # Run ask_clarification - should not raise exception
        result = asyncio.run(self.integration.ask_clarification(question))

        # Should still return True (TTS succeeded)
        self.assertTrue(result)
        self.mock_tts.speak.assert_called_once()

    def test_ask_clarification_custom_priority(self):
        """Test ask_clarification with custom priority"""
        question = "Important question?"
        custom_priority = 10

        result = asyncio.run(self.integration.ask_clarification(question, priority=custom_priority))

        # Verify custom priority was used
        self.assertTrue(result)
        call_args = self.mock_tts.speak.call_args
        self.assertEqual(call_args[1]["priority"], custom_priority)

    def test_ask_clarification_integration_flow(self):
        """Test complete flow: TTS speak -> wait -> enable mic"""
        call_sequence = []

        def mock_speak(text, **kwargs):
            call_sequence.append("speak")
            return True

        async def mock_enable():
            call_sequence.append("enable")

        self.mock_tts.speak = Mock(side_effect=mock_speak)
        self.integration.set_stt_enable_callback(mock_enable)

        # Run ask_clarification
        result = asyncio.run(self.integration.ask_clarification("Test?"))

        # Verify sequence: speak then enable
        self.assertTrue(result)
        self.assertEqual(call_sequence, ["speak", "enable"])


if __name__ == "__main__":
    unittest.main()
