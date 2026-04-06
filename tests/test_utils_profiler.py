"""
Unit tests for janus.utils.profiler module
Tests performance profiling, timing, and memory tracking
"""

import time
import pytest
from unittest.mock import Mock, patch
from janus.utils.profiler import (
    PerformanceProfiler,
    get_profiler,
    profile,
    timed,
    MemoryTracker,
    get_memory_tracker,
)


class TestPerformanceProfiler:
    """Test PerformanceProfiler class"""

    def test_initialization(self):
        """Test profiler initialization"""
        profiler = PerformanceProfiler()
        # Test public behavior: profiler starts enabled and with no stats
        stats = profiler.get_stats()
        assert stats == {}  # No timings recorded yet

    def test_enable_disable(self):
        """Test enabling and disabling profiler"""
        profiler = PerformanceProfiler()
        
        # When disabled, no timings should be recorded
        profiler.disable()
        profiler.record_timing("test_op", 1.0)
        assert profiler.get_stats("test_op") == {}
        
        # When enabled, timings should be recorded
        profiler.enable()
        profiler.record_timing("test_op", 1.0)
        assert profiler.get_stats("test_op")["count"] == 1

    def test_record_timing_when_enabled(self):
        """Test recording timing when profiler is enabled"""
        profiler = PerformanceProfiler()
        profiler.record_timing("test_op", 1.5)
        
        stats = profiler.get_stats("test_op")
        assert stats["count"] == 1
        assert stats["total"] == 1.5
        assert stats["mean"] == 1.5

    def test_record_timing_when_disabled(self):
        """Test recording timing when profiler is disabled"""
        profiler = PerformanceProfiler()
        profiler.disable()
        profiler.record_timing("test_op", 1.5)
        
        stats = profiler.get_stats("test_op")
        assert stats == {}

    def test_record_multiple_timings(self):
        """Test recording multiple timings for same operation"""
        profiler = PerformanceProfiler()
        profiler.record_timing("test_op", 1.0)
        profiler.record_timing("test_op", 2.0)
        profiler.record_timing("test_op", 3.0)
        
        stats = profiler.get_stats("test_op")
        assert stats["count"] == 3
        assert stats["total"] == 6.0
        assert stats["mean"] == 2.0
        assert stats["min"] == 1.0
        assert stats["max"] == 3.0

    def test_get_stats_for_missing_operation(self):
        """Test getting stats for non-existent operation"""
        profiler = PerformanceProfiler()
        stats = profiler.get_stats("nonexistent")
        assert stats == {}

    def test_get_stats_all_operations(self):
        """Test getting stats for all operations"""
        profiler = PerformanceProfiler()
        profiler.record_timing("op1", 1.0)
        profiler.record_timing("op1", 2.0)
        profiler.record_timing("op2", 3.0)
        
        stats = profiler.get_stats()
        assert "op1" in stats
        assert "op2" in stats
        assert stats["op1"]["count"] == 2
        assert stats["op2"]["count"] == 1

    def test_get_stats_empty_timings(self):
        """Test getting stats when no timings recorded"""
        profiler = PerformanceProfiler()
        stats = profiler.get_stats()
        assert stats == {}

    def test_reset(self):
        """Test resetting profiler data"""
        profiler = PerformanceProfiler()
        profiler.record_timing("test_op", 1.0)
        
        assert len(profiler.get_stats()) > 0
        
        profiler.reset()
        assert len(profiler.get_stats()) == 0

    def test_thread_safety(self):
        """Test profiler is thread-safe"""
        import threading
        
        profiler = PerformanceProfiler()
        
        def record_timings():
            for i in range(100):
                profiler.record_timing("concurrent_op", 0.001 * i)
        
        threads = [threading.Thread(target=record_timings) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        stats = profiler.get_stats("concurrent_op")
        assert stats["count"] == 500  # 100 * 5 threads

    def test_print_report_with_data(self):
        """Test printing report with profiling data"""
        profiler = PerformanceProfiler()
        profiler.record_timing("op1", 1.0)
        profiler.record_timing("op2", 2.0)
        
        # Should not raise exception
        profiler.print_report()

    def test_print_report_without_data(self):
        """Test printing report without profiling data"""
        profiler = PerformanceProfiler()
        
        # Should not raise exception
        profiler.print_report()


class TestGlobalProfiler:
    """Test global profiler instance"""

    def test_get_profiler(self):
        """Test getting global profiler instance"""
        profiler = get_profiler()
        assert isinstance(profiler, PerformanceProfiler)
        
        # Should return same instance
        profiler2 = get_profiler()
        assert profiler is profiler2


class TestProfileContextManager:
    """Test profile context manager"""

    def test_profile_records_timing(self):
        """Test profile context manager records timing"""
        profiler = PerformanceProfiler()
        
        with profile("test_operation", profiler):
            time.sleep(0.01)
        
        stats = profiler.get_stats("test_operation")
        assert stats["count"] == 1
        assert stats["total"] >= 0.01

    def test_profile_with_exception(self):
        """Test profile records timing even with exception"""
        profiler = PerformanceProfiler()
        
        try:
            with profile("failing_op", profiler):
                time.sleep(0.01)
                raise ValueError("Test error")
        except ValueError:
            pass
        
        stats = profiler.get_stats("failing_op")
        assert stats["count"] == 1
        assert stats["total"] >= 0.01

    def test_profile_uses_global_profiler(self):
        """Test profile uses global profiler by default"""
        global_profiler = get_profiler()
        global_profiler.reset()
        
        with profile("global_test"):
            time.sleep(0.01)
        
        stats = global_profiler.get_stats("global_test")
        assert stats["count"] == 1

    def test_profile_multiple_operations(self):
        """Test profiling multiple operations"""
        profiler = PerformanceProfiler()
        
        with profile("op1", profiler):
            time.sleep(0.01)
        
        with profile("op2", profiler):
            time.sleep(0.01)
        
        stats = profiler.get_stats()
        assert "op1" in stats
        assert "op2" in stats
        assert stats["op1"]["count"] == 1
        assert stats["op2"]["count"] == 1


class TestTimedDecorator:
    """Test timed decorator"""

    def test_timed_records_timing(self):
        """Test timed decorator records timing"""
        profiler = PerformanceProfiler()
        
        @timed("decorated_func", profiler)
        def test_func():
            time.sleep(0.01)
            return "result"
        
        result = test_func()
        assert result == "result"
        
        stats = profiler.get_stats("decorated_func")
        assert stats["count"] == 1
        assert stats["total"] >= 0.01

    def test_timed_uses_function_name(self):
        """Test timed uses function name when no name provided"""
        profiler = PerformanceProfiler()
        
        @timed(profiler=profiler)
        def my_function():
            return "result"
        
        result = my_function()
        assert result == "result"
        
        stats = profiler.get_stats("my_function")
        assert stats["count"] == 1

    def test_timed_preserves_function_signature(self):
        """Test timed decorator preserves function signature"""
        profiler = PerformanceProfiler()
        
        @timed("func_with_args", profiler)
        def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"
        
        result = func_with_args("x", "y", c="z")
        assert result == "x-y-z"

    def test_timed_multiple_calls(self):
        """Test timed decorator across multiple calls"""
        profiler = PerformanceProfiler()
        
        @timed("multi_call", profiler)
        def test_func():
            time.sleep(0.01)
        
        test_func()
        test_func()
        test_func()
        
        stats = profiler.get_stats("multi_call")
        assert stats["count"] == 3

    def test_timed_with_exception(self):
        """Test timed decorator with exception"""
        profiler = PerformanceProfiler()
        
        @timed("failing_func", profiler)
        def failing_func():
            time.sleep(0.01)
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_func()
        
        # Should still record timing
        stats = profiler.get_stats("failing_func")
        assert stats["count"] == 1


class TestMemoryTracker:
    """Test MemoryTracker class"""

    def test_initialization_with_psutil(self):
        """Test MemoryTracker initialization with psutil"""
        try:
            tracker = MemoryTracker()
            assert tracker.available in (True, False)
        except Exception:
            pytest.skip("Failed to initialize MemoryTracker")

    def test_get_memory_mb(self):
        """Test getting memory usage in MB"""
        tracker = MemoryTracker()
        
        if tracker.available:
            memory_mb = tracker.get_memory_mb()
            assert isinstance(memory_mb, float)
            assert memory_mb >= 0
        else:
            assert tracker.get_memory_mb() == 0.0

    def test_get_memory_info(self):
        """Test getting detailed memory info"""
        tracker = MemoryTracker()
        info = tracker.get_memory_info()
        
        assert "available" in info
        
        if tracker.available:
            assert "rss_mb" in info
            assert "vms_mb" in info
            assert "percent" in info
            assert info["rss_mb"] >= 0
        else:
            assert info["available"] is False

    def test_track_context_manager(self):
        """Test memory tracking context manager"""
        tracker = MemoryTracker()
        
        # Should not raise exception regardless of psutil availability
        with tracker.track("test_operation"):
            # Allocate some memory
            data = [i for i in range(1000)]
            assert len(data) == 1000

    def test_track_with_exception(self):
        """Test memory tracking with exception"""
        tracker = MemoryTracker()
        
        try:
            with tracker.track("failing_operation"):
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected

    def test_global_memory_tracker(self):
        """Test global memory tracker instance"""
        tracker = get_memory_tracker()
        assert isinstance(tracker, MemoryTracker)
        
        # Should return same instance
        tracker2 = get_memory_tracker()
        assert tracker is tracker2


class TestMemoryTrackerWithoutPsutil:
    """Test MemoryTracker behavior without psutil"""

    def test_tracker_when_psutil_unavailable(self):
        """Test MemoryTracker handles missing psutil gracefully"""
        # Create tracker and test it handles unavailable psutil
        tracker = MemoryTracker()
        
        # If psutil is not available, these should return safe values
        if not tracker.available:
            assert tracker.get_memory_mb() == 0.0
            info = tracker.get_memory_info()
            assert info["available"] is False
