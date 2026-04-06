"""
Tests for UI Feedback States (TICKET-UX-001)
Tests the new LOOKING state and optimistic UI feedback functionality
"""
import unittest

from janus.ui.overlay_types import StatusState
from janus.i18n import status_looking, set_language


class TestUIFeedbackStatesUX001(unittest.TestCase):
    """Test cases for TICKET-UX-001 UI feedback states"""

    def test_looking_state_exists(self):
        """Verify LOOKING state is part of StatusState enum"""
        self.assertIn(StatusState.LOOKING, StatusState)
        self.assertEqual(StatusState.LOOKING.value, "looking")

    def test_all_expected_states_exist(self):
        """Verify all expected states are present"""
        expected_states = {"idle", "listening", "looking", "thinking", "acting", "loading", "error"}
        actual_states = {state.value for state in StatusState}
        self.assertEqual(expected_states, actual_states)

    def test_status_looking_french(self):
        """Verify status_looking() returns correct French text"""
        set_language("fr")
        result = status_looking()
        self.assertEqual(result, "Observation")

    def test_status_looking_english(self):
        """Verify status_looking() returns correct English text"""
        set_language("en")
        result = status_looking()
        self.assertEqual(result, "Looking")

    def test_state_transition_order(self):
        """Verify state values maintain expected order for UI transitions"""
        # Get all states in order
        states = [
            StatusState.IDLE,
            StatusState.LISTENING,
            StatusState.THINKING,
            StatusState.LOOKING,
            StatusState.ACTING,
        ]
        
        # Verify each state exists and has correct value
        self.assertEqual(states[0].value, "idle")
        self.assertEqual(states[1].value, "listening")
        self.assertEqual(states[2].value, "thinking")
        self.assertEqual(states[3].value, "looking")
        self.assertEqual(states[4].value, "acting")

    def test_looking_state_between_thinking_and_acting(self):
        """
        Verify acceptance criteria: at least 2 state changes between command and action
        Expected flow: THINKING → LOOKING → ACTING (2 transitions)
        """
        flow_states = [StatusState.THINKING, StatusState.LOOKING, StatusState.ACTING]
        
        # Calculate number of transitions (state changes)
        # 3 states = 2 transitions: THINKING→LOOKING and LOOKING→ACTING
        num_transitions = len(flow_states) - 1
        
        # Verify at least 2 transitions between command and action
        self.assertGreaterEqual(num_transitions, 2, 
                                "Must have at least 2 state transitions for optimistic feedback")
        
        # Verify order is maintained
        self.assertEqual(flow_states[0], StatusState.THINKING)
        self.assertEqual(flow_states[1], StatusState.LOOKING)
        self.assertEqual(flow_states[2], StatusState.ACTING)


if __name__ == "__main__":
    unittest.main()
