"""
Tests for SemanticRouter - Ultra-fast input filtering
TICKET-401: Semantic Gatekeeper implementation
"""
import unittest
from unittest.mock import MagicMock, patch

from janus.ai.reasoning.semantic_router import SemanticRouter


class TestSemanticRouterKeywordFallback(unittest.TestCase):
    """Test SemanticRouter with keyword-based fallback (no LLM)"""

    def setUp(self):
        """Set up test SemanticRouter without LLM"""
        self.router = SemanticRouter(reasoner=None)

    def test_initialization_without_llm(self):
        """Test SemanticRouter initialization without LLM"""
        self.assertIsNone(self.router.reasoner)
        self.assertIsNotNone(self.router.noise_keywords)
        self.assertIsNotNone(self.router.action_keywords)

    # NOISE tests
    def test_noise_merci(self):
        """Test 'Merci' is classified as NOISE"""
        result = self.router.classify_intent("Merci")
        self.assertEqual(result, "NOISE")

    def test_noise_merci_beaucoup(self):
        """Test 'Merci beaucoup' is classified as NOISE"""
        result = self.router.classify_intent("Merci beaucoup")
        self.assertEqual(result, "NOISE")

    def test_noise_bonjour(self):
        """Test 'Bonjour' is classified as NOISE"""
        result = self.router.classify_intent("Bonjour")
        self.assertEqual(result, "NOISE")

    def test_noise_salut(self):
        """Test 'Salut' is classified as NOISE"""
        result = self.router.classify_intent("Salut")
        self.assertEqual(result, "NOISE")

    def test_noise_ok(self):
        """Test 'Ok' is classified as NOISE"""
        result = self.router.classify_intent("Ok")
        self.assertEqual(result, "NOISE")

    def test_noise_daccord(self):
        """Test 'D'accord' is classified as NOISE"""
        result = self.router.classify_intent("D'accord")
        self.assertEqual(result, "NOISE")

    def test_noise_oui(self):
        """Test 'Oui' is classified as NOISE"""
        result = self.router.classify_intent("Oui")
        self.assertEqual(result, "NOISE")

    def test_noise_english_thanks(self):
        """Test 'Thanks' is classified as NOISE"""
        result = self.router.classify_intent("Thanks")
        self.assertEqual(result, "NOISE")

    def test_noise_english_hello(self):
        """Test 'Hello' is classified as NOISE"""
        result = self.router.classify_intent("Hello")
        self.assertEqual(result, "NOISE")

    def test_noise_empty_string(self):
        """Test empty string is classified as NOISE"""
        result = self.router.classify_intent("")
        self.assertEqual(result, "NOISE")

    def test_noise_whitespace(self):
        """Test whitespace-only is classified as NOISE"""
        result = self.router.classify_intent("   ")
        self.assertEqual(result, "NOISE")

    # ACTION tests
    def test_action_ouvre_safari(self):
        """Test 'Ouvre Safari' is classified as ACTION (TICKET-401 acceptance criteria)"""
        result = self.router.classify_intent("Ouvre Safari")
        self.assertEqual(result, "ACTION")

    def test_action_ouvre_chrome(self):
        """Test 'Ouvre Chrome' is classified as ACTION"""
        result = self.router.classify_intent("Ouvre Chrome")
        self.assertEqual(result, "ACTION")

    def test_action_ferme_safari(self):
        """Test 'Ferme Safari' is classified as ACTION"""
        result = self.router.classify_intent("Ferme Safari")
        self.assertEqual(result, "ACTION")

    def test_action_cherche_google(self):
        """Test 'Cherche sur Google' is classified as ACTION"""
        result = self.router.classify_intent("Cherche sur Google")
        self.assertEqual(result, "ACTION")

    def test_action_envoie_email(self):
        """Test 'Envoie un email' is classified as ACTION"""
        result = self.router.classify_intent("Envoie un email")
        self.assertEqual(result, "ACTION")

    def test_action_english_open_chrome(self):
        """Test 'Open Chrome' is classified as ACTION"""
        result = self.router.classify_intent("Open Chrome")
        self.assertEqual(result, "ACTION")

    def test_action_english_close_window(self):
        """Test 'Close the window' is classified as ACTION"""
        result = self.router.classify_intent("Close the window")
        self.assertEqual(result, "ACTION")

    def test_action_complex_command(self):
        """Test complex action command"""
        result = self.router.classify_intent("Ouvre Safari et cherche recette gâteau")
        self.assertEqual(result, "ACTION")

    # CHAT tests
    def test_chat_question_qui(self):
        """Test 'Qui est...' is classified as CHAT"""
        result = self.router.classify_intent("Qui est le président de la France ?")
        self.assertEqual(result, "CHAT")

    def test_chat_question_comment(self):
        """Test 'Comment...' is classified as CHAT"""
        result = self.router.classify_intent("Comment faire un gâteau ?")
        self.assertEqual(result, "CHAT")

    def test_chat_question_pourquoi(self):
        """Test 'Pourquoi...' is classified as CHAT"""
        result = self.router.classify_intent("Pourquoi le ciel est bleu ?")
        self.assertEqual(result, "CHAT")

    def test_chat_question_mark(self):
        """Test question with ? is classified as CHAT"""
        result = self.router.classify_intent("Quel temps fait-il ?")
        self.assertEqual(result, "CHAT")

    def test_chat_english_what(self):
        """Test 'What...' is classified as CHAT"""
        result = self.router.classify_intent("What is the weather today?")
        self.assertEqual(result, "CHAT")

    def test_chat_raconte_blague(self):
        """Test 'Raconte une blague' is classified as CHAT"""
        result = self.router.classify_intent("Raconte une blague")
        self.assertEqual(result, "CHAT")

    # Edge cases
    def test_action_with_noise_prefix(self):
        """Test action with noise prefix still classified as ACTION"""
        result = self.router.classify_intent("Merci et maintenant ouvre Safari")
        self.assertEqual(result, "ACTION")

    def test_unclear_short_input(self):
        """Test unclear short input defaults to NOISE"""
        result = self.router.classify_intent("hmm")
        self.assertEqual(result, "NOISE")

    def test_generic_statement(self):
        """Test generic statement without keywords defaults to CHAT"""
        result = self.router.classify_intent("Le temps est vraiment magnifique aujourd'hui")
        self.assertEqual(result, "CHAT")


class TestSemanticRouterWithLLM(unittest.TestCase):
    """Test SemanticRouter with mocked LLM"""

    def setUp(self):
        """Set up test SemanticRouter with mocked LLM"""
        self.mock_reasoner = MagicMock()
        self.mock_reasoner.available = True
        self.router = SemanticRouter(reasoner=self.mock_reasoner)

    def test_initialization_with_llm(self):
        """Test SemanticRouter initialization with LLM"""
        self.assertIsNotNone(self.router.reasoner)
        self.assertTrue(self.router.reasoner.available)

    def test_llm_classification_noise(self):
        """Test LLM-based classification returns NOISE"""
        self.mock_reasoner._run_inference.return_value = '{"intent": "NOISE"}'
        result = self.router.classify_intent("Merci beaucoup")
        self.assertEqual(result, "NOISE")
        self.mock_reasoner._run_inference.assert_called_once()

    def test_llm_classification_action(self):
        """Test LLM-based classification returns ACTION"""
        self.mock_reasoner._run_inference.return_value = '{"intent": "ACTION"}'
        result = self.router.classify_intent("Ouvre Safari")
        self.assertEqual(result, "ACTION")
        self.mock_reasoner._run_inference.assert_called_once()

    def test_llm_classification_chat(self):
        """Test LLM-based classification returns CHAT"""
        self.mock_reasoner._run_inference.return_value = '{"intent": "CHAT"}'
        result = self.router.classify_intent("Raconte une blague")
        self.assertEqual(result, "CHAT")
        self.mock_reasoner._run_inference.assert_called_once()

    def test_llm_fallback_on_error(self):
        """Test fallback to keyword-based classification when LLM fails"""
        self.mock_reasoner._run_inference.side_effect = Exception("LLM error")
        result = self.router.classify_intent("Ouvre Safari")
        # Should fallback to keyword-based classification
        self.assertEqual(result, "ACTION")

    def test_llm_inference_parameters(self):
        """Test LLM is called with correct parameters"""
        self.mock_reasoner._run_inference.return_value = '{"intent": "ACTION"}'
        self.router.classify_intent("Ouvre Safari")
        
        # Verify call parameters
        call_args = self.mock_reasoner._run_inference.call_args
        self.assertIsNotNone(call_args)
        kwargs = call_args[1]
        self.assertEqual(kwargs.get("max_tokens"), 10)
        # TICKET-500: json_mode is enabled for structured output
        self.assertTrue(kwargs.get("json_mode"))

    def test_extract_classification_exact_match(self):
        """Test extraction of classification from LLM response (JSON format - TICKET-500)"""
        self.assertEqual(self.router._extract_classification('{"intent": "NOISE"}'), "NOISE")
        self.assertEqual(self.router._extract_classification('{"intent": "ACTION"}'), "ACTION")
        self.assertEqual(self.router._extract_classification('{"intent": "CHAT"}'), "CHAT")

    def test_extract_classification_with_context(self):
        """Test extraction when classification has extra whitespace (JSON format)"""
        self.assertEqual(
            self.router._extract_classification('  {"intent": "NOISE"}  '),
            "NOISE"
        )
        self.assertEqual(
            self.router._extract_classification('{"intent": "ACTION"}\n'),
            "ACTION"
        )

    def test_extract_classification_default(self):
        """Test extraction defaults to ACTION for unclear response (fail-open - TICKET-500)"""
        # Invalid JSON should fail-open to ACTION
        self.assertEqual(
            self.router._extract_classification("unclear response"),
            "ACTION"
        )
        self.assertEqual(self.router._extract_classification(""), "ACTION")


class TestSemanticRouterIntegration(unittest.TestCase):
    """Integration tests for SemanticRouter"""

    def setUp(self):
        """Set up test SemanticRouter"""
        self.router = SemanticRouter(reasoner=None)

    def test_batch_noise_classification(self):
        """Test batch of noise inputs"""
        noise_inputs = [
            "Merci",
            "Salut",
            "Bonjour",
            "Au revoir",
            "Ok",
            "D'accord",
            "Oui",
            "Non",
            "",
            "   ",
        ]
        for input_text in noise_inputs:
            with self.subTest(input=input_text):
                result = self.router.classify_intent(input_text)
                self.assertEqual(result, "NOISE", f"Failed for input: '{input_text}'")

    def test_batch_action_classification(self):
        """Test batch of action inputs"""
        action_inputs = [
            "Ouvre Safari",
            "Ferme Chrome",
            "Cherche sur Google",
            "Lance VSCode",
            "Envoie un email",
            "Copie le texte",
            "Open Safari",
            "Close Chrome",
            "Search on Google",
        ]
        for input_text in action_inputs:
            with self.subTest(input=input_text):
                result = self.router.classify_intent(input_text)
                self.assertEqual(result, "ACTION", f"Failed for input: '{input_text}'")

    def test_batch_chat_classification(self):
        """Test batch of chat inputs"""
        chat_inputs = [
            "Qui est le président ?",
            "Quel temps fait-il ?",
            "Comment faire un gâteau ?",
            "Pourquoi le ciel est bleu ?",
            "What is the weather?",
            "Raconte une blague",
        ]
        for input_text in chat_inputs:
            with self.subTest(input=input_text):
                result = self.router.classify_intent(input_text)
                self.assertEqual(result, "CHAT", f"Failed for input: '{input_text}'")


if __name__ == "__main__":
    unittest.main()
