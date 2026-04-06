"""
Test TICKET-001: Safari + YouTube + search workflow
Critical acceptance criteria from issue requirements
"""
import unittest

from janus.ai.reasoning.reasoner_llm import ReasonerLLM


class TestSafariYouTubeSearch(unittest.TestCase):
    """Test the critical Safari + YouTube + search workflow"""

    def setUp(self):
        """Initialize with mock backend"""
        self.reasoner = ReasonerLLM(backend="mock")

    def test_safari_youtube_search_workflow_french(self):
        """
        Test critical workflow: Ouvre Safari, va sur YouTube et cherche [query]
        
        This is the PRIMARY acceptance criterion from TICKET-001:
        "Safari + YouTube + recherche fonctionne à 100% en un seul prompt"
        """
        # The exact command from requirements
        command = "Ouvre Safari, va sur YouTube et cherche Forgive de Burial"
        
        plan = self.reasoner.generate_structured_plan(command, language="fr")
        
        # CRITICAL: Must have exactly 3 steps
        self.assertEqual(len(plan["steps"]), 3, 
                        "Safari + YouTube + search must produce exactly 3 steps")
        
        # Step 1: Open Safari
        step1 = plan["steps"][0]
        self.assertEqual(step1["module"], "system")
        self.assertEqual(step1["action"], "open_app")
        self.assertEqual(step1["args"]["app_name"], "Safari")
        
        # Context: All None for initial app open
        ctx1 = step1["context"]
        self.assertIsNone(ctx1["app"])
        self.assertIsNone(ctx1["surface"])
        self.assertIsNone(ctx1["url"])
        self.assertIsNone(ctx1["domain"])
        self.assertIsNone(ctx1["thread"])
        self.assertIsNone(ctx1["record"])
        
        # Step 2: Navigate to YouTube
        step2 = plan["steps"][1]
        self.assertEqual(step2["module"], "browser")
        self.assertEqual(step2["action"], "open_url")
        self.assertIn("youtube.com", step2["args"]["url"])
        
        # Context: app=Safari, domain=youtube.com, surface=browser
        ctx2 = step2["context"]
        self.assertEqual(ctx2["app"], "Safari")
        self.assertEqual(ctx2["domain"], "youtube.com")
        self.assertEqual(ctx2["surface"], "browser")
        self.assertIn("youtube.com", ctx2["url"])
        
        # Step 3: Search on YouTube
        step3 = plan["steps"][2]
        self.assertEqual(step3["module"], "browser")
        self.assertEqual(step3["action"], "search")
        self.assertIn("query", step3["args"])
        
        # Context: Propagated from step 2
        ctx3 = step3["context"]
        self.assertEqual(ctx3["app"], "Safari")
        self.assertEqual(ctx3["domain"], "youtube.com")
        self.assertEqual(ctx3["surface"], "browser")

    def test_safari_youtube_search_workflow_english(self):
        """
        Test workflow in English: Open Safari, go to YouTube and search [query]
        """
        command = "Open Safari, go to YouTube and search Python tutorials"
        
        plan = self.reasoner.generate_structured_plan(command, language="en")
        
        # Must have exactly 3 steps
        self.assertEqual(len(plan["steps"]), 3)
        
        # Validate step sequence
        self.assertEqual(plan["steps"][0]["module"], "system")
        self.assertEqual(plan["steps"][0]["action"], "open_app")
        
        self.assertEqual(plan["steps"][1]["module"], "browser")
        self.assertEqual(plan["steps"][1]["action"], "open_url")
        
        self.assertEqual(plan["steps"][2]["module"], "browser")
        self.assertEqual(plan["steps"][2]["action"], "search")

    def test_chrome_youtube_search_workflow(self):
        """
        Test same workflow but with Chrome instead of Safari
        """
        command = "Ouvre Chrome, va sur YouTube et cherche jazz"
        
        plan = self.reasoner.generate_structured_plan(command, language="fr")
        
        self.assertEqual(len(plan["steps"]), 3)
        
        # Should use Chrome instead of Safari
        self.assertEqual(plan["steps"][0]["args"]["app_name"], "Chrome")
        self.assertEqual(plan["steps"][1]["context"]["app"], "Chrome")
        self.assertEqual(plan["steps"][2]["context"]["app"], "Chrome")

    def test_context_propagation_full_workflow(self):
        """
        Test that context properly propagates through all 3 steps
        """
        command = "Ouvre Safari, va sur YouTube et cherche machine learning"
        
        plan = self.reasoner.generate_structured_plan(command, language="fr")
        
        # Validate context propagation chain
        # Step 1: Empty context
        self.assertIsNone(plan["steps"][0]["context"]["app"])
        
        # Step 2: app=Safari, domain=youtube.com
        self.assertEqual(plan["steps"][1]["context"]["app"], "Safari")
        self.assertEqual(plan["steps"][1]["context"]["domain"], "youtube.com")
        
        # Step 3: Context fully propagated from step 2
        ctx3 = plan["steps"][2]["context"]
        self.assertEqual(ctx3["app"], "Safari")
        self.assertEqual(ctx3["domain"], "youtube.com")
        self.assertEqual(ctx3["surface"], "browser")

    def test_json_structure_validity(self):
        """
        Test that the JSON structure is valid V3 format
        """
        command = "Ouvre Safari, va sur YouTube et cherche anything"
        
        plan = self.reasoner.generate_structured_plan(command, language="fr")
        
        # Must have "steps" key
        self.assertIn("steps", plan)
        self.assertIsInstance(plan["steps"], list)
        
        # Each step must have required fields
        for step in plan["steps"]:
            self.assertIn("module", step)
            self.assertIn("action", step)
            self.assertIn("args", step)
            self.assertIn("context", step)
            
            # Context must be a dict with all 6 fields
            ctx = step["context"]
            self.assertIsInstance(ctx, dict)
            for field in ["app", "surface", "url", "domain", "thread", "record"]:
                self.assertIn(field, ctx)

    def test_multi_step_commands_work_100_percent(self):
        """
        Test from TICKET-001: "Toute commande multi-step produit un JSON propre et complet"
        """
        test_commands = [
            ("Ouvre Safari, va sur YouTube et cherche Python", "fr", 3),
            ("Ouvre Safari et va sur YouTube", "fr", 2),
            ("Open Safari, go to YouTube and search Python", "en", 3),
        ]
        
        for command, lang, expected_steps in test_commands:
            with self.subTest(command=command):
                plan = self.reasoner.generate_structured_plan(command, language=lang)
                
                # Must produce valid JSON
                self.assertIn("steps", plan)
                self.assertIsInstance(plan["steps"], list)
                self.assertEqual(len(plan["steps"]), expected_steps)
                
                # All steps must be complete
                for step in plan["steps"]:
                    self.assertIn("module", step)
                    self.assertIn("action", step)
                    self.assertIn("context", step)
                    self.assertIsInstance(step["context"], dict)


if __name__ == "__main__":
    unittest.main()
