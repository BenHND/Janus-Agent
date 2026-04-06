"""
Tests for decide_next_action - ReAct-style Next Step Logic
TICKET-ARCH-001: New architecture for step-by-step reasoning
"""
import json
import unittest

from janus.ai.reasoning.reasoner_llm import ReasonerLLM


class TestDecideNextAction(unittest.TestCase):
    """Test the new decide_next_action method"""

    def setUp(self):
        """Set up test ReasonerLLM with mock backend"""
        self.llm = ReasonerLLM(backend="mock")

    def test_decide_next_action_returns_single_action(self):
        """Test that decide_next_action returns a single action"""
        user_goal = "Find the CEO of Acme Corp"
        system_state = {
            "active_app": "Safari",
            "url": "https://acme.com/about",
            "clipboard": ""
        }
        visual_context = """
        [
            {"id": "ceo_name_1", "type": "text", "content": "John Smith"},
            {"id": "ceo_title_2", "type": "text", "content": "CEO"}
        ]
        """
        memory = {}

        result = self.llm.decide_next_action(
            user_goal=user_goal,
            system_state=system_state,
            visual_context=visual_context,
            memory=memory,
            language="en"
        )

        # Verify structure
        self.assertIn("action", result)
        self.assertIn("args", result)
        self.assertIn("reasoning", result)
        
        # Verify it's a single action (not an array)
        self.assertIsInstance(result, dict)
        self.assertNotIsInstance(result.get("action"), list)

    def test_decide_next_action_french(self):
        """Test decide_next_action with French language"""
        user_goal = "Trouve le CEO d'Acme Corp"
        system_state = {
            "active_app": "Safari",
            "url": "https://acme.com/about",
            "clipboard": ""
        }
        visual_context = """
        [
            {"id": "ceo_name_1", "type": "text", "content": "Jean Dupont"},
            {"id": "ceo_title_2", "type": "text", "content": "PDG"}
        ]
        """
        memory = {}

        result = self.llm.decide_next_action(
            user_goal=user_goal,
            system_state=system_state,
            visual_context=visual_context,
            memory=memory,
            language="fr"
        )

        # Verify structure
        self.assertIn("action", result)
        self.assertIn("args", result)
        self.assertIn("reasoning", result)

    def test_decide_next_action_with_memory(self):
        """Test decide_next_action with existing memory"""
        user_goal = "Find the CEO of Acme Corp"
        system_state = {
            "active_app": "Safari",
            "url": "https://acme.com",
            "clipboard": ""
        }
        visual_context = "[...]"
        memory = {
            "CEO_name": "John Smith",
            "company": "Acme Corp"
        }

        result = self.llm.decide_next_action(
            user_goal=user_goal,
            system_state=system_state,
            visual_context=visual_context,
            memory=memory,
            language="en"
        )

        # Should return "done" since info is in memory (for mock)
        self.assertEqual(result["action"], "done")

    def test_decide_next_action_llm_unavailable(self):
        """Test decide_next_action when LLM is unavailable"""
        # Create reasoner with non-existent model
        llm = ReasonerLLM(backend="llama-cpp", model_path="/nonexistent/model.gguf")
        
        result = llm.decide_next_action(
            user_goal="Test",
            system_state={"active_app": "Safari"},
            visual_context="[]",
            memory={},
            language="en"
        )

        # Should return error action
        self.assertEqual(result["action"], "error")
        self.assertIn("error", result)
        self.assertIn("Reasoner unavailable", result.get("error", ""))

    def test_decide_next_action_no_planning(self):
        """Test that decide_next_action doesn't return multiple steps"""
        user_goal = "Open Chrome and search for Python"
        system_state = {"active_app": "Finder", "url": "", "clipboard": ""}
        visual_context = "[]"
        memory = {}

        result = self.llm.decide_next_action(
            user_goal=user_goal,
            system_state=system_state,
            visual_context=visual_context,
            memory=memory,
            language="en"
        )

        # Verify it's a single action dict, not a list
        self.assertIsInstance(result, dict)
        self.assertIn("action", result)
        
        # The action should not be a list
        action = result.get("action")
        self.assertIsInstance(action, str)


if __name__ == "__main__":
    unittest.main()
