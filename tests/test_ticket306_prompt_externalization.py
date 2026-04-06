"""
Tests for PromptLoader - TICKET-306

Tests the externalization of prompts to Jinja2 templates.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from janus.ai.reasoning.prompt_loader import (
    PromptLoader,
    get_prompt_loader,
    load_prompt,
    PROMPTS_DIR,
)


class TestPromptLoader(unittest.TestCase):
    """Test PromptLoader functionality"""

    def setUp(self):
        """Set up test PromptLoader"""
        self.loader = PromptLoader()

    def test_prompts_directory_exists(self):
        """Test that prompts directory exists"""
        self.assertTrue(PROMPTS_DIR.exists())
        self.assertTrue(PROMPTS_DIR.is_dir())

    def test_load_french_parse_command_template(self):
        """Test loading French parse command template"""
        prompt = self.loader.load_prompt("parse_command", language="fr")
        
        self.assertIsNotNone(prompt)
        self.assertIn("macOS", prompt)
        self.assertIn("JSON", prompt)

    def test_load_english_parse_command_template(self):
        """Test loading English parse command template"""
        prompt = self.loader.load_prompt("parse_command", language="en")
        
        self.assertIsNotNone(prompt)
        self.assertIn("macOS", prompt)
        self.assertIn("JSON", prompt)

    def test_load_french_reasoner_v3_template(self):
        """Test loading French Reasoner V3 system template"""
        schema = "[TEST_SCHEMA]"
        prompt = self.loader.load_prompt(
            "reasoner_v3_system",
            language="fr",
            schema_section=schema
        )
        
        self.assertIsNotNone(prompt)
        self.assertIn("Reasoner V3", prompt)
        self.assertIn(schema, prompt)

    def test_load_english_reasoner_v3_template(self):
        """Test loading English Reasoner V3 system template"""
        schema = "[TEST_SCHEMA]"
        prompt = self.loader.load_prompt(
            "reasoner_v3_system",
            language="en",
            schema_section=schema
        )
        
        self.assertIsNotNone(prompt)
        self.assertIn("Reasoner V3", prompt)
        self.assertIn(schema, prompt)

    def test_load_french_plan_generation_template(self):
        """Test loading French plan generation template - DEPRECATED"""
        # TICKET-AUDIT-004: plan_generation prompts deleted (static planning era)
        # This test now verifies that the deprecated method returns expected fallback
        prompt = self.loader.load_prompt("plan_generation", language="fr")
        
        # Should return None since template no longer exists
        self.assertIsNone(prompt)

    def test_load_english_plan_generation_template(self):
        """Test loading English plan generation template - DEPRECATED"""
        # TICKET-AUDIT-004: plan_generation prompts deleted (static planning era)
        # This test now verifies that the deprecated method returns expected fallback
        prompt = self.loader.load_prompt("plan_generation", language="en")
        
        # Should return None since template no longer exists
        self.assertIsNone(prompt)

    def test_load_french_replan_template(self):
        """Test loading French replan template - DEPRECATED"""
        # TICKET-AUDIT-004: replan prompts deleted (static planning era)
        prompt = self.loader.load_prompt("replan", language="fr")
        
        # Should return None since template no longer exists
        self.assertIsNone(prompt)

    def test_load_english_replan_template(self):
        """Test loading English replan template - DEPRECATED"""
        # TICKET-AUDIT-004: replan prompts deleted (static planning era)
        prompt = self.loader.load_prompt("replan", language="en")
        
        # Should return None since template no longer exists
        self.assertIsNone(prompt)

    def test_load_french_decomposition_template(self):
        """Test loading French decomposition template - DEPRECATED"""
        # TICKET-AUDIT-004: decomposition prompts deleted (static planning era)
        prompt = self.loader.load_prompt("decomposition", language="fr")
        
        # Should return None since template no longer exists
        self.assertIsNone(prompt)

    def test_load_english_decomposition_template(self):
        """Test loading English decomposition template - DEPRECATED"""
        # TICKET-AUDIT-004: decomposition prompts deleted (static planning era)
        prompt = self.loader.load_prompt("decomposition", language="en")
        
        # Should return None since template no longer exists
        self.assertIsNone(prompt)

    def test_fallback_to_french_for_missing_language(self):
        """Test fallback to French when requested language not found"""
        # Request German (de) which doesn't exist
        prompt = self.loader.load_prompt("parse_command", language="de")
        
        # Should fallback to French
        self.assertIsNotNone(prompt)
        self.assertIn("macOS", prompt)

    def test_nonexistent_template_returns_none(self):
        """Test that nonexistent template returns None"""
        prompt = self.loader.load_prompt("nonexistent_template", language="fr")
        
        self.assertIsNone(prompt)

    def test_template_exists_method(self):
        """Test template_exists method"""
        # Existing template
        self.assertTrue(self.loader.template_exists("parse_command", "fr"))
        self.assertTrue(self.loader.template_exists("parse_command", "en"))
        
        # Non-existing template
        self.assertFalse(self.loader.template_exists("nonexistent", "fr"))
        self.assertFalse(self.loader.template_exists("parse_command", "de"))

    def test_clear_cache(self):
        """Test cache clearing"""
        # Load a template to populate cache
        self.loader.load_prompt("parse_command", language="fr")
        
        # Clear cache - should not raise
        self.loader.clear_cache()

    def test_global_loader_singleton(self):
        """Test that get_prompt_loader returns singleton"""
        loader1 = get_prompt_loader()
        loader2 = get_prompt_loader()
        
        self.assertIs(loader1, loader2)

    def test_convenience_load_prompt_function(self):
        """Test convenience load_prompt function"""
        prompt = load_prompt("parse_command", "fr")
        
        self.assertIsNotNone(prompt)
        self.assertIn("macOS", prompt)

    def test_custom_prompts_directory(self):
        """Test PromptLoader with custom directory"""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create a test template
            (tmppath / "test_fr.jinja2").write_text("Test template {{ var }}")
            
            loader = PromptLoader(prompts_dir=tmppath)
            prompt = loader.load_prompt("test", "fr", var="VALUE")
            
            self.assertIsNotNone(prompt)
            self.assertEqual(prompt, "Test template VALUE")

    def test_prompts_are_not_empty(self):
        """Test that all active prompts have meaningful content"""
        # TICKET-AUDIT-004: Updated to exclude deprecated prompts
        templates = [
            ("parse_command", "fr"),
            ("parse_command", "en"),
            ("reasoner_react_system", "fr"),
            ("reasoner_react_system", "en"),
            ("reasoner_reflex", "fr"),
            ("reasoner_reflex", "en"),
        ]
        
        for template_name, lang in templates:
            with self.subTest(template=template_name, lang=lang):
                prompt = self.loader.load_prompt(template_name, lang)
                
                self.assertIsNotNone(prompt, f"Template {template_name}_{lang} not found")
                self.assertGreater(len(prompt), 50, f"Template {template_name}_{lang} is too short")


class TestReasonerLLMWithTemplates(unittest.TestCase):
    """Test ReasonerLLM uses templates correctly"""

    def setUp(self):
        """Set up ReasonerLLM with mock backend"""
        from janus.ai.reasoning.reasoner_llm import ReasonerLLM
        self.llm = ReasonerLLM(backend="mock")

    def test_parse_command_uses_template(self):
        """Test that parse_command still works with templates"""
        result = self.llm.parse_command("ouvre Chrome", language="fr")
        
        self.assertIn("intents", result)
        self.assertIn("source", result)

    def test_generate_plan_uses_template(self):
        """Test that generate_plan still works with templates"""
        plan = self.llm.generate_plan("open_app", {"app_name": "Chrome"}, language="fr")
        
        self.assertIsInstance(plan, list)

    def test_generate_structured_plan_uses_template(self):
        """Test that generate_structured_plan still works with templates"""
        result = self.llm.generate_structured_plan("ouvre Chrome", language="fr")
        
        self.assertIn("steps", result)

    def test_replan_uses_template(self):
        """Test that replan still works with templates"""
        failed_action = {"module": "chrome", "action": "open_url", "args": {"url": "test.com"}}
        result = self.llm.replan(failed_action, "Network error", language="fr")
        
        self.assertIn("steps", result)

    def test_decompose_task_uses_template(self):
        """Test that decompose_task still works with templates"""
        result = self.llm.decompose_task("Prepare presentation", language="fr")
        
        self.assertIn("task", result)


if __name__ == "__main__":
    unittest.main()
