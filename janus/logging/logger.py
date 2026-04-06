"""
Core logging functionality for Janus
Provides structured logging with rotation, levels, and formatting
Includes secrets filtering to prevent sensitive data exposure
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from janus.utils.paths import get_log_dir
from janus.utils.secrets_filter import get_secrets_filter


class LogLevel(Enum):
    """Log levels for Janus"""

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogFormatter(Enum):
    """Log output formatters"""

    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data)


class JanusLogger:
    """
    Enhanced logger for Janus with rotation, levels, and formatting
    """

    def __init__(
        self,
        name: str,
        log_dir: Optional[str] = None,
        level: LogLevel = LogLevel.INFO,
        formatter: LogFormatter = LogFormatter.DETAILED,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        console_output: bool = True,
    ):
        """
        Initialize Janus logger

        Args:
            name: Logger name
            log_dir: Directory for log files (default: platform-specific log directory)
            level: Minimum log level
            formatter: Log output format
            max_bytes: Maximum size per log file
            backup_count: Number of backup files to keep
            console_output: Also output to console
        """
        self.name = name
        self.logger = logging.getLogger(f"janus.{name}")
        self.logger.setLevel(level.value)
        self.logger.propagate = False

        # Clear existing handlers
        self.logger.handlers.clear()

        # Set up log directory using cross-platform paths
        if log_dir is None:
            log_dir = str(get_log_dir())

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Set up file handler with rotation
        log_file = self.log_dir / f"{name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(level.value)
        file_handler.setFormatter(self._get_formatter(formatter))
        self.logger.addHandler(file_handler)

        # Set up console handler if requested
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level.value)
            console_handler.setFormatter(self._get_formatter(LogFormatter.SIMPLE))
            self.logger.addHandler(console_handler)

        # Log initialization
        self.info(f"Logger initialized for {name}", extra={"log_dir": str(log_dir)})

    def _get_formatter(self, formatter: LogFormatter) -> logging.Formatter:
        """Get formatter based on type"""
        if formatter == LogFormatter.SIMPLE:
            return logging.Formatter("%(levelname)s: %(message)s")
        elif formatter == LogFormatter.DETAILED:
            return logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        elif formatter == LogFormatter.JSON:
            return JSONFormatter()
        else:
            return logging.Formatter("%(message)s")

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log debug message"""
        self._log(logging.DEBUG, message, extra)

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log info message"""
        self._log(logging.INFO, message, extra)

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log warning message"""
        self._log(logging.WARNING, message, extra)

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log error message"""
        self._log(logging.ERROR, message, extra, exc_info=exc_info)
        # TICKET-OPS-002: Capture errors in Sentry if crash reporting is enabled
        self._capture_to_sentry(message, "error", extra)

    def critical(
        self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False
    ):
        """Log critical message"""
        self._log(logging.CRITICAL, message, extra, exc_info=exc_info)
        # TICKET-OPS-002: Capture critical errors in Sentry if crash reporting is enabled
        self._capture_to_sentry(message, "fatal", extra)

    def _log(
        self,
        level: int,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ):
        """Internal logging method with secrets filtering"""
        # Filter sensitive data from message and extra data
        secrets_filter = get_secrets_filter()
        filtered_message, filtered_extra = secrets_filter.filter_log_record(message, extra)

        if filtered_extra:
            # Create a LogRecord with filtered extra data
            record = self.logger.makeRecord(
                self.logger.name,
                level,
                "(unknown file)",
                0,
                filtered_message,
                (),
                None,
                "(unknown function)",
            )
            record.extra_data = filtered_extra
            self.logger.handle(record)
        else:
            self.logger.log(level, filtered_message, exc_info=exc_info)

    def _capture_to_sentry(
        self, message: str, level: str, extra: Optional[Dict[str, Any]] = None
    ):
        """
        Capture log message to Sentry if crash reporting is enabled
        
        TICKET-OPS-002: Integration with crash reporting
        
        Args:
            message: Log message
            level: Sentry level (error, warning, info, etc.)
            extra: Extra context data
        """
        try:
            # Import crash reporter lazily to avoid circular dependencies
            from janus.telemetry.crash_reporter import get_crash_reporter
            
            reporter = get_crash_reporter()
            if reporter and reporter.initialized:
                if extra:
                    reporter.capture_message(message, level=level, **extra)
                else:
                    reporter.capture_message(message, level=level)
        except Exception:
            # Silently fail if Sentry capture fails
            # We don't want logging to crash the application
            pass

    def set_level(self, level: LogLevel):
        """Change log level dynamically"""
        self.logger.setLevel(level.value)
        for handler in self.logger.handlers:
            handler.setLevel(level.value)
        self.info(f"Log level changed to {level.name}")

    def get_log_files(self) -> list:
        """Get list of log files for this logger"""
        pattern = f"{self.name}.log*"
        return sorted(self.log_dir.glob(pattern))

    def get_log_size(self) -> int:
        """Get total size of log files in bytes"""
        return sum(f.stat().st_size for f in self.get_log_files())


# Global logger registry
_loggers: Dict[str, JanusLogger] = {}
_default_config = {
    "level": LogLevel.INFO,
    "formatter": LogFormatter.DETAILED,
    "console_output": True,
}


def configure_logging(
    level: Optional[LogLevel] = None,
    formatter: Optional[LogFormatter] = None,
    console_output: Optional[bool] = None,
    log_dir: Optional[str] = None,
):
    """
    Configure global logging settings for all Janus loggers

    Args:
        level: Minimum log level
        formatter: Log output format
        console_output: Enable console output
        log_dir: Directory for log files
    """
    global _default_config

    if level is not None:
        _default_config["level"] = level
    if formatter is not None:
        _default_config["formatter"] = formatter
    if console_output is not None:
        _default_config["console_output"] = console_output
    if log_dir is not None:
        _default_config["log_dir"] = log_dir

    # Update existing loggers
    for logger in _loggers.values():
        if level is not None:
            logger.set_level(level)


def get_logger(name: str, **kwargs) -> JanusLogger:
    """
    Get or create a logger with the given name

    Args:
        name: Logger name
        **kwargs: Additional arguments for JanusLogger

    Returns:
        JanusLogger instance
    """
    if name not in _loggers:
        # Merge default config with kwargs
        config = {**_default_config, **kwargs}
        _loggers[name] = JanusLogger(name, **config)

    return _loggers[name]
