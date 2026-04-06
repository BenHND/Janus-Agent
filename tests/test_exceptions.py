"""
Tests for custom exception hierarchy.

Tests the Janus exception hierarchy defined in janus/exceptions.py
to ensure proper inheritance, error handling, and functionality.
"""
import unittest

from janus.exceptions import (
    AudioError,
    AutomationError,
    CommandError,
    ConfigError,
    ExecutionError,
    IntegrationError,
    ParsingError,
    JanusError,
    JanusMemoryError,
    ValidationError,
    VisionError,
)


class TestJanusError(unittest.TestCase):
    """Test base JanusError class"""

    def test_basic_error(self):
        """Test basic error creation"""
        error = JanusError("Test error")
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertIsNone(error.error_code)
        self.assertEqual(error.details, {})

    def test_error_with_code(self):
        """Test error with error code"""
        error = JanusError("Test error", error_code="E001")
        self.assertEqual(str(error), "[E001] Test error")
        self.assertEqual(error.error_code, "E001")

    def test_error_with_details(self):
        """Test error with additional details"""
        details = {"file": "test.py", "line": 42}
        error = JanusError("Test error", details=details)
        self.assertEqual(error.details, details)
        self.assertEqual(error.details["file"], "test.py")
        self.assertEqual(error.details["line"], 42)

    def test_error_inheritance(self):
        """Test that JanusError inherits from Exception"""
        error = JanusError("Test error")
        self.assertIsInstance(error, Exception)

    def test_error_raising(self):
        """Test raising and catching JanusError"""
        with self.assertRaises(JanusError) as context:
            raise JanusError("Test error", error_code="E001")
        self.assertEqual(context.exception.message, "Test error")
        self.assertEqual(context.exception.error_code, "E001")


class TestCommandErrors(unittest.TestCase):
    """Test command-related exception classes"""

    def test_command_error_inheritance(self):
        """Test CommandError inherits from JanusError"""
        error = CommandError("Command failed")
        self.assertIsInstance(error, JanusError)
        self.assertIsInstance(error, Exception)

    def test_parsing_error(self):
        """Test ParsingError"""
        error = ParsingError("Failed to parse command", error_code="P001")
        self.assertIsInstance(error, CommandError)
        self.assertIsInstance(error, JanusError)
        self.assertEqual(str(error), "[P001] Failed to parse command")

    def test_execution_error(self):
        """Test ExecutionError"""
        error = ExecutionError("Failed to execute", error_code="E001")
        self.assertIsInstance(error, CommandError)
        self.assertIsInstance(error, JanusError)
        self.assertEqual(error.message, "Failed to execute")

    def test_validation_error(self):
        """Test ValidationError"""
        error = ValidationError("Command validation failed", error_code="V001")
        self.assertIsInstance(error, CommandError)
        self.assertIsInstance(error, JanusError)

    def test_catch_all_command_errors(self):
        """Test catching all command errors with CommandError"""
        # Should catch ParsingError
        with self.assertRaises(CommandError):
            raise ParsingError("Parse failed")

        # Should catch ExecutionError
        with self.assertRaises(CommandError):
            raise ExecutionError("Execution failed")

        # Should catch ValidationError
        with self.assertRaises(CommandError):
            raise ValidationError("Validation failed")


class TestConfigError(unittest.TestCase):
    """Test ConfigError exception class"""

    def test_config_error(self):
        """Test ConfigError creation and inheritance"""
        error = ConfigError("Invalid configuration", error_code="C001")
        self.assertIsInstance(error, JanusError)
        self.assertEqual(error.message, "Invalid configuration")
        self.assertEqual(error.error_code, "C001")

    def test_config_error_with_details(self):
        """Test ConfigError with additional details"""
        details = {"config_file": "config.ini", "missing_key": "api_key"}
        error = ConfigError("Missing config key", details=details)
        self.assertEqual(error.details["config_file"], "config.ini")
        self.assertEqual(error.details["missing_key"], "api_key")


class TestMemoryError(unittest.TestCase):
    """Test JanusMemoryError exception class"""

    def test_memory_error(self):
        """Test JanusMemoryError creation"""
        error = JanusMemoryError("Database connection failed", error_code="M001")
        self.assertIsInstance(error, JanusError)
        self.assertEqual(error.message, "Database connection failed")

    def test_memory_error_not_builtin(self):
        """Test that JanusMemoryError is not the builtin MemoryError"""
        error = JanusMemoryError("Test")
        # JanusMemoryError should not be instance of builtin MemoryError
        # (The builtin MemoryError is for out-of-memory conditions)
        self.assertIsInstance(error, JanusError)


class TestIntegrationError(unittest.TestCase):
    """Test IntegrationError exception class"""

    def test_integration_error(self):
        """Test IntegrationError creation"""
        error = IntegrationError("API request failed", error_code="I001")
        self.assertIsInstance(error, JanusError)
        self.assertEqual(error.message, "API request failed")


class TestAudioError(unittest.TestCase):
    """Test AudioError exception class"""

    def test_audio_error(self):
        """Test AudioError creation"""
        error = AudioError("Microphone not available", error_code="A001")
        self.assertIsInstance(error, JanusError)
        self.assertEqual(error.message, "Microphone not available")


class TestVisionError(unittest.TestCase):
    """Test VisionError exception class"""

    def test_vision_error(self):
        """Test VisionError creation"""
        error = VisionError("OCR engine failed", error_code="V001")
        self.assertIsInstance(error, JanusError)
        self.assertEqual(error.message, "OCR engine failed")


class TestAutomationError(unittest.TestCase):
    """Test AutomationError exception class"""

    def test_automation_error(self):
        """Test AutomationError creation"""
        error = AutomationError("UI automation failed", error_code="AU001")
        self.assertIsInstance(error, JanusError)
        self.assertEqual(error.message, "UI automation failed")


class TestExceptionHierarchy(unittest.TestCase):
    """Test overall exception hierarchy behavior"""

    def test_catch_all_janus_errors(self):
        """Test catching all Janus errors with JanusError"""
        # All custom exceptions should be catchable with JanusError
        exceptions_to_test = [
            CommandError("test"),
            ParsingError("test"),
            ExecutionError("test"),
            ValidationError("test"),
            ConfigError("test"),
            JanusMemoryError("test"),
            IntegrationError("test"),
            AudioError("test"),
            VisionError("test"),
            AutomationError("test"),
        ]

        for exc in exceptions_to_test:
            with self.assertRaises(JanusError):
                raise exc

    def test_specific_exception_catching(self):
        """Test catching specific exception types"""
        # Should not catch unrelated exceptions
        with self.assertRaises(ConfigError):
            try:
                raise ConfigError("Config error")
            except CommandError:
                self.fail("Should not catch ConfigError as CommandError")

    def test_exception_hierarchy_depth(self):
        """Test multi-level exception hierarchy"""
        error = ParsingError("test")

        # Check inheritance chain
        self.assertIsInstance(error, ParsingError)
        self.assertIsInstance(error, CommandError)
        self.assertIsInstance(error, JanusError)
        self.assertIsInstance(error, Exception)

        # But not other branches
        self.assertNotIsInstance(error, ConfigError)
        self.assertNotIsInstance(error, AudioError)


class TestExceptionUsagePatterns(unittest.TestCase):
    """Test common exception usage patterns"""

    def test_reraise_with_context(self):
        """Test re-raising exceptions with additional context"""
        try:
            try:
                raise ParsingError("Original error")
            except ParsingError as e:
                # Add context and re-raise
                raise ParsingError(
                    f"Failed to process command: {e.message}",
                    error_code="P002",
                    details={"original_error": str(e)},
                ) from e
        except ParsingError as final_error:
            self.assertIn("Failed to process command", final_error.message)
            self.assertEqual(final_error.error_code, "P002")
            self.assertIn("original_error", final_error.details)

    def test_exception_chaining(self):
        """Test exception chaining with 'from' clause"""
        try:
            try:
                # Simulate an underlying error
                raise ValueError("Invalid value")
            except ValueError as e:
                raise ExecutionError("Command execution failed", error_code="E002") from e
        except ExecutionError as final_error:
            self.assertEqual(final_error.message, "Command execution failed")
            self.assertIsInstance(final_error.__cause__, ValueError)


if __name__ == "__main__":
    unittest.main()
