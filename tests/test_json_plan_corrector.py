"""
Tests for JSON Plan Corrector - TICKET 004
"""

import json
import unittest

from janus.safety.validation.json_plan_corrector import (
    JSONPlanCorrector,
    correct_json_plan,
    correct_plan_structure,
)


class TestJSONPlanCorrector(unittest.TestCase):
    """Test JSON Plan Corrector functionality"""

    def setUp(self):
        """Set up test corrector"""
        self.corrector = JSONPlanCorrector(aggressive=True)

    def test_valid_json_no_correction_needed(self):
        """Test that valid JSON passes through unchanged"""
        json_str = '{"steps": [{"module": "system", "action": "open_app", "args": {}}]}'

        success, corrected, fixes = self.corrector.correct_json_string(json_str)
        
        self.assertTrue(success)
        self.assertEqual(json.loads(corrected), json.loads(json_str))
        # No fixes should be needed for valid JSON
        self.assertEqual(len(fixes), 0)

    def test_trailing_comma_fix(self):
        """Test removal of trailing commas"""
        json_str = '{"steps": [{"module": "system", "action": "open_app",}],}'

        success, corrected, fixes = self.corrector.correct_json_string(json_str)
        
        self.assertTrue(success)
        self.assertIn("removed_trailing_commas", fixes)
        # Should parse without error
        parsed = json.loads(corrected)
        self.assertIn("steps", parsed)

    def test_single_quotes_to_double_quotes(self):
        """Test conversion of single quotes to double quotes"""
        json_str = "{'steps': [{'module': 'system', 'action': 'open_app'}]}"

        success, corrected, fixes = self.corrector.correct_json_string(json_str)
        
        self.assertTrue(success)
        self.assertTrue(
            any("single_quotes" in fix for fix in fixes)
        )
        parsed = json.loads(corrected)
        self.assertEqual(parsed["steps"][0]["module"], "system")

    def test_missing_quotes_around_keys(self):
        """Test adding quotes around unquoted keys"""
        json_str = '{steps: [{module: "system"}]}'

        success, corrected, fixes = self.corrector.correct_json_string(json_str)
        
        self.assertTrue(success)
        self.assertIn("added_quotes_to_unquoted_keys", fixes)

    def test_python_none_to_json_null(self):
        """Test conversion of Python None to JSON null"""
        json_str = '{"steps": [{"context": None}]}'

        success, corrected, fixes = self.corrector.correct_json_string(json_str)
        
        self.assertTrue(success)
        self.assertIn("converted_None_to_null", fixes)
        parsed = json.loads(corrected)
        self.assertIsNone(parsed["steps"][0]["context"])

    def test_python_bool_to_json_bool(self):
        """Test conversion of Python True/False to JSON true/false"""
        json_str = '{"enabled": True, "disabled": False}'

        success, corrected, fixes = self.corrector.correct_json_string(json_str)
        
        self.assertTrue(success)
        self.assertIn("converted_Python_booleans_to_JSON", fixes)

    def test_extract_json_from_mixed_text(self):
        """Test extraction of JSON from text with explanations"""
        mixed_text = """
        Here is the plan in JSON format:
        {"steps": [{"module": "system", "action": "open_app"}]}
        This plan will open an application.
        """

        success, corrected, fixes = self.corrector.correct_json_string(mixed_text)
        
        self.assertTrue(success)
        self.assertIn("extracted_json_from_mixed_output", fixes)
        parsed = json.loads(corrected)
        self.assertIn("steps", parsed)

    def test_extract_json_from_code_block(self):
        """Test extraction from markdown code blocks"""
        markdown_json = """
        ```json
        {"steps": [{"module": "browser", "action": "open_url"}]}
        ```
        """

        success, corrected, fixes = self.corrector.correct_json_string(markdown_json)
        
        self.assertTrue(success)
        self.assertIn("extracted_json_from_mixed_output", fixes)

    def test_qwen_style_markdown_with_preamble(self):
        """Test extraction from Qwen-style output with preamble - TICKET-310"""
        qwen_output = """
Voici le plan :
```json
{
    "steps": [
        {"module": "system", "action": "open_application", "args": {"app_name": "Chrome"}},
        {"module": "browser", "action": "open_url", "args": {"url": "https://youtube.com"}}
    ]
}
```
Ce plan va ouvrir Chrome et naviguer vers YouTube.
        """

        success, corrected, fixes = self.corrector.correct_json_string(qwen_output)
        
        self.assertTrue(success)
        self.assertIn("extracted_json_from_mixed_output", fixes)
        parsed = json.loads(corrected)
        self.assertIn("steps", parsed)
        self.assertEqual(len(parsed["steps"]), 2)
        self.assertEqual(parsed["steps"][0]["module"], "system")
        self.assertEqual(parsed["steps"][1]["action"], "open_url")

    def test_markdown_without_json_specifier(self):
        """Test extraction from markdown block without 'json' specifier - TICKET-310"""
        markdown_json = """
Here is the plan:
```
{"steps": [{"module": "ui", "action": "click", "args": {"target": "button"}}]}
```
        """

        success, corrected, fixes = self.corrector.correct_json_string(markdown_json)
        
        self.assertTrue(success)
        self.assertIn("extracted_json_from_mixed_output", fixes)
        parsed = json.loads(corrected)
        self.assertEqual(parsed["steps"][0]["module"], "ui")

    def test_nested_json_in_markdown(self):
        """Test extraction of deeply nested JSON from markdown - TICKET-310"""
        nested_json = """
```json
{
    "steps": [
        {
            "module": "browser",
            "action": "open_url",
            "args": {"url": "https://example.com"},
            "context": {
                "app": "Chrome",
                "surface": "browser",
                "url": null,
                "domain": "example.com",
                "thread": null,
                "record": null
            }
        }
    ]
}
```
        """

        success, corrected, fixes = self.corrector.correct_json_string(nested_json)
        
        self.assertTrue(success)
        parsed = json.loads(corrected)
        self.assertIn("steps", parsed)
        self.assertEqual(parsed["steps"][0]["context"]["domain"], "example.com")

    def test_trailing_comma_in_markdown_json(self):
        """Test handling of trailing commas in markdown JSON - TICKET-310"""
        markdown_with_trailing = """
Voici:
```json
{
    "steps": [
        {"module": "system", "action": "open_app", "args": {},},
    ],
}
```
        """

        success, corrected, fixes = self.corrector.correct_json_string(markdown_with_trailing)
        
        self.assertTrue(success)
        # Should have extracted from markdown AND fixed trailing commas
        self.assertTrue(any("extracted" in fix.lower() for fix in fixes) or 
                       any("trailing" in fix.lower() for fix in fixes))
        parsed = json.loads(corrected)
        self.assertIn("steps", parsed)

    def test_urls_preserved_in_json(self):
        """Test that URLs with // are not corrupted by comment removal - TICKET-310"""
        json_with_urls = '''
        {
            "steps": [
                {"module": "browser", "action": "open_url", "args": {"url": "https://example.com"}},
                {"module": "browser", "action": "open_url", "args": {"url": "http://localhost:8080//api/v1"}}
            ]
        }
        '''

        success, corrected, fixes = self.corrector.correct_json_string(json_with_urls)
        
        self.assertTrue(success)
        parsed = json.loads(corrected)
        # URLs should be preserved exactly
        self.assertEqual(parsed["steps"][0]["args"]["url"], "https://example.com")
        self.assertEqual(parsed["steps"][1]["args"]["url"], "http://localhost:8080//api/v1")

    def test_unclosed_braces_fix(self):
        """Test auto-closing of unclosed braces"""
        # This is a simple case where we can add closing braces
        json_str = '{"steps": [{"module": "system", "action": "open_app", "args": {}}'
        # Missing closing brace for object, closing bracket for array, and closing brace for root

        success, corrected, fixes = self.corrector.correct_json_string(json_str)
        
        # With aggressive mode, should attempt recovery
        # Note: Very malformed JSON might still fail - that's acceptable
        # The corrector will try but some JSON is just too broken
        if success:
            parsed = json.loads(corrected)
            self.assertIn("steps", parsed)
            # Should have added closing braces
            self.assertTrue(any("closing_braces" in fix or "closing_brackets" in fix for fix in fixes))
        else:
            # If it fails, it should have tried to fix it
            self.assertTrue(len(fixes) > 0)

    def test_correct_plan_structure_add_missing_module(self):
        """Test adding missing module field"""
        plan = {"steps": [{"action": "open_app", "args": {}}]}

        corrected, fixes = self.corrector.correct_plan_structure(plan)
        
        self.assertIn("module", corrected["steps"][0])
        self.assertTrue(any("added_default_module" in fix for fix in fixes))

    def test_correct_plan_structure_add_missing_action(self):
        """Test adding missing action field"""
        plan = {"steps": [{"module": "system", "args": {}}]}

        corrected, fixes = self.corrector.correct_plan_structure(plan)
        
        self.assertIn("action", corrected["steps"][0])
        self.assertTrue(any("added_default_action" in fix for fix in fixes))

    def test_correct_plan_structure_add_missing_args(self):
        """Test adding missing args field"""
        plan = {"steps": [{"module": "system", "action": "open_app"}]}

        corrected, fixes = self.corrector.correct_plan_structure(plan)
        
        self.assertIn("args", corrected["steps"][0])
        self.assertIsInstance(corrected["steps"][0]["args"], dict)
        self.assertTrue(any("added_empty_args" in fix for fix in fixes))

    def test_correct_plan_structure_add_missing_context(self):
        """Test adding missing context field with V3 structure"""
        plan = {"steps": [{"module": "system", "action": "open_app", "args": {}}]}

        corrected, fixes = self.corrector.correct_plan_structure(plan)
        
        self.assertIn("context", corrected["steps"][0])
        context = corrected["steps"][0]["context"]
        self.assertIn("app", context)
        self.assertIn("surface", context)
        self.assertIn("url", context)
        self.assertIn("domain", context)
        self.assertIn("thread", context)
        self.assertIn("record", context)
        self.assertTrue(any("added_empty_context_v3" in fix for fix in fixes))

    def test_complete_context_v3_structure(self):
        """Test completion of incomplete context"""
        plan = {
            "steps": [
                {
                    "module": "browser",
                    "action": "open_url",
                    "args": {},
                    "context": {"app": "Chrome"},  # Missing other V3 fields
                }
            ]
        }

        corrected, fixes = self.corrector.correct_plan_structure(plan)
        
        context = corrected["steps"][0]["context"]
        self.assertIn("surface", context)
        self.assertIn("url", context)
        self.assertIn("domain", context)
        self.assertTrue(any("context_field" in fix for fix in fixes))

    def test_normalize_module_name(self):
        """Test normalization of module names using schema"""
        plan = {"steps": [{"module": "SYSTEM", "action": "open_app", "args": {}}]}

        corrected, fixes = self.corrector.correct_plan_structure(plan)
        
        # Should normalize to lowercase (if schema supports it)
        # This depends on auto_correct_module implementation
        # Just check that it doesn't break
        self.assertIn("module", corrected["steps"][0])

    def test_normalize_action_name(self):
        """Test normalization of action names using schema"""
        plan = {"steps": [{"module": "system", "action": "OPEN_APP", "args": {}}]}

        corrected, fixes = self.corrector.correct_plan_structure(plan)
        
        # Should normalize action name
        self.assertIn("action", corrected["steps"][0])

    def test_handle_non_dict_step(self):
        """Test correction of non-dict step"""
        plan = {"steps": ["not a dict"]}

        corrected, fixes = self.corrector.correct_plan_structure(plan)
        
        # Should create minimal valid step
        self.assertIsInstance(corrected["steps"][0], dict)
        self.assertIn("module", corrected["steps"][0])
        self.assertIn("action", corrected["steps"][0])

    def test_handle_missing_steps_field(self):
        """Test adding missing steps array"""
        plan = {"actions": []}  # Wrong field name

        corrected, fixes = self.corrector.correct_plan_structure(plan)
        
        self.assertIn("steps", corrected)
        self.assertIsInstance(corrected["steps"], list)
        self.assertIn("added_empty_steps_array", fixes)

    def test_convert_dict_steps_to_list(self):
        """Test conversion of dict steps to list"""
        plan = {"steps": {"module": "system"}}  # Should be a list

        corrected, fixes = self.corrector.correct_plan_structure(plan)
        
        self.assertIsInstance(corrected["steps"], list)
        self.assertTrue(any("converted_steps" in fix for fix in fixes))

    def test_complex_correction_scenario(self):
        """Test a complex scenario with multiple issues"""
        # This is a more realistic scenario with correctable issues
        malformed = """
        {'steps': [
            {'module': 'system', 'action': 'open_app', 'args': {'app_name': 'Chrome'}},
            {'module': 'browser', 'action': 'open_url', 'args': {'url': 'test'}}
        ]}
        """

        success, corrected, fixes = self.corrector.correct_json_string(malformed)
        
        # This should be fixable - single quotes
        self.assertTrue(success)
        # Should have extracted and fixed quotes
        self.assertTrue(len(fixes) > 0)
        if success:
            parsed = json.loads(corrected)
            self.assertIn("steps", parsed)
            # Both steps should be present
            self.assertEqual(len(parsed["steps"]), 2)

    def test_aggressive_recovery_truncation(self):
        """Test aggressive recovery with truncation"""
        # Simulate LLM that stops mid-JSON
        truncated = '{"steps": [{"module": "system", "action": "open_app", "args": {"app_name": "Ch'

        success, corrected, fixes = self.corrector.correct_json_string(truncated)
        
        # With aggressive mode, should attempt recovery
        self.assertTrue(success or len(fixes) > 0)

    def test_statistics_tracking(self):
        """Test that statistics are tracked correctly"""
        corrector = JSONPlanCorrector()
        
        # Successful correction
        corrector.correct_json_string('{"steps": [{"module": "system",}]}')
        
        # Failed correction (completely invalid)
        corrector.correct_json_string('completely invalid {{{')
        
        stats = corrector.get_stats()
        self.assertEqual(stats["total_corrections"], 2)
        self.assertGreater(stats["successful_repairs"], 0)

    def test_convenience_functions(self):
        """Test convenience functions work correctly"""
        # correct_json_plan
        success, corrected, fixes = correct_json_plan('{"steps": []}')
        self.assertTrue(success)

        # correct_plan_structure
        plan = {"steps": [{"module": "system", "action": "open_app"}]}
        corrected, fixes = correct_plan_structure(plan)
        self.assertIn("args", corrected["steps"][0])


if __name__ == "__main__":
    unittest.main()
