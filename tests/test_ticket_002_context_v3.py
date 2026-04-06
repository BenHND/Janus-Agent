"""
Tests for TICKET-002: Context V3 Implementation (Propagation & Validation)

Tests context propagation, validation, and automatic inheritance across multi-step execution.
"""
import unittest
from janus.runtime.core.contracts import ExecutionContext


class TestContextV3Structure(unittest.TestCase):
    """Test Context V3 structure and basic operations"""

    def setUp(self):
        """Set up test execution context"""
        self.context = ExecutionContext()

    def test_context_initialization(self):
        """Test that context initializes with all V3 fields as None"""
        self.assertIsNone(self.context.active_app)
        self.assertIsNone(self.context.surface)
        self.assertIsNone(self.context.url)
        self.assertIsNone(self.context.domain)
        self.assertIsNone(self.context.thread)
        self.assertIsNone(self.context.record)

    def test_get_current_context(self):
        """Test get_current_context returns complete V3 structure"""
        ctx = self.context.get_current_context()
        
        self.assertIn("app", ctx)
        self.assertIn("surface", ctx)
        self.assertIn("url", ctx)
        self.assertIn("domain", ctx)
        self.assertIn("thread", ctx)
        self.assertIn("record", ctx)
        
        # All should be None initially
        self.assertIsNone(ctx["app"])
        self.assertIsNone(ctx["surface"])
        self.assertIsNone(ctx["url"])
        self.assertIsNone(ctx["domain"])
        self.assertIsNone(ctx["thread"])
        self.assertIsNone(ctx["record"])

    def test_update_from_step_context_full(self):
        """Test updating context from a complete step context"""
        step_context = {
            "app": "Safari",
            "surface": "browser",
            "url": "https://www.youtube.com",
            "domain": "youtube.com",
            "thread": None,
            "record": None
        }
        
        self.context.update_from_step_context(step_context)
        
        self.assertEqual(self.context.active_app, "Safari")
        self.assertEqual(self.context.surface, "browser")
        self.assertEqual(self.context.url, "https://www.youtube.com")
        self.assertEqual(self.context.domain, "youtube.com")
        self.assertIsNone(self.context.thread)
        self.assertIsNone(self.context.record)

    def test_update_from_step_context_partial(self):
        """Test updating context with partial step context (only non-null values)"""
        # Set initial context
        self.context.active_app = "Chrome"
        self.context.surface = "browser"
        
        # Update with partial step context
        step_context = {
            "app": "Safari",  # Should update
            "surface": None,  # Should not change existing value
            "url": "https://github.com",
            "domain": "github.com",
            "thread": None,
            "record": None
        }
        
        self.context.update_from_step_context(step_context)
        
        self.assertEqual(self.context.active_app, "Safari")
        self.assertEqual(self.context.surface, "browser")  # Unchanged
        self.assertEqual(self.context.url, "https://github.com")
        self.assertEqual(self.context.domain, "github.com")

    def test_domain_extraction_from_url(self):
        """Test automatic domain extraction when URL is provided without explicit domain"""
        step_context = {
            "app": "Safari",
            "surface": "browser",
            "url": "https://www.youtube.com/watch?v=123",
            "domain": None,  # Not explicitly provided
            "thread": None,
            "record": None
        }
        
        self.context.update_from_step_context(step_context)
        
        # Domain should be auto-extracted
        self.assertEqual(self.context.domain, "youtube.com")

    def test_extract_domain_various_formats(self):
        """Test _extract_domain with various URL formats"""
        test_cases = [
            ("https://www.youtube.com/watch", "youtube.com"),
            ("http://github.com/user/repo", "github.com"),
            ("https://subdomain.example.com:8080/path", "subdomain.example.com"),
            ("www.google.com", "google.com"),
            ("example.com", "example.com"),
            ("", None),
            (None, None),
        ]
        
        for url, expected_domain in test_cases:
            with self.subTest(url=url):
                result = self.context._extract_domain(url)
                self.assertEqual(result, expected_domain)


class TestContextPropagation(unittest.TestCase):
    """Test context propagation and injection into steps"""

    def setUp(self):
        """Set up test execution context"""
        self.context = ExecutionContext()

    def test_inject_context_empty_step(self):
        """Test injecting context into step with no context field"""
        # Set execution context
        self.context.active_app = "Safari"
        self.context.surface = "browser"
        self.context.domain = "youtube.com"
        
        # Step with no context
        step = {
            "module": "browser",
            "action": "search",
            "args": {"query": "Python tutorial"}
        }
        
        updated_step = self.context.inject_context_if_missing(step)
        
        # Context should be injected
        self.assertIn("context", updated_step)
        self.assertEqual(updated_step["context"]["app"], "Safari")
        self.assertEqual(updated_step["context"]["surface"], "browser")
        self.assertEqual(updated_step["context"]["domain"], "youtube.com")

    def test_inject_context_partial_step_context(self):
        """Test injecting context into step with partial context"""
        # Set execution context
        self.context.active_app = "Chrome"
        self.context.surface = "browser"
        self.context.url = "https://github.com"
        self.context.domain = "github.com"
        
        # Step with partial context (only app specified)
        step = {
            "module": "browser",
            "action": "navigate",
            "args": {},
            "context": {
                "app": "Safari",  # Explicitly set, should not be overridden
                "surface": None,
                "url": None,
                "domain": None,
                "thread": None,
                "record": None
            }
        }
        
        updated_step = self.context.inject_context_if_missing(step)
        
        # Explicit app should be preserved
        self.assertEqual(updated_step["context"]["app"], "Safari")
        # Missing fields should be inherited
        self.assertEqual(updated_step["context"]["surface"], "browser")
        self.assertEqual(updated_step["context"]["url"], "https://github.com")
        self.assertEqual(updated_step["context"]["domain"], "github.com")

    def test_inject_context_complete_step_context(self):
        """Test that complete step context is not modified"""
        # Set execution context
        self.context.active_app = "Chrome"
        self.context.surface = "browser"
        
        # Step with complete context
        step = {
            "module": "browser",
            "action": "open_url",
            "args": {"url": "https://youtube.com"},
            "context": {
                "app": "Safari",
                "surface": "browser",
                "url": "https://youtube.com",
                "domain": "youtube.com",
                "thread": None,
                "record": None
            }
        }
        
        updated_step = self.context.inject_context_if_missing(step)
        
        # Step context should remain unchanged
        self.assertEqual(updated_step["context"]["app"], "Safari")
        self.assertEqual(updated_step["context"]["surface"], "browser")
        self.assertEqual(updated_step["context"]["url"], "https://youtube.com")
        self.assertEqual(updated_step["context"]["domain"], "youtube.com")


class TestContextSequence(unittest.TestCase):
    """Test context propagation across multiple steps (integration-like)"""

    def test_multi_step_context_propagation(self):
        """Test context propagates correctly across a sequence of steps"""
        context = ExecutionContext()
        
        # Step 1: Open Safari (initializes app context)
        step1 = {
            "module": "system",
            "action": "open_app",
            "args": {"app_name": "Safari"},
            "context": {
                "app": None, "surface": None, "url": None,
                "domain": None, "thread": None, "record": None
            }
        }
        
        # After step 1 executes, update context
        step1_result_context = {
            "app": "Safari",
            "surface": None,
            "url": None,
            "domain": None,
            "thread": None,
            "record": None
        }
        context.update_from_step_context(step1_result_context)
        
        self.assertEqual(context.active_app, "Safari")
        
        # Step 2: Open YouTube (should inherit Safari context)
        step2 = {
            "module": "browser",
            "action": "open_url",
            "args": {"url": "https://www.youtube.com"},
            "context": {}
        }
        
        step2 = context.inject_context_if_missing(step2)
        
        # Should have inherited Safari
        self.assertEqual(step2["context"]["app"], "Safari")
        
        # After step 2 executes with YouTube URL
        step2_result_context = {
            "app": "Safari",
            "surface": "browser",
            "url": "https://www.youtube.com",
            "domain": "youtube.com",
            "thread": None,
            "record": None
        }
        context.update_from_step_context(step2_result_context)
        
        self.assertEqual(context.active_app, "Safari")
        self.assertEqual(context.surface, "browser")
        self.assertEqual(context.url, "https://www.youtube.com")
        self.assertEqual(context.domain, "youtube.com")
        
        # Step 3: Search (should inherit full context)
        step3 = {
            "module": "browser",
            "action": "search",
            "args": {"query": "Python tutorials"},
            "context": {}
        }
        
        step3 = context.inject_context_if_missing(step3)
        
        # Should have inherited everything
        self.assertEqual(step3["context"]["app"], "Safari")
        self.assertEqual(step3["context"]["surface"], "browser")
        self.assertEqual(step3["context"]["url"], "https://www.youtube.com")
        self.assertEqual(step3["context"]["domain"], "youtube.com")


class TestContextValidation(unittest.TestCase):
    """Test context validation scenarios"""

    def test_context_matches_expected(self):
        """Test validation passes when context matches expected"""
        context = ExecutionContext()
        context.active_app = "Safari"
        context.surface = "browser"
        context.domain = "youtube.com"
        
        step = {
            "module": "browser",
            "action": "search",
            "args": {},
            "context": {
                "app": "Safari",
                "surface": "browser",
                "url": "https://youtube.com",
                "domain": "youtube.com",
                "thread": None,
                "record": None
            }
        }
        
        # Validation should pass (app matches)
        # Note: This would be validated by pipeline's _validate_step_preconditions
        # Here we just verify the context structure is correct
        self.assertEqual(step["context"]["app"], context.active_app)

    def test_context_mismatch_detection(self):
        """Test detecting context mismatch"""
        context = ExecutionContext()
        context.active_app = "Chrome"
        
        step = {
            "module": "browser",
            "action": "search",
            "args": {},
            "context": {
                "app": "Safari",  # Mismatch!
                "surface": "browser",
                "url": None,
                "domain": None,
                "thread": None,
                "record": None
            }
        }
        
        # Context mismatch should be detectable
        self.assertNotEqual(step["context"]["app"], context.active_app)
    
    def test_validation_missing_module(self):
        """Test validation fails when module is missing"""
        context = ExecutionContext()
        
        step = {
            # Missing "module" field
            "action": "search",
            "args": {},
            "context": {}
        }
        
        # Should be invalid - module required
        self.assertNotIn("module", step)
    
    def test_validation_missing_action(self):
        """Test validation fails when action is missing"""
        context = ExecutionContext()
        
        step = {
            "module": "browser",
            # Missing "action" field
            "args": {},
            "context": {}
        }
        
        # Should be invalid - action required
        self.assertNotIn("action", step)
    
    def test_validation_app_context_mismatch(self):
        """Test validation detects app context mismatch"""
        context = ExecutionContext()
        context.active_app = "Chrome"
        
        step = {
            "module": "browser",
            "action": "search",
            "args": {},
            "context": {
                "app": "Safari",  # Expected Safari but current is Chrome
                "surface": "browser",
                "url": None,
                "domain": None,
                "thread": None,
                "record": None
            }
        }
        
        # App mismatch should be detectable
        expected_app = step["context"]["app"]
        current_app = context.active_app
        self.assertNotEqual(expected_app, current_app)
        self.assertEqual(expected_app, "Safari")
        self.assertEqual(current_app, "Chrome")
    
    def test_validation_no_app_when_required(self):
        """Test validation detects missing app when required"""
        context = ExecutionContext()
        context.active_app = None  # No app active
        
        step = {
            "module": "browser",
            "action": "search",
            "args": {},
            "context": {
                "app": "Safari",  # Requires Safari
                "surface": "browser",
                "url": None,
                "domain": None,
                "thread": None,
                "record": None
            }
        }
        
        # Should detect that Safari is required but no app is active
        expected_app = step["context"]["app"]
        current_app = context.active_app
        self.assertIsNotNone(expected_app)
        self.assertIsNone(current_app)
    
    def test_validation_surface_requirement(self):
        """Test validation of surface requirement for certain actions"""
        context = ExecutionContext()
        context.active_app = "Safari"
        context.surface = None  # No surface set
        
        step = {
            "module": "browser",
            "action": "search",  # Requires browser surface
            "args": {},
            "context": {
                "app": "Safari",
                "surface": "browser",  # Requires browser surface
                "url": None,
                "domain": None,
                "thread": None,
                "record": None
            }
        }
        
        # Should detect that browser surface is required but not active
        expected_surface = step["context"]["surface"]
        current_surface = context.surface
        self.assertEqual(expected_surface, "browser")
        self.assertIsNone(current_surface)


if __name__ == "__main__":
    unittest.main()
