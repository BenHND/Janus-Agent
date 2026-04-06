"""
Secrets filtering utility for Janus
Prevents sensitive data from appearing in logs and error messages
"""

import re
from typing import Any, Dict, List, Optional, Union


class SecretsFilter:
    """
    Filter sensitive data from strings, logs, and error messages

    This class provides pattern-based filtering to redact API keys,
    tokens, passwords, and other sensitive information from text.
    """

    # Patterns for detecting sensitive data
    SENSITIVE_PATTERNS = {
        "api_key": re.compile(
            r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-]{8,})(["\']?)', re.IGNORECASE
        ),
        "bearer_token": re.compile(r"(bearer\s+)([a-zA-Z0-9_\-\.]{20,})", re.IGNORECASE),
        "password": re.compile(
            r'(password["\']?\s*[:=]\s*["\']?)([^\s"\']{4,})(["\']?)', re.IGNORECASE
        ),
        "secret": re.compile(
            r'(secret["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-]{8,})(["\']?)', re.IGNORECASE
        ),
        "token": re.compile(
            r'(token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-\.]{10,})(["\']?)', re.IGNORECASE
        ),
        "auth": re.compile(
            r'(authorization["\']?\s*[:=]\s*["\']?)([^\s"\']{10,})(["\']?)', re.IGNORECASE
        ),
        # OpenAI API key pattern (sk-...)
        "openai_key": re.compile(r"(sk-[a-zA-Z0-9]{10,})"),
        # Anthropic API key pattern (sk-ant-...)
        "anthropic_key": re.compile(r"(sk-ant-[a-zA-Z0-9\-_]{10,})"),
        # Generic base64 encoded secrets
        "base64_secret": re.compile(r'(["\']?)([A-Za-z0-9+/]{40,}={0,2})(["\']?)'),
        # AWS keys
        "aws_access_key": re.compile(r"(AKIA[0-9A-Z]{16})"),
        "aws_secret_key": re.compile(r'(["\']?)([A-Za-z0-9/+=]{40})(["\']?)'),
    }

    # Keywords that indicate sensitive fields
    SENSITIVE_KEYWORDS = {
        "api_key",
        "apikey",
        "api-key",
        "password",
        "passwd",
        "pwd",
        "secret",
        "secret_key",
        "secret-key",
        "token",
        "auth_token",
        "auth-token",
        "bearer",
        "authorization",
        "private_key",
        "private-key",
        "client_secret",
        "client-secret",
        "access_token",
        "access-token",
        "refresh_token",
        "refresh-token",
        "openai_api_key",
        "anthropic_api_key",
        "mistral_api_key",
    }

    # Minimum length for a value to be considered potentially sensitive
    MIN_SENSITIVE_LENGTH = 8

    # Replacement text for redacted secrets
    REDACTED_TEXT = "***REDACTED***"

    def __init__(
        self,
        additional_patterns: Optional[Dict[str, re.Pattern]] = None,
        additional_keywords: Optional[List[str]] = None,
    ):
        """
        Initialize secrets filter

        Args:
            additional_patterns: Additional regex patterns to detect sensitive data
            additional_keywords: Additional keywords to identify sensitive fields
        """
        self.patterns = self.SENSITIVE_PATTERNS.copy()
        if additional_patterns:
            self.patterns.update(additional_patterns)

        self.keywords = self.SENSITIVE_KEYWORDS.copy()
        if additional_keywords:
            self.keywords.update(set(k.lower() for k in additional_keywords))

    def filter_string(self, text: str) -> str:
        """
        Filter sensitive data from a string

        Args:
            text: Input text that may contain sensitive data

        Returns:
            Filtered text with sensitive data redacted
        """
        if not text or not isinstance(text, str):
            return text

        filtered_text = text

        # Apply all patterns
        for pattern_name, pattern in self.patterns.items():
            if pattern_name in ["api_key", "password", "secret", "token", "auth"]:
                # For patterns with 3 groups, preserve the key name but redact value
                def replace_with_groups(match):
                    groups = match.groups()
                    if len(groups) >= 3:
                        return groups[0] + self.REDACTED_TEXT + groups[2]
                    else:
                        return self.REDACTED_TEXT

                filtered_text = pattern.sub(replace_with_groups, filtered_text)
            elif pattern_name == "bearer_token":
                # Bearer token pattern has 2 groups
                def replace_bearer(match):
                    groups = match.groups()
                    if len(groups) >= 2:
                        return groups[0] + self.REDACTED_TEXT
                    else:
                        return self.REDACTED_TEXT

                filtered_text = pattern.sub(replace_bearer, filtered_text)
            elif pattern_name in ["openai_key", "anthropic_key", "aws_access_key"]:
                # For simple patterns, replace entire match
                filtered_text = pattern.sub(self.REDACTED_TEXT, filtered_text)
            elif pattern_name == "base64_secret":
                # Only redact if it looks like a secret (not just any base64)
                # Check if it's in a suspicious context
                def replace_if_suspicious(match):
                    before = filtered_text[max(0, match.start() - 20) : match.start()].lower()
                    if any(kw in before for kw in ["key", "secret", "token", "auth", "password"]):
                        groups = match.groups()
                        if len(groups) >= 3:
                            return groups[0] + self.REDACTED_TEXT + groups[2]
                        else:
                            return self.REDACTED_TEXT
                    return match.group(0)

                filtered_text = pattern.sub(replace_if_suspicious, filtered_text)
            elif pattern_name == "aws_secret_key":
                # AWS secret key pattern has 3 groups
                def replace_aws(match):
                    groups = match.groups()
                    if len(groups) >= 3:
                        return groups[0] + self.REDACTED_TEXT + groups[2]
                    else:
                        return self.REDACTED_TEXT

                filtered_text = pattern.sub(replace_aws, filtered_text)

        return filtered_text

    def filter_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter sensitive data from a dictionary

        Args:
            data: Dictionary that may contain sensitive data

        Returns:
            New dictionary with sensitive values redacted
        """
        if not isinstance(data, dict):
            return data

        filtered = {}
        for key, value in data.items():
            key_lower = key.lower().replace("-", "_")

            # Check if key name indicates sensitive data
            if any(kw in key_lower for kw in self.keywords):
                if isinstance(value, str) and len(value) >= self.MIN_SENSITIVE_LENGTH:
                    filtered[key] = self.REDACTED_TEXT
                else:
                    filtered[key] = value
            elif isinstance(value, dict):
                # Recursively filter nested dictionaries
                filtered[key] = self.filter_dict(value)
            elif isinstance(value, list):
                # Filter lists
                filtered[key] = [
                    (
                        self.filter_dict(item)
                        if isinstance(item, dict)
                        else self.filter_string(item) if isinstance(item, str) else item
                    )
                    for item in value
                ]
            elif isinstance(value, str):
                # Filter string values
                filtered[key] = self.filter_string(value)
            else:
                filtered[key] = value

        return filtered

    def filter_exception(self, exc: Exception) -> str:
        """
        Filter sensitive data from exception messages

        Args:
            exc: Exception object

        Returns:
            Filtered exception message
        """
        exc_str = str(exc)
        return self.filter_string(exc_str)

    def filter_log_record(self, message: str, extra: Optional[Dict[str, Any]] = None) -> tuple:
        """
        Filter sensitive data from log record

        Args:
            message: Log message
            extra: Extra data dictionary

        Returns:
            Tuple of (filtered_message, filtered_extra)
        """
        filtered_message = self.filter_string(message)
        filtered_extra = self.filter_dict(extra) if extra else None

        return filtered_message, filtered_extra

    def is_sensitive_key(self, key: str) -> bool:
        """
        Check if a key name indicates sensitive data

        Args:
            key: Key name to check

        Returns:
            True if key name suggests sensitive data
        """
        key_lower = key.lower().replace("-", "_")
        return any(kw in key_lower for kw in self.keywords)

    def add_pattern(self, name: str, pattern: re.Pattern):
        """
        Add a custom pattern for detecting sensitive data

        Args:
            name: Pattern name
            pattern: Compiled regex pattern
        """
        self.patterns[name] = pattern

    def add_keyword(self, keyword: str):
        """
        Add a keyword that indicates sensitive data

        Args:
            keyword: Keyword to add (case-insensitive)
        """
        self.keywords.add(keyword.lower())


# Global secrets filter instance
_secrets_filter: Optional[SecretsFilter] = None


def get_secrets_filter() -> SecretsFilter:
    """
    Get or create the global secrets filter instance

    Returns:
        SecretsFilter instance
    """
    global _secrets_filter
    if _secrets_filter is None:
        _secrets_filter = SecretsFilter()
    return _secrets_filter


def filter_secrets(text: Union[str, Dict, Exception]) -> Union[str, Dict]:
    """
    Convenience function to filter secrets from various types

    Args:
        text: String, dictionary, or exception to filter

    Returns:
        Filtered version of input
    """
    filter_instance = get_secrets_filter()

    if isinstance(text, str):
        return filter_instance.filter_string(text)
    elif isinstance(text, dict):
        return filter_instance.filter_dict(text)
    elif isinstance(text, Exception):
        return filter_instance.filter_exception(text)
    else:
        return text
