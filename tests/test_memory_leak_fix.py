"""
Tests for memory leak fix in vision cache - TICKET B1
These tests reproduce the memory leak and validate the fix with TTLCache
"""
import sys
import time
import unittest

from PIL import Image

from janus.vision.cache import OCRCache


class TestMemoryLeakFix(unittest.TestCase):
    """Test memory leak fix with TTLCache"""

    def setUp(self):
        """Set up test fixtures"""
        self.cache = OCRCache(ttl=2, max_size=10)
        self.test_images = []

        # Create multiple test images
        for i in range(20):
            img = Image.new("RGB", (100 + i, 100), color=(i * 10, 100, 150))
            self.test_images.append(img)

    def test_ttl_cache_automatic_expiration(self):
        """Test that TTLCache automatically expires old entries"""
        # Add entries
        for i in range(5):
            self.cache.set(self.test_images[i], f"result_{i}")

        # Verify entries exist
        for i in range(5):
            self.assertIsNotNone(self.cache.get(self.test_images[i]))

        # Wait for TTL expiration
        time.sleep(2.5)

        # All entries should be expired
        for i in range(5):
            result = self.cache.get(self.test_images[i])
            self.assertIsNone(result, f"Entry {i} should be expired")

    def test_memory_leak_reproduction(self):
        """Reproduce memory leak by continuously adding entries"""
        # This test simulates the memory leak scenario
        # Without TTLCache, old entries would accumulate

        initial_cache_size = len(self.cache._cache)

        # Add many entries without accessing old ones
        for i in range(50):
            img = Image.new("RGB", (100 + i, 100), color=(i, i, i))
            self.cache.set(img, f"result_{i}")

            # Small delay to allow TTL to work
            if i % 10 == 0:
                time.sleep(0.1)

        # With TTLCache, cache should not grow unbounded
        # Should respect max_size limit
        final_cache_size = len(self.cache._cache)
        self.assertLessEqual(
            final_cache_size, self.cache.max_size, "Cache should not exceed max_size"
        )

    def test_ttl_cache_respects_max_size(self):
        """Test that cache respects max_size even with TTL"""
        # Fill cache beyond max_size rapidly
        for i in range(20):
            self.cache.set(self.test_images[i], f"result_{i}")

        # Cache size should not exceed max_size
        self.assertLessEqual(len(self.cache._cache), self.cache.max_size)

    def test_memory_usage_stays_bounded(self):
        """Test that memory usage stays bounded over time"""
        # Track approximate memory by cache size
        cache_sizes = []

        # Add entries over time
        for iteration in range(5):
            # Add batch of entries
            for i in range(10):
                idx = iteration * 10 + i
                img = Image.new("RGB", (100, 100), color=(idx, idx, idx))
                self.cache.set(img, f"result_{iteration}_{i}")

            cache_sizes.append(len(self.cache._cache))

            # Wait for some entries to expire
            time.sleep(0.5)

        # Cache size should stabilize and not grow unbounded
        max_cache_size = max(cache_sizes)
        self.assertLessEqual(
            max_cache_size, self.cache.max_size * 1.1, "Cache size should stay near max_size limit"
        )

    def test_ttl_cache_with_frequent_access(self):
        """Test TTL cache behavior with frequently accessed entries"""
        # Add entries
        for i in range(5):
            self.cache.set(self.test_images[i], f"result_{i}")

        # Keep accessing some entries
        for _ in range(3):
            time.sleep(0.8)
            # Access some entries to keep them alive
            for i in range(3):
                result = self.cache.get(self.test_images[i])
                # With TTLCache, entries may still expire based on creation time
                # not access time (depends on implementation)

        # After total of 2.4 seconds, entries should be expired (TTL=2)
        time.sleep(0.5)

        # All entries should be expired now
        for i in range(5):
            result = self.cache.get(self.test_images[i])
            self.assertIsNone(result)

    def test_cache_clear_frees_memory(self):
        """Test that clearing cache properly frees memory"""
        # Fill cache
        for i in range(10):
            self.cache.set(self.test_images[i], f"result_{i}")

        self.assertGreater(len(self.cache._cache), 0)

        # Clear cache
        self.cache.clear()

        # Cache should be empty
        self.assertEqual(len(self.cache._cache), 0)
        self.assertEqual(len(self.cache._access_times), 0)

    def test_no_memory_leak_with_perceptual_hash(self):
        """Test that perceptual hash doesn't cause memory leak"""
        cache_with_phash = OCRCache(ttl=2, max_size=10, use_perceptual_hash=True)

        # Add many entries
        for i in range(30):
            img = Image.new("RGB", (100, 100), color=(i * 8, i * 8, i * 8))
            cache_with_phash.set(img, f"result_{i}")

        # Perceptual hash dict should also respect max_size
        self.assertLessEqual(len(cache_with_phash._perceptual_hashes), cache_with_phash.max_size)

        # Wait for TTL
        time.sleep(2.5)

        # Access to trigger cleanup
        test_img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        cache_with_phash.get(test_img)

        # Old entries should be expired
        self.assertLessEqual(len(cache_with_phash._cache), cache_with_phash.max_size)


class TestTTLCacheIntegration(unittest.TestCase):
    """Test integration of TTLCache with existing cache API"""

    def setUp(self):
        """Set up test fixtures"""
        self.cache = OCRCache(ttl=3, max_size=5)
        self.test_image = Image.new("RGB", (100, 100), color="white")

    def test_api_compatibility_set_get(self):
        """Test that existing API still works with TTLCache"""
        result = {"text": "Test", "confidence": 95.0}

        # Set and get should work as before
        self.cache.set(self.test_image, result)
        cached = self.cache.get(self.test_image)

        self.assertEqual(cached, result)

    def test_api_compatibility_with_query(self):
        """Test that query parameter still works"""
        result1 = {"matches": ["Button"]}
        result2 = {"matches": ["Link"]}

        self.cache.set(self.test_image, result1, query="Button")
        self.cache.set(self.test_image, result2, query="Link")

        cached1 = self.cache.get(self.test_image, query="Button")
        cached2 = self.cache.get(self.test_image, query="Link")

        self.assertEqual(cached1, result1)
        self.assertEqual(cached2, result2)

    def test_api_compatibility_clear(self):
        """Test that clear() still works"""
        self.cache.set(self.test_image, "result")
        self.assertIsNotNone(self.cache.get(self.test_image))

        self.cache.clear()
        self.assertIsNone(self.cache.get(self.test_image))

    def test_api_compatibility_stats(self):
        """Test that get_stats() still works"""
        self.cache.set(self.test_image, "result")
        stats = self.cache.get_stats()

        self.assertIn("size", stats)
        self.assertIn("max_size", stats)
        self.assertIn("ttl", stats)


class TestElementCacheMemoryLeak(unittest.TestCase):
    """Test that ElementCache also doesn't have memory leaks"""

    def test_element_cache_bounded_growth(self):
        """Test that ElementCache also stays bounded"""
        from janus.vision.cache import ElementCache

        cache = ElementCache(ttl=2, max_size=10)

        # Add many entries
        for i in range(30):
            cache.set(f"Element_{i}", (i * 10, i * 10))

        # Should not exceed max_size
        self.assertLessEqual(len(cache._cache), cache.max_size)

        # Wait for TTL
        time.sleep(2.5)

        # Access to trigger cleanup
        cache.get("NonExistent")

        # Old entries should be expired
        cache.set("New", (0, 0))
        self.assertLessEqual(len(cache._cache), cache.max_size)


if __name__ == "__main__":
    unittest.main()
