"""
Test suite for TICKET-MAC-06: Nettoyage Reasoner + Context Engine
Validates:
1. ReasonerLLM has fallback to classic parser when LLM unavailable
2. ContextAPI is exposed globally via main.py
3. Cognitive mode toggle exists and works in config UI
4. Imports are clean in reasoning module
"""
import os
import sys
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _tkinter_available():
    """Check if tkinter is available"""
    try:
        import tkinter

        return True
    except ImportError:
        return False


class TestReasonerFallback(unittest.TestCase):
    """Test ReasonerLLM fallback mechanism"""

    def test_fallback_when_llm_unavailable(self):
        """Test that fallback parser is used when LLM is not available"""
        from janus.ai.reasoning.reasoner_llm import ReasonerLLM

        # Create reasoner with non-existent model path (simulates unavailable LLM)
        llm = ReasonerLLM(backend="llama-cpp", model_path="/nonexistent/model.gguf")

        # Verify LLM is not available
        self.assertFalse(llm.available, "LLM should not be available with invalid path")

        # Test parsing - should use fallback
        result = llm.parse_command("ouvre Chrome", language="fr")

        # Verify fallback was used
        self.assertEqual(result.get("source"), "fallback", "Should use fallback parser")
        self.assertIn("intents", result, "Result should contain intents")
        self.assertGreater(len(result["intents"]), 0, "Should parse at least one intent")

        # Verify metrics tracked fallback
        metrics = llm.get_metrics()
        self.assertGreater(metrics["fallback_count"], 0, "Should track fallback usage")

    def test_fallback_parse_functionality(self):
        """Test that fallback parser produces valid results"""
        from janus.ai.reasoning.reasoner_llm import ReasonerLLM

        llm = ReasonerLLM(backend="mock")  # Mock backend for testing

        # Test various commands
        test_cases = [
            ("ouvre Chrome", "open_app"),
            ("copie", "copy"),
            ("colle", "paste"),
        ]

        for command, expected_intent in test_cases:
            with self.subTest(command=command):
                result = llm.parse_command(command, language="fr")

                self.assertIn("intents", result, f"Result should contain intents for: {command}")
                if result["intents"]:
                    intent = result["intents"][0]["intent"]
                    self.assertEqual(
                        intent,
                        expected_intent,
                        f"Expected intent '{expected_intent}' for command '{command}'",
                    )

    def test_fallback_plan_generation(self):
        """Test that fallback planner generates valid action plans"""
        from janus.ai.reasoning.reasoner_llm import ReasonerLLM

        llm = ReasonerLLM(backend="llama-cpp", model_path="/nonexistent/model.gguf")

        # Test plan generation with unavailable LLM
        plan = llm.generate_plan(
            intent="open_app", parameters={"app_name": "Chrome"}, context={}, language="fr"
        )

        # Verify plan was generated
        self.assertIsInstance(plan, list, "Plan should be a list")
        self.assertGreater(len(plan), 0, "Plan should contain at least one action")

        # Verify action structure
        action = plan[0]
        self.assertIn("action", action, "Action should have 'action' field")
        self.assertIn("module", action, "Action should have 'module' field")
        self.assertIn("parameters", action, "Action should have 'parameters' field")


class TestContextAPIExposure(unittest.TestCase):
    """Test that ContextAPI is exposed globally"""

    def test_context_api_importable_from_main(self):
        """Test that context API functions are importable from main module"""
        try:
            from main import clear_context, get_context, get_context_engine, update_context

            # Verify all functions are callable
            self.assertTrue(callable(get_context_engine), "get_context_engine should be callable")
            self.assertTrue(callable(get_context), "get_context should be callable")
            self.assertTrue(callable(update_context), "update_context should be callable")
            self.assertTrue(callable(clear_context), "clear_context should be callable")

        except ImportError as e:
            self.fail(f"Failed to import context API from main: {e}")

    def test_context_engine_initialization(self):
        """Test that global context engine can be initialized"""
        from janus.runtime.api.context_api import get_context_engine

        # Get context engine instance
        engine = get_context_engine()

        # Verify it's properly initialized
        self.assertIsNotNone(engine, "Context engine should not be None")
        self.assertTrue(hasattr(engine, "get_context"), "Engine should have get_context method")
        self.assertTrue(
            hasattr(engine, "update_context"), "Engine should have update_context method"
        )
        self.assertTrue(hasattr(engine, "clear_context"), "Engine should have clear_context method")

    def test_context_api_functions_work(self):
        """Test that context API functions work correctly"""
        from janus.runtime.api.context_api import clear_context, get_context, update_context

        # Test get_context
        context = get_context(include_ocr=False)
        self.assertIsInstance(context, dict, "Context should be a dictionary")
        self.assertIn("timestamp", context, "Context should have timestamp")
        self.assertIn("system_state", context, "Context should have system_state")
        self.assertIn("memory", context, "Context should have memory")

        # Test update_context
        try:
            update_context(
                command_text="test command", intent="test_intent", parameters={"test": "value"}
            )
        except Exception as e:
            self.fail(f"update_context raised exception: {e}")

        # Test clear_context
        try:
            clear_context(clear_session=True, clear_memory=False, clear_persistence=False)
        except Exception as e:
            self.fail(f"clear_context raised exception: {e}")


class TestCognitiveModeToggle(unittest.TestCase):
    """Test cognitive mode configuration"""

    @unittest.skipIf(not _tkinter_available(), "tkinter not available")
    def test_config_has_cognitive_planner_section(self):
        """Test that config includes cognitive planner settings"""
        from janus.ui.config_ui import ConfigUI

        config_ui = ConfigUI(config_path="/tmp/test_config_mac06.json")
        config = config_ui.get_config()

        # Verify cognitive planner section exists
        self.assertIn("cognitive_planner", config, "Config should have cognitive_planner section")

        planner_config = config["cognitive_planner"]
        self.assertIn("backend", planner_config, "Cognitive planner should have backend option")
        self.assertIn("fallback_enabled", planner_config, "Should have fallback_enabled option")

        # Verify fallback is enabled by default
        self.assertTrue(
            planner_config["fallback_enabled"].get("enabled", False),
            "Fallback should be enabled by default",
        )

    @unittest.skipIf(not _tkinter_available(), "tkinter not available")
    def test_config_has_cognitive_feature_toggle(self):
        """Test that features section includes cognitive planner toggle"""
        from janus.ui.config_ui import ConfigUI

        config_ui = ConfigUI(config_path="/tmp/test_config_mac06_features.json")
        config = config_ui.get_config()

        # Verify features section has cognitive planner
        self.assertIn("features", config, "Config should have features section")
        features = config["features"]
        self.assertIn("cognitive_planner", features, "Features should include cognitive_planner")

        # Verify it has proper structure
        cognitive_feature = features["cognitive_planner"]
        self.assertIn("enabled", cognitive_feature, "Cognitive feature should have enabled field")
        self.assertIn("label", cognitive_feature, "Cognitive feature should have label")


class TestReasoningImports(unittest.TestCase):
    """Test that reasoning module imports are clean"""

    def test_reasoning_module_imports(self):
        """Test that all reasoning components are importable"""
        try:
            from janus.ai.reasoning import (
                CommandClassifier,
                ContextMemory,
                EnhancedCommandParser,
                IntentClass,
                LLMBackend,
                LLMConfig,
                ReasonerLLM,
                VoiceReasoner,
            )

            # Verify all imports are classes/enums
            self.assertTrue(
                hasattr(EnhancedCommandParser, "__init__"),
                "EnhancedCommandParser should be a class",
            )
            self.assertTrue(
                hasattr(CommandClassifier, "__init__"), "CommandClassifier should be a class"
            )
            self.assertTrue(hasattr(ContextMemory, "__init__"), "ContextMemory should be a class")
            self.assertTrue(hasattr(VoiceReasoner, "__init__"), "VoiceReasoner should be a class")
            self.assertTrue(hasattr(ReasonerLLM, "__init__"), "ReasonerLLM should be a class")

        except ImportError as e:
            self.fail(f"Failed to import reasoning components: {e}")

    def test_no_circular_imports(self):
        """Test that there are no circular import issues"""
        try:
            # This should not raise circular import errors
            import janus.api.context_api
            import janus.ai.reasoning
            from janus.runtime.api.context_api import get_context_engine

            # Try importing in different orders
            from janus.ai.reasoning.reasoner_llm import ReasonerLLM

        except ImportError as e:
            if "circular import" in str(e).lower():
                self.fail(f"Circular import detected: {e}")
            # Other import errors might be acceptable (missing dependencies)


class TestReasonerPrompts(unittest.TestCase):
    """Test that prompts are clean and not duplicated"""

    def test_prompt_methods_exist(self):
        """Test that prompt building methods exist and work"""
        from janus.ai.reasoning.reasoner_llm import ReasonerLLM

        llm = ReasonerLLM(backend="mock")

        # Test parse prompt building
        parse_prompt = llm._build_parse_prompt(text="ouvre Chrome", language="fr", context=None)
        self.assertIsInstance(parse_prompt, str, "Parse prompt should be a string")
        self.assertGreater(len(parse_prompt), 0, "Parse prompt should not be empty")

        # Test plan prompt building
        plan_prompt = llm._build_plan_prompt(
            intent="open_app", parameters={"app_name": "Chrome"}, context=None, language="fr"
        )
        self.assertIsInstance(plan_prompt, str, "Plan prompt should be a string")
        self.assertGreater(len(plan_prompt), 0, "Plan prompt should not be empty")

    def test_prompts_support_both_languages(self):
        """Test that prompts support both French and English"""
        from janus.ai.reasoning.reasoner_llm import ReasonerLLM

        llm = ReasonerLLM(backend="mock")

        # Test French prompts
        fr_parse = llm._build_parse_prompt("test", language="fr", context=None)
        self.assertIn("Tu es", fr_parse, "French prompt should use 'Tu es'")

        fr_plan = llm._build_plan_prompt("test", {}, None, language="fr")
        self.assertIn("Tu es", fr_plan, "French plan prompt should use 'Tu es'")

        # Test English prompts
        en_parse = llm._build_parse_prompt("test", language="en", context=None)
        self.assertIn("You are", en_parse, "English prompt should use 'You are'")

        en_plan = llm._build_plan_prompt("test", {}, None, language="en")
        self.assertIn("You are", en_plan, "English plan prompt should use 'You are'")


if __name__ == "__main__":
    unittest.main()
