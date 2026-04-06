"""
Performance profiling utilities for Janus
Provides timing, memory tracking, and benchmarking tools
"""

import functools
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

from janus.logging import get_logger

# Initialize logger
logger = get_logger("profiler")


class PerformanceProfiler:
    """
    Thread-safe performance profiler for tracking execution times and memory usage
    """

    def __init__(self):
        self._timings: Dict[str, list] = {}
        self._lock = threading.Lock()
        self._enabled = True

    def enable(self):
        """Enable profiling"""
        self._enabled = True

    def disable(self):
        """Disable profiling"""
        self._enabled = False

    def record_timing(self, name: str, duration: float):
        """
        Record a timing measurement

        Args:
            name: Name of the operation
            duration: Duration in seconds
        """
        if not self._enabled:
            return

        with self._lock:
            if name not in self._timings:
                self._timings[name] = []
            self._timings[name].append(duration)

    def get_stats(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get timing statistics

        Args:
            name: Optional specific operation name, or all if None

        Returns:
            Dictionary with timing statistics
        """
        with self._lock:
            if name:
                if name not in self._timings:
                    return {}
                timings = self._timings[name]
                if not timings:
                    return {}
                return {
                    "name": name,
                    "count": len(timings),
                    "total": sum(timings),
                    "mean": sum(timings) / len(timings),
                    "min": min(timings),
                    "max": max(timings),
                }

            # Return stats for all operations
            stats = {}
            for op_name, timings in self._timings.items():
                if timings:
                    stats[op_name] = {
                        "count": len(timings),
                        "total": sum(timings),
                        "mean": sum(timings) / len(timings),
                        "min": min(timings),
                        "max": max(timings),
                    }
            return stats

    def reset(self):
        """Clear all timing data"""
        with self._lock:
            self._timings.clear()

    def print_report(self):
        """Print a formatted performance report"""
        stats = self.get_stats()
        if not stats:
            logger.debug("No profiling data available")
            return

        # Build report as string first, then log it
        report_lines = [
            "",
            "=" * 70,
            "PERFORMANCE PROFILING REPORT",
            "=" * 70,
        ]

        # Sort by total time descending
        sorted_stats = sorted(stats.items(), key=lambda x: x[1]["total"], reverse=True)

        report_lines.append(
            f"{'Operation':<40} {'Count':>8} {'Total':>10} {'Mean':>10} {'Min':>8} {'Max':>8}"
        )
        report_lines.append("-" * 70)

        for name, data in sorted_stats:
            report_lines.append(
                f"{name:<40} "
                f"{data['count']:>8} "
                f"{data['total']:>10.3f}s "
                f"{data['mean']:>10.3f}s "
                f"{data['min']:>8.3f}s "
                f"{data['max']:>8.3f}s"
            )

        report_lines.append("=" * 70)
        report_lines.append("")

        # Log the entire report
        logger.info("\n".join(report_lines))


# Global profiler instance
_profiler = PerformanceProfiler()


def get_profiler() -> PerformanceProfiler:
    """Get the global profiler instance"""
    return _profiler


@contextmanager
def profile(name: str, profiler: Optional[PerformanceProfiler] = None):
    """
    Context manager for timing a block of code

    Args:
        name: Name of the operation being profiled
        profiler: Optional profiler instance, uses global if None

    Example:
        with profile("model_loading"):
            model = load_model()
    """
    prof = profiler or _profiler
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        prof.record_timing(name, duration)


def timed(name: Optional[str] = None, profiler: Optional[PerformanceProfiler] = None):
    """
    Decorator for timing function execution

    Args:
        name: Optional name for the operation (uses function name if None)
        profiler: Optional profiler instance, uses global if None

    Example:
        @timed("transcribe")
        def transcribe_audio(audio_path):
            ...
    """

    def decorator(func: Callable) -> Callable:
        operation_name = name or func.__name__
        prof = profiler or _profiler

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with profile(operation_name, prof):
                return func(*args, **kwargs)

        return wrapper

    return decorator


class MemoryTracker:
    """
    Track memory usage (requires psutil)
    """

    def __init__(self):
        try:
            import psutil

            self.psutil = psutil
            self.process = psutil.Process()
            self.available = True
        except ImportError:
            self.available = False

    def get_memory_mb(self) -> float:
        """
        Get current memory usage in MB

        Returns:
            Memory usage in MB or 0 if psutil unavailable
        """
        if not self.available:
            return 0.0
        return self.process.memory_info().rss / 1024 / 1024

    def get_memory_info(self) -> Dict[str, Any]:
        """
        Get detailed memory information

        Returns:
            Dictionary with memory stats
        """
        if not self.available:
            return {"available": False}

        mem_info = self.process.memory_info()
        return {
            "available": True,
            "rss_mb": mem_info.rss / 1024 / 1024,
            "vms_mb": mem_info.vms / 1024 / 1024,
            "percent": self.process.memory_percent(),
        }

    @contextmanager
    def track(self, name: str):
        """
        Context manager for tracking memory usage of a code block

        Args:
            name: Name of the operation

        Example:
            with memory_tracker.track("model_loading"):
                model = load_model()
        """
        if not self.available:
            yield
            return

        mem_before = self.get_memory_mb()
        try:
            yield
        finally:
            mem_after = self.get_memory_mb()
            delta = mem_after - mem_before
            logger.debug(
                f"{name}: Memory delta = {delta:+.2f} MB (before: {mem_before:.2f} MB, after: {mem_after:.2f} MB)"
            )


# Global memory tracker
_memory_tracker = MemoryTracker()


def get_memory_tracker() -> MemoryTracker:
    """Get the global memory tracker instance"""
    return _memory_tracker
