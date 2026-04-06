"""
Test for browser search planning functionality.
This tests that the DeterministicPlanner correctly handles search intents.
"""

import unittest
from janus.runtime.core.deterministic_planner import DeterministicPlanner, ActionStep
from janus.runtime.core.deterministic_nlu import DeterministicNLU, IntentValidationStatus
from janus.runtime.core.contracts import Intent
from janus.legacy.parser.unified_command_parser import UnifiedCommandParser, Intent as ParserIntent, ParserProvider


class TestSearchPlanning(unittest.TestCase):
    """Test browser search planning functionality"""
    
    def setUp(self):
        self.planner = DeterministicPlanner()
        self.nlu = DeterministicNLU()
    
    def test_planner_has_search_rule(self):
        """Verify that the planner has a 'search' rule registered"""
        self.assertIn("search", self.planner.planning_rules)
        self.assertIsNotNone(self.planner.planning_rules.get("search"))
    
    def test_planner_creates_search_plan(self):
        """Test that planner creates a valid search plan"""
        intent = Intent(
            action="search",
            confidence=0.9,
            raw_command="cherche Python tutoriels",
            parameters={"query": "Python tutoriels"}
        )
        
        plan = self.planner.create_plan(intent)
        
        # Verify plan is created
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.actions), 1)
        
        # Verify action details
        action = plan.actions[0]
        self.assertEqual(action["type"], "search")
        self.assertEqual(action["module"], "browser")
        self.assertEqual(action.get("query"), "Python tutoriels")
    
    def test_planner_search_uses_text_param_fallback(self):
        """Test that planner uses 'text' parameter if 'query' is not available"""
        intent = Intent(
            action="search",
            confidence=0.9,
            raw_command="cherche Daft Punk",
            parameters={"text": "Daft Punk"}
        )
        
        plan = self.planner.create_plan(intent)
        
        self.assertEqual(len(plan.actions), 1)
        action = plan.actions[0]
        self.assertEqual(action["type"], "search")
        self.assertEqual(action.get("query"), "Daft Punk")
    
    def test_nlu_validates_search_with_query(self):
        """Test NLU validates search intent with query parameter"""
        intent = Intent(
            action="search",
            confidence=0.9,
            raw_command="search Python",
            parameters={"query": "Python"}
        )
        
        validated = self.nlu._validate_intent(intent)
        self.assertEqual(validated.validation_status, IntentValidationStatus.VALID)
    
    def test_nlu_validates_search_with_text(self):
        """Test NLU validates search intent with text parameter"""
        intent = Intent(
            action="search",
            confidence=0.9,
            raw_command="cherche musique",
            parameters={"text": "musique"}
        )
        
        validated = self.nlu._validate_intent(intent)
        self.assertEqual(validated.validation_status, IntentValidationStatus.VALID)
    
    def test_nlu_invalidates_empty_search(self):
        """Test NLU invalidates search intent without query/text"""
        intent = Intent(
            action="search",
            confidence=0.9,
            raw_command="cherche",
            parameters={}
        )
        
        validated = self.nlu._validate_intent(intent)
        self.assertEqual(validated.validation_status, IntentValidationStatus.INVALID)
        # Check that the error message is clear
        self.assertIn("query", validated.ambiguity_reason.lower())
        self.assertIn("text", validated.ambiguity_reason.lower())

    def test_planner_returns_empty_for_missing_query(self):
        """Test that planner returns empty plan when query is missing"""
        intent = Intent(
            action="search",
            confidence=0.9,
            raw_command="search",
            parameters={}  # No query or text
        )
        
        # Get planning method directly to test
        steps = self.planner._plan_search(intent)
        self.assertEqual(len(steps), 0)


class TestUnifiedParserSearch(unittest.TestCase):
    """Test that UnifiedCommandParser correctly generates search actions"""
    
    def setUp(self):
        self.parser = UnifiedCommandParser(
            provider=ParserProvider.DETERMINISTIC,
            skip_llm_parsing=True
        )
    
    def test_generate_action_plan_search(self):
        """Test that action plan generation includes browser search"""
        from janus.legacy.parser.unified_command_parser import ParsedCommand
        
        command = ParsedCommand(
            intent=ParserIntent.SEARCH,
            parameters={"query": "Python tutorials"},
            confidence=0.9,
            raw_text="search Python tutorials",
            provider=ParserProvider.DETERMINISTIC
        )
        
        actions = self.parser.generate_action_plan([command])
        
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action["action"], "search")
        self.assertEqual(action["module"], "browser")
        self.assertEqual(action["query"], "Python tutorials")
    
    def test_generate_action_plan_search_with_text_param(self):
        """Test that action plan uses text parameter for search query"""
        from janus.legacy.parser.unified_command_parser import ParsedCommand
        
        command = ParsedCommand(
            intent=ParserIntent.SEARCH,
            parameters={"text": "Daft Punk"},
            confidence=0.9,
            raw_text="cherche Daft Punk",
            provider=ParserProvider.DETERMINISTIC
        )
        
        actions = self.parser.generate_action_plan([command])
        
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action["action"], "search")
        self.assertEqual(action["query"], "Daft Punk")


class TestSearchEstimatedDuration(unittest.TestCase):
    """Test that search has proper estimated duration"""
    
    def setUp(self):
        self.planner = DeterministicPlanner()
    
    def test_search_has_estimated_duration(self):
        """Test that search action has estimated duration"""
        self.assertIn("search", self.planner.estimated_durations)
        # Browser search should take longer than simple actions
        self.assertGreaterEqual(self.planner.estimated_durations["search"], 1000)


if __name__ == "__main__":
    unittest.main()
