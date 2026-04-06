"""
Tests for MockReasoner - Fixture-based mock inference

This test file validates the refactored mock inference logic
that was extracted from reasoner_llm.py into mock_reasoner.py.
"""

import json
import unittest
from pathlib import Path

from janus.ai.reasoning.mock_reasoner import MockReasoner


class TestMockReasoner(unittest.TestCase):
    """Test MockReasoner functionality"""

    def setUp(self):
        """Set up test MockReasoner"""
        self.mock = MockReasoner()

    def test_initialization(self):
        """Test MockReasoner initialization"""
        self.assertIsNotNone(self.mock.fixtures)
        self.assertGreater(len(self.mock.fixtures), 0)

    def test_fixtures_loaded(self):
        """Test that all expected fixtures are loaded"""
        expected_fixtures = [
            "parse_command",
            "react_decision",
            "burst_decision",
            "reflex_action",
            "structured_plan",
            "v4_analysis",
        ]
        
        for fixture_name in expected_fixtures:
            self.assertIn(fixture_name, self.mock.fixtures)

    def test_parse_command_open_app_french(self):
        """Test parse_command fixture with French open app command"""
        prompt = "Commande: ouvre Chrome\n\nRéponds uniquement avec du JSON valide:"
        response = self.mock.generate_response(prompt)
        
        data = json.loads(response)
        self.assertIn("intents", data)
        self.assertGreater(len(data["intents"]), 0)
        
        intent = data["intents"][0]
        self.assertEqual(intent["intent"], "open_app")
        self.assertEqual(intent["parameters"]["app_name"], "Chrome")

    def test_parse_command_open_app_english(self):
        """Test parse_command fixture with English open app command"""
        prompt = "Command: open Safari\n\nRespond with JSON:"
        response = self.mock.generate_response(prompt)
        
        data = json.loads(response)
        self.assertIn("intents", data)
        intent = data["intents"][0]
        self.assertEqual(intent["intent"], "open_app")
        self.assertEqual(intent["parameters"]["app_name"], "Safari")

    def test_parse_command_copy(self):
        """Test parse_command fixture with copy command"""
        prompt = "Commande: copie ce texte\n\nJSON:"
        response = self.mock.generate_response(prompt)
        
        data = json.loads(response)
        intent = data["intents"][0]
        self.assertEqual(intent["intent"], "copy")
        self.assertGreater(intent["confidence"], 0.5)

    def test_parse_command_paste(self):
        """Test parse_command fixture with paste command"""
        prompt = "Command: paste here\n\nJSON:"
        response = self.mock.generate_response(prompt)
        
        data = json.loads(response)
        intent = data["intents"][0]
        self.assertEqual(intent["intent"], "paste")

    def test_react_decision(self):
        """Test ReAct decision fixture"""
        prompt = "Voici ta décision pour la prochaine action..."
        response = self.mock.generate_response(prompt)
        
        data = json.loads(response)
        self.assertIn("action", data)
        self.assertEqual(data["action"], "done")
        self.assertIn("reasoning", data)

    def test_reflex_action(self):
        """Test reflex action fixture"""
        prompt = "Système réflexe: action précédente a échoué"
        response = self.mock.generate_response(prompt)
        
        data = json.loads(response)
        self.assertIn("action", data)
        self.assertEqual(data["action"], "type_text")
        self.assertIn("args", data)

    def test_v4_analysis(self):
        """Test V4 analysis fixture"""
        prompt = "V4 analysis format with detailed analysis"
        response = self.mock.generate_response(prompt)
        
        data = json.loads(response)
        self.assertIn("analysis", data)
        self.assertIn("plan", data)
        self.assertIn("user_intent", data["analysis"])

    def test_structured_plan_with_app(self):
        """Test structured plan fixture with app name"""
        prompt = "Génère le plan JSON steps module pour ouvrir chrome"
        response = self.mock.generate_response(prompt)
        
        data = json.loads(response)
        self.assertIn("steps", data)
        self.assertGreater(len(data["steps"]), 0)
        
        step = data["steps"][0]
        self.assertEqual(step["module"], "system")
        self.assertEqual(step["action"], "open_application")
        self.assertEqual(step["args"]["app_name"], "Chrome")

    def test_structured_plan_without_app(self):
        """Test structured plan fixture without specific app"""
        prompt = "Génère le plan JSON with steps and module fields"
        response = self.mock.generate_response(prompt)
        
        data = json.loads(response)
        self.assertIn("steps", data)
        # Should return empty steps when no app is detected
        self.assertEqual(len(data["steps"]), 0)

    def test_default_response(self):
        """Test default response for unmatched prompts"""
        prompt = "This is some random prompt that doesn't match any pattern"
        response = self.mock.generate_response(prompt)
        
        data = json.loads(response)
        self.assertIn("intents", data)
        # Default should return unknown intent
        self.assertEqual(data["intents"][0]["intent"], "unknown")

    def test_fixture_file_exists(self):
        """Test that fixture files exist in the correct location"""
        fixtures_dir = Path(__file__).parent.parent / "janus" / "ai" / "reasoning" / "fixtures"
        
        fixture_files = [
            "parse_command.json",
            "react_decision.json",
            "burst_decision.json",
            "reflex_action.json",
            "structured_plan.json",
            "v4_analysis.json",
        ]
        
        for filename in fixture_files:
            fixture_path = fixtures_dir / filename
            self.assertTrue(fixture_path.exists(), f"Fixture file {filename} should exist")

    def test_custom_fixtures_dir(self):
        """Test MockReasoner with custom fixtures directory"""
        # Use the actual fixtures directory
        fixtures_dir = Path(__file__).parent.parent / "janus" / "ai" / "reasoning" / "fixtures"
        mock = MockReasoner(fixtures_dir=fixtures_dir)
        
        self.assertIsNotNone(mock.fixtures)
        self.assertGreater(len(mock.fixtures), 0)


class TestMockReasonerPatterns(unittest.TestCase):
    """Test pattern matching logic in MockReasoner"""

    def setUp(self):
        """Set up test MockReasoner"""
        self.mock = MockReasoner()

    def test_case_insensitive_matching(self):
        """Test that pattern matching is case-insensitive"""
        # French command with mixed case
        prompt1 = "Commande: Ouvre CHROME\n"
        response1 = self.mock.generate_response(prompt1)
        data1 = json.loads(response1)
        
        # Should still match and capitalize correctly
        self.assertEqual(data1["intents"][0]["parameters"]["app_name"], "Chrome")

    def test_multiple_keywords(self):
        """Test that multiple keywords work correctly"""
        # Test "lance" keyword (French for launch)
        prompt = "Commande: lance Safari\n"
        response = self.mock.generate_response(prompt)
        data = json.loads(response)
        
        self.assertEqual(data["intents"][0]["intent"], "open_app")
        self.assertEqual(data["intents"][0]["parameters"]["app_name"], "Safari")

    def test_priority_order(self):
        """Test that pattern matching priority works correctly"""
        # ReAct prompt should match before parse_command
        prompt = "Ta décision: Commande ouvre Chrome"
        response = self.mock.generate_response(prompt)
        data = json.loads(response)
        
        # Should match ReAct pattern (has "action" field)
        self.assertIn("action", data)
        self.assertEqual(data["action"], "done")


if __name__ == "__main__":
    unittest.main()
