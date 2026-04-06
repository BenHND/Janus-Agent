"""
Telemetry and crash reporting module for Janus

TICKET-OPS-002: Provides crash reporting and error telemetry with:
- Sentry integration for remote crash reporting
- Opt-in consent management
- Automatic sanitization of sensitive data
- Global exception handling for UI and asyncio
"""

from .crash_reporter import CrashReporter, initialize_crash_reporting
from .consent_manager import ConsentManager, prompt_for_consent
from .sanitizer import sanitize_event

__all__ = [
    "CrashReporter",
    "initialize_crash_reporting",
    "ConsentManager",
    "prompt_for_consent",
    "sanitize_event",
]
