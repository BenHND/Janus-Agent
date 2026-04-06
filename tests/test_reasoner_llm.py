"""
Tests for ReasonerLLM - Cognitive Planner
Phase 20B

TICKET-ARCH-001 NOTE:
Some tests in this file (TestReasonerLLMUseCase1) are now OBSOLETE and will fail.
These tests were for site-specific pattern matching (YouTube, Spotify) that has been
REMOVED as per the issue requirements. The new architecture uses decide_next_action()
with ReAct loops instead of pre-planning with site-specific heuristics.

See:
- tests/test_arch_001_decide_next_action.py for new ReAct loop tests
- docs/architecture/13-dynamic-react-loop.md for architecture docs
"""
import json
import unittest

from janus.ai.reasoning.reasoner_llm import LLMBackend, LLMConfig, ReasonerLLM


class TestReasonerLLM(unittest.TestCase):
    """Test ReasonerLLM functionality"""

    def setUp(self):
        """Set up test ReasonerLLM with mock backend"""
        self.llm = ReasonerLLM(backend="mock")

    def test_initialization_mock(self):
        """Test ReasonerLLM initialization with mock backend"""
        self.assertEqual(self.llm.backend, LLMBackend.MOCK)
        self.assertTrue(self.llm.available)
        self.assertIsNotNone(self.llm.llm)

    def test_initialization_llama_cpp_without_model(self):
        """Test llama-cpp backend fails gracefully without model"""
        llm = ReasonerLLM(backend="llama-cpp", model_path="/nonexistent/model.gguf")
        self.assertFalse(llm.available)

    def test_parse_command_french_open_app(self):
        """Test parsing French command: open application"""
        result = self.llm.parse_command("ouvre Chrome", language="fr")

        self.assertIn("intents", result)
        self.assertGreater(len(result["intents"]), 0)

        intent = result["intents"][0]
        self.assertEqual(intent["intent"], "open_app")
        self.assertIn("app_name", intent["parameters"])
        self.assertEqual(intent["parameters"]["app_name"], "Chrome")
        self.assertGreater(intent["confidence"], 0.5)

    def test_parse_command_english_open_app(self):
        """Test parsing English command: open application"""
        result = self.llm.parse_command("open Safari", language="en")

        self.assertIn("intents", result)
        self.assertGreater(len(result["intents"]), 0)

        intent = result["intents"][0]
        self.assertEqual(intent["intent"], "open_app")
        self.assertEqual(intent["parameters"]["app_name"], "Safari")

    def test_parse_command_french_copy(self):
        """Test parsing French command: copy"""
        result = self.llm.parse_command("copie ce texte", language="fr")

        self.assertIn("intents", result)
        intent = result["intents"][0]
        self.assertEqual(intent["intent"], "copy")
        self.assertGreater(intent["confidence"], 0.5)

    def test_parse_command_english_paste(self):
        """Test parsing English command: paste"""
        result = self.llm.parse_command("paste here", language="en")

        self.assertIn("intents", result)
        intent = result["intents"][0]
        self.assertEqual(intent["intent"], "paste")

    def test_parse_command_with_context(self):
        """Test parsing with context from Phase 19"""
        context = {
            "memory": {"last_app": "Chrome", "last_url": "https://github.com"},
            "session": {"last_click_position": (100, 200)},
        }

        result = self.llm.parse_command("navigue vers Google", language="fr", context=context)
        self.assertIn("intents", result)
        self.assertIn("source", result)

    def test_parse_command_latency_tracking(self):
        """Test that latency is tracked"""
        result = self.llm.parse_command("open Chrome", language="en")

        self.assertIn("latency_ms", result)
        self.assertGreater(result["latency_ms"], 0)

        # Mock should be very fast (<50ms)
        self.assertLess(result["latency_ms"], 50)

    # Tests for removed generate_plan() method have been deleted
    # This method was part of the legacy planning system and has been removed
    # in TICKET-REFACTOR-002. Use decide_next_action() for ReAct-style planning.

    def test_fallback_parse_when_unavailable(self):
        """
        Test explicit error when LLM unavailable
        
        ARCH-REMEDIATION-CRITICAL: All fallbacks removed. 
        When LLM is unavailable, return explicit error state (not fallback).
        """
        # Create LLM with unavailable backend
        llm = ReasonerLLM(backend="llama-cpp", model_path="/nonexistent/model.gguf")
        self.assertFalse(llm.available)

        result = llm.parse_command("ouvre Chrome", language="fr")

        # Should return error state, not fallback
        self.assertIn("source", result)
        self.assertEqual(result["source"], "error", "Should return 'error' not 'fallback'")
        self.assertIn("intents", result)
        self.assertEqual(len(result["intents"]), 0, "Should return empty intents on error")
        self.assertIn("error", result, "Should include error message")

    # test_fallback_plan_when_unavailable removed - generate_plan() was deleted

    def test_metrics_tracking(self):
        """Test performance metrics tracking"""
        # Reset metrics
        self.llm.reset_metrics()

        # Make some calls (only parse_command is available after legacy removal)
        self.llm.parse_command("ouvre Chrome", language="fr")
        self.llm.parse_command("copie", language="fr")

        metrics = self.llm.get_metrics()

        self.assertEqual(metrics["total_calls"], 2)
        self.assertGreater(metrics["total_time_ms"], 0)
        self.assertGreater(metrics["avg_latency_ms"], 0)
        self.assertEqual(metrics["fallback_count"], 0)
        self.assertTrue(metrics["available"])

    def test_llm_config_custom(self):
        """Test custom LLM configuration"""
        config = LLMConfig(
            backend=LLMBackend.MOCK,
            n_ctx=4096,
            temperature=0.2,
            max_tokens=1024,
            timeout_ms=500,
        )

        llm = ReasonerLLM(backend="mock", config=config)

        self.assertEqual(llm.config.n_ctx, 4096)
        self.assertEqual(llm.config.temperature, 0.2)
        self.assertEqual(llm.config.max_tokens, 1024)
        self.assertEqual(llm.config.timeout_ms, 500)

    def test_multiple_intents_parsing(self):
        """Test parsing command with multiple intents"""
        # Complex command that should generate multiple intents
        result = self.llm.parse_command("ouvre Chrome et va sur GitHub", language="fr")

        self.assertIn("intents", result)
        # Mock may return single or multiple intents
        self.assertGreater(len(result["intents"]), 0)

    def test_unknown_command_handling(self):
        """Test handling of unknown/unclear commands"""
        result = self.llm.parse_command("xyzabc unclear command", language="en")

        self.assertIn("intents", result)
        # Should return some response even for unclear commands
        self.assertIsInstance(result["intents"], list)

    def test_json_response_parsing(self):
        """Test parsing of JSON from LLM response"""
        # Test with clean JSON
        response = '{"intents": [{"intent": "open_app", "parameters": {"app_name": "Chrome"}, "confidence": 0.9}]}'
        result = self.llm._parse_llm_response(response)

        self.assertIn("intents", result)
        self.assertEqual(len(result["intents"]), 1)
        self.assertEqual(result["intents"][0]["intent"], "open_app")

    def test_json_response_with_extra_text(self):
        """Test parsing JSON when LLM adds extra text"""
        # LLM might add explanation before/after JSON
        response = 'Here is the parsed command:\n{"intents": [{"intent": "copy", "parameters": {}, "confidence": 0.85}]}\nThis command will copy content.'
        result = self.llm._parse_llm_response(response)

        self.assertIn("intents", result)
        self.assertEqual(result["intents"][0]["intent"], "copy")

    # test_plan_response_parsing removed - _parse_plan_response() was deleted

    def test_backend_enum(self):
        """Test LLMBackend enum"""
        self.assertEqual(LLMBackend.LLAMA_CPP.value, "llama-cpp")
        self.assertEqual(LLMBackend.OLLAMA.value, "ollama")
        self.assertEqual(LLMBackend.MOCK.value, "mock")


class TestReasonerLLMIntegration(unittest.TestCase):
    """Integration tests for ReasonerLLM with various commands"""

    def setUp(self):
        """Set up ReasonerLLM for integration tests"""
        self.llm = ReasonerLLM(backend="mock")

    # French command tests (30+ varied commands)

    def test_fr_command_01_open_chrome(self):
        """FR: ouvre Chrome"""
        result = self.llm.parse_command("ouvre Chrome", language="fr")
        self.assertIn("intents", result)

    def test_fr_command_02_open_safari(self):
        """FR: lance Safari"""
        result = self.llm.parse_command("lance Safari", language="fr")
        self.assertIn("intents", result)

    def test_fr_command_03_copy(self):
        """FR: copie ce texte"""
        result = self.llm.parse_command("copie ce texte", language="fr")
        self.assertIn("intents", result)

    def test_fr_command_04_paste(self):
        """FR: colle ici"""
        result = self.llm.parse_command("colle ici", language="fr")
        self.assertIn("intents", result)

    def test_fr_command_05_click(self):
        """FR: clique sur le bouton"""
        result = self.llm.parse_command("clique sur le bouton", language="fr")
        self.assertIn("intents", result)

    def test_fr_command_06_navigate_url(self):
        """FR: va sur github.com"""
        result = self.llm.parse_command("va sur github.com", language="fr")
        self.assertIn("intents", result)

    def test_fr_command_07_open_file(self):
        """FR: ouvre le fichier test.py"""
        result = self.llm.parse_command("ouvre le fichier test.py", language="fr")
        self.assertIn("intents", result)

    def test_fr_command_08_close_app(self):
        """FR: ferme l'application"""
        result = self.llm.parse_command("ferme l'application", language="fr")
        self.assertIn("intents", result)

    def test_fr_command_09_save_file(self):
        """FR: sauvegarde le fichier"""
        result = self.llm.parse_command("sauvegarde le fichier", language="fr")
        self.assertIn("intents", result)

    def test_fr_command_10_search(self):
        """FR: cherche Python tutorial"""
        result = self.llm.parse_command("cherche Python tutorial", language="fr")
        self.assertIn("intents", result)

    # English command tests

    def test_en_command_01_open_chrome(self):
        """EN: open Chrome"""
        result = self.llm.parse_command("open Chrome", language="en")
        self.assertIn("intents", result)

    def test_en_command_02_launch_vscode(self):
        """EN: launch VSCode"""
        result = self.llm.parse_command("launch VSCode", language="en")
        self.assertIn("intents", result)

    def test_en_command_03_copy_text(self):
        """EN: copy this text"""
        result = self.llm.parse_command("copy this text", language="en")
        self.assertIn("intents", result)

    def test_en_command_04_paste_content(self):
        """EN: paste here"""
        result = self.llm.parse_command("paste here", language="en")
        self.assertIn("intents", result)

    def test_en_command_05_click_button(self):
        """EN: click on the button"""
        result = self.llm.parse_command("click on the button", language="en")
        self.assertIn("intents", result)

    def test_en_command_06_go_to_url(self):
        """EN: go to google.com"""
        result = self.llm.parse_command("go to google.com", language="en")
        self.assertIn("intents", result)

    def test_en_command_07_open_file(self):
        """EN: open file readme.md"""
        result = self.llm.parse_command("open file readme.md", language="en")
        self.assertIn("intents", result)

    def test_en_command_08_close_window(self):
        """EN: close the window"""
        result = self.llm.parse_command("close the window", language="en")
        self.assertIn("intents", result)

    def test_en_command_09_save_document(self):
        """EN: save the document"""
        result = self.llm.parse_command("save the document", language="en")
        self.assertIn("intents", result)

    def test_en_command_10_find_text(self):
        """EN: find TODO in file"""
        result = self.llm.parse_command("find TODO in file", language="en")
        self.assertIn("intents", result)

    # Complex multi-step commands

    def test_complex_command_01_open_and_navigate(self):
        """Complex: open Chrome and go to GitHub"""
        result = self.llm.parse_command("open Chrome and go to GitHub", language="en")
        self.assertIn("intents", result)

    def test_complex_command_02_copy_and_paste(self):
        """Complex: copy this and paste it there"""
        result = self.llm.parse_command("copy this and paste it there", language="en")
        self.assertIn("intents", result)

    def test_complex_command_03_search_and_open(self):
        """Complex: search Python tutorial and open first result"""
        result = self.llm.parse_command(
            "search Python tutorial and open first result", language="en"
        )
        self.assertIn("intents", result)

    def test_complex_command_04_fr_ouvre_et_va(self):
        """Complex FR: ouvre Chrome et va sur GitHub"""
        result = self.llm.parse_command("ouvre Chrome et va sur GitHub", language="fr")
        self.assertIn("intents", result)

    def test_complex_command_05_file_operations(self):
        """Complex: open file, find text, copy"""
        result = self.llm.parse_command("open file test.py, find TODO, and copy it", language="en")
        self.assertIn("intents", result)

    # Contextual commands

    def test_contextual_command_01_implicit_app(self):
        """Contextual: navigate URL with implicit browser"""
        context = {"memory": {"last_app": "Chrome"}}
        result = self.llm.parse_command("go to GitHub", language="en", context=context)
        self.assertIn("intents", result)

    def test_contextual_command_02_implicit_file(self):
        """Contextual: save with implicit file"""
        context = {"memory": {"last_file": "test.py"}}
        result = self.llm.parse_command("save", language="en", context=context)
        self.assertIn("intents", result)

    def test_contextual_command_03_reference_it(self):
        """Contextual: paste it (reference to last copied)"""
        context = {"session": {"last_copied_content": "Hello World"}}
        result = self.llm.parse_command("paste it", language="en", context=context)
        self.assertIn("intents", result)

    def test_contextual_command_04_reference_here(self):
        """Contextual: click here (reference to last position)"""
        context = {"session": {"last_click_position": (100, 200)}}
        result = self.llm.parse_command("click here", language="en", context=context)
        self.assertIn("intents", result)

    def test_contextual_command_05_chained_actions(self):
        """Contextual: chained actions with implicit references"""
        context = {
            "memory": {"last_app": "Chrome", "last_url": "https://github.com"},
            "session": {"last_click_position": (500, 300)},
        }
        result = self.llm.parse_command("refresh page", language="en", context=context)
        self.assertIn("intents", result)

    # Edge cases

    def test_edge_case_empty_command(self):
        """Edge case: empty command"""
        result = self.llm.parse_command("", language="en")
        self.assertIn("intents", result)

    def test_edge_case_whitespace_only(self):
        """Edge case: whitespace only"""
        result = self.llm.parse_command("   ", language="en")
        self.assertIn("intents", result)

    def test_edge_case_special_characters(self):
        """Edge case: command with special characters"""
        result = self.llm.parse_command("open @#$%^", language="en")
        self.assertIn("intents", result)

    # Latency tests

    def test_latency_simple_command(self):
        """Latency test: simple command should be fast"""
        result = self.llm.parse_command("open Chrome", language="en")
        self.assertLess(result["latency_ms"], 100)

    def test_latency_complex_command(self):
        """Latency test: complex command should still be fast with mock"""
        result = self.llm.parse_command(
            "open Chrome, go to GitHub, find repository, and copy URL", language="en"
        )
        # Mock should be very fast even for complex commands
        self.assertLess(result["latency_ms"], 100)


# TICKET-REFACTOR-002: TestReasonerLLMStructuredPlanning removed
# generate_structured_plan() was part of the OLD planning-based architecture.
# The new architecture uses ActionCoordinator with decide_next_action() for ReAct-style execution.
# Tests for ReAct architecture are in test_arch_001_decide_next_action.py


if __name__ == "__main__":
    unittest.main()


# TestReasonerLLMUseCase1 class REMOVED in TICKET-ARCH-007
# This class tested OBSOLETE site-specific YouTube logic that was removed
# in favor of the generic ReAct loop architecture.
# See: tests/test_arch_001_decide_next_action.py and 
#      tests/test_arch_007_ooda_scenarios.py for new tests


