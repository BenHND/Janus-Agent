"""
Tests for TICKET-304: Automated QA Evaluation Pipeline

Tests the evals pipeline components:
- Dataset loading
- Semantic comparison functions
- Report generation
"""

import json
import sys
import unittest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestEvalsDataset(unittest.TestCase):
    """Test that the Golden Set dataset is valid"""
    
    def setUp(self):
        """Load the dataset"""
        self.dataset_path = project_root / "tests" / "evals" / "dataset_v1.json"
        self.assertTrue(self.dataset_path.exists(), f"Dataset not found at {self.dataset_path}")
        
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            self.dataset = json.load(f)
    
    def test_dataset_has_required_fields(self):
        """Dataset has version, description, and test_cases"""
        self.assertIn("version", self.dataset)
        self.assertIn("description", self.dataset)
        self.assertIn("test_cases", self.dataset)
    
    def test_dataset_has_50_test_cases(self):
        """Dataset has exactly 50 test cases per requirements"""
        test_cases = self.dataset.get("test_cases", [])
        self.assertEqual(len(test_cases), 50)
    
    def test_test_case_structure(self):
        """Each test case has required fields"""
        test_cases = self.dataset.get("test_cases", [])
        
        for tc in test_cases:
            self.assertIn("id", tc, f"Test case missing 'id': {tc}")
            self.assertIn("category", tc, f"Test case missing 'category': {tc.get('id', 'unknown')}")
            self.assertIn("language", tc, f"Test case missing 'language': {tc.get('id', 'unknown')}")
            self.assertIn("input", tc, f"Test case missing 'input': {tc.get('id', 'unknown')}")
            self.assertIn("expected_plan", tc, f"Test case missing 'expected_plan': {tc.get('id', 'unknown')}")
    
    def test_expected_plan_structure(self):
        """Each expected_plan has a steps array"""
        test_cases = self.dataset.get("test_cases", [])
        
        for tc in test_cases:
            expected_plan = tc.get("expected_plan", {})
            self.assertIn("steps", expected_plan, f"expected_plan missing 'steps': {tc.get('id', 'unknown')}")
            self.assertIsInstance(expected_plan["steps"], list, f"'steps' should be a list: {tc.get('id', 'unknown')}")
    
    def test_valid_categories(self):
        """All test cases have valid categories"""
        valid_categories = {"simple", "multi_step", "ambiguous", "contextual", "edge_case"}
        test_cases = self.dataset.get("test_cases", [])
        
        for tc in test_cases:
            category = tc.get("category")
            self.assertIn(category, valid_categories, f"Invalid category '{category}' in {tc.get('id', 'unknown')}")
    
    def test_valid_languages(self):
        """All test cases have valid language codes"""
        valid_languages = {"fr", "en"}
        test_cases = self.dataset.get("test_cases", [])
        
        for tc in test_cases:
            language = tc.get("language")
            self.assertIn(language, valid_languages, f"Invalid language '{language}' in {tc.get('id', 'unknown')}")
    
    def test_unique_ids(self):
        """All test case IDs are unique"""
        test_cases = self.dataset.get("test_cases", [])
        ids = [tc.get("id") for tc in test_cases]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate test case IDs found")


class TestSemanticComparison(unittest.TestCase):
    """Test semantic comparison functions"""
    
    def setUp(self):
        """Import comparison functions from run_evals"""
        # Import the functions we need to test
        sys.path.insert(0, str(project_root / "scripts"))
        from run_evals import (
            compare_args_semantic,
            compare_plan_semantic,
            compare_step_semantic,
            normalize_string,
            normalize_url,
        )
        self.normalize_url = normalize_url
        self.normalize_string = normalize_string
        self.compare_args_semantic = compare_args_semantic
        self.compare_step_semantic = compare_step_semantic
        self.compare_plan_semantic = compare_plan_semantic
    
    def test_normalize_url_basic(self):
        """Test URL normalization"""
        self.assertEqual(
            self.normalize_url("https://www.youtube.com/"),
            "https://youtube.com"
        )
        self.assertEqual(
            self.normalize_url("https://github.com"),
            "https://github.com"
        )
        # HTTP is preserved, www is stripped
        self.assertEqual(
            self.normalize_url("HTTP://WWW.GOOGLE.COM/"),
            "http://google.com"
        )
    
    def test_normalize_string(self):
        """Test string normalization"""
        self.assertEqual(self.normalize_string("  Chrome  "), "chrome")
        self.assertEqual(self.normalize_string("SAFARI"), "safari")
        self.assertIsNone(self.normalize_string(None))
    
    def test_compare_step_module_match(self):
        """Test step comparison with matching modules"""
        expected = {"module": "system", "action": "open_application", "args": {"app_name": "Chrome"}}
        actual = {"module": "system", "action": "open_application", "args": {"app_name": "Chrome"}}
        
        match, error = self.compare_step_semantic(expected, actual)
        self.assertTrue(match)
        self.assertIsNone(error)
    
    def test_compare_step_module_mismatch(self):
        """Test step comparison with mismatching modules"""
        expected = {"module": "system", "action": "open_application", "args": {}}
        actual = {"module": "browser", "action": "open_application", "args": {}}
        
        match, error = self.compare_step_semantic(expected, actual)
        self.assertFalse(match)
        self.assertIn("Module mismatch", error)
    
    def test_compare_step_action_alias(self):
        """Test step comparison with action aliases"""
        expected = {"module": "system", "action": "open_application", "args": {"app_name": "Chrome"}}
        actual = {"module": "system", "action": "launch", "args": {"app_name": "Chrome"}}
        
        # launch is an alias for open_application
        match, error = self.compare_step_semantic(expected, actual)
        self.assertTrue(match)
    
    def test_compare_plan_exact_match(self):
        """Test plan comparison with exact match"""
        expected = {
            "steps": [
                {"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}
            ]
        }
        actual = {
            "steps": [
                {"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}
            ]
        }
        
        match, error, details = self.compare_plan_semantic(expected, actual)
        self.assertTrue(match)
    
    def test_compare_plan_step_count_tolerance(self):
        """Test plan comparison allows ±1 step difference"""
        expected = {
            "steps": [
                {"module": "system", "action": "open_application", "args": {"app_name": "Safari"}}
            ]
        }
        actual = {
            "steps": [
                {"module": "system", "action": "open_application", "args": {"app_name": "Safari"}},
                {"module": "browser", "action": "refresh", "args": {}}
            ]
        }
        
        # Should match because difference is only 1 step
        match, error, details = self.compare_plan_semantic(expected, actual)
        self.assertTrue(match)
    
    def test_compare_plan_step_count_too_different(self):
        """Test plan comparison fails when step count differs by more than 1"""
        expected = {"steps": [{"module": "ui", "action": "copy", "args": {}}]}
        actual = {
            "steps": [
                {"module": "system", "action": "open_application", "args": {"app_name": "Chrome"}},
                {"module": "browser", "action": "open_url", "args": {}},
                {"module": "ui", "action": "copy", "args": {}},
            ]
        }
        
        match, error, details = self.compare_plan_semantic(expected, actual)
        self.assertFalse(match)
        self.assertIn("Step count mismatch", error)
    
    def test_compare_plan_empty_expected(self):
        """Test plan comparison with empty expected (edge cases)"""
        expected = {"steps": []}
        actual = {"steps": []}
        
        match, error, details = self.compare_plan_semantic(expected, actual)
        self.assertTrue(match)
        
        # Also allow single-step fallback for empty expected
        actual_with_one = {"steps": [{"module": "ui", "action": "click", "args": {}}]}
        match2, error2, details2 = self.compare_plan_semantic(expected, actual_with_one)
        self.assertTrue(match2)


class TestEvalsRunner(unittest.TestCase):
    """Test the evaluation runner"""
    
    def test_run_evals_with_mock(self):
        """Test that evals run successfully with mock backend"""
        sys.path.insert(0, str(project_root / "scripts"))
        from run_evals import run_evaluation
        
        report = run_evaluation(backend="mock", verbose=False)
        
        # Should complete
        self.assertEqual(report.total_tests, 50)
        
        # Should have some passes (mock handles common patterns)
        self.assertGreater(report.passed, 0)
        
        # Should have accuracy calculated
        self.assertGreater(report.accuracy_percent, 0)
    
    def test_report_has_category_breakdown(self):
        """Test that report includes category breakdown"""
        sys.path.insert(0, str(project_root / "scripts"))
        from run_evals import run_evaluation
        
        report = run_evaluation(backend="mock", verbose=False)
        
        # Should have results by category
        self.assertIn("simple", report.results_by_category)
        self.assertIn("multi_step", report.results_by_category)
        self.assertIn("ambiguous", report.results_by_category)
    
    def test_execution_time_under_2_minutes(self):
        """Test that evals complete in under 2 minutes"""
        import time
        
        sys.path.insert(0, str(project_root / "scripts"))
        from run_evals import run_evaluation
        
        start = time.time()
        run_evaluation(backend="mock", verbose=False)
        elapsed = time.time() - start
        
        # Should complete in under 2 minutes (requirement from TICKET-304)
        self.assertLess(elapsed, 120)
        
        # With mock, should be much faster (<5 seconds)
        self.assertLess(elapsed, 5)


if __name__ == "__main__":
    unittest.main()
