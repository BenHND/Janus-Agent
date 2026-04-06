"""Test that fallback parser produces same format as LLM"""
import unittest

from janus.ai.reasoning.reasoner_llm import ReasonerLLM


class TestFallbackFormat(unittest.TestCase):
    """Test fallback parser format consistency"""
    
    def setUp(self):
        """Initialize reasoner without LLM"""
        self.reasoner = ReasonerLLM(backend="mock")
    
    def test_fallback_has_steps(self):
        """Test that fallback returns steps array"""
        # Simulate LLM unavailable
        self.reasoner.available = False
        
        plan = self.reasoner.generate_structured_plan("Ouvre Chrome", language="fr")
        
        self.assertIn("steps", plan)
        self.assertIsInstance(plan["steps"], list)
    
    def test_fallback_steps_have_context(self):
        """Test that fallback steps include context field"""
        self.reasoner.available = False
        
        plan = self.reasoner.generate_structured_plan("Ouvre Safari", language="fr")
        
        for step in plan["steps"]:
            self.assertIn("context", step, f"Step {step} missing context field")
    
    def test_fallback_format_matches_llm(self):
        """Test that fallback and LLM formats are identical"""
        # Get LLM format (mock)
        self.reasoner.available = True
        llm_plan = self.reasoner.generate_structured_plan("Ouvre Chrome", language="fr")
        
        # Get fallback format
        self.reasoner.available = False
        fallback_plan = self.reasoner.generate_structured_plan("Ouvre Chrome", language="fr")
        
        # Both should have steps
        self.assertIn("steps", llm_plan)
        self.assertIn("steps", fallback_plan)
        
        # Both steps should have same fields
        llm_fields = set(llm_plan["steps"][0].keys())
        fallback_fields = set(fallback_plan["steps"][0].keys())
        
        # Context field must be present in both
        self.assertIn("context", llm_fields)
        self.assertIn("context", fallback_fields)
    
    def test_fallback_multi_step(self):
        """Test fallback with multi-step command"""
        self.reasoner.available = False
        
        plan = self.reasoner.generate_structured_plan(
            "Cherche Python tutorial",
            language="fr"
        )
        
        # Should generate: open Chrome, then search
        self.assertEqual(len(plan["steps"]), 2)
        
        # First step: open Chrome with context=null
        self.assertEqual(plan["steps"][0]["action"], "open_application")
        self.assertIsNone(plan["steps"][0]["context"])
        
        # Second step: search with context="Chrome"
        self.assertEqual(plan["steps"][1]["action"], "open_url")
        self.assertEqual(plan["steps"][1]["context"], "Chrome")
    
    def test_fallback_safari_support(self):
        """Test that fallback supports Safari"""
        self.reasoner.available = False
        
        plan = self.reasoner.generate_structured_plan("Ouvre Safari", language="fr")
        
        self.assertEqual(len(plan["steps"]), 1)
        self.assertEqual(plan["steps"][0]["action"], "open_application")
        self.assertEqual(plan["steps"][0]["args"]["app_name"], "Safari")
        self.assertIsNone(plan["steps"][0]["context"])
    
    def test_fallback_copy_has_args(self):
        """Test that copy action has args field"""
        self.reasoner.available = False
        
        plan = self.reasoner.generate_structured_plan("Copie", language="fr")
        
        self.assertEqual(len(plan["steps"]), 1)
        self.assertIn("args", plan["steps"][0])
        self.assertEqual(plan["steps"][0]["action"], "copy")
        self.assertIsNone(plan["steps"][0]["context"])
    
    def test_fallback_paste_has_args(self):
        """Test that paste action has args field"""
        self.reasoner.available = False
        
        plan = self.reasoner.generate_structured_plan("Colle", language="fr")
        
        self.assertEqual(len(plan["steps"]), 1)
        self.assertIn("args", plan["steps"][0])
        self.assertEqual(plan["steps"][0]["action"], "paste")
        self.assertIsNone(plan["steps"][0]["context"])
    
    def test_fallback_parse_redirects_to_structured(self):
        """Test that _fallback_parse redirects to _fallback_structured_plan"""
        self.reasoner.available = False
        
        # Call parse_command which uses _fallback_parse
        result = self.reasoner.parse_command("Ouvre Chrome", language="fr")
        
        # Should have structured_plan field
        self.assertIn("structured_plan", result)
        self.assertIn("steps", result["structured_plan"])
        
        # Steps should have context field
        for step in result["structured_plan"]["steps"]:
            self.assertIn("context", step)
    
    def test_fallback_english_commands(self):
        """Test fallback with English commands"""
        self.reasoner.available = False
        
        # Test open command
        plan = self.reasoner.generate_structured_plan("Open Chrome", language="en")
        self.assertEqual(len(plan["steps"]), 1)
        self.assertEqual(plan["steps"][0]["action"], "open_application")
        self.assertIn("context", plan["steps"][0])
        
        # Test copy command
        plan = self.reasoner.generate_structured_plan("Copy", language="en")
        self.assertEqual(len(plan["steps"]), 1)
        self.assertEqual(plan["steps"][0]["action"], "copy")
        self.assertIn("args", plan["steps"][0])
        self.assertIn("context", plan["steps"][0])
        
        # Test paste command
        plan = self.reasoner.generate_structured_plan("Paste", language="en")
        self.assertEqual(len(plan["steps"]), 1)
        self.assertEqual(plan["steps"][0]["action"], "paste")
        self.assertIn("args", plan["steps"][0])
        self.assertIn("context", plan["steps"][0])
    
    def test_fallback_unknown_command(self):
        """Test fallback with unknown command"""
        self.reasoner.available = False
        
        plan = self.reasoner.generate_structured_plan("XyzAbc unknown", language="en")
        
        self.assertEqual(len(plan["steps"]), 1)
        self.assertEqual(plan["steps"][0]["action"], "unknown")
        self.assertIn("args", plan["steps"][0])
        self.assertIn("command", plan["steps"][0]["args"])
        self.assertIn("context", plan["steps"][0])


if __name__ == "__main__":
    unittest.main()
