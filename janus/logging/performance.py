"""
Performance logging for Janus
Tracks execution times, resource usage, and performance metrics
"""

import os
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

from .logger import LogLevel, get_logger


class PerformanceLogger:
    """
    Logger for performance metrics and timing
    """

    def __init__(self, name: str = "performance"):
        """
        Initialize performance logger

        Args:
            name: Logger name
        """
        self.logger = get_logger(name, level=LogLevel.DEBUG)
        self.timers: Dict[str, float] = {}

    def start_timer(self, operation: str):
        """
        Start timing an operation

        Args:
            operation: Operation name
        """
        self.timers[operation] = time.time()
        self.logger.debug(f"Started timing: {operation}")

    def end_timer(self, operation: str, log_result: bool = True) -> Optional[float]:
        """
        End timing an operation

        Args:
            operation: Operation name
            log_result: Log the result

        Returns:
            Duration in seconds, or None if timer not found
        """
        if operation not in self.timers:
            self.logger.warning(f"No timer found for operation: {operation}")
            return None

        duration = time.time() - self.timers[operation]
        del self.timers[operation]

        if log_result:
            self.logger.info(
                f"Operation completed: {operation}",
                extra={"duration_seconds": duration, "duration_ms": duration * 1000},
            )

        return duration

    @contextmanager
    def measure(self, operation: str):
        """
        Context manager for measuring operation duration

        Args:
            operation: Operation name

        Example:
            with perf_logger.measure("process_command"):
                # code to measure
                pass
        """
        self.start_timer(operation)
        try:
            yield
        finally:
            self.end_timer(operation)

    def log_memory_usage(self, context: str = ""):
        """
        Log current memory usage

        Args:
            context: Context description
        """
        if not PSUTIL_AVAILABLE:
            return
        
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            self.logger.info(
                f"Memory usage{': ' + context if context else ''}",
                extra={
                    "rss_mb": memory_info.rss / 1024 / 1024,
                    "vms_mb": memory_info.vms / 1024 / 1024,
                },
            )
        except Exception as e:
            self.logger.warning(f"Could not log memory usage: {e}")

    def log_cpu_usage(self, context: str = "", interval: float = 0.1):
        """
        Log current CPU usage

        Args:
            context: Context description
            interval: Interval for CPU measurement
        """
        if not PSUTIL_AVAILABLE:
            return
        
        try:
            process = psutil.Process(os.getpid())
            cpu_percent = process.cpu_percent(interval=interval)

            self.logger.info(
                f"CPU usage{': ' + context if context else ''}", extra={"cpu_percent": cpu_percent}
            )
        except Exception as e:
            self.logger.warning(f"Could not log CPU usage: {e}")

    def log_system_resources(self, context: str = ""):
        """
        Log comprehensive system resource information

        Args:
            context: Context description
        """
        if not PSUTIL_AVAILABLE:
            return
        
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent(interval=0.1)

            # System-wide stats
            system_memory = psutil.virtual_memory()
            system_cpu = psutil.cpu_percent(interval=0.1)

            self.logger.info(
                f"System resources{': ' + context if context else ''}",
                extra={
                    "process": {
                        "rss_mb": memory_info.rss / 1024 / 1024,
                        "vms_mb": memory_info.vms / 1024 / 1024,
                        "cpu_percent": cpu_percent,
                    },
                    "system": {
                        "memory_percent": system_memory.percent,
                        "memory_available_mb": system_memory.available / 1024 / 1024,
                        "cpu_percent": system_cpu,
                    },
                },
            )
        except Exception as e:
            self.logger.warning(f"Could not log system resources: {e}")

    def log_operation_stats(
        self,
        operation: str,
        success: bool,
        duration: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Log operation statistics

        Args:
            operation: Operation name
            success: Whether operation succeeded
            duration: Operation duration in seconds
            extra: Additional data to log
        """
        log_data = {
            "operation": operation,
            "success": success,
        }

        if duration is not None:
            log_data["duration_seconds"] = duration
            log_data["duration_ms"] = duration * 1000

        if extra:
            log_data.update(extra)

        level = self.logger.info if success else self.logger.error
        level(f"Operation {'succeeded' if success else 'failed'}: {operation}", extra=log_data)
