"""
Tests for TICKET 003 - Module Action Schema

Tests for:
- Module and action definitions
- Schema validation
- Parameter validation
- Auto-correction
"""

import unittest

from janus.runtime.core.module_action_schema import (
    ALL_MODULES,
    ModuleName,
    auto_correct_action,
    auto_correct_module,
    get_all_actions_for_module,
    get_all_module_names,
    get_module,
    get_prompt_schema_section,
    get_schema_summary,
    is_valid_action,
    is_valid_module,
    validate_action_plan,
    validate_action_step,
)


class TestModuleSchema(unittest.TestCase):
    """Test module schema definitions"""
    
    def test_all_8_modules_defined(self):
        """Test that all 8 modules are defined"""
        self.assertEqual(len(ALL_MODULES), 8)
        
        expected_modules = [
            "system", "browser", "messaging", "crm",
            "files", "ui", "code", "llm"
        ]
        
        for module_name in expected_modules:
            self.assertIn(module_name, ALL_MODULES)
    
    def test_system_module_actions(self):
        """Test system module has all required actions"""
        system = get_module("system")
        self.assertIsNotNone(system)
        
        expected_actions = ["open_app", "close_app", "switch_app", "get_active_app"]
        action_names = system.get_action_names()
        
        for action in expected_actions:
            self.assertIn(action, action_names)
    
    def test_browser_module_actions(self):
        """Test browser module has all required actions"""
        browser = get_module("browser")
        self.assertIsNotNone(browser)
        
        expected_actions = [
            "open_url", "navigate_back", "navigate_forward",
            "refresh", "open_tab", "close_tab", "search", "extract_text"
        ]
        action_names = browser.get_action_names()
        
        for action in expected_actions:
            self.assertIn(action, action_names)
    
    def test_llm_module_actions(self):
        """Test LLM module has all required actions"""
        llm = get_module("llm")
        self.assertIsNotNone(llm)
        
        expected_actions = [
            "summarize", "rewrite", "extract_keywords",
            "analyze_error", "answer_question"
        ]
        action_names = llm.get_action_names()
        
        for action in expected_actions:
            self.assertIn(action, action_names)
    
    def test_action_has_parameters(self):
        """Test actions have parameter definitions"""
        browser = get_module("browser")
        open_url = browser.get_action("open_url")
        
        self.assertIsNotNone(open_url)
        self.assertGreater(len(open_url.parameters), 0)
        
        # Check url parameter
        url_param = open_url.parameters[0]
        self.assertEqual(url_param.name, "url")
        self.assertTrue(url_param.required)
        self.assertEqual(url_param.type, "string")
    
    def test_action_aliases(self):
        """Test action aliases work"""
        system = get_module("system")
        
        # Try getting action by alias
        action1 = system.get_action("open_app")
        action2 = system.get_action("open_application")
        action3 = system.get_action("launch")
        
        # All should resolve to the same action
        self.assertIsNotNone(action1)
        self.assertEqual(action1.name, "open_app")
        self.assertEqual(action2.name, "open_app")
        self.assertEqual(action3.name, "open_app")


class TestSchemaValidation(unittest.TestCase):
    """Test schema validation functions"""
    
    def test_is_valid_module(self):
        """Test module validation"""
        self.assertTrue(is_valid_module("system"))
        self.assertTrue(is_valid_module("browser"))
        self.assertTrue(is_valid_module("llm"))
        
        self.assertFalse(is_valid_module("invalid"))
        self.assertFalse(is_valid_module("chrome"))  # chrome is not a module
        self.assertFalse(is_valid_module(""))
    
    def test_is_valid_action(self):
        """Test action validation"""
        self.assertTrue(is_valid_action("system", "open_app"))
        self.assertTrue(is_valid_action("browser", "open_url"))
        self.assertTrue(is_valid_action("llm", "summarize"))
        
        self.assertFalse(is_valid_action("system", "invalid_action"))
        self.assertFalse(is_valid_action("browser", "delete_file"))  # wrong module
        self.assertFalse(is_valid_action("invalid_module", "open_app"))
    
    def test_validate_valid_step(self):
        """Test validating a valid step"""
        step = {
            "module": "system",
            "action": "open_app",
            "args": {"app_name": "Safari"}
        }
        
        is_valid, error = validate_action_step(step)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_validate_step_missing_module(self):
        """Test validation fails for missing module"""
        step = {
            "action": "open_app",
            "args": {"app_name": "Safari"}
        }
        
        is_valid, error = validate_action_step(step)
        self.assertFalse(is_valid)
        self.assertIn("module", error.lower())
    
    def test_validate_step_invalid_module(self):
        """Test validation fails for invalid module"""
        step = {
            "module": "invalid_module",
            "action": "open_app",
            "args": {}
        }
        
        is_valid, error = validate_action_step(step)
        self.assertFalse(is_valid)
        self.assertIn("invalid module", error.lower())
    
    def test_validate_step_invalid_action(self):
        """Test validation fails for invalid action"""
        step = {
            "module": "system",
            "action": "invalid_action",
            "args": {}
        }
        
        is_valid, error = validate_action_step(step)
        self.assertFalse(is_valid)
        self.assertIn("invalid action", error.lower())
    
    def test_validate_step_missing_required_param(self):
        """Test validation fails for missing required parameter"""
        step = {
            "module": "system",
            "action": "open_app",
            "args": {}  # Missing required app_name
        }
        
        is_valid, error = validate_action_step(step)
        self.assertFalse(is_valid)
        self.assertIn("required parameter", error.lower())
        self.assertIn("app_name", error.lower())
    
    def test_validate_step_with_optional_params(self):
        """Test validation succeeds with optional parameters"""
        step = {
            "module": "browser",
            "action": "open_tab",
            "args": {}  # url is optional
        }
        
        is_valid, error = validate_action_step(step)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_validate_plan_valid(self):
        """Test validating a valid plan"""
        plan = {
            "steps": [
                {"module": "system", "action": "open_app", "args": {"app_name": "Safari"}},
                {"module": "browser", "action": "open_url", "args": {"url": "https://youtube.com"}},
                {"module": "browser", "action": "search", "args": {"query": "Python"}}
            ]
        }
        
        is_valid, errors = validate_action_plan(plan)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_plan_with_invalid_step(self):
        """Test validating a plan with an invalid step"""
        plan = {
            "steps": [
                {"module": "system", "action": "open_app", "args": {"app_name": "Safari"}},
                {"module": "browser", "action": "invalid_action", "args": {}},  # Invalid
                {"module": "browser", "action": "search", "args": {"query": "Python"}}
            ]
        }
        
        is_valid, errors = validate_action_plan(plan)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        self.assertIn("Step 1", errors[0])  # Second step (index 1)
    
    def test_validate_plan_missing_steps(self):
        """Test validation fails for missing steps field"""
        plan = {}
        
        is_valid, errors = validate_action_plan(plan)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)


class TestAutoCorrection(unittest.TestCase):
    """Test auto-correction features"""
    
    def test_auto_correct_module_case(self):
        """Test auto-correcting module name case"""
        self.assertEqual(auto_correct_module("SYSTEM"), "system")
        self.assertEqual(auto_correct_module("Browser"), "browser")
        self.assertEqual(auto_correct_module("LLM"), "llm")
    
    def test_auto_correct_module_invalid(self):
        """Test auto-correction returns None for invalid modules"""
        self.assertIsNone(auto_correct_module("invalid_module"))
        self.assertIsNone(auto_correct_module("chrome"))
    
    def test_auto_correct_action_alias(self):
        """Test auto-correcting action using alias"""
        # open_application -> open_app
        self.assertEqual(auto_correct_action("system", "open_application"), "open_app")
        self.assertEqual(auto_correct_action("system", "launch"), "open_app")
        
        # navigate -> open_url
        self.assertEqual(auto_correct_action("browser", "navigate"), "open_url")
    
    def test_auto_correct_action_case(self):
        """Test auto-correcting action name case"""
        self.assertEqual(auto_correct_action("system", "OPEN_APP"), "open_app")
        self.assertEqual(auto_correct_action("browser", "Open_Url"), "open_url")
    
    def test_auto_correct_action_invalid(self):
        """Test auto-correction returns None for invalid actions"""
        self.assertIsNone(auto_correct_action("system", "invalid_action"))
        self.assertIsNone(auto_correct_action("browser", "delete_file"))


class TestSchemaUtilities(unittest.TestCase):
    """Test utility functions"""
    
    def test_get_all_module_names(self):
        """Test getting all module names"""
        names = get_all_module_names()
        
        self.assertEqual(len(names), 8)
        self.assertIn("system", names)
        self.assertIn("browser", names)
        self.assertIn("llm", names)
    
    def test_get_all_actions_for_module(self):
        """Test getting all actions for a module"""
        system_actions = get_all_actions_for_module("system")
        
        self.assertGreater(len(system_actions), 0)
        self.assertIn("open_app", system_actions)
        self.assertIn("close_app", system_actions)
    
    def test_get_schema_summary(self):
        """Test generating schema summary"""
        summary = get_schema_summary()
        
        self.assertIsInstance(summary, str)
        self.assertIn("system", summary.lower())
        self.assertIn("browser", summary.lower())
        self.assertIn("open_app", summary.lower())
        self.assertIn("open_url", summary.lower())
    
    def test_get_prompt_schema_section_french(self):
        """Test generating French prompt schema"""
        prompt = get_prompt_schema_section("fr")
        
        self.assertIsInstance(prompt, str)
        self.assertIn("MODULES DISPONIBLES", prompt)
        self.assertIn("system", prompt)
        self.assertIn("browser", prompt)
        self.assertIn("RÈGLES STRICTES", prompt)
    
    def test_get_prompt_schema_section_english(self):
        """Test generating English prompt schema"""
        prompt = get_prompt_schema_section("en")
        
        self.assertIsInstance(prompt, str)
        self.assertIn("AVAILABLE MODULES", prompt)
        self.assertIn("system", prompt)
        self.assertIn("browser", prompt)
        self.assertIn("STRICT RULES", prompt)


class TestParameterValidation(unittest.TestCase):
    """Test parameter validation"""
    
    def test_validate_string_parameter(self):
        """Test string parameter validation"""
        from janus.runtime.core.module_action_schema import ActionParameter
        
        param = ActionParameter("name", "string", True, "Name parameter")
        
        self.assertTrue(param.validate("valid string"))
        self.assertFalse(param.validate(123))
        self.assertFalse(param.validate([]))
    
    def test_validate_int_parameter(self):
        """Test int parameter validation"""
        from janus.runtime.core.module_action_schema import ActionParameter
        
        param = ActionParameter("count", "int", True, "Count parameter")
        
        self.assertTrue(param.validate(42))
        self.assertFalse(param.validate("42"))
        self.assertFalse(param.validate(3.14))
    
    def test_validate_bool_parameter(self):
        """Test bool parameter validation"""
        from janus.runtime.core.module_action_schema import ActionParameter
        
        param = ActionParameter("enabled", "bool", True, "Enable flag")
        
        self.assertTrue(param.validate(True))
        self.assertTrue(param.validate(False))
        self.assertFalse(param.validate("true"))
        self.assertFalse(param.validate(1))
    
    def test_validate_optional_parameter(self):
        """Test optional parameter validation"""
        from janus.runtime.core.module_action_schema import ActionParameter
        
        param = ActionParameter("optional", "string", False, "Optional parameter")
        
        self.assertTrue(param.validate(None))  # None is valid for optional
        self.assertTrue(param.validate("value"))
    
    def test_action_validate_params(self):
        """Test action parameter validation"""
        system = get_module("system")
        open_app = system.get_action("open_app")
        
        # Valid parameters
        is_valid, error = open_app.validate_params({"app_name": "Safari"})
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Missing required parameter
        is_valid, error = open_app.validate_params({})
        self.assertFalse(is_valid)
        self.assertIn("app_name", error)


if __name__ == "__main__":
    unittest.main()
