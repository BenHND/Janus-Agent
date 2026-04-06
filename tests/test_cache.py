"""
Tests for OCR Cache (Ticket 6.3)
"""
import time
import unittest

from PIL import Image

from janus.vision.cache import ElementCache, OCRCache


class TestOCRCache(unittest.TestCase):
    """Test cases for OCR caching"""

    def setUp(self):
        """Set up test fixtures"""
        self.cache = OCRCache(ttl=2, max_size=5)
        # Create test image
        self.test_image = Image.new("RGB", (100, 100), color="white")

    def test_initialization(self):
        """Test cache initialization"""
        self.assertEqual(self.cache.ttl, 2)
        self.assertEqual(self.cache.max_size, 5)
        self.assertEqual(len(self.cache._cache), 0)

    def test_cache_set_and_get(self):
        """Test setting and getting cached values"""
        result = {"text": "Hello World", "confidence": 95.5}

        # Cache result
        self.cache.set(self.test_image, result)

        # Retrieve result
        cached = self.cache.get(self.test_image)
        self.assertEqual(cached, result)

    def test_cache_with_query(self):
        """Test caching with search query"""
        result1 = {"matches": ["Submit"]}
        result2 = {"matches": ["Cancel"]}

        # Cache results with different queries
        self.cache.set(self.test_image, result1, query="Submit")
        self.cache.set(self.test_image, result2, query="Cancel")

        # Retrieve results
        cached1 = self.cache.get(self.test_image, query="Submit")
        cached2 = self.cache.get(self.test_image, query="Cancel")

        self.assertEqual(cached1, result1)
        self.assertEqual(cached2, result2)

    def test_cache_miss(self):
        """Test cache miss"""
        # Create different image
        other_image = Image.new("RGB", (100, 100), color="black")

        # Should return None for uncached image
        result = self.cache.get(other_image)
        self.assertIsNone(result)

    def test_cache_expiration(self):
        """Test cache TTL expiration"""
        result = {"text": "Temporary"}

        # Cache result
        self.cache.set(self.test_image, result)

        # Should be cached
        cached = self.cache.get(self.test_image)
        self.assertEqual(cached, result)

        # Wait for expiration
        time.sleep(2.5)

        # Should be expired
        cached = self.cache.get(self.test_image)
        self.assertIsNone(cached)

    def test_cache_max_size(self):
        """Test cache size limit"""
        # Fill cache to max
        for i in range(6):
            img = Image.new("RGB", (100 + i, 100), color="white")
            self.cache.set(img, f"result_{i}")

        # Should not exceed max size
        self.assertLessEqual(len(self.cache._cache), self.cache.max_size)

    def test_cache_lru_eviction(self):
        """Test LRU eviction"""
        images = []

        # Fill cache
        for i in range(5):
            img = Image.new("RGB", (100 + i, 100), color="white")
            images.append(img)
            self.cache.set(img, f"result_{i}")

        # Access first image to make it recently used
        self.cache.get(images[0])

        # Add new image (should evict LRU, not recently used one)
        new_img = Image.new("RGB", (200, 100), color="white")
        self.cache.set(new_img, "new_result")

        # First image should still be cached (it was accessed)
        self.assertIsNotNone(self.cache.get(images[0]))

    def test_cache_clear(self):
        """Test clearing cache"""
        # Add some entries
        for i in range(3):
            img = Image.new("RGB", (100 + i, 100), color="white")
            self.cache.set(img, f"result_{i}")

        self.assertGreater(len(self.cache._cache), 0)

        # Clear cache
        self.cache.clear()

        self.assertEqual(len(self.cache._cache), 0)
        self.assertEqual(len(self.cache._access_times), 0)

    def test_cache_stats(self):
        """Test cache statistics"""
        # Add entries
        self.cache.set(self.test_image, "result1")

        stats = self.cache.get_stats()

        self.assertEqual(stats["size"], 1)
        self.assertEqual(stats["max_size"], 5)
        self.assertEqual(stats["ttl"], 2)
        self.assertIsNotNone(stats["oldest_entry"])
        self.assertIsNotNone(stats["newest_entry"])


class TestElementCache(unittest.TestCase):
    """Test cases for Element position caching"""

    def setUp(self):
        """Set up test fixtures"""
        self.cache = ElementCache(ttl=2, max_size=10)

    def test_initialization(self):
        """Test cache initialization"""
        self.assertEqual(self.cache.ttl, 2)
        self.assertEqual(self.cache.max_size, 10)

    def test_cache_element_position(self):
        """Test caching element position"""
        position = (100, 200)

        # Cache position
        self.cache.set("Submit Button", position)

        # Retrieve position
        cached = self.cache.get("Submit Button")
        self.assertEqual(cached, position)

    def test_cache_with_context(self):
        """Test caching with context"""
        position1 = (100, 200)
        position2 = (300, 400)

        # Cache same element in different contexts
        self.cache.set("OK", position1, context="Dialog1")
        self.cache.set("OK", position2, context="Dialog2")

        # Retrieve with context
        cached1 = self.cache.get("OK", context="Dialog1")
        cached2 = self.cache.get("OK", context="Dialog2")

        self.assertEqual(cached1, position1)
        self.assertEqual(cached2, position2)

    def test_element_cache_miss(self):
        """Test cache miss"""
        result = self.cache.get("NonExistent")
        self.assertIsNone(result)

    def test_element_expiration(self):
        """Test element cache expiration"""
        self.cache.set("Button", (100, 200))

        # Should be cached
        self.assertIsNotNone(self.cache.get("Button"))

        # Wait for expiration
        time.sleep(2.5)

        # Should be expired
        self.assertIsNone(self.cache.get("Button"))

    def test_invalidate_specific(self):
        """Test invalidating specific element"""
        self.cache.set("Button1", (100, 200))
        self.cache.set("Button2", (300, 400))

        # Invalidate Button1
        self.cache.invalidate("Button1")

        # Button1 should be gone, Button2 should remain
        self.assertIsNone(self.cache.get("Button1"))
        self.assertIsNotNone(self.cache.get("Button2"))

    def test_invalidate_all(self):
        """Test invalidating all elements"""
        self.cache.set("Button1", (100, 200))
        self.cache.set("Button2", (300, 400))

        # Invalidate all
        self.cache.invalidate()

        # Both should be gone
        self.assertIsNone(self.cache.get("Button1"))
        self.assertIsNone(self.cache.get("Button2"))

    def test_element_cache_stats(self):
        """Test element cache statistics"""
        self.cache.set("Button", (100, 200))

        stats = self.cache.get_stats()

        self.assertEqual(stats["size"], 1)
        self.assertEqual(stats["max_size"], 10)
        self.assertEqual(stats["ttl"], 2)


if __name__ == "__main__":
    unittest.main()
