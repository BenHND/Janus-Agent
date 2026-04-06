"""
OCR Cache - Caching layer for OCR results
Ticket 6.3: Latency Optimization
TICKET-013: Enhanced with perceptual hashing for semantic similarity
TICKET B1: Fixed memory leak using TTLCache with automatic expiration
"""

import hashlib
import io
import time
from typing import Any, Dict, List, Optional, Tuple

from cachetools import TTLCache
from PIL import Image


class OCRCache:
    """
    Cache for OCR results to improve performance in repetitive workflows
    Caches results based on image hash and search query
    TICKET-013: Enhanced with perceptual hashing for similar image matching
    """

    def __init__(self, ttl: int = 300, max_size: int = 100, use_perceptual_hash: bool = True):
        """
        Initialize OCR cache

        Args:
            ttl: Time-to-live for cache entries in seconds (default: 5 minutes)
            max_size: Maximum number of entries to cache
            use_perceptual_hash: Use perceptual hashing for similar image matching (TICKET-013)
        """
        self.ttl = ttl
        self.max_size = max_size
        self.use_perceptual_hash = use_perceptual_hash

        # TICKET B1: Use TTLCache for automatic expiration (fixes memory leak)
        self._cache = TTLCache(maxsize=max_size, ttl=ttl)
        self._access_times: Dict[str, float] = {}  # Track access for stats
        self._perceptual_hashes: Dict[str, str] = (
            {}
        )  # TICKET-013: Map exact hash to perceptual hash

    def _compute_perceptual_hash(self, image: Image.Image) -> str:
        """
        Compute perceptual hash (pHash) for similar image matching

        Args:
            image: PIL Image

        Returns:
            Perceptual hash string
        """
        # Convert to grayscale and resize to 8x8 for perceptual hashing
        gray = image.convert("L")
        small = gray.resize((8, 8), Image.LANCZOS)

        # Get pixel data
        pixels = list(small.getdata())

        # Compute average
        avg = sum(pixels) / len(pixels)

        # Create hash based on pixels above/below average
        bits = "".join("1" if p > avg else "0" for p in pixels)

        # Convert to hex
        phash = hex(int(bits, 2))[2:].zfill(16)
        return phash

    def _hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        Compute Hamming distance between two hashes

        Args:
            hash1: First hash
            hash2: Second hash

        Returns:
            Hamming distance (number of differing bits)
        """
        if len(hash1) != len(hash2):
            return float("inf")

        # Convert hex to binary and compare
        int1 = int(hash1, 16)
        int2 = int(hash2, 16)
        xor = int1 ^ int2

        # Count set bits
        distance = bin(xor).count("1")
        return distance

    def _compute_image_hash(self, image: Image.Image) -> str:
        """
        Compute hash of image for cache key

        Args:
            image: PIL Image to hash

        Returns:
            Hash string
        """
        # Convert image to bytes
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        img_bytes = img_bytes.getvalue()

        # Compute SHA256 hash
        return hashlib.sha256(img_bytes).hexdigest()

    def _make_cache_key(self, image: Image.Image, query: Optional[str] = None) -> str:
        """
        Create cache key from image and optional query

        Args:
            image: PIL Image
            query: Optional search query

        Returns:
            Cache key string
        """
        img_hash = self._compute_image_hash(image)
        if query:
            query_hash = hashlib.md5(query.encode()).hexdigest()
            return f"{img_hash}:{query_hash}"
        return img_hash

    def _evict_expired(self):
        """
        Remove expired entries from cache
        TICKET B1: TTLCache handles expiration automatically,
        but we clean up auxiliary data structures
        """
        # TTLCache automatically removes expired entries
        # We need to clean up our auxiliary tracking dictionaries
        current_time = time.time()

        # Clean up perceptual hashes for keys no longer in cache
        keys_to_remove = [key for key in self._perceptual_hashes if key not in self._cache]
        for key in keys_to_remove:
            self._perceptual_hashes.pop(key, None)

        # Clean up access times based on TTL
        expired_keys = [
            key
            for key, timestamp in self._access_times.items()
            if current_time - timestamp > self.ttl or key not in self._cache
        ]
        for key in expired_keys:
            self._access_times.pop(key, None)

    def _evict_lru(self):
        """
        Remove least recently used entry if cache is full
        TICKET B1: TTLCache handles LRU eviction automatically,
        but we clean up auxiliary data structures
        """
        # TTLCache automatically handles size limit with LRU eviction
        # We just need to ensure our auxiliary structures stay in sync

        # Clean up perceptual hashes and access times for keys no longer in cache
        current_cache_keys = set(self._cache.keys())

        # Clean up perceptual hashes
        phash_keys_to_remove = [
            key for key in self._perceptual_hashes if key not in current_cache_keys
        ]
        for key in phash_keys_to_remove:
            self._perceptual_hashes.pop(key, None)

        # Clean up access times
        access_keys_to_remove = [key for key in self._access_times if key not in current_cache_keys]
        for key in access_keys_to_remove:
            self._access_times.pop(key, None)

    def _find_similar_cached_image(self, image: Image.Image, threshold: int = 10) -> Optional[str]:
        """
        Find a similar cached image using perceptual hashing (TICKET-013)

        Args:
            image: PIL Image to find similar match for
            threshold: Maximum Hamming distance for match (default: 10 out of 64 bits)

        Returns:
            Cache key of similar image or None if no match
        """
        if not self.use_perceptual_hash:
            return None

        phash = self._compute_perceptual_hash(image)

        # Find closest match
        best_match = None
        best_distance = threshold + 1

        for key, cached_phash in self._perceptual_hashes.items():
            distance = self._hamming_distance(phash, cached_phash)
            if distance < best_distance:
                best_distance = distance
                best_match = key

        return best_match if best_distance <= threshold else None

    def get(
        self, image: Image.Image, query: Optional[str] = None, use_similarity: bool = True
    ) -> Optional[Any]:
        """
        Get cached OCR result

        Args:
            image: PIL Image
            query: Optional search query
            use_similarity: Try to find similar images if exact match not found (TICKET-013)

        Returns:
            Cached result or None if not found/expired
        """
        # Clean up expired entries in auxiliary structures
        self._evict_expired()

        key = self._make_cache_key(image, query)

        # Try exact match first
        # TICKET B1: TTLCache automatically handles expiration
        if key in self._cache:
            # Update access time for stats
            self._access_times[key] = time.time()
            return self._cache[key]

        # TICKET-013: Try perceptual hash matching for similar images
        if use_similarity and self.use_perceptual_hash and query is None:
            similar_key = self._find_similar_cached_image(image)
            if similar_key and similar_key in self._cache:
                # Update access time
                self._access_times[similar_key] = time.time()
                return self._cache[similar_key]

        return None

    def set(self, image: Image.Image, result: Any, query: Optional[str] = None):
        """
        Cache OCR result

        Args:
            image: PIL Image
            result: OCR result to cache
            query: Optional search query
        """
        key = self._make_cache_key(image, query)
        current_time = time.time()

        # TICKET B1: Store result directly in TTLCache (it handles expiration)
        # Store in cache first, then TTLCache will handle eviction if needed
        self._cache[key] = result
        self._access_times[key] = current_time

        # TICKET-013: Compute and store perceptual hash after cache update
        # This ensures we only store phashes for items actually in the cache
        if self.use_perceptual_hash and query is None:
            self._perceptual_hashes[key] = self._compute_perceptual_hash(image)

        # Clean up auxiliary structures to stay in sync with TTLCache
        self._evict_lru()

    def clear(self):
        """Clear all cached entries"""
        self._cache.clear()
        self._access_times.clear()
        self._perceptual_hashes.clear()  # TICKET B1: Also clear perceptual hashes

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "oldest_entry": min(self._access_times.values()) if self._access_times else None,
            "newest_entry": max(self._access_times.values()) if self._access_times else None,
        }


class ElementCache:
    """
    Cache for UI element positions
    Caches element coordinates for repeated lookups
    """

    def __init__(self, ttl: int = 60, max_size: int = 50):
        """
        Initialize element position cache

        Args:
            ttl: Time-to-live for cache entries in seconds (default: 1 minute)
            max_size: Maximum number of entries to cache
        """
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}

    def _make_cache_key(self, element_text: str, context: Optional[str] = None) -> str:
        """
        Create cache key from element text and context

        Args:
            element_text: Text of the element
            context: Optional context (e.g., window title)

        Returns:
            Cache key string
        """
        if context:
            return f"{element_text}:{context}"
        return element_text

    def _evict_expired(self):
        """Remove expired entries from cache"""
        current_time = time.time()
        expired_keys = [
            key
            for key, timestamp in self._access_times.items()
            if current_time - timestamp > self.ttl
        ]

        for key in expired_keys:
            self._cache.pop(key, None)
            self._access_times.pop(key, None)

    def _evict_lru(self):
        """Remove least recently used entry if cache is full"""
        if len(self._cache) >= self.max_size:
            lru_key = min(self._access_times.items(), key=lambda x: x[1])[0]
            self._cache.pop(lru_key, None)
            self._access_times.pop(lru_key, None)

    def get(self, element_text: str, context: Optional[str] = None) -> Optional[Tuple[int, int]]:
        """
        Get cached element position

        Args:
            element_text: Text of the element
            context: Optional context

        Returns:
            Tuple of (x, y) coordinates or None if not found/expired
        """
        self._evict_expired()

        key = self._make_cache_key(element_text, context)

        if key in self._cache:
            self._access_times[key] = time.time()
            return self._cache[key]["position"]

        return None

    def set(self, element_text: str, position: Tuple[int, int], context: Optional[str] = None):
        """
        Cache element position

        Args:
            element_text: Text of the element
            position: Tuple of (x, y) coordinates
            context: Optional context
        """
        self._evict_lru()

        key = self._make_cache_key(element_text, context)
        current_time = time.time()

        self._cache[key] = {"position": position, "cached_at": current_time}
        self._access_times[key] = current_time

    def invalidate(self, element_text: Optional[str] = None):
        """
        Invalidate cache entries

        Args:
            element_text: If provided, only invalidate entries for this element.
                         If None, clear entire cache.
        """
        if element_text is None:
            self.clear()
        else:
            # Remove all entries starting with element_text
            keys_to_remove = [key for key in self._cache if key.startswith(element_text)]
            for key in keys_to_remove:
                self._cache.pop(key, None)
                self._access_times.pop(key, None)

    def clear(self):
        """Clear all cached entries"""
        self._cache.clear()
        self._access_times.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "oldest_entry": min(self._access_times.values()) if self._access_times else None,
            "newest_entry": max(self._access_times.values()) if self._access_times else None,
        }
