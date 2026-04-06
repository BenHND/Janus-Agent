"""
Test USE-CASE-1: Safari + YouTube + play media workflow

This test validates the fix for the issue where:
- Command: "Ouvre Safari, va sur Youtube et met Forgive de Burial"
- Expected: Search for "Forgive Burial" (full title + artist), then click to play
- Bug: Was only searching for "Burial" instead of the full "Forgive Burial"

The key distinction:
- "cherche" (search) = 3 steps, user wants to choose from results
- "mets/joue" (play/put on) = 4 steps, user wants immediate playback
"""
import unittest

from janus.ai.reasoning.reasoner_llm import ReasonerLLM


class TestUseCaseForgivesBurial(unittest.TestCase):
    """Test the critical media playback workflow with "[title] de [artist]" pattern"""

    def setUp(self):
        """Initialize with mock backend"""
        self.reasoner = ReasonerLLM(backend="mock")

    def test_mets_forgive_de_burial_query_extraction(self):
        """
        Test critical workflow: Mets Forgive de Burial sur YouTube
        
        The search query MUST contain BOTH "Forgive" AND "Burial" (not just "Burial").
        This is the core fix for USE-CASE-1.
        """
        command = "Ouvre Safari, va sur YouTube et mets Forgive de Burial"
        
        plan = self.reasoner.generate_structured_plan(command, language="fr")
        
        # CRITICAL: Must have exactly 4 steps (consumption pattern = search + click)
        self.assertEqual(len(plan["steps"]), 4, 
                        "Play/mets workflow must produce 4 steps (including click)")
        
        # Step 1: Open Safari
        step1 = plan["steps"][0]
        self.assertEqual(step1["module"], "system")
        self.assertEqual(step1["action"], "open_application")
        self.assertEqual(step1["args"]["app_name"], "Safari")
        
        # Step 2: Navigate to YouTube
        step2 = plan["steps"][1]
        self.assertEqual(step2["module"], "browser")
        self.assertEqual(step2["action"], "open_url")
        self.assertIn("youtube.com", step2["args"]["url"].lower())
        
        # Step 3: Search - CRITICAL FIX VALIDATION
        step3 = plan["steps"][2]
        self.assertEqual(step3["module"], "browser")
        self.assertEqual(step3["action"], "search")
        self.assertIn("query", step3["args"])
        
        # THE KEY FIX: Query must contain BOTH "Forgive" AND "Burial"
        query = step3["args"]["query"]
        self.assertIn("Forgive", query, 
                     f"Search query '{query}' must contain 'Forgive'")
        self.assertIn("Burial", query,
                     f"Search query '{query}' must contain 'Burial'")
        
        # Query should NOT contain "de" (French "by")
        self.assertNotIn(" de ", query.lower(),
                        f"Search query '{query}' should not contain ' de ' (should be 'Forgive Burial' not 'Forgive de Burial')")
        
        # Step 4: Click on first result
        step4 = plan["steps"][3]
        self.assertEqual(step4["module"], "ui")
        self.assertEqual(step4["action"], "click")
        # Click target should be the title (Forgive)
        click_text = step4["args"].get("text") or step4["args"].get("target", "")
        self.assertIn("Forgive", click_text,
                     f"Click target '{click_text}' should contain 'Forgive'")

    def test_joue_bohemian_rhapsody_de_queen(self):
        """
        Test another example: Joue Bohemian Rhapsody de Queen
        
        Validates the general pattern "[verb] [title] de [artist]"
        """
        command = "Ouvre Safari, va sur YouTube et joue Bohemian Rhapsody de Queen"
        
        plan = self.reasoner.generate_structured_plan(command, language="fr")
        
        # Must have 4 steps
        self.assertEqual(len(plan["steps"]), 4)
        
        # Step 3: Search query must contain both title and artist
        step3 = plan["steps"][2]
        query = step3["args"].get("query", "")
        self.assertIn("Bohemian", query,
                     f"Query '{query}' must contain 'Bohemian'")
        self.assertIn("Queen", query,
                     f"Query '{query}' must contain 'Queen'")
        
        # Click target should be the title
        step4 = plan["steps"][3]
        click_text = step4["args"].get("text") or step4["args"].get("target", "")
        self.assertTrue(
            "Bohemian" in click_text or "Rhapsody" in click_text,
            f"Click target '{click_text}' should contain 'Bohemian' or 'Rhapsody'"
        )

    def test_cherche_vs_mets_step_count(self):
        """
        Test that "cherche" produces 3 steps while "mets" produces 4 steps.
        
        This validates the semantic nuance:
        - "cherche" = user wants to choose from results (3 steps, no click)
        - "mets" = user wants immediate playback (4 steps, with click)
        """
        # Search pattern - 3 steps
        search_command = "Ouvre Safari, va sur YouTube et cherche Daft Punk"
        search_plan = self.reasoner.generate_structured_plan(search_command, language="fr")
        self.assertEqual(len(search_plan["steps"]), 3,
                        "Search pattern must produce 3 steps")
        
        # Play pattern - 4 steps
        play_command = "Ouvre Safari, va sur YouTube et mets Daft Punk"
        play_plan = self.reasoner.generate_structured_plan(play_command, language="fr")
        self.assertEqual(len(play_plan["steps"]), 4,
                        "Play pattern must produce 4 steps")

    def test_context_propagation_with_mets(self):
        """
        Test that context properly propagates through all 4 steps
        """
        command = "Ouvre Safari, va sur YouTube et mets Forgive de Burial"
        
        plan = self.reasoner.generate_structured_plan(command, language="fr")
        
        # Step 1: Empty context
        self.assertIsNone(plan["steps"][0]["context"]["app"])
        
        # Step 2: app=Safari, domain=youtube.com
        self.assertEqual(plan["steps"][1]["context"]["app"], "Safari")
        self.assertEqual(plan["steps"][1]["context"]["domain"], "youtube.com")
        
        # Step 3: Context propagated
        ctx3 = plan["steps"][2]["context"]
        self.assertEqual(ctx3["app"], "Safari")
        self.assertEqual(ctx3["domain"], "youtube.com")
        
        # Step 4: Context propagated to click step
        ctx4 = plan["steps"][3]["context"]
        self.assertEqual(ctx4["app"], "Safari")
        self.assertEqual(ctx4["domain"], "youtube.com")

    def test_english_play_by_artist_pattern(self):
        """
        Test English pattern: "play [title] by [artist]"
        """
        command = "Open Safari, go to YouTube and play Forgive by Burial"
        
        plan = self.reasoner.generate_structured_plan(command, language="en")
        
        # Must have 4 steps
        self.assertEqual(len(plan["steps"]), 4)
        
        # Query must contain both title and artist
        step3 = plan["steps"][2]
        query = step3["args"].get("query", "")
        self.assertIn("Forgive", query)
        self.assertIn("Burial", query)
        
        # Query should NOT contain "by"
        self.assertNotIn(" by ", query.lower(),
                        f"Search query '{query}' should not contain ' by '")


if __name__ == "__main__":
    unittest.main(verbosity=2)
