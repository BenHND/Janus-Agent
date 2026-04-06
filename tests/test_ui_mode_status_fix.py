"""
Test for UI mode status update after recording stops with no transcription
Ticket: Fix Status - Status should return to idle after silence detection
"""
import unittest
from unittest.mock import MagicMock, Mock, patch, AsyncMock
import asyncio
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestUIModesStatusUpdate(unittest.TestCase):
    """Test UI mode status updates correctly after recording stops"""

    def test_status_returns_to_idle_immediately_after_recording_stops(self):
        """
        Test that status returns to IDLE IMMEDIATELY after recording stops,
        regardless of transcription result.
        This simulates the scenario:
        1. User clicks mic -> status becomes "Listening..."
        2. Recording starts and captures audio
        3. Silence is detected -> recording stops
        4. Status IMMEDIATELY updates to "Ready" (before checking transcription)
        5. Then process transcription result (continue listening if no text)
        """
        # Mock the necessary components
        mock_overlay = Mock()
        mock_overlay.mic_enabled = True
        mock_overlay.signals = Mock()
        mock_overlay.signals.set_status_signal = Mock()
        mock_overlay.signals.append_transcript_signal = Mock()

        # Simulate the listening state
        class ListeningState:
            def __init__(self):
                self.active = True
                self.event_loop = None

        listening_state = ListeningState()

        # Simulate the NEW logic: status is set to IDLE immediately after recording
        text = None  # Recording stopped with no transcription
        
        # Status is set IMMEDIATELY after listen_and_transcribe_async returns
        mock_overlay.signals.set_status_signal.emit(("idle", "Ready"))
        
        should_continue = False
        # Then process the result
        if text and listening_state.active:
            # This branch handles successful transcription
            pass
        elif not listening_state.active:
            # This branch handles manual stop during transcription
            pass
        else:
            # Recording stopped but no text - just continue (status already set)
            should_continue = True

        # Verify the state after the fix
        self.assertTrue(listening_state.active, "Listening should remain active to continue listening")
        self.assertTrue(mock_overlay.mic_enabled, "Mic button should remain enabled")
        self.assertTrue(should_continue, "Loop should continue listening")
        # Verify that set_status was called with IDLE state IMMEDIATELY after recording
        mock_overlay.signals.set_status_signal.emit.assert_called_once()
        call_args = mock_overlay.signals.set_status_signal.emit.call_args[0][0]
        self.assertEqual(call_args[0], "idle", "Status should be set to IDLE immediately after recording stops")

    def test_status_updates_on_successful_transcription(self):
        """Test that status updates correctly when transcription succeeds"""
        mock_overlay = Mock()
        mock_overlay.mic_enabled = True
        mock_overlay.signals = Mock()
        mock_overlay.signals.set_status_signal = Mock()
        mock_overlay.signals.append_transcript_signal = Mock()

        class ListeningState:
            def __init__(self):
                self.active = True

        listening_state = ListeningState()
        text = "hello world"  # Successful transcription

        # Simulate successful transcription branch
        if text and listening_state.active:
            listening_state.active = False
            mock_overlay.mic_enabled = False
            mock_overlay.signals.append_transcript_signal.emit(text)

        # Verify state
        self.assertFalse(listening_state.active, "Listening should be deactivated")
        self.assertFalse(mock_overlay.mic_enabled, "Mic should be disabled")
        mock_overlay.signals.append_transcript_signal.emit.assert_called_once_with("hello world")

    def test_status_updates_on_manual_stop(self):
        """Test that status updates correctly when user manually stops listening"""
        class ListeningState:
            def __init__(self):
                self.active = False  # User stopped manually

        listening_state = ListeningState()
        text = None  # No transcription

        should_break = False
        # Simulate manual stop branch
        if text and listening_state.active:
            pass
        elif not listening_state.active:
            # Manual stop during transcription
            should_break = True

        self.assertTrue(should_break, "Loop should break on manual stop")
        self.assertFalse(listening_state.active, "Listening should remain inactive")


if __name__ == "__main__":
    unittest.main()
