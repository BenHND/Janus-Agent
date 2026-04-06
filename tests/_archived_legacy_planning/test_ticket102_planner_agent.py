"""
TICKET 102 - Planner Agent Tests

Comprehensive test suite for the formal Planner Agent that encapsulates Reasoner V3.
Tests verify autonomy, JSON V3 compliance, context propagation, and correctness.
"""

import unittest
from typing import Dict, Any

from janus.capabilities.agents.planner_agent import PlannerAgent
from janus.runtime.core.module_action_schema import (
    validate_action_step,
    is_valid_module,
    is_valid_action,
)


class TestPlannerAgentAutonomy(unittest.TestCase):
    """Test that Planner Agent is fully autonomous"""
    
    def setUp(self):
        """Initialize Planner Agent with mock backend"""
        self.planner = PlannerAgent(backend="mock")
    
    def test_planner_initialization(self):
        """Test that Planner Agent initializes correctly"""
        self.assertIsNotNone(self.planner)
        self.assertTrue(self.planner.available)
        self.assertEqual(self.planner.backend_name, "mock")
    
    def test_planner_has_reasoner(self):
        """Test that Planner has ReasonerLLM internally"""
        self.assertIsNotNone(self.planner.reasoner)
        self.assertTrue(self.planner.reasoner.available)
    
    def test_planner_independent_interface(self):
        """Test that Planner provides clean interface"""
        # Should have plan() method
        self.assertTrue(hasattr(self.planner, 'plan'))
        self.assertTrue(callable(self.planner.plan))
        
        # Should have metrics
        self.assertTrue(hasattr(self.planner, 'get_metrics'))
        metrics = self.planner.get_metrics()
        self.assertIn('total_plans', metrics)
        self.assertIn('successful_plans', metrics)


class TestPlannerAgentJSONV3(unittest.TestCase):
    """Test that Planner generates strict JSON V3 format"""
    
    def setUp(self):
        """Initialize Planner Agent with mock backend"""
        self.planner = PlannerAgent(backend="mock", enable_validation=True)
    
    def test_plan_structure(self):
        """Test that plan has correct V3 structure"""
        plan = self.planner.plan("ouvre Chrome", language="fr")
        
        # Must have "steps" key
        self.assertIn("steps", plan)
        self.assertIsInstance(plan["steps"], list)
    
    def test_step_structure(self):
        """Test that each step has required V3 fields"""
        plan = self.planner.plan("ouvre Safari", language="fr")
        
        self.assertGreater(len(plan["steps"]), 0)
        
        for step in plan["steps"]:
            # Must have all required fields
            self.assertIn("module", step)
            self.assertIn("action", step)
            self.assertIn("args", step)
            self.assertIn("context", step)
            
            # Verify types
            self.assertIsInstance(step["module"], str)
            self.assertIsInstance(step["action"], str)
            self.assertIsInstance(step["args"], dict)
            self.assertIsInstance(step["context"], dict)
    
    def test_context_structure(self):
        """Test that context has all V3 fields"""
        plan = self.planner.plan("ouvre Chrome", language="fr")
        
        step = plan["steps"][0]
        context = step["context"]
        
        # Must have all context fields
        required_fields = ["app", "surface", "url", "domain", "thread", "record"]
        for field in required_fields:
            self.assertIn(field, context)


class TestPlannerAgentContextPropagation(unittest.TestCase):
    """Test automatic context propagation between steps"""
    
    def setUp(self):
        """Initialize Planner Agent with mock backend"""
        self.planner = PlannerAgent(backend="mock")
    
    def test_app_context_propagation(self):
        """Test that app context propagates from open_app"""
        plan = self.planner.plan(
            "ouvre Safari et va sur YouTube",
            language="fr"
        )
        
        self.assertEqual(len(plan["steps"]), 2)
        
        # Step 1: Open Safari - context.app should be null
        step1 = plan["steps"][0]
        self.assertEqual(step1["module"], "system")
        # Context app can be null for initial step
        
        # Step 2: Open URL - context.app should be "Safari"
        step2 = plan["steps"][1]
        self.assertEqual(step2["module"], "browser")
        self.assertEqual(step2["context"]["app"], "Safari")
    
    def test_domain_context_propagation(self):
        """Test that domain context propagates from open_url"""
        plan = self.planner.plan(
            "ouvre Safari et va sur YouTube et cherche Python",
            language="fr"
        )
        
        self.assertEqual(len(plan["steps"]), 3)
        
        # Step 2: Open URL - should set domain
        step2 = plan["steps"][1]
        self.assertIn("youtube", step2["context"]["domain"].lower())
        
        # Step 3: Search - should maintain domain
        step3 = plan["steps"][2]
        self.assertIn("youtube", step3["context"]["domain"].lower())
    
    def test_surface_context_propagation(self):
        """Test that surface context propagates correctly"""
        plan = self.planner.plan(
            "ouvre Chrome et va sur GitHub",
            language="fr"
        )
        
        self.assertEqual(len(plan["steps"]), 2)
        
        # Step 2: Open URL - surface should be "browser"
        step2 = plan["steps"][1]
        self.assertEqual(step2["context"]["surface"], "browser")


class TestPlannerAgentModuleActionMapping(unittest.TestCase):
    """Test that Planner uses correct module/action mappings"""
    
    def setUp(self):
        """Initialize Planner Agent with mock backend"""
        self.planner = PlannerAgent(backend="mock", enable_validation=True)
    
    def test_open_app_uses_system_module(self):
        """Test that opening apps uses system module"""
        plan = self.planner.plan("ouvre Safari", language="fr")
        
        step = plan["steps"][0]
        self.assertEqual(step["module"], "system")
        self.assertIn(step["action"], ["open_app", "open_application"])
    
    def test_open_url_uses_browser_module(self):
        """Test that opening URLs uses browser module"""
        plan = self.planner.plan("va sur YouTube", language="fr")
        
        step = plan["steps"][0]
        self.assertEqual(step["module"], "browser")
        self.assertEqual(step["action"], "open_url")
    
    def test_search_uses_browser_module(self):
        """Test that search uses browser module"""
        plan = self.planner.plan("cherche Python tutorials", language="fr")
        
        step = plan["steps"][0]
        self.assertEqual(step["module"], "browser")
        self.assertEqual(step["action"], "search")
    
    def test_all_steps_validated(self):
        """Test that all generated steps pass schema validation"""
        plan = self.planner.plan(
            "ouvre Safari et va sur YouTube et cherche Python",
            language="fr"
        )
        
        for i, step in enumerate(plan["steps"]):
            is_valid, error = validate_action_step(step)
            self.assertTrue(
                is_valid,
                f"Step {i+1} failed validation: {error}. Step: {step}"
            )


class TestPlannerAgentRequiredCommand(unittest.TestCase):
    """Test the required command from TICKET 102"""
    
    def setUp(self):
        """Initialize Planner Agent with mock backend"""
        self.planner = PlannerAgent(backend="mock", enable_validation=True)
    
    def test_safari_youtube_search_command(self):
        """
        Test: "ouvre safari et va sur youtube et cherche forgive burial"
        
        Must produce EXACTLY 3 steps with:
        - Step 1: module=system, action=open_app
        - Step 2: module=browser, action=open_url
        - Step 3: module=browser, action=search
        - Correct args
        - Context propagated
        """
        command = "ouvre safari et va sur youtube et cherche forgive burial"
        plan = self.planner.plan(command, language="fr")
        
        # Must have exactly 3 steps
        self.assertIsNotNone(plan)
        self.assertIn("steps", plan)
        self.assertEqual(
            len(plan["steps"]), 
            3,
            f"Expected 3 steps, got {len(plan['steps'])}"
        )
        
        # Step 1: Open Safari
        step1 = plan["steps"][0]
        self.assertEqual(step1["module"], "system")
        self.assertIn(step1["action"], ["open_app", "open_application"])
        self.assertIn("app_name", step1["args"])
        self.assertIn("safari", step1["args"]["app_name"].lower())
        
        # Validate step 1
        is_valid, error = validate_action_step(step1)
        self.assertTrue(is_valid, f"Step 1 validation failed: {error}")
        
        # Step 2: Open YouTube
        step2 = plan["steps"][1]
        self.assertEqual(step2["module"], "browser")
        self.assertEqual(step2["action"], "open_url")
        self.assertIn("url", step2["args"])
        self.assertIn("youtube", step2["args"]["url"].lower())
        
        # Context propagation: app should be Safari
        self.assertEqual(step2["context"]["app"], "Safari")
        self.assertEqual(step2["context"]["surface"], "browser")
        
        # Validate step 2
        is_valid, error = validate_action_step(step2)
        self.assertTrue(is_valid, f"Step 2 validation failed: {error}")
        
        # Step 3: Search
        step3 = plan["steps"][2]
        self.assertEqual(step3["module"], "browser")
        self.assertEqual(step3["action"], "search")
        self.assertIn("query", step3["args"])
        query = step3["args"]["query"].lower()
        self.assertIn("forgive", query)
        self.assertIn("burial", query)
        
        # Context propagation: maintain browser context
        self.assertEqual(step3["context"]["app"], "Safari")
        self.assertEqual(step3["context"]["surface"], "browser")
        self.assertIn("youtube", step3["context"]["domain"].lower())
        
        # Validate step 3
        is_valid, error = validate_action_step(step3)
        self.assertTrue(is_valid, f"Step 3 validation failed: {error}")
    
    def test_chrome_youtube_search_variant(self):
        """Test variant with Chrome instead of Safari"""
        command = "ouvre chrome et va sur youtube et cherche python"
        plan = self.planner.plan(command, language="fr")
        
        self.assertEqual(len(plan["steps"]), 3)
        
        # Step 1: Chrome
        step1 = plan["steps"][0]
        self.assertEqual(step1["module"], "system")
        self.assertIn("chrome", step1["args"]["app_name"].lower())
        
        # Step 2: Context should have Chrome
        step2 = plan["steps"][1]
        self.assertEqual(step2["context"]["app"], "Chrome")
        
        # Step 3: Context should maintain Chrome
        step3 = plan["steps"][2]
        self.assertEqual(step3["context"]["app"], "Chrome")


class TestPlannerAgentMetrics(unittest.TestCase):
    """Test Planner Agent metrics tracking"""
    
    def setUp(self):
        """Initialize Planner Agent with mock backend"""
        self.planner = PlannerAgent(backend="mock")
        self.planner.reset_metrics()
    
    def test_metrics_tracking(self):
        """Test that metrics are tracked correctly"""
        # Generate a plan
        self.planner.plan("ouvre Safari", language="fr")
        
        metrics = self.planner.get_metrics()
        
        self.assertEqual(metrics["total_plans"], 1)
        self.assertEqual(metrics["successful_plans"], 1)
        self.assertEqual(metrics["validation_failures"], 0)
    
    def test_multiple_plans_metrics(self):
        """Test metrics with multiple plans"""
        commands = [
            "ouvre Chrome",
            "va sur GitHub",
            "cherche Python"
        ]
        
        for cmd in commands:
            self.planner.plan(cmd, language="fr")
        
        metrics = self.planner.get_metrics()
        self.assertEqual(metrics["total_plans"], 3)
        self.assertEqual(metrics["successful_plans"], 3)
    
    def test_metrics_reset(self):
        """Test that metrics can be reset"""
        self.planner.plan("ouvre Safari", language="fr")
        
        metrics = self.planner.get_metrics()
        self.assertGreater(metrics["total_plans"], 0)
        
        # Reset
        self.planner.reset_metrics()
        
        metrics = self.planner.get_metrics()
        self.assertEqual(metrics["total_plans"], 0)
        self.assertEqual(metrics["successful_plans"], 0)


class TestPlannerAgentErrorHandling(unittest.TestCase):
    """Test Planner Agent error handling"""
    
    def setUp(self):
        """Initialize Planner Agent with mock backend"""
        self.planner = PlannerAgent(backend="mock", enable_fallback=True)
    
    def test_empty_text_raises_error(self):
        """Test that empty text raises ValueError"""
        with self.assertRaises(ValueError):
            self.planner.plan("", language="fr")
        
        with self.assertRaises(ValueError):
            self.planner.plan("   ", language="fr")
    
    def test_fallback_on_failure(self):
        """Test that fallback is used when enabled"""
        # Even with unusual input, should return a valid structure
        plan = self.planner.plan("xyz abc 123", language="fr")
        
        # Should have steps key (even if empty)
        self.assertIn("steps", plan)
        self.assertIsInstance(plan["steps"], list)


if __name__ == "__main__":
    unittest.main()
