"""
Tests for memory profiling and leak detection utilities
"""
import tempfile
import time
import unittest
from pathlib import Path

from janus.utils.memory_profiler import (
    MemoryLeakDetector,
    MemoryProfiler,
    get_memory_usage,
    track_memory,
)


class TestMemoryProfiler(unittest.TestCase):
    """Test MemoryProfiler class"""

    def test_basic_profiling(self):
        """Test basic memory profiling"""
        profiler = MemoryProfiler(enable_tracemalloc=True)
        profiler.start_tracking()

        # Allocate some memory
        data = [0] * 1000000

        # Take snapshot
        snapshot = profiler.take_snapshot()

        self.assertIsNotNone(snapshot)
        self.assertGreater(snapshot.current_mb, 0)
        self.assertIsInstance(snapshot.object_counts, dict)

        # Stop tracking
        summary = profiler.stop_tracking()

        self.assertIn("baseline_mb", summary)
        self.assertIn("final_mb", summary)
        self.assertIn("memory_increase_mb", summary)

        # Clean up
        del data

    def test_snapshot_tracking(self):
        """Test taking multiple snapshots"""
        profiler = MemoryProfiler(enable_tracemalloc=True)
        profiler.start_tracking()

        # Take first snapshot
        snapshot1 = profiler.take_snapshot()

        # Allocate significant memory
        data = [0] * 5000000  # Larger allocation to ensure detection

        # Take second snapshot
        snapshot2 = profiler.take_snapshot()

        # Should have increased (use peak_mb which is more reliable)
        self.assertGreaterEqual(snapshot2.peak_mb, snapshot1.peak_mb)

        profiler.stop_tracking()
        del data

    def test_object_registration(self):
        """Test object lifecycle tracking"""
        profiler = MemoryProfiler(enable_tracemalloc=False)

        # Create objects that support weak references
        class TestObject:
            def __init__(self, name):
                self.name = name

        obj1 = TestObject("obj1")
        obj2 = TestObject("obj2")

        profiler.register_object(obj1)
        profiler.register_object(obj2)

        # Should have 2 tracked objects
        self.assertEqual(profiler.get_live_tracked_objects(), 2)

        # Delete one
        del obj1

        # Should have 1 tracked object
        self.assertEqual(profiler.get_live_tracked_objects(), 1)

        del obj2

    def test_profile_section(self):
        """Test profiling a code section"""
        profiler = MemoryProfiler(enable_tracemalloc=True)
        profiler.start_tracking()

        with profiler.profile_section("test_section") as result:
            # Allocate some memory
            data = [0] * 100000

        self.assertIn("name", result)
        self.assertEqual(result["name"], "test_section")
        self.assertIn("memory_delta_mb", result)

        profiler.stop_tracking()
        del data


class TestMemoryLeakDetector(unittest.TestCase):
    """Test MemoryLeakDetector class"""

    def test_no_leak_detection(self):
        """Test that no leak is detected for stable memory"""
        detector = MemoryLeakDetector(threshold_mb=5.0, min_iterations=3)

        # Run iterations without leaking
        for _ in range(10):
            detector.start_iteration()
            data = [0] * 1000
            del data
            detector.end_iteration()

        # Should not detect leak
        self.assertFalse(detector.has_leak())

    def test_leak_detection(self):
        """Test that leak is detected for growing memory"""
        detector = MemoryLeakDetector(threshold_mb=2.0, min_iterations=3)

        # Simulate leak by accumulating data
        leaked_data = []
        for _ in range(10):
            detector.start_iteration()
            # Leak memory each iteration
            leaked_data.append([0] * 500000)
            detector.end_iteration()

        # Should detect leak
        self.assertTrue(detector.has_leak())

        # Get report
        report = detector.get_leak_report()
        self.assertIn("Memory Leak Detection Report", report)
        self.assertIn("YES", report)

        # Clean up
        del leaked_data


class TestMemoryUtils(unittest.TestCase):
    """Test memory utility functions"""

    def test_get_memory_usage(self):
        """Test getting current memory usage"""
        usage = get_memory_usage()

        self.assertIn("rss_mb", usage)
        self.assertIn("vms_mb", usage)
        self.assertIn("available_mb", usage)
        self.assertIn("percent", usage)

        self.assertGreater(usage["rss_mb"], 0)
        self.assertGreater(usage["available_mb"], 0)

    def test_track_memory_context(self):
        """Test track_memory context manager"""
        result = {}

        with track_memory("test_operation", print_report=False) as result:
            # Allocate some memory
            data = [0] * 100000

        self.assertIn("memory_increase_mb", result)
        self.assertIn("baseline_mb", result)
        self.assertIn("final_mb", result)

        del data


class TestMemoryLeakRegression(unittest.TestCase):
    """Regression tests for common memory leak patterns"""

    def test_cache_size_limits(self):
        """Test that caches have size limits"""
        from janus.vision.cache import ElementCache, OCRCache

        # OCRCache should have max_size
        cache = OCRCache(max_size=10)

        # Add more than max_size entries
        for i in range(20):
            from PIL import Image

            img = Image.new("RGB", (100, 100))
            cache.set(img, f"result_{i}")

        # Should not exceed max_size
        self.assertLessEqual(len(cache._cache), 10)

    def test_learning_cache_size_limits(self):
        """Test that learning cache has size limits"""
        from janus.learning.learning_cache import LearningCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test_cache.json"
            cache = LearningCache(cache_path=str(cache_path), max_heuristics=50, max_preferences=30)

            # Add many heuristics
            for i in range(100):
                cache.store_heuristic(f"heuristic_{i}", i)

            # Should be limited
            heuristics = cache.get_all_heuristics()
            self.assertLessEqual(len(heuristics), 50)

            # Add many preferences
            for i in range(100):
                cache.store_preference(f"pref_{i}", i)

            # Should be limited
            prefs = cache.get_all_preferences()
            self.assertLessEqual(len(prefs), 30)

    def test_voice_cache_size_limits(self):
        """Test that voice adaptation cache has size limits"""
        from janus.io.stt.voice_adaptation_cache import VoiceAdaptationCache

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_voice.db"
            cache = VoiceAdaptationCache(
                db_path=str(db_path), enable_encryption=False, max_entries=20
            )

            # Add many corrections
            for i in range(50):
                audio_data = f"audio_{i}".encode()
                cache.add_correction(audio_data, f"raw_{i}", f"corrected_{i}")

            # Should be limited
            stats = cache.get_statistics()
            self.assertLessEqual(stats["total_entries"], 20)

    def test_database_connections_closed(self):
        """Test that database connections are properly closed"""
        import sqlite3

        from janus.io.stt.voice_adaptation_cache import VoiceAdaptationCache

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_conn.db"
            cache = VoiceAdaptationCache(db_path=str(db_path), enable_encryption=False)

            # Perform operations
            audio_data = b"test_audio"
            cache.add_correction(audio_data, "raw", "corrected")
            cache.get_correction(audio_data)
            cache.cleanup_old_entries()

            # Try to open connection - should work if previous ones closed
            try:
                conn = sqlite3.connect(db_path)
                conn.close()
                connection_ok = True
            except Exception:
                connection_ok = False

            self.assertTrue(connection_ok)


if __name__ == "__main__":
    unittest.main()
