"""
Tests for TICKET-OPT-001: Reasoning Tiers (Fast & Slow Mode)

Tests for:
1. Reflex prompt templates (FR/EN)
2. decide_reflex_action() method with aggressive parameters
3. Switch logic heuristic (without full executor)
4. Token reduction on form-filling scenarios
5. Performance metrics (<800ms for reflex mode)
"""
import json
import time
import unittest
from unittest.mock import Mock, patch, AsyncMock

from janus.ai.reasoning.reasoner_llm import ReasonerLLM, LLMBackend


# Test constants
REFLEX_PROMPT_SIZE_THRESHOLD = 0.5  # Reflex prompt should be <50% of analysis prompt
REFLEX_WORD_COUNT_THRESHOLD = 0.4  # Reflex prompt should be <40% analysis word count
TOKEN_REDUCTION_TARGET = 40.0  # Target at least 40% token reduction (goal is 50%)


class TestReasonerReflexMode(unittest.TestCase):
    """Test reflex mode in ReasonerLLM"""
    
    def setUp(self):
        """Set up test ReasonerLLM with mock backend"""
        self.reasoner = ReasonerLLM(backend="mock")
    
    def test_reflex_template_french_loaded(self):
        """Test that French reflex template exists"""
        from janus.ai.reasoning.prompt_loader import get_prompt_loader
        loader = get_prompt_loader()
        self.assertTrue(loader.template_exists("reasoner_reflex", "fr"))
    
    def test_reflex_template_english_loaded(self):
        """Test that English reflex template exists"""
        from janus.ai.reasoning.prompt_loader import get_prompt_loader
        loader = get_prompt_loader()
        self.assertTrue(loader.template_exists("reasoner_reflex", "en"))
    
    def test_decide_reflex_action_basic(self):
        """Test decide_reflex_action returns valid action"""
        result = self.reasoner.decide_reflex_action(
            previous_action="clicked login button",
            visible_elements="[text_field: email, text_field: password, button: submit]",
            language="fr"
        )
        
        # Should return valid action structure
        self.assertIn("action", result)
        self.assertIn("args", result)
        self.assertIn("reasoning", result)
        
        # Should not be an error
        self.assertNotEqual(result.get("action"), "error")
    
    def test_decide_reflex_action_unavailable(self):
        """Test decide_reflex_action handles unavailable LLM"""
        # Create reasoner with unavailable backend
        reasoner = ReasonerLLM(backend="llama-cpp", model_path="/nonexistent/model.gguf")
        
        result = reasoner.decide_reflex_action(
            previous_action="clicked button",
            visible_elements="[]",
            language="fr"
        )
        
        # Should return error
        self.assertEqual(result.get("action"), "error")
        self.assertIn("error", result)
    
    def test_reflex_action_performance_target(self):
        """Test that reflex mode is faster than 800ms (with mock backend)"""
        start = time.time()
        result = self.reasoner.decide_reflex_action(
            previous_action="typed email",
            visible_elements="[text_field: password, button: login]",
            language="fr"
        )
        latency_ms = (time.time() - start) * 1000
        
        # Mock backend should be very fast (<50ms)
        self.assertLess(latency_ms, 50)
        
        # Should succeed
        self.assertNotEqual(result.get("action"), "error")
    
    def test_reflex_minimal_prompt(self):
        """Test that reflex prompt is minimal (shorter than regular prompt)"""
        # Build a reflex prompt
        reflex_prompt = self.reasoner._build_reflex_prompt(
            previous_action="clicked button",
            visible_elements="[field: email]",
            language="fr"
        )
        
        # Build a regular React prompt for comparison
        react_prompt = self.reasoner._build_react_prompt(
            user_goal="Fill login form",
            system_state={"active_app": "Chrome", "url": "https://example.com"},
            visual_context="[field: email, field: password]",
            memory={},
            language="fr"
        )
        
        # Reflex prompt should be significantly shorter
        self.assertLess(len(reflex_prompt), len(react_prompt) * REFLEX_PROMPT_SIZE_THRESHOLD)
        print(f"\nReflex prompt: {len(reflex_prompt)} chars")
        print(f"React prompt: {len(react_prompt)} chars")
        print(f"Reduction: {(1 - len(reflex_prompt)/len(react_prompt))*100:.1f}%")


class TestSwitchLogicHeuristic(unittest.TestCase):
    """Test switch logic heuristic (without full executor dependency)"""
    
    def test_should_use_reflex_first_iteration(self):
        """Test first iteration uses analysis mode"""
        # First iteration - no previous action
        result = self._should_use_reflex_mode(
            previous_action_success=False,
            previous_action_type=None,
            current_url="https://example.com",
            previous_url=None,
            current_app="Chrome",
            previous_app=None,
        )
        
        # First iteration should use analysis mode
        self.assertFalse(result)
    
    def test_should_use_reflex_after_success_type_text(self):
        """Test reflex mode after successful type_text"""
        result = self._should_use_reflex_mode(
            previous_action_success=True,
            previous_action_type="type_text",
            current_url="https://example.com/login",
            previous_url="https://example.com/login",
            current_app="Chrome",
            previous_app="Chrome",
        )
        
        # Should use reflex mode (same context, success, form action)
        self.assertTrue(result)
    
    def test_should_use_reflex_after_success_click(self):
        """Test reflex mode after successful click"""
        result = self._should_use_reflex_mode(
            previous_action_success=True,
            previous_action_type="click",
            current_url="https://example.com/form",
            previous_url="https://example.com/form",
            current_app="Safari",
            previous_app="Safari",
        )
        
        # Should use reflex mode
        self.assertTrue(result)
    
    def test_should_use_analysis_after_failure(self):
        """Test analysis mode after action failure"""
        result = self._should_use_reflex_mode(
            previous_action_success=False,  # Failed
            previous_action_type="click",
            current_url="https://example.com",
            previous_url="https://example.com",
            current_app="Chrome",
            previous_app="Chrome",
        )
        
        # Should use analysis mode after failure
        self.assertFalse(result)
    
    def test_should_use_analysis_after_url_change(self):
        """Test analysis mode after URL change (navigation)"""
        result = self._should_use_reflex_mode(
            previous_action_success=True,
            previous_action_type="click",
            current_url="https://example.com/dashboard",  # Changed
            previous_url="https://example.com/login",
            current_app="Chrome",
            previous_app="Chrome",
        )
        
        # Should use analysis mode after navigation
        self.assertFalse(result)
    
    def test_should_use_analysis_after_app_change(self):
        """Test analysis mode after app change"""
        result = self._should_use_reflex_mode(
            previous_action_success=True,
            previous_action_type="type_text",
            current_url="https://example.com",
            previous_url="https://example.com",
            current_app="Safari",  # Changed
            previous_app="Chrome",
        )
        
        # Should use analysis mode after app change
        self.assertFalse(result)
    
    def test_should_use_analysis_for_non_form_actions(self):
        """Test analysis mode for non-form actions (open_app, extract_data, etc.)"""
        result = self._should_use_reflex_mode(
            previous_action_success=True,
            previous_action_type="open_app",  # Not form-related
            current_url="https://example.com",
            previous_url="https://example.com",
            current_app="Chrome",
            previous_app="Chrome",
        )
        
        # Should use analysis mode for non-form actions
        self.assertFalse(result)
    
    def test_reflex_eligible_actions(self):
        """Test that only form-related actions are reflex-eligible"""
        eligible_actions = ["type_text", "click", "type", "fill"]
        
        for action in eligible_actions:
            result = self._should_use_reflex_mode(
                previous_action_success=True,
                previous_action_type=action,
                current_url="https://example.com",
                previous_url="https://example.com",
                current_app="Chrome",
                previous_app="Chrome",
            )
            self.assertTrue(result, f"Action '{action}' should be reflex-eligible")
        
        # Test non-eligible actions
        non_eligible = ["open_app", "open_url", "scroll", "extract_data", "press_key"]
        for action in non_eligible:
            result = self._should_use_reflex_mode(
                previous_action_success=True,
                previous_action_type=action,
                current_url="https://example.com",
                previous_url="https://example.com",
                current_app="Chrome",
                previous_app="Chrome",
            )
            self.assertFalse(result, f"Action '{action}' should NOT be reflex-eligible")
    
    # Copy of the heuristic logic from AgentExecutorV3 for testing
    def _should_use_reflex_mode(
        self,
        previous_action_success: bool,
        previous_action_type: str,
        current_url: str,
        previous_url: str,
        current_app: str,
        previous_app: str,
    ) -> bool:
        """Heuristic for reflex mode (copied from AgentExecutorV3)"""
        if previous_action_type is None:
            return False
        if not previous_action_success:
            return False
        if previous_url != current_url and previous_url is not None:
            return False
        if previous_app != current_app and previous_app is not None:
            return False
        reflex_eligible_actions = ["type_text", "click", "type", "fill"]
        if previous_action_type not in reflex_eligible_actions:
            return False
        return True


class TestTokenReductionFormScenario(unittest.TestCase):
    """Test token reduction in form-filling scenario"""
    
    def setUp(self):
        """Set up test reasoner"""
        self.reasoner = ReasonerLLM(backend="mock")
    
    def test_form_filling_token_reduction(self):
        """Test that form-filling with reflex mode uses fewer tokens than analysis mode"""
        # Simulate a form-filling scenario with 5 steps
        # Step 1: Analysis mode (first action)
        # Step 2-5: Reflex mode (subsequent form actions)
        
        # Count tokens in prompts
        analysis_tokens = 0
        reflex_tokens = 0
        
        # Step 1: Initial analysis (full prompt)
        analysis_prompt_1 = self.reasoner._build_react_prompt(
            user_goal="Fill login form with email and password",
            system_state={"active_app": "Chrome", "url": "https://example.com/login"},
            visual_context='[{"id": "email_1", "type": "input"}, {"id": "password_2", "type": "input"}]',
            memory={},
            language="fr"
        )
        analysis_tokens += len(analysis_prompt_1.split())
        
        # Step 2-5: Reflex mode (minimal prompts)
        for i in range(4):
            reflex_prompt = self.reasoner._build_reflex_prompt(
                previous_action="typed text",
                visible_elements='[{"id": "field", "type": "input"}]',
                language="fr"
            )
            reflex_tokens += len(reflex_prompt.split())
        
        # Total tokens with reflex mode
        total_with_reflex = analysis_tokens + reflex_tokens
        
        # Total tokens if all steps used analysis mode
        total_without_reflex = analysis_tokens * 5
        
        # Calculate reduction
        reduction_percent = (1 - total_with_reflex / total_without_reflex) * 100
        
        print(f"\nToken usage comparison (5-step form filling):")
        print(f"  With reflex mode: {total_with_reflex} tokens")
        print(f"  Without reflex mode: {total_without_reflex} tokens")
        print(f"  Reduction: {reduction_percent:.1f}%")
        
        # Should achieve at least 40% reduction (target is 50%)
        self.assertGreaterEqual(reduction_percent, TOKEN_REDUCTION_TARGET)
    
    def test_reflex_vs_analysis_prompt_size(self):
        """Test individual prompt sizes for reflex vs analysis"""
        reflex_prompt = self.reasoner._build_reflex_prompt(
            previous_action="clicked submit",
            visible_elements="[field: email]",
            language="fr"
        )
        
        analysis_prompt = self.reasoner._build_react_prompt(
            user_goal="Login to website",
            system_state={"active_app": "Chrome"},
            visual_context="[field: email]",
            memory={},
            language="fr"
        )
        
        reflex_words = len(reflex_prompt.split())
        analysis_words = len(analysis_prompt.split())
        
        print(f"\nPrompt word counts:")
        print(f"  Reflex: {reflex_words} words")
        print(f"  Analysis: {analysis_words} words")
        print(f"  Reflex is {(1 - reflex_words/analysis_words)*100:.1f}% smaller")
        
        # Reflex should be at least 60% smaller than analysis
        self.assertLess(reflex_words, analysis_words * REFLEX_WORD_COUNT_THRESHOLD)


if __name__ == "__main__":
    unittest.main()

