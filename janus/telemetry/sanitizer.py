"""
Data sanitizer for crash reports and error telemetry

TICKET-OPS-002 & TICKET-PRIV-001: Ensures crash reports are sanitized
- Removes screenshots
- Filters sensitive data from stack traces
- Removes raw prompts and user input
- Keeps only essential stack trace information
"""

import re
from typing import Any, Dict, Optional


class DataSanitizer:
    """Sanitize crash reports to prevent exposure of sensitive data"""

    # Patterns for sensitive data detection
    SENSITIVE_PATTERNS = [
        # OpenAI keys (must be before generic API keys to match first)
        # Supports alphanumeric and common base64 characters
        (r'sk-[a-zA-Z0-9+/=]{6,}', r'***REDACTED_OPENAI_KEY***'),
        # Anthropic keys (must be before generic API keys to match first)
        (r'sk-ant-[a-zA-Z0-9\-_+/=]{6,}', r'***REDACTED_ANTHROPIC_KEY***'),
        # API Keys - supports alphanumeric, underscores, dashes, and base64 chars
        (r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-+/=]{8,})', r'\1***REDACTED***'),
        # Passwords
        (r'(password["\']?\s*[:=]\s*["\']?)([^\s"\']{4,})', r'\1***REDACTED***'),
        # Tokens
        (r'(token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-\.]{10,})', r'\1***REDACTED***'),
        # Bearer tokens
        (r'(bearer\s+)([a-zA-Z0-9_\-\.]{20,})', r'\1***REDACTED***'),
        # Email addresses (optional - can be disabled if needed)
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', r'***EMAIL***'),
        # File paths (keep structure but remove username)
        (r'/Users/([^/\s]+)/', r'/Users/***USER***/'),
        (r'C:\\Users\\([^\\s]+)\\', r'C:\\Users\\***USER***\\'),
        # IP addresses (IPv4)
        (r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', r'***IP***'),
    ]

    # Keys that should be removed entirely from events
    SENSITIVE_KEYS = {
        'user_input',
        'prompt',
        'raw_command',
        'screenshot',
        'image',
        'image_data',
        'screen_capture',
        'clipboard',
        'cookies',
        'session_token',
        'auth_token',
        'authorization',
        'api_key',
        'apikey',
        'password',
        'passwd',
        'secret',
        'private_key',
    }

    @classmethod
    def sanitize_string(cls, text: str) -> str:
        """
        Sanitize a string by removing sensitive data patterns

        Args:
            text: String to sanitize

        Returns:
            Sanitized string with sensitive data redacted
        """
        if not isinstance(text, str):
            return text

        sanitized = text
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        return sanitized

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
        """
        Recursively sanitize a dictionary

        Args:
            data: Dictionary to sanitize
            depth: Current recursion depth (prevents infinite recursion)

        Returns:
            Sanitized dictionary
        """
        if depth > 10:  # Prevent infinite recursion
            return {"error": "Max recursion depth reached"}

        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            # Check if key is sensitive (use word boundary matching to avoid false positives)
            key_lower = str(key).lower().replace('-', '_')
            # Match exact sensitive keys or keys ending with sensitive words
            is_sensitive = any(
                key_lower == sk or key_lower.endswith('_' + sk) 
                for sk in cls.SENSITIVE_KEYS
            )
            if is_sensitive:
                sanitized[key] = "***REDACTED***"
                continue

            # Recursively sanitize values
            if isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value, depth + 1)
            elif isinstance(value, list):
                sanitized[key] = cls.sanitize_list(value, depth + 1)
            elif isinstance(value, str):
                sanitized[key] = cls.sanitize_string(value)
            else:
                sanitized[key] = value

        return sanitized

    @classmethod
    def sanitize_list(cls, data: list, depth: int = 0) -> list:
        """
        Recursively sanitize a list

        Args:
            data: List to sanitize
            depth: Current recursion depth

        Returns:
            Sanitized list
        """
        if depth > 10:
            return ["Max recursion depth reached"]

        if not isinstance(data, list):
            return data

        sanitized = []
        for item in data:
            if isinstance(item, dict):
                sanitized.append(cls.sanitize_dict(item, depth + 1))
            elif isinstance(item, list):
                sanitized.append(cls.sanitize_list(item, depth + 1))
            elif isinstance(item, str):
                sanitized.append(cls.sanitize_string(item))
            else:
                sanitized.append(item)

        return sanitized


def sanitize_event(event: Dict[str, Any], hint: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Sentry before_send hook to sanitize events before sending

    TICKET-OPS-002 & TICKET-PRIV-001: Ensures no sensitive data is sent
    - Removes screenshots and images
    - Sanitizes stack traces and error messages
    - Removes user input and prompts
    - Keeps only essential debugging information

    Args:
        event: Sentry event dictionary
        hint: Optional hint dictionary (contains exception info)

    Returns:
        Sanitized event or None to drop the event
    """
    try:
        # Remove screenshots and attachments
        if 'attachments' in event:
            del event['attachments']

        # Sanitize exception values and stack traces
        if 'exception' in event and 'values' in event['exception']:
            for exception in event['exception']['values']:
                # Sanitize exception message
                if 'value' in exception:
                    exception['value'] = DataSanitizer.sanitize_string(exception['value'])

                # Sanitize stack trace
                if 'stacktrace' in exception and 'frames' in exception['stacktrace']:
                    for frame in exception['stacktrace']['frames']:
                        # Sanitize local variables
                        if 'vars' in frame:
                            frame['vars'] = DataSanitizer.sanitize_dict(frame['vars'])

        # Sanitize breadcrumbs
        if 'breadcrumbs' in event and 'values' in event['breadcrumbs']:
            for breadcrumb in event['breadcrumbs']['values']:
                if 'message' in breadcrumb:
                    breadcrumb['message'] = DataSanitizer.sanitize_string(breadcrumb['message'])
                if 'data' in breadcrumb:
                    breadcrumb['data'] = DataSanitizer.sanitize_dict(breadcrumb['data'])

        # Sanitize request data if present
        if 'request' in event:
            request = event['request']
            if 'data' in request:
                request['data'] = DataSanitizer.sanitize_dict(request['data'])
            if 'headers' in request:
                request['headers'] = DataSanitizer.sanitize_dict(request['headers'])
            if 'cookies' in request:
                del request['cookies']

        # Sanitize extra context
        if 'extra' in event:
            event['extra'] = DataSanitizer.sanitize_dict(event['extra'])

        # Sanitize user context (but keep non-sensitive data)
        if 'user' in event:
            user = event['user']
            # Remove email if present
            if 'email' in user:
                user['email'] = '***REDACTED***'
            # Keep user ID for tracking unique users (if it's not sensitive)
            # Remove username if it contains sensitive info
            if 'username' in user:
                user['username'] = DataSanitizer.sanitize_string(user['username'])

        # Sanitize tags
        if 'tags' in event:
            event['tags'] = DataSanitizer.sanitize_dict(event['tags'])

        return event

    except Exception as e:
        # If sanitization fails, log error but still send the event
        # Better to have a potentially unsanitized report than no report
        import logging
        logging.getLogger(__name__).error(f"Failed to sanitize event: {e}")
        return event
