"""
Tests for Phase 9: OCR and LLM Optimization
Tests performance improvements, caching, and async processing
"""
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

from janus.ai.llm.unified_client import UnifiedLLMClient


class TestLLMServiceOptimization(unittest.TestCase):
    """Test LLM Service optimization features"""

    def setUp(self):
        """Set up test LLM service"""
        self.llm = UnifiedLLMClient(provider="mock", enable_cache=True, cache_ttl=60, request_timeout=30)

    def test_cache_initialization(self):
        """Test cache is properly initialized"""
        self.assertTrue(self.llm.enable_cache)
        self.assertEqual(self.llm.cache_ttl, 60)
        self.assertEqual(self.llm.request_timeout, 30)

    def test_command_caching(self):
        """Test command responses are cached"""
        # First call should miss cache
        result1 = self.llm.analyze_command("open chrome")
        metrics1 = self.llm.get_performance_metrics()
        self.assertEqual(metrics1["cache_misses"], 1)
        self.assertEqual(metrics1["cache_hits"], 0)

        # Second identical call should hit cache
        result2 = self.llm.analyze_command("open chrome")
        metrics2 = self.llm.get_performance_metrics()
        self.assertEqual(metrics2["cache_hits"], 1)
        self.assertEqual(metrics2["cache_misses"], 1)

        # Results should be identical
        self.assertEqual(result1, result2)

    def test_cache_key_normalization(self):
        """Test cache keys are normalized (case insensitive, etc.)"""
        # These should produce the same cache key
        result1 = self.llm.analyze_command("Open Chrome")
        result2 = self.llm.analyze_command("open chrome")
        result3 = self.llm.analyze_command("  open chrome  ")

        metrics = self.llm.get_performance_metrics()

        # First call is cache miss, next two are hits
        self.assertEqual(metrics["cache_misses"], 1)
        self.assertEqual(metrics["cache_hits"], 2)

    def test_cache_ttl_expiration(self):
        """Test cache entries expire after TTL"""
        # Use very short TTL for testing
        llm = UnifiedLLMClient(provider="mock", enable_cache=True, cache_ttl=0.1)

        # First call
        result1 = llm.analyze_command("open chrome")
        metrics1 = llm.get_performance_metrics()
        self.assertEqual(metrics1["cache_misses"], 1)

        # Wait for cache to expire
        time.sleep(0.15)

        # Second call should miss cache due to expiration
        result2 = llm.analyze_command("open chrome")
        metrics2 = llm.get_performance_metrics()
        self.assertEqual(metrics2["cache_misses"], 2)
        self.assertEqual(metrics2["cache_hits"], 0)

    def test_cache_disabled(self):
        """Test LLM works correctly with cache disabled"""
        llm = UnifiedLLMClient(provider="mock", enable_cache=False)

        result1 = llm.analyze_command("open chrome")
        result2 = llm.analyze_command("open chrome")

        metrics = llm.get_performance_metrics()

        # All calls should be cache misses
        self.assertEqual(metrics["cache_misses"], 2)
        self.assertEqual(metrics["cache_hits"], 0)

    def test_clear_cache(self):
        """Test cache can be cleared"""
        result1 = self.llm.analyze_command("open chrome")

        # Should hit cache
        result2 = self.llm.analyze_command("open chrome")
        metrics1 = self.llm.get_performance_metrics()
        self.assertEqual(metrics1["cache_hits"], 1)

        # Clear cache
        self.llm.clear_cache()

        # Should miss cache after clearing
        result3 = self.llm.analyze_command("open chrome")
        metrics2 = self.llm.get_performance_metrics()
        self.assertEqual(metrics2["cache_misses"], 2)

    def test_performance_metrics(self):
        """Test performance metrics are tracked correctly"""
        # Make several calls
        self.llm.analyze_command("open chrome")
        self.llm.analyze_command("open chrome")  # Cache hit
        self.llm.analyze_command("open safari")  # Cache miss

        metrics = self.llm.get_performance_metrics()

        self.assertEqual(metrics["total_calls"], 3)
        self.assertEqual(metrics["cache_hits"], 1)
        self.assertEqual(metrics["cache_misses"], 2)
        self.assertGreater(metrics["average_time"], 0)
        self.assertGreater(metrics["cache_hit_rate"], 0)

    def test_reset_metrics(self):
        """Test metrics can be reset"""
        self.llm.analyze_command("open chrome")

        metrics1 = self.llm.get_performance_metrics()
        self.assertEqual(metrics1["total_calls"], 1)

        self.llm.reset_metrics()

        metrics2 = self.llm.get_performance_metrics()
        self.assertEqual(metrics2["total_calls"], 0)
        self.assertEqual(metrics2["cache_hits"], 0)
        self.assertEqual(metrics2["cache_misses"], 0)

    def test_cache_lru_eviction(self):
        """Test LRU cache eviction when cache is full"""
        # Create LLM with small cache
        llm = UnifiedLLMClient(provider="mock", enable_cache=True)

        # Fill cache beyond limit (100 entries)
        # This should trigger LRU eviction
        for i in range(105):
            llm.analyze_command(f"command {i}")

        # Cache should not exceed max size
        # Oldest entries should be evicted
        # We can't directly test this without accessing private variables
        # but we can verify it doesn't crash
        metrics = llm.get_performance_metrics()
        self.assertEqual(metrics["cache_misses"], 105)

    def test_context_affects_cache_key(self):
        """Test that relevant context affects cache key"""
        # Same command with different stable context
        context1 = {"last_app": "Chrome", "language": "en"}
        context2 = {"last_app": "Safari", "language": "en"}

        result1 = self.llm.analyze_command("click", context1)
        result2 = self.llm.analyze_command("click", context2)

        metrics = self.llm.get_performance_metrics()

        # Should be two cache misses (different context)
        self.assertEqual(metrics["cache_misses"], 2)
        self.assertEqual(metrics["cache_hits"], 0)

    def test_unstable_context_ignored(self):
        """Test that unstable context doesn't affect cache key"""
        # Same command with different unstable context
        context1 = {"last_app": "Chrome", "timestamp": "2024-01-01"}
        context2 = {"last_app": "Chrome", "timestamp": "2024-01-02"}

        result1 = self.llm.analyze_command("click", context1)
        result2 = self.llm.analyze_command("click", context2)

        metrics = self.llm.get_performance_metrics()

        # Should be one cache miss and one hit (timestamp ignored)
        self.assertEqual(metrics["cache_misses"], 1)
        self.assertEqual(metrics["cache_hits"], 1)


class TestOCREngineOptimization(unittest.TestCase):
    """Test OCR Engine optimization features"""

    @unittest.skip("Tesseract backend no longer supported - native engines used instead")
    def test_performance_metrics_tracking(self):
        """Test OCR performance metrics are tracked"""
        pass

    @unittest.skip("Tesseract backend no longer supported - native engines used instead")
    def test_async_processing_available(self):
        """Test async OCR processing is available"""
        pass

    @unittest.skip("Tesseract backend no longer supported - native engines used instead")
    def test_batch_processing(self):
        """Test batch OCR processing"""
        pass

    @unittest.skip("Tesseract backend no longer supported - native engines used instead")
    def test_reset_metrics(self):
        """Test OCR metrics can be reset"""
        pass

    @unittest.skip("Tesseract backend no longer supported - native engines used instead")
    def test_shutdown_cleanup(self):
        """Test OCR engine can be shut down cleanly"""
        pass


class TestScreenshotEngineOptimization(unittest.TestCase):
    """Test Screenshot Engine optimization features"""

    @patch("janus.vision.screenshot_engine.pyautogui")
    def test_performance_metrics_tracking(self, mock_pyautogui):
        """Test screenshot performance metrics are tracked"""
        from PIL import Image

        from janus.vision.screenshot_engine import ScreenshotEngine

        # Mock screenshot
        mock_pyautogui.screenshot.return_value = Image.new("RGB", (100, 100))

        engine = ScreenshotEngine(optimize_quality=True)

        screenshot = engine.capture_screen()

        metrics = engine.get_performance_metrics()

        self.assertEqual(metrics["total_captures"], 1)
        self.assertGreater(metrics["total_time"], 0)
        self.assertGreater(metrics["average_time"], 0)

    @patch("janus.vision.screenshot_engine.pyautogui")
    def test_optimized_compression(self, mock_pyautogui):
        """Test optimized image compression settings"""
        from PIL import Image

        from janus.vision.screenshot_engine import ScreenshotEngine

        mock_pyautogui.screenshot.return_value = Image.new("RGB", (100, 100))

        engine = ScreenshotEngine(optimize_quality=True)
        img = Image.new("RGB", (100, 100))

        # Test PNG optimization
        png_bytes = engine.get_screenshot_bytes(img, format="PNG")
        self.assertIsInstance(png_bytes, bytes)

        # Test JPEG optimization
        jpeg_bytes = engine.get_screenshot_bytes(img, format="JPEG")
        self.assertIsInstance(jpeg_bytes, bytes)

    @patch("janus.vision.screenshot_engine.pyautogui")
    def test_reset_metrics(self, mock_pyautogui):
        """Test screenshot metrics can be reset"""
        from PIL import Image

        from janus.vision.screenshot_engine import ScreenshotEngine

        mock_pyautogui.screenshot.return_value = Image.new("RGB", (100, 100))

        engine = ScreenshotEngine()
        engine.capture_screen()

        metrics1 = engine.get_performance_metrics()
        self.assertEqual(metrics1["total_captures"], 1)

        engine.reset_metrics()

        metrics2 = engine.get_performance_metrics()
        self.assertEqual(metrics2["total_captures"], 0)


if __name__ == "__main__":
    unittest.main()
