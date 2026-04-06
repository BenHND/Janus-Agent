"""
Memory profiling utilities for detecting memory leaks

This module provides utilities for memory profiling and leak detection:
- tracemalloc wrapper for memory snapshots
- Memory usage tracking and reporting
- Memory leak detection in tests
- Resource cleanup verification
"""

import gc
import os
import tracemalloc
import weakref
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import psutil

from janus.logging import get_logger

from ..constants import MEMORY_LEAK_THRESHOLD_MB, MIN_LEAK_DETECTION_ITERATIONS

# Initialize logger
logger = get_logger("memory_profiler")


@dataclass
class MemorySnapshot:
    """Memory usage snapshot"""

    timestamp: float
    current_mb: float
    peak_mb: float
    top_allocations: List[Tuple[str, int]]
    object_counts: Dict[str, int]


class MemoryProfiler:
    """
    Memory profiler for tracking memory usage and detecting leaks

    Features:
    - tracemalloc integration for precise allocation tracking
    - Memory snapshots with top allocations
    - Memory leak detection via object counting
    - Resource cleanup verification
    """

    def __init__(self, enable_tracemalloc: bool = True):
        """
        Initialize memory profiler

        Args:
            enable_tracemalloc: Enable tracemalloc for detailed tracking
        """
        self.enable_tracemalloc = enable_tracemalloc
        self._snapshots: List[MemorySnapshot] = []
        self._baseline_snapshot: Optional[MemorySnapshot] = None
        self._tracked_objects: weakref.WeakSet = weakref.WeakSet()

        if self.enable_tracemalloc and not tracemalloc.is_tracing():
            tracemalloc.start()

    def start_tracking(self):
        """Start memory tracking"""
        if self.enable_tracemalloc and not tracemalloc.is_tracing():
            tracemalloc.start()

        # Clear any previous snapshots
        self._snapshots.clear()

        # Take baseline snapshot
        self._baseline_snapshot = self.take_snapshot()

    def take_snapshot(self, top_n: int = 10) -> MemorySnapshot:
        """
        Take a memory snapshot

        Args:
            top_n: Number of top allocations to include

        Returns:
            MemorySnapshot with current state
        """
        import time

        # Force garbage collection for accurate reading
        gc.collect()

        # Get process memory info
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        current_mb = memory_info.rss / 1024 / 1024

        # Get tracemalloc stats if enabled
        top_allocations = []
        if self.enable_tracemalloc and tracemalloc.is_tracing():
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics("lineno")

            for stat in top_stats[:top_n]:
                size_mb = stat.size / 1024 / 1024
                location = f"{stat.traceback.format()[0]}"
                top_allocations.append((location, stat.size))

            current, peak = tracemalloc.get_traced_memory()
            peak_mb = peak / 1024 / 1024
        else:
            peak_mb = current_mb

        # Count objects by type
        object_counts = {}
        for obj in gc.get_objects():
            obj_type = type(obj).__name__
            object_counts[obj_type] = object_counts.get(obj_type, 0) + 1

        # Create snapshot
        snapshot = MemorySnapshot(
            timestamp=time.time(),
            current_mb=current_mb,
            peak_mb=peak_mb,
            top_allocations=top_allocations,
            object_counts=object_counts,
        )

        self._snapshots.append(snapshot)
        return snapshot

    def stop_tracking(self) -> Dict[str, Any]:
        """
        Stop tracking and return summary

        Returns:
            Dictionary with memory statistics
        """
        # Take final snapshot
        final_snapshot = self.take_snapshot()

        # Calculate deltas from baseline
        if self._baseline_snapshot:
            memory_increase_mb = final_snapshot.current_mb - self._baseline_snapshot.current_mb
            peak_increase_mb = final_snapshot.peak_mb - self._baseline_snapshot.peak_mb

            # Find objects that increased significantly
            object_increases = {}
            for obj_type, count in final_snapshot.object_counts.items():
                baseline_count = self._baseline_snapshot.object_counts.get(obj_type, 0)
                increase = count - baseline_count
                if increase > 10:  # Only report significant increases
                    object_increases[obj_type] = {
                        "baseline": baseline_count,
                        "final": count,
                        "increase": increase,
                    }
        else:
            memory_increase_mb = 0
            peak_increase_mb = 0
            object_increases = {}

        summary = {
            "baseline_mb": self._baseline_snapshot.current_mb if self._baseline_snapshot else 0,
            "final_mb": final_snapshot.current_mb,
            "memory_increase_mb": memory_increase_mb,
            "peak_increase_mb": peak_increase_mb,
            "snapshots_taken": len(self._snapshots),
            "object_increases": object_increases,
            "top_allocations": final_snapshot.top_allocations[:5],
        }

        # Stop tracemalloc if we started it
        if self.enable_tracemalloc and tracemalloc.is_tracing():
            tracemalloc.stop()

        return summary

    def register_object(self, obj: Any):
        """
        Register an object for lifecycle tracking

        Args:
            obj: Object to track (uses weak reference)
        """
        try:
            self._tracked_objects.add(obj)
        except TypeError:
            # Some objects don't support weak references
            pass

    def get_live_tracked_objects(self) -> int:
        """
        Get count of tracked objects still alive

        Returns:
            Number of live tracked objects
        """
        # Force garbage collection
        gc.collect()

        return len(self._tracked_objects)

    @contextmanager
    def profile_section(self, name: str):
        """
        Context manager for profiling a code section

        Args:
            name: Name of the section being profiled

        Yields:
            Dictionary that will contain profiling results
        """
        # Take before snapshot
        before = self.take_snapshot()

        # Result dictionary
        result = {}

        try:
            yield result
        finally:
            # Take after snapshot
            after = self.take_snapshot()

            # Calculate deltas
            memory_delta = after.current_mb - before.current_mb
            peak_delta = after.peak_mb - before.peak_mb

            result.update(
                {
                    "name": name,
                    "memory_before_mb": before.current_mb,
                    "memory_after_mb": after.current_mb,
                    "memory_delta_mb": memory_delta,
                    "peak_delta_mb": peak_delta,
                }
            )

    def print_summary(self, summary: Optional[Dict[str, Any]] = None):
        """
        Print memory profiling summary

        Args:
            summary: Summary dict (uses stop_tracking() result if None)
        """
        if summary is None:
            summary = self.stop_tracking()

        report_lines = [
            "",
            "=" * 60,
            "MEMORY PROFILING SUMMARY",
            "=" * 60,
            f"Baseline:        {summary['baseline_mb']:.2f} MB",
            f"Final:           {summary['final_mb']:.2f} MB",
            f"Memory increase: {summary['memory_increase_mb']:.2f} MB",
            f"Peak increase:   {summary['peak_increase_mb']:.2f} MB",
            f"Snapshots taken: {summary['snapshots_taken']}",
        ]

        if summary["object_increases"]:
            report_lines.append("\nObject count increases:")
            for obj_type, counts in sorted(
                summary["object_increases"].items(), key=lambda x: x[1]["increase"], reverse=True
            )[:10]:
                report_lines.append(
                    f"  {obj_type:30s}: {counts['baseline']:6d} → {counts['final']:6d} "
                    f"(+{counts['increase']:6d})"
                )

        if summary["top_allocations"]:
            report_lines.append("\nTop allocations:")
            for location, size in summary["top_allocations"]:
                size_mb = size / 1024 / 1024
                report_lines.append(f"  {size_mb:8.2f} MB: {location[:80]}")

        report_lines.append("=" * 60)
        report_lines.append("")

        logger.info("\n".join(report_lines))


class MemoryLeakDetector:
    """
    Utility for detecting memory leaks in tests

    Usage:
        detector = MemoryLeakDetector()

        # Run test iterations
        for i in range(10):
            detector.start_iteration()
            # ... test code ...
            detector.end_iteration()

        # Check for leaks
        if detector.has_leak():
            print(detector.get_leak_report())
    """

    def __init__(
        self,
        threshold_mb: float = MEMORY_LEAK_THRESHOLD_MB,
        min_iterations: int = MIN_LEAK_DETECTION_ITERATIONS,
    ):
        """
        Initialize leak detector

        Args:
            threshold_mb: Memory increase threshold to consider a leak
            min_iterations: Minimum iterations before detecting leaks
        """
        self.threshold_mb = threshold_mb
        self.min_iterations = min_iterations
        self._iteration_snapshots: List[float] = []
        self._current_iteration_start: Optional[float] = None

    def start_iteration(self):
        """Start a test iteration"""
        gc.collect()
        process = psutil.Process(os.getpid())
        self._current_iteration_start = process.memory_info().rss / 1024 / 1024

    def end_iteration(self):
        """End a test iteration and record memory"""
        gc.collect()
        process = psutil.Process(os.getpid())
        current_mb = process.memory_info().rss / 1024 / 1024

        if self._current_iteration_start is not None:
            self._iteration_snapshots.append(current_mb)

    def has_leak(self) -> bool:
        """
        Check if memory leak detected

        Returns:
            True if leak detected
        """
        if len(self._iteration_snapshots) < self.min_iterations:
            return False

        # Check if memory is consistently increasing
        first_third = self._iteration_snapshots[: len(self._iteration_snapshots) // 3]
        last_third = self._iteration_snapshots[-len(self._iteration_snapshots) // 3 :]

        avg_first = sum(first_third) / len(first_third)
        avg_last = sum(last_third) / len(last_third)

        increase = avg_last - avg_first

        return increase > self.threshold_mb

    def get_leak_report(self) -> str:
        """
        Get leak detection report

        Returns:
            String report
        """
        if len(self._iteration_snapshots) < 2:
            return "Not enough iterations for leak detection"

        first = self._iteration_snapshots[0]
        last = self._iteration_snapshots[-1]
        increase = last - first
        avg_increase = increase / len(self._iteration_snapshots)

        report = []
        report.append(f"Memory Leak Detection Report")
        report.append(f"  Iterations: {len(self._iteration_snapshots)}")
        report.append(f"  First:      {first:.2f} MB")
        report.append(f"  Last:       {last:.2f} MB")
        report.append(f"  Increase:   {increase:.2f} MB")
        report.append(f"  Avg/iter:   {avg_increase:.2f} MB")
        report.append(f"  Threshold:  {self.threshold_mb:.2f} MB")
        report.append(f"  Leak:       {'YES' if self.has_leak() else 'NO'}")

        return "\n".join(report)


def get_memory_usage() -> Dict[str, float]:
    """
    Get current memory usage

    Returns:
        Dictionary with memory statistics in MB
    """
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()

    return {
        "rss_mb": memory_info.rss / 1024 / 1024,
        "vms_mb": memory_info.vms / 1024 / 1024,
        "available_mb": psutil.virtual_memory().available / 1024 / 1024,
        "percent": process.memory_percent(),
    }


@contextmanager
def track_memory(name: str = "operation", print_report: bool = True):
    """
    Context manager for tracking memory usage of an operation

    Args:
        name: Name of operation
        print_report: Whether to print report at end

    Yields:
        Dictionary with profiling results
    """
    profiler = MemoryProfiler(enable_tracemalloc=True)
    profiler.start_tracking()

    result = {}

    try:
        yield result
    finally:
        summary = profiler.stop_tracking()
        result.update(summary)

        if print_report:
            logger.debug(f"Memory Profile: {name}")
            logger.debug(f"Memory increase: {summary['memory_increase_mb']:.2f} MB")
            if summary["memory_increase_mb"] > 10:
                logger.warning(f"Significant memory increase detected in {name}")
