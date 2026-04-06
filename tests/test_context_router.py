"""
Tests for ContextRouter - AI Context Pruning
TICKET-305: Performance optimization through intelligent context filtering
"""
import unittest

from janus.ai.reasoning.context_router import (
    VALID_CONTEXT_KEYS,
    ContextRouter,
    MockContextRouter,
)


class TestMockContextRouter(unittest.TestCase):
    """Test MockContextRouter functionality (keyword-based)"""

    def setUp(self):
        """Set up test MockContextRouter"""
        self.router = MockContextRouter()

    def test_initialization(self):
        """Test MockContextRouter initialization"""
        self.assertTrue(self.router.available)
        self.assertEqual(self.router.metrics["total_calls"], 0)

    def test_simple_command_no_context(self):
        """Test simple command that doesn't need special context"""
        # "Open Safari" should not need vision, clipboard, etc.
        result = self.router.get_requirements("Ouvre Safari")
        self.assertEqual(result, [])

    def test_simple_command_english_no_context(self):
        """Test simple English command that doesn't need special context"""
        result = self.router.get_requirements("Open Chrome")
        self.assertEqual(result, [])

    def test_clipboard_command_french(self):
        """Test French clipboard command"""
        result = self.router.get_requirements("Copie ça")
        self.assertIn("clipboard", result)

    def test_clipboard_command_paste(self):
        """Test paste command"""
        result = self.router.get_requirements("Colle le texte")
        self.assertIn("clipboard", result)

    def test_screen_content_command_french(self):
        """Test French screen content command"""
        result = self.router.get_requirements("Qu'est-ce qu'il y a à l'écran ?")
        self.assertIn("vision", result)

    def test_screen_read_command(self):
        """Test read screen command"""
        result = self.router.get_requirements("Lis le texte visible")
        self.assertIn("vision", result)

    def test_browser_content_command(self):
        """Test browser content command"""
        result = self.router.get_requirements("Résume cette page")
        self.assertIn("browser_content", result)

    def test_file_history_command(self):
        """Test file history command"""
        result = self.router.get_requirements("Ouvre le dernier fichier")
        self.assertIn("file_history", result)

    def test_command_history_redo(self):
        """Test command history for redo command (TICKET-P2-03)"""
        result = self.router.get_requirements("Refais la même chose")
        self.assertIn("command_history", result)

    def test_command_history_previous(self):
        """Test command history for previous command reference (TICKET-P2-03)"""
        result = self.router.get_requirements("Comme tout à l'heure")
        self.assertIn("command_history", result)

    def test_command_history_continue(self):
        """Test command history for continue command (TICKET-P2-03)"""
        result = self.router.get_requirements("Continue")
        self.assertIn("command_history", result)

    def test_combined_clipboard_browser(self):
        """Test command needing multiple context types"""
        result = self.router.get_requirements("Copie ce texte et va sur YouTube")
        # May contain both clipboard and browser_content depending on keyword detection
        self.assertTrue(len(result) >= 1)

    def test_first_iteration_enables_vision(self):
        """Test that vision is enabled by default on first iteration (TICKET-ARCHI)"""
        # Non-first iteration without vision keywords should not have vision
        result = self.router.get_requirements("Open Safari", is_first_iteration=False)
        self.assertNotIn("vision", result)
        
        # First iteration should always have vision, even without keywords
        result = self.router.get_requirements("Open Safari", is_first_iteration=True)
        self.assertIn("vision", result)
        
        # First iteration with vision keywords should still have vision
        result = self.router.get_requirements("What's on the screen?", is_first_iteration=True)
        self.assertIn("vision", result)

    def test_metrics_tracking(self):
        """Test that metrics are tracked"""
        self.router.get_requirements("Test command")
        self.assertEqual(self.router.metrics["total_calls"], 1)
        self.assertGreater(self.router.metrics["total_time_ms"], 0)

    def test_metrics_reset(self):
        """Test metrics reset"""
        self.router.get_requirements("Test command")
        self.router.reset_metrics()
        self.assertEqual(self.router.metrics["total_calls"], 0)


class TestContextRouterValidation(unittest.TestCase):
    """Test ContextRouter response validation"""

    def setUp(self):
        """Set up test router"""
        self.router = MockContextRouter()

    def test_valid_context_keys_frozenset(self):
        """Test that VALID_CONTEXT_KEYS is a frozenset"""
        self.assertIsInstance(VALID_CONTEXT_KEYS, frozenset)
        # TICKET-P2-03: Added command_history key for TF-IDF context pruning
        self.assertEqual(
            VALID_CONTEXT_KEYS,
            frozenset(["vision", "clipboard", "browser_content", "file_history", "command_history"])
        )

    def test_parse_response_valid_json(self):
        """Test parsing valid JSON array"""
        response = '["vision", "clipboard"]'
        result = self.router._parse_response(response)
        self.assertEqual(result, ["vision", "clipboard"])

    def test_parse_response_empty_array(self):
        """Test parsing empty JSON array"""
        response = '[]'
        result = self.router._parse_response(response)
        self.assertEqual(result, [])

    def test_parse_response_with_text(self):
        """Test parsing JSON array with surrounding text"""
        response = 'The required context keys are: ["vision"]'
        result = self.router._parse_response(response)
        self.assertEqual(result, ["vision"])

    def test_parse_response_filters_invalid_keys(self):
        """Test that invalid keys are filtered out"""
        response = '["vision", "invalid_key", "clipboard"]'
        result = self.router._parse_response(response)
        self.assertEqual(result, ["vision", "clipboard"])

    def test_parse_response_invalid_json(self):
        """Test parsing invalid JSON returns empty list"""
        response = 'not valid json'
        result = self.router._parse_response(response)
        self.assertEqual(result, [])


class TestContextRouterInitialization(unittest.TestCase):
    """Test ContextRouter initialization scenarios"""

    def test_init_without_client(self):
        """Test initialization without LLM client (will try to connect)"""
        # This may not be available, so we just test it doesn't crash
        router = ContextRouter(llm_client=None)
        # Should have attempted to initialize
        self.assertIsNotNone(router.metrics)

    def test_init_with_mock_client(self):
        """Test initialization with mock client"""
        # Create a mock client object
        class MockClient:
            def is_available(self):
                return True
            def generate(self, model, prompt, stream, options):
                return [{"response": '[]'}]
        
        router = ContextRouter(llm_client=MockClient())
        self.assertTrue(router.available)


class TestContextRouterPerformanceDoD(unittest.TestCase):
    """
    Test Definition of Done criteria from TICKET-305:
    
    [ ] A command "Ouvre Safari" does NOT inject OCR or Clipboard into Reasoner prompt
    [ ] A command "Résume cette page" DOES inject browser_content or clipboard
    """

    def setUp(self):
        """Set up test router"""
        self.router = MockContextRouter()

    def test_dod_simple_command_no_extra_context(self):
        """
        DoD: "Ouvre Safari" should NOT require screen analysis or clipboard.
        This ensures simple commands don't inject unnecessary context.
        """
        result = self.router.get_requirements("Ouvre Safari")
        self.assertNotIn("vision", result)
        self.assertNotIn("clipboard", result)
        # Empty list is ideal for simple commands
        self.assertEqual(result, [])

    def test_dod_summarize_requires_browser_content(self):
        """
        DoD: "Résume cette page" SHOULD require browser_content.
        """
        result = self.router.get_requirements("Résume cette page")
        self.assertIn("browser_content", result)

    def test_dod_copy_requires_clipboard(self):
        """Test that copy commands require clipboard context"""
        result = self.router.get_requirements("Copie ça")
        self.assertIn("clipboard", result)

    def test_dod_screen_read_requires_screen_context(self):
        """Test that screen reading commands require screen analysis context"""
        result = self.router.get_requirements("Qu'est-ce qu'il y a à l'écran ?")
        self.assertIn("vision", result)


if __name__ == "__main__":
    unittest.main()
