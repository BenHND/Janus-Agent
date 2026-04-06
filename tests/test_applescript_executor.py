"""
Unit tests for AppleScript Executor
MAC-06: Test stabilization improvements
"""
import platform
import unittest

from janus.platform.os.macos.applescript_executor import (
    AppleScriptError,
    AppleScriptExecutor,
    execute_applescript,
    get_executor,
)


class TestAppleScriptExecutor(unittest.TestCase):
    """Test AppleScript executor functionality"""

    def setUp(self):
        """Set up test executor"""
        self.is_mac = platform.system() == "Darwin"
        if self.is_mac:
            self.executor = AppleScriptExecutor(
                default_timeout=5.0,
                max_retries=1,
                retry_delay=0.2,
                enable_logging=False,  # Disable for tests
            )

    @unittest.skipUnless(platform.system() == "Darwin", "macOS only")
    def test_simple_execution(self):
        """Test simple AppleScript execution"""
        script = 'return "Hello World"'
        result = self.executor.execute(script, timeout=3.0, retries=0)

        self.assertEqual(result["status"], "success")
        self.assertIn("Hello World", result["stdout"])
        self.assertIn("execution_time", result)
        self.assertIn("retry_count", result)
        self.assertEqual(result["retry_count"], 0)

    @unittest.skipUnless(platform.system() == "Darwin", "macOS only")
    def test_execution_with_timeout(self):
        """Test that timeout is enforced"""
        # Script that would hang forever without timeout
        script = "delay 60"
        result = self.executor.execute(script, timeout=1.0, retries=0)

        self.assertEqual(result["status"], "failed")
        self.assertTrue(result.get("timeout", False))
        self.assertIn("Timeout", result.get("error", ""))

    @unittest.skipUnless(platform.system() == "Darwin", "macOS only")
    def test_error_parsing(self):
        """Test error message parsing"""
        script = 'error "Test error message"'
        result = self.executor.execute(script, timeout=3.0, retries=0)

        self.assertEqual(result["status"], "failed")
        self.assertIn("error", result)
        self.assertIsNotNone(result["error"])

    @unittest.skipUnless(platform.system() == "Darwin", "macOS only")
    def test_retry_logic(self):
        """Test retry on failure"""
        # This will fail, but should retry
        script = 'error "Temporary error"'
        result = self.executor.execute(script, timeout=3.0, retries=2)

        self.assertEqual(result["status"], "failed")
        # Should have attempted retries
        self.assertGreater(result.get("retry_count", 0), 0)

    @unittest.skipUnless(platform.system() == "Darwin", "macOS only")
    def test_execution_time_tracking(self):
        """Test that execution time is tracked"""
        script = "delay 0.1"
        result = self.executor.execute(script, timeout=3.0, retries=0)

        self.assertIn("execution_time", result)
        self.assertGreater(result["execution_time"], 0.0)
        self.assertIn("total_time", result)

    @unittest.skipUnless(platform.system() == "Darwin", "macOS only")
    def test_execute_simple(self):
        """Test simple convenience method"""
        script = 'return "test"'
        success = self.executor.execute_simple(script)
        self.assertTrue(success)

        script = 'error "test error"'
        success = self.executor.execute_simple(script)
        self.assertFalse(success)

    @unittest.skipUnless(platform.system() == "Darwin", "macOS only")
    def test_execute_with_result(self):
        """Test result extraction convenience method"""
        script = 'return "output text"'
        result = self.executor.execute_with_result(script)
        self.assertIsNotNone(result)
        self.assertIn("output text", result)

        script = 'error "fail"'
        result = self.executor.execute_with_result(script)
        self.assertIsNone(result)

    @unittest.skipUnless(platform.system() == "Darwin", "macOS only")
    def test_application_error_detection(self):
        """Test application error detection"""
        self.assertTrue(AppleScriptExecutor.is_application_error("Application not running"))
        self.assertTrue(AppleScriptExecutor.is_application_error("Process not found"))
        self.assertFalse(AppleScriptExecutor.is_application_error("Syntax error"))

    @unittest.skipUnless(platform.system() == "Darwin", "macOS only")
    def test_global_executor(self):
        """Test global executor instance"""
        executor = get_executor()
        self.assertIsInstance(executor, AppleScriptExecutor)

        # Should return same instance
        executor2 = get_executor()
        self.assertIs(executor, executor2)

    @unittest.skipUnless(platform.system() == "Darwin", "macOS only")
    def test_convenience_function(self):
        """Test convenience function"""
        script = 'return "convenience"'
        result = execute_applescript(script)
        self.assertEqual(result["status"], "success")
        self.assertIn("convenience", result["stdout"])

    def test_non_mac_fallback(self):
        """Test that executor works on non-Mac (returns error)"""
        if not self.is_mac:
            executor = AppleScriptExecutor()
            result = executor.execute('return "test"')
            # Should fail gracefully on non-Mac
            self.assertEqual(result["status"], "failed")


if __name__ == "__main__":
    unittest.main()
