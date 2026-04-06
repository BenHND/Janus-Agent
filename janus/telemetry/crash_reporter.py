"""
Crash reporter with Sentry integration

TICKET-OPS-002: Provides crash reporting and error telemetry
- Integrates Sentry SDK
- Handles uncaught exceptions globally
- Captures PySide6 UI exceptions
- Handles asyncio unhandled exceptions
- Integrates with logging system
"""

import asyncio
import logging
import sys
from typing import Any, Callable, Optional

from janus import __version__

logger = logging.getLogger(__name__)


class CrashReporter:
    """
    Crash reporter with Sentry integration

    TICKET-OPS-002: Captures and reports application crashes
    """

    def __init__(
        self,
        dsn: Optional[str] = None,
        environment: str = "production",
        enable_tracing: bool = False,
        traces_sample_rate: float = 0.1,
    ):
        """
        Initialize crash reporter

        Args:
            dsn: Sentry DSN (Data Source Name). If None, uses a default test DSN
            environment: Environment name (production, development, etc.)
            enable_tracing: Enable performance tracing
            traces_sample_rate: Sample rate for traces (0.0 to 1.0)
        """
        self.dsn = dsn
        self.environment = environment
        self.enable_tracing = enable_tracing
        self.traces_sample_rate = traces_sample_rate
        self.initialized = False
        self._original_excepthook = None
        self._original_asyncio_exception_handler = None

    def initialize(self, sanitize_callback: Optional[Callable] = None) -> bool:
        """
        Initialize Sentry SDK and exception handlers

        Args:
            sanitize_callback: Optional callback for sanitizing events

        Returns:
            True if initialization succeeded, False otherwise
        """
        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration

            # Use provided DSN (environment variable check happens in initialize_crash_reporting)
            dsn = self.dsn

            if not dsn:
                logger.info("No Sentry DSN provided. Crash reporting disabled.")
                return False

            # Configure logging integration
            # Capture breadcrumbs for WARNING and above
            # Capture events for ERROR and above
            logging_integration = LoggingIntegration(
                level=logging.WARNING,  # Breadcrumbs from WARNING and up
                event_level=logging.ERROR  # Send events for ERROR and CRITICAL
            )

            # Initialize Sentry
            sentry_sdk.init(
                dsn=dsn,
                environment=self.environment,
                release=f"janus@{__version__}",
                integrations=[logging_integration],
                traces_sample_rate=self.traces_sample_rate if self.enable_tracing else 0.0,
                before_send=sanitize_callback,
                # Send default PII (False = more privacy)
                send_default_pii=False,
                # Attach stack trace to messages
                attach_stacktrace=True,
                # Set max breadcrumbs
                max_breadcrumbs=50,
            )

            logger.info(f"Sentry crash reporting initialized (environment: {self.environment})")
            self.initialized = True

            # Install global exception handlers
            self._install_exception_handlers()

            return True

        except ImportError:
            logger.warning("Sentry SDK not installed. Crash reporting disabled.")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
            return False

    def _install_exception_handlers(self):
        """Install global exception handlers for uncaught exceptions"""
        # Install sys.excepthook for uncaught exceptions
        self._original_excepthook = sys.excepthook
        sys.excepthook = self._handle_exception

        # Install asyncio exception handler
        self._install_asyncio_handler()

        # Install PySide6 exception handler if available
        self._install_qt_handler()

    def _handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        Global exception handler for uncaught exceptions

        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        # Ignore KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            if self._original_excepthook:
                self._original_excepthook(exc_type, exc_value, exc_traceback)
            return

        # Log the error
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

        # Capture with Sentry if initialized
        if self.initialized:
            try:
                import sentry_sdk
                sentry_sdk.capture_exception((exc_type, exc_value, exc_traceback))
                logger.info("Exception captured by Sentry")
            except Exception as e:
                logger.error(f"Failed to capture exception with Sentry: {e}")

        # Call original excepthook
        if self._original_excepthook:
            self._original_excepthook(exc_type, exc_value, exc_traceback)

    def _install_asyncio_handler(self):
        """Install asyncio exception handler for unhandled exceptions in tasks"""
        try:
            # Try to get the running event loop (Python 3.10+)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, try to get or create one (fallback for older Python)
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    # No event loop available yet
                    return
        except Exception:
            # Safety fallback
            return

        self._original_asyncio_exception_handler = loop.get_exception_handler()

        def asyncio_exception_handler(loop, context):
            """Handle asyncio exceptions"""
            # Extract exception if present
            exception = context.get('exception')
            message = context.get('message', 'Unhandled exception in asyncio')

            # Log the error
            if exception:
                logger.error(f"Asyncio exception: {message}", exc_info=exception)
            else:
                logger.error(f"Asyncio exception: {message}")

            # Capture with Sentry
            if self.initialized:
                try:
                    import sentry_sdk
                    if exception:
                        sentry_sdk.capture_exception(exception)
                    else:
                        sentry_sdk.capture_message(message, level='error')
                except Exception as e:
                    logger.error(f"Failed to capture asyncio exception with Sentry: {e}")

            # Call original handler if it exists
            if self._original_asyncio_exception_handler:
                self._original_asyncio_exception_handler(loop, context)

        loop.set_exception_handler(asyncio_exception_handler)

    def _install_qt_handler(self):
        """Install PySide6 exception handler if Qt is available"""
        try:
            from PySide6.QtCore import qInstallMessageHandler, QtMsgType

            def qt_message_handler(msg_type, context, message):
                """Handle Qt messages and errors"""
                # Map Qt message types to log levels
                if msg_type == QtMsgType.QtDebugMsg:
                    logger.debug(f"Qt: {message}")
                elif msg_type == QtMsgType.QtInfoMsg:
                    logger.info(f"Qt: {message}")
                elif msg_type == QtMsgType.QtWarningMsg:
                    logger.warning(f"Qt: {message}")
                elif msg_type == QtMsgType.QtCriticalMsg:
                    logger.error(f"Qt Critical: {message}")
                    # Capture critical Qt messages with Sentry
                    if self.initialized:
                        try:
                            import sentry_sdk
                            sentry_sdk.capture_message(
                                f"Qt Critical: {message}",
                                level='error'
                            )
                        except Exception:
                            pass
                elif msg_type == QtMsgType.QtFatalMsg:
                    logger.critical(f"Qt Fatal: {message}")
                    # Capture fatal Qt messages with Sentry
                    if self.initialized:
                        try:
                            import sentry_sdk
                            sentry_sdk.capture_message(
                                f"Qt Fatal: {message}",
                                level='fatal'
                            )
                        except Exception:
                            pass

            qInstallMessageHandler(qt_message_handler)
            logger.info("Qt exception handler installed")

        except ImportError:
            # PySide6 not available
            pass
        except Exception as e:
            logger.warning(f"Failed to install Qt exception handler: {e}")

    def capture_exception(self, exception: Exception, **kwargs):
        """
        Manually capture an exception

        Args:
            exception: Exception to capture
            **kwargs: Additional context to include
        """
        if not self.initialized:
            logger.warning("Cannot capture exception: Sentry not initialized")
            return

        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                # Add extra context
                for key, value in kwargs.items():
                    scope.set_extra(key, value)
                sentry_sdk.capture_exception(exception)
        except Exception as e:
            logger.error(f"Failed to capture exception: {e}")

    def capture_message(self, message: str, level: str = "info", **kwargs):
        """
        Manually capture a message

        Args:
            message: Message to capture
            level: Message level (debug, info, warning, error, fatal)
            **kwargs: Additional context to include
        """
        if not self.initialized:
            logger.warning("Cannot capture message: Sentry not initialized")
            return

        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                # Add extra context
                for key, value in kwargs.items():
                    scope.set_extra(key, value)
                sentry_sdk.capture_message(message, level=level)
        except Exception as e:
            logger.error(f"Failed to capture message: {e}")

    def shutdown(self):
        """Shutdown crash reporter and flush pending events"""
        if not self.initialized:
            return

        try:
            import sentry_sdk
            # Flush pending events (wait up to 2 seconds)
            client = sentry_sdk.Hub.current.client
            if client:
                client.flush(timeout=2.0)
            logger.info("Sentry shutdown complete")
        except Exception as e:
            logger.error(f"Error during Sentry shutdown: {e}")


# Global crash reporter instance
_crash_reporter: Optional[CrashReporter] = None


def initialize_crash_reporting(
    enabled: bool,
    dsn: Optional[str] = None,
    environment: str = "production",
    sanitize_callback: Optional[Callable] = None,
) -> Optional[CrashReporter]:
    """
    Initialize global crash reporting

    TICKET-OPS-002: Convenience function to initialize crash reporting

    Args:
        enabled: Whether crash reporting is enabled
        dsn: Sentry DSN
        environment: Environment name
        sanitize_callback: Optional sanitization callback

    Returns:
        CrashReporter instance if initialized, None otherwise
    """
    global _crash_reporter

    if not enabled:
        logger.info("Crash reporting disabled by configuration")
        return None

    _crash_reporter = CrashReporter(dsn=dsn, environment=environment)

    if _crash_reporter.initialize(sanitize_callback):
        logger.info("Crash reporting initialized successfully")
        return _crash_reporter
    else:
        logger.warning("Failed to initialize crash reporting")
        _crash_reporter = None
        return None


def get_crash_reporter() -> Optional[CrashReporter]:
    """
    Get global crash reporter instance

    Returns:
        CrashReporter instance or None if not initialized
    """
    return _crash_reporter
