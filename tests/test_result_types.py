"""
Unit tests for standardized Result types (TICKET-CODE-02)

Tests the new Result[T], ParserResult, and AdapterResult classes
that standardize return values across the codebase.
"""
import unittest
from datetime import datetime

from janus.runtime.core.contracts import AdapterResult, ErrorType, Intent, ParserResult, Result


class TestGenericResult(unittest.TestCase):
    """Test cases for Result[T] generic wrapper"""

    def test_ok_result(self):
        """Test successful result creation"""
        result = Result.ok("test_value", message="Success")

        self.assertTrue(result.is_ok())
        self.assertFalse(result.is_err())
        self.assertEqual(result.value, "test_value")
        self.assertEqual(result.message, "Success")
        self.assertIsNone(result.error)

    def test_err_result(self):
        """Test error result creation"""
        result = Result.err("Something failed", error_type=ErrorType.SYSTEM_ERROR)

        self.assertFalse(result.is_ok())
        self.assertTrue(result.is_err())
        self.assertEqual(result.error, "Something failed")
        self.assertEqual(result.error_type, ErrorType.SYSTEM_ERROR)
        self.assertIsNone(result.value)

    def test_unwrap_success(self):
        """Test unwrap on successful result"""
        result = Result.ok(42)
        value = result.unwrap()
        self.assertEqual(value, 42)

    def test_unwrap_failure_raises(self):
        """Test unwrap on failed result raises ValueError"""
        result = Result.err("Failed")
        with self.assertRaises(ValueError):
            result.unwrap()

    def test_unwrap_or(self):
        """Test unwrap_or with default value"""
        success_result = Result.ok(42)
        fail_result = Result.err("Failed")

        self.assertEqual(success_result.unwrap_or(0), 42)
        self.assertEqual(fail_result.unwrap_or(0), 0)

    def test_to_dict_success(self):
        """Test to_dict serialization for success"""
        result = Result.ok("data", message="OK", metadata={"key": "value"})
        result_dict = result.to_dict()

        self.assertTrue(result_dict["success"])
        self.assertEqual(result_dict["value"], "data")
        self.assertEqual(result_dict["message"], "OK")
        self.assertEqual(result_dict["metadata"], {"key": "value"})
        self.assertNotIn("error", result_dict)

    def test_to_dict_failure(self):
        """Test to_dict serialization for failure"""
        result = Result.err("error msg", error_type=ErrorType.PARSE_ERROR)
        result_dict = result.to_dict()

        self.assertFalse(result_dict["success"])
        self.assertEqual(result_dict["error"], "error msg")
        self.assertEqual(result_dict["error_type"], "parse_error")
        self.assertNotIn("value", result_dict)

    def test_timestamp_auto_set(self):
        """Test timestamp is automatically set"""
        result = Result.ok("test")
        self.assertIsNotNone(result.timestamp)
        self.assertIsInstance(result.timestamp, datetime)


class TestParserResult(unittest.TestCase):
    """Test cases for ParserResult"""

    def test_from_intent_success(self):
        """Test creating ParserResult from single intent"""
        intent = Intent(action="open_app", confidence=0.9, parameters={"app": "Chrome"})
        result = ParserResult.from_intent(intent, raw_command="open chrome")

        self.assertTrue(result.ok())
        self.assertTrue(result.is_success)
        self.assertFalse(result.is_ambiguous)
        self.assertEqual(len(result.intents), 1)
        self.assertEqual(result.get_intent().action, "open_app")
        self.assertEqual(result.raw_command, "open chrome")

    def test_from_intents_multiple(self):
        """Test creating ParserResult from multiple intents"""
        intent1 = Intent(action="open_app", confidence=0.8)
        intent2 = Intent(action="click", confidence=0.7)
        result = ParserResult.from_intents([intent1, intent2])

        self.assertTrue(result.ok())
        self.assertEqual(len(result.get_intents()), 2)
        self.assertEqual(result.get_intent().action, "open_app")

    def test_from_error(self):
        """Test creating failed ParserResult"""
        result = ParserResult.from_error(
            "Unknown command", error_type=ErrorType.UNKNOWN_COMMAND, raw_command="xyz"
        )

        self.assertFalse(result.ok())
        self.assertFalse(result.is_success)
        self.assertEqual(result.error, "Unknown command")
        self.assertEqual(result.error_type, ErrorType.UNKNOWN_COMMAND)
        self.assertEqual(result.raw_command, "xyz")
        self.assertEqual(len(result.intents), 0)

    def test_from_ambiguous(self):
        """Test creating ambiguous ParserResult"""
        intent1 = Intent(action="open_app", confidence=0.5)
        intent2 = Intent(action="launch_app", confidence=0.5)
        result = ParserResult.from_ambiguous(
            [intent1, intent2], reason="Multiple interpretations possible"
        )

        self.assertFalse(result.ok())  # Ambiguous is not "ok"
        self.assertTrue(result.is_success)  # But is technically successful
        self.assertTrue(result.is_ambiguous)
        self.assertEqual(result.ambiguity_reason, "Multiple interpretations possible")
        self.assertEqual(len(result.intents), 2)

    def test_to_dict(self):
        """Test ParserResult serialization"""
        intent = Intent(action="open_app", confidence=0.9)
        result = ParserResult.from_intent(intent)
        result_dict = result.to_dict()

        self.assertIn("success", result_dict)
        self.assertIn("intents", result_dict)
        self.assertEqual(len(result_dict["intents"]), 1)
        self.assertEqual(result_dict["intents"][0]["action"], "open_app")

    def test_confidence_override(self):
        """Test confidence can be overridden"""
        intent = Intent(action="test", confidence=0.5)
        result = ParserResult.from_intent(intent, confidence=0.9)

        self.assertEqual(result.get_intent().confidence, 0.9)


class TestAdapterResult(unittest.TestCase):
    """Test cases for AdapterResult"""

    def test_from_success(self):
        """Test creating successful AdapterResult"""
        result = AdapterResult.from_success(
            "open_url",
            message="Opened successfully",
            data={"url": "https://github.com"},
            duration_ms=150,
        )

        self.assertTrue(result.ok())
        self.assertTrue(result.is_success)
        self.assertEqual(result.action, "open_url")
        self.assertEqual(result.message, "Opened successfully")
        self.assertEqual(result.data, {"url": "https://github.com"})
        self.assertEqual(result.duration_ms, 150)
        self.assertIsNone(result.error)

    def test_from_success_default_message(self):
        """Test default message is generated"""
        result = AdapterResult.from_success("click")
        self.assertIn("click", result.message)
        self.assertIn("successfully", result.message)

    def test_from_failure(self):
        """Test creating failed AdapterResult"""
        result = AdapterResult.from_failure(
            "click",
            "Element not found",
            error_type=ErrorType.EXECUTION_ERROR,
            retryable=True,
            retry_count=2,
        )

        self.assertFalse(result.ok())
        self.assertFalse(result.is_success)
        self.assertEqual(result.action, "click")
        self.assertEqual(result.error, "Element not found")
        self.assertEqual(result.error_type, ErrorType.EXECUTION_ERROR)
        self.assertTrue(result.is_retryable)
        self.assertEqual(result.retry_count, 2)

    def test_to_dict_backward_compat(self):
        """Test to_dict produces backward compatible format"""
        result = AdapterResult.from_success("open_url", data={"url": "test.com"}, duration_ms=100)
        result_dict = result.to_dict()

        # Check backward compatibility keys
        self.assertEqual(result_dict["status"], "success")
        self.assertEqual(result_dict["action"], "open_url")
        self.assertIn("message", result_dict)
        self.assertIn("timestamp", result_dict)
        self.assertEqual(result_dict["data"], {"url": "test.com"})
        self.assertEqual(result_dict["duration_ms"], 100)
        self.assertEqual(result_dict["execution_time"], 0.1)  # Legacy field

    def test_from_dict_legacy(self):
        """Test creating AdapterResult from legacy dict format"""
        legacy_dict = {
            "status": "success",
            "action": "click",
            "message": "Clicked button",
            "data": {"x": 100, "y": 200},
            "duration_ms": 50,
            "retry_count": 1,
        }

        result = AdapterResult.from_dict(legacy_dict)

        self.assertTrue(result.ok())
        self.assertEqual(result.action, "click")
        self.assertEqual(result.message, "Clicked button")
        self.assertEqual(result.data, {"x": 100, "y": 200})
        self.assertEqual(result.duration_ms, 50)
        self.assertEqual(result.retry_count, 1)

    def test_from_dict_failed(self):
        """Test creating failed AdapterResult from legacy dict"""
        legacy_dict = {
            "status": "failed",
            "action": "open_file",
            "error": "File not found",
            "error_type": "execution_error",
            "retryable": False,
        }

        result = AdapterResult.from_dict(legacy_dict)

        self.assertFalse(result.ok())
        self.assertEqual(result.error, "File not found")
        self.assertEqual(result.error_type, ErrorType.EXECUTION_ERROR)
        self.assertFalse(result.is_retryable)

    def test_timestamp_auto_set(self):
        """Test timestamp is automatically set"""
        result = AdapterResult.from_success("test")
        self.assertIsNotNone(result.timestamp)
        self.assertIsInstance(result.timestamp, datetime)


class TestResultTypeIntegration(unittest.TestCase):
    """Integration tests for Result types"""

    def test_parser_to_adapter_flow(self):
        """Test passing parser result to adapter"""
        # Parse command
        intent = Intent(action="open_url", confidence=0.9, parameters={"url": "github.com"})
        parser_result = ParserResult.from_intent(intent)

        # Verify parsing succeeded
        self.assertTrue(parser_result.ok())

        # Simulate adapter execution
        if parser_result.ok():
            intent = parser_result.get_intent()
            adapter_result = AdapterResult.from_success(intent.action, data=intent.parameters)

            self.assertTrue(adapter_result.ok())
            self.assertEqual(adapter_result.action, "open_url")

    def test_error_propagation(self):
        """Test error propagation through Result types"""
        # Parser fails
        parser_result = ParserResult.from_error("Invalid syntax", error_type=ErrorType.PARSE_ERROR)

        self.assertFalse(parser_result.ok())
        self.assertEqual(parser_result.error_type, ErrorType.PARSE_ERROR)

        # Could wrap in generic Result for uniform handling
        generic_result = Result.err(parser_result.error, error_type=parser_result.error_type)

        self.assertTrue(generic_result.is_err())
        self.assertEqual(generic_result.error_type, ErrorType.PARSE_ERROR)


if __name__ == "__main__":
    unittest.main()
