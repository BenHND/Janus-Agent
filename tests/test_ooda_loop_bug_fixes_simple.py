"""
Simple Tests for OODA Loop Bug Fixes (No Dependencies)

This test suite validates the 6 critical bug fixes by checking source code directly.
"""

import unittest
import os
import re


class TestBug1ElementIdInstructions(unittest.TestCase):
    """Test Bug #1: Element ID usage instructions in burst prompt"""
    
    def test_french_prompt_has_element_id_instructions(self):
        """Test that French burst prompt includes element_id usage instructions"""
        with open("janus/ai/reasoning/reasoner_llm.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Verify element_id instructions are present in French section
        self.assertIn("element_id", content, "Should mention element_id")
        self.assertIn("UTILISATION DES ÉLÉMENTS VISUELS", content, 
                      "Should have French visual elements usage section")
        self.assertIn("ui.click", content, "Should mention ui.click")
        
    def test_english_prompt_has_element_id_instructions(self):
        """Test that English burst prompt includes element_id usage instructions"""
        with open("janus/ai/reasoning/reasoner_llm.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Verify element_id instructions are present in English section
        self.assertIn("USING VISUAL ELEMENTS", content,
                      "Should have English visual elements usage section")


class TestBug2SafariTabReuse(unittest.TestCase):
    """Test Bug #2: Safari tab reuse instead of creating new windows"""
    
    def test_safari_checks_current_url(self):
        """Test that Safari script checks currentURL before opening new tab"""
        with open("janus/capabilities/agents/browser_agent.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Verify script checks currentURL
        self.assertIn("currentURL", content, 
                      "Safari script should check current URL")
        self.assertIn("contains", content,
                      "Should check if URL contains domain")
        
    def test_safari_reuses_tab_on_same_domain(self):
        """Test that Safari reuses tab when on same domain"""
        with open("janus/capabilities/agents/browser_agent.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Verify logic to reuse tab exists
        self.assertIn("set URL of front document", content,
                      "Should set URL of existing document when on same domain")


class TestBug3MissingValueURL(unittest.TestCase):
    """Test Bug #3: 'missing value' URL handling"""
    
    def test_missing_value_handled(self):
        """Test that 'missing value' from Safari is handled"""
        with open("janus/runtime/core/system_state_observer.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Verify "missing value" is handled
        self.assertIn('missing value', content,
                      "Should check for 'missing value' string")
        self.assertIn('url == "missing value"', content,
                      "Should compare URL to 'missing value'")


class TestBug4SOMTokenBudget(unittest.TestCase):
    """Test Bug #4: SOM token budget increase (800 → 1500)"""
    
    def test_som_token_budget_increased(self):
        """Test that max_som_tokens is increased to 1500"""
        with open("janus/ai/reasoning/context_assembler.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Find the max_som_tokens line
        match = re.search(r'max_som_tokens:\s*int\s*=\s*(\d+)', content)
        self.assertIsNotNone(match, "Should find max_som_tokens definition")
        
        value = int(match.group(1))
        self.assertEqual(value, 1500, 
                        f"max_som_tokens should be 1500, got {value}")
        
    def test_total_token_budget_updated(self):
        """Test that max_total_tokens is updated to 2700"""
        with open("janus/ai/reasoning/context_assembler.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Find the max_total_tokens line
        match = re.search(r'max_total_tokens:\s*int\s*=\s*(\d+)', content)
        self.assertIsNotNone(match, "Should find max_total_tokens definition")
        
        value = int(match.group(1))
        self.assertEqual(value, 2700,
                        f"max_total_tokens should be 2700, got {value}")


class TestBug5ElementLimit(unittest.TestCase):
    """Test Bug #5: Element limit adjustment (50 → 30)"""
    
    def test_element_limit_reduced_to_30(self):
        """Test that DEFAULT_ELEMENT_LIMIT is reduced to 30"""
        with open("janus/vision/set_of_marks.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Find DEFAULT_ELEMENT_LIMIT
        match = re.search(r'DEFAULT_ELEMENT_LIMIT\s*=\s*(\d+)', content)
        self.assertIsNotNone(match, "Should find DEFAULT_ELEMENT_LIMIT")
        
        value = int(match.group(1))
        self.assertEqual(value, 30,
                        f"DEFAULT_ELEMENT_LIMIT should be 30, got {value}")
    
    def test_budget_config_max_som_elements_reduced(self):
        """Test that max_som_elements in BudgetConfig is 30"""
        with open("janus/ai/reasoning/context_assembler.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Find max_som_elements
        match = re.search(r'max_som_elements:\s*int\s*=\s*(\d+)', content)
        self.assertIsNotNone(match, "Should find max_som_elements")
        
        value = int(match.group(1))
        self.assertEqual(value, 30,
                        f"max_som_elements should be 30, got {value}")


class TestBug6VisionFallback(unittest.TestCase):
    """Test Bug #6: Vision fallback when accessibility returns 0"""
    
    def test_vision_fallback_exists(self):
        """Test that vision fallback logic exists when accessibility returns 0"""
        with open("janus/runtime/core/visual_observer.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Verify fallback logic exists
        self.assertIn("len(parsed_elements) > 0", content,
                      "Should check if accessibility returned elements")
        self.assertIn("falling back to vision", content.lower(),
                      "Should mention falling back to vision")
        self.assertIn("get_elements_for_reasoner", content,
                      "Should call vision engine when accessibility fails")


if __name__ == "__main__":
    unittest.main()
