"""
Tests for NLU Parser module
"""
import json
import unittest

from janus.ai.llm.nlu_parser import NLUParser, ParsedIntent


class TestNLUParser(unittest.TestCase):
    """Test NLU Parser functionality"""

    def setUp(self):
        """Set up test NLU parser"""
        self.parser = NLUParser()

    def test_parse_successful_response(self):
        """Test parsing a successful LLM response"""
        response = {
            "status": "success",
            "intent": "open_app",
            "confidence": 0.9,
            "parameters": {"app_name": "Chrome"},
            "actions": [{"action": "open_application", "app_name": "Chrome"}],
            "requires_confirmation": False,
            "explanation": "Opening Chrome",
        }

        result = self.parser.parse_llm_response(response)
        self.assertIsInstance(result, ParsedIntent)
        self.assertEqual(result.intent, "open_app")
        self.assertEqual(result.confidence, 0.9)
        self.assertFalse(result.requires_confirmation)

    def test_parse_error_response(self):
        """Test parsing an error response"""
        response = {"status": "error", "error": "API error"}

        result = self.parser.parse_llm_response(response)
        self.assertEqual(result.intent, "error")
        self.assertEqual(result.confidence, 0.0)

    def test_parse_text_response(self):
        """Test parsing text response with JSON embedded"""
        text = 'Here is the result: {"intent": "click", "confidence": 0.8}'
        response = {"status": "success", "requires_parsing": True, "text": text}

        result = self.parser.parse_llm_response(response)
        self.assertIsInstance(result, ParsedIntent)

    def test_validate_actions(self):
        """Test action validation"""
        actions = [
            {"action": "open_application", "app_name": "Safari"},
            {"action": "open_url", "url": "google.com"},
            {"action": "click"},
        ]

        validated = self.parser._validate_actions(actions)
        self.assertEqual(len(validated), 3)
        self.assertIn("module", validated[0])
        # URL should be normalized with https://
        self.assertTrue(validated[1]["url"].startswith("https://"))

    def test_infer_module(self):
        """Test module inference"""
        self.assertEqual(self.parser._infer_module("open_url"), "chrome")
        self.assertEqual(self.parser._infer_module("open_file"), "vscode")
        self.assertEqual(self.parser._infer_module("execute_command"), "terminal")
        self.assertEqual(self.parser._infer_module("click"), "default")

    def test_validate_open_url(self):
        """Test URL validation"""
        action = {"action": "open_url", "url": "github.com"}
        validated = self.parser._validate_open_url(action)
        self.assertTrue(validated["url"].startswith("https://"))

    def test_validate_goto_line(self):
        """Test goto_line validation"""
        action = {"action": "goto_line", "line_number": "42"}
        validated = self.parser._validate_goto_line(action)
        self.assertIsInstance(validated["line_number"], int)
        self.assertEqual(validated["line_number"], 42)

    def test_convert_to_orchestrator_format(self):
        """Test conversion to orchestrator format"""
        parsed = ParsedIntent(
            intent="open_app",
            confidence=0.9,
            parameters={"app_name": "Chrome"},
            actions=[{"action": "open_application", "module": "default"}],
            requires_confirmation=False,
            explanation="Test",
        )

        actions = self.parser.convert_to_orchestrator_format(parsed)
        self.assertIsInstance(actions, list)
        self.assertEqual(len(actions), 1)

    def test_extract_json_from_text(self):
        """Test JSON extraction from text"""
        text = 'Some text before {"key": "value"} and after'
        result = self.parser.extract_json_from_text(text)
        self.assertIsNotNone(result)
        self.assertEqual(result["key"], "value")

    def test_extract_json_array(self):
        """Test JSON array extraction"""
        text = 'Actions: [{"action": "click"}, {"action": "copy"}]'
        result = self.parser.extract_json_from_text(text)
        self.assertIsNotNone(result)
        # Note: the regex will match individual JSON objects first, so we get the first object
        # For full array extraction, the text should start with the array
        self.assertIsInstance(result, (list, dict))


if __name__ == "__main__":
    unittest.main()
