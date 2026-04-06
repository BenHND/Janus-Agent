"""
Tests for crash reporting and telemetry

TICKET-OPS-002: Validates crash reporting functionality
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import configparser

from janus.telemetry.sanitizer import DataSanitizer, sanitize_event
from janus.telemetry.consent_manager import ConsentManager
from janus.telemetry.crash_reporter import CrashReporter


class TestDataSanitizer:
    """Test data sanitization for crash reports"""

    def test_sanitize_openai_api_key(self):
        """Test that OpenAI API keys are redacted"""
        text = "Using API key: sk-1234567890abcdef"
        result = DataSanitizer.sanitize_string(text)
        assert "sk-1234567890" not in result
        assert "***REDACTED_OPENAI_KEY***" in result

    def test_sanitize_anthropic_api_key(self):
        """Test that Anthropic API keys are redacted"""
        text = "API key: sk-ant-1234567890abcdef"
        result = DataSanitizer.sanitize_string(text)
        assert "sk-ant-1234567890" not in result
        assert "***REDACTED_ANTHROPIC_KEY***" in result

    def test_sanitize_generic_api_key(self):
        """Test that generic API keys are redacted"""
        text = 'api_key="my_secret_key_12345"'
        result = DataSanitizer.sanitize_string(text)
        assert "my_secret_key_12345" not in result
        assert "***REDACTED***" in result

    def test_sanitize_password(self):
        """Test that passwords are redacted"""
        text = 'password="mySecretPass123"'
        result = DataSanitizer.sanitize_string(text)
        assert "mySecretPass123" not in result
        assert "***REDACTED***" in result

    def test_sanitize_token(self):
        """Test that tokens are redacted"""
        text = 'token="bearer_token_1234567890"'
        result = DataSanitizer.sanitize_string(text)
        assert "bearer_token_1234567890" not in result
        assert "***REDACTED***" in result

    def test_sanitize_email(self):
        """Test that email addresses are redacted"""
        text = "User email: user@example.com"
        result = DataSanitizer.sanitize_string(text)
        assert "user@example.com" not in result
        assert "***EMAIL***" in result

    def test_sanitize_file_path_mac(self):
        """Test that macOS file paths with usernames are redacted"""
        text = "/Users/john_doe/Documents/secret.txt"
        result = DataSanitizer.sanitize_string(text)
        assert "john_doe" not in result
        assert "/Users/***USER***/" in result

    def test_sanitize_file_path_windows(self):
        """Test that Windows file paths with usernames are redacted"""
        text = "C:\\Users\\john_doe\\Documents\\secret.txt"
        result = DataSanitizer.sanitize_string(text)
        assert "john_doe" not in result
        assert "C:\\Users\\***USER***\\" in result

    def test_sanitize_ip_address(self):
        """Test that IP addresses are redacted"""
        text = "Server IP: 192.168.1.100"
        result = DataSanitizer.sanitize_string(text)
        assert "192.168.1.100" not in result
        assert "***IP***" in result

    def test_sanitize_dict_sensitive_keys(self):
        """Test that sensitive dictionary keys are redacted"""
        data = {
            "api_key": "secret123",
            "password": "pass456",
            "user_input": "confidential",
            "screenshot": "base64data",
            "safe_key": "safe_value",
            "error_message": "Connection failed"
        }
        result = DataSanitizer.sanitize_dict(data)
        
        # Sensitive keys should be redacted
        assert result["api_key"] == "***REDACTED***"
        assert result["password"] == "***REDACTED***"
        assert result["user_input"] == "***REDACTED***"
        assert result["screenshot"] == "***REDACTED***"
        
        # Safe keys should be preserved
        assert result["safe_key"] == "safe_value"
        assert result["error_message"] == "Connection failed"

    def test_sanitize_nested_dict(self):
        """Test sanitization of nested dictionaries"""
        data = {
            "level1": {
                "api_key": "secret",
                "level2": {
                    "password": "pass",
                    "safe": "value"
                }
            }
        }
        result = DataSanitizer.sanitize_dict(data)
        
        assert result["level1"]["api_key"] == "***REDACTED***"
        assert result["level1"]["level2"]["password"] == "***REDACTED***"
        assert result["level1"]["level2"]["safe"] == "value"

    def test_sanitize_list(self):
        """Test sanitization of lists"""
        data = [
            "safe string",
            "sk-1234567890",
            {"api_key": "secret"},
            ["nested", "sk-abcdef123456"]
        ]
        result = DataSanitizer.sanitize_list(data)
        
        assert result[0] == "safe string"
        assert "sk-1234567890" not in result[1]
        assert result[2]["api_key"] == "***REDACTED***"
        assert "sk-abcdef123456" not in result[3][1]

    def test_sanitize_event_removes_attachments(self):
        """Test that sanitize_event removes attachments"""
        event = {
            "attachments": ["screenshot.png", "data.json"],
            "message": "Test error"
        }
        result = sanitize_event(event)
        
        assert "attachments" not in result
        assert result["message"] == "Test error"

    def test_sanitize_event_exception_values(self):
        """Test that exception values are sanitized"""
        event = {
            "exception": {
                "values": [
                    {
                        "value": "Error with API key: sk-1234567890",
                        "stacktrace": {
                            "frames": [
                                {
                                    "vars": {
                                        "api_key": "secret123",
                                        "safe_var": "value"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        result = sanitize_event(event)
        
        # Exception value should be sanitized
        assert "sk-1234567890" not in result["exception"]["values"][0]["value"]
        
        # Stack trace vars should be sanitized
        frame_vars = result["exception"]["values"][0]["stacktrace"]["frames"][0]["vars"]
        assert frame_vars["api_key"] == "***REDACTED***"
        assert frame_vars["safe_var"] == "value"

    def test_sanitize_event_breadcrumbs(self):
        """Test that breadcrumbs are sanitized"""
        event = {
            "breadcrumbs": {
                "values": [
                    {
                        "message": "Using API key: sk-test123456",
                        "data": {
                            "password": "secret",
                            "status": "ok"
                        }
                    }
                ]
            }
        }
        result = sanitize_event(event)
        
        breadcrumb = result["breadcrumbs"]["values"][0]
        assert "sk-test123456" not in breadcrumb["message"]
        assert breadcrumb["data"]["password"] == "***REDACTED***"
        assert breadcrumb["data"]["status"] == "ok"

    def test_max_recursion_depth(self):
        """Test that sanitization handles deep recursion"""
        # Create deeply nested structure
        data = {"level": 0}
        current = data
        for i in range(15):
            current["nested"] = {"level": i + 1}
            current = current["nested"]
        
        result = DataSanitizer.sanitize_dict(data)
        # Should not crash and should handle gracefully
        assert result is not None


class TestConsentManager:
    """Test consent management functionality"""

    def test_no_consent_by_default(self):
        """Test that consent is not granted by default"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            config_path = f.name
        
        try:
            manager = ConsentManager(config_path)
            assert not manager.has_answered()
            assert not manager.get_consent()
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_set_consent_true(self):
        """Test setting consent to true"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            config_path = f.name
        
        try:
            manager = ConsentManager(config_path)
            assert manager.set_consent(True)
            assert manager.has_answered()
            assert manager.get_consent()
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_set_consent_false(self):
        """Test setting consent to false"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            config_path = f.name
        
        try:
            manager = ConsentManager(config_path)
            assert manager.set_consent(False)
            assert manager.has_answered()
            assert not manager.get_consent()
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_consent_persists(self):
        """Test that consent persists across instances"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            config_path = f.name
        
        try:
            # Set consent in first instance
            manager1 = ConsentManager(config_path)
            manager1.set_consent(True)
            
            # Check consent in second instance
            manager2 = ConsentManager(config_path)
            assert manager2.has_answered()
            assert manager2.get_consent()
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_revoke_consent(self):
        """Test revoking consent"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            config_path = f.name
        
        try:
            manager = ConsentManager(config_path)
            manager.set_consent(True)
            assert manager.get_consent()
            
            manager.revoke_consent()
            assert not manager.get_consent()
        finally:
            Path(config_path).unlink(missing_ok=True)


class TestCrashReporter:
    """Test crash reporter functionality"""

    def test_initialization_without_dsn(self):
        """Test that initialization fails gracefully without DSN"""
        reporter = CrashReporter(dsn=None)
        result = reporter.initialize()
        assert not result
        assert not reporter.initialized

    @patch('builtins.__import__')
    def test_initialization_with_dsn(self, mock_import):
        """Test successful initialization with DSN"""
        # Create mock sentry_sdk module
        mock_sentry = MagicMock()
        mock_sentry.init = Mock()
        mock_sentry.integrations = MagicMock()
        mock_sentry.integrations.logging = MagicMock()
        mock_sentry.integrations.logging.LoggingIntegration = MagicMock()
        
        def import_side_effect(name, *args, **kwargs):
            if name == 'sentry_sdk':
                return mock_sentry
            elif name == 'sentry_sdk.integrations.logging':
                return mock_sentry.integrations.logging
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = import_side_effect
        
        reporter = CrashReporter(dsn="https://test@sentry.io/123")
        result = reporter.initialize()
        
        assert result
        assert reporter.initialized
        assert mock_sentry.init.called

    @patch('builtins.__import__')
    def test_capture_exception(self, mock_import):
        """Test manual exception capture"""
        # Create mock sentry_sdk module
        mock_sentry = MagicMock()
        mock_sentry.init = Mock()
        mock_sentry.capture_exception = Mock()
        mock_sentry.push_scope = MagicMock()
        mock_sentry.integrations = MagicMock()
        mock_sentry.integrations.logging = MagicMock()
        mock_sentry.integrations.logging.LoggingIntegration = MagicMock()
        
        def import_side_effect(name, *args, **kwargs):
            if name == 'sentry_sdk':
                return mock_sentry
            elif name == 'sentry_sdk.integrations.logging':
                return mock_sentry.integrations.logging
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = import_side_effect
        
        reporter = CrashReporter(dsn="https://test@sentry.io/123")
        reporter.initialize()
        
        test_exception = ValueError("Test error")
        reporter.capture_exception(test_exception, module="test")
        
        # Verify exception was captured
        assert mock_sentry.capture_exception.called

    @patch('builtins.__import__')
    def test_capture_message(self, mock_import):
        """Test manual message capture"""
        # Create mock sentry_sdk module
        mock_sentry = MagicMock()
        mock_sentry.init = Mock()
        mock_sentry.capture_message = Mock()
        mock_sentry.push_scope = MagicMock()
        mock_sentry.integrations = MagicMock()
        mock_sentry.integrations.logging = MagicMock()
        mock_sentry.integrations.logging.LoggingIntegration = MagicMock()
        
        def import_side_effect(name, *args, **kwargs):
            if name == 'sentry_sdk':
                return mock_sentry
            elif name == 'sentry_sdk.integrations.logging':
                return mock_sentry.integrations.logging
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = import_side_effect
        
        reporter = CrashReporter(dsn="https://test@sentry.io/123")
        reporter.initialize()
        
        reporter.capture_message("Test message", level="error")
        
        # Verify message was captured
        assert mock_sentry.capture_message.called

    def test_capture_without_initialization(self):
        """Test that capture fails gracefully without initialization"""
        reporter = CrashReporter()
        
        # These should not crash
        reporter.capture_exception(ValueError("Test"))
        reporter.capture_message("Test message")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
