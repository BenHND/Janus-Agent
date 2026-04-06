"""Tests for RateLimiter (P2 Feature)"""

import os
import tempfile
import time
import unittest
from pathlib import Path

from janus.safety.rate_limiter import RateLimiter, RateLimitConfig, RateLimitExceeded


class TestRateLimiter(unittest.TestCase):
    """Test rate limiting functionality"""
    
    def setUp(self):
        """Create temp database for tests"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db_path = self.test_db.name
        self.limiter = RateLimiter(db_path=self.db_path)
    
    def tearDown(self):
        """Clean up temp database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_configure_rate_limit(self):
        """Test configuring a rate limit"""
        self.limiter.configure("test", max_requests=10, time_window_seconds=60)
        
        # Should have tokens available
        remaining = self.limiter.get_remaining("test")
        self.assertEqual(remaining, 10.0)
    
    def test_consume_tokens(self):
        """Test consuming tokens"""
        self.limiter.configure("test", max_requests=5, time_window_seconds=60)
        
        # Consume 3 tokens
        self.assertTrue(self.limiter.check_and_consume("test", 3.0))
        remaining = self.limiter.get_remaining("test")
        self.assertAlmostEqual(remaining, 2.0, places=1)
    
    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded"""
        self.limiter.configure("test", max_requests=3, time_window_seconds=60)
        
        # Consume all tokens
        self.assertTrue(self.limiter.check_and_consume("test", 3.0))
        
        # Next request should fail
        self.assertFalse(self.limiter.check_and_consume("test", 1.0))
    
    def test_token_refill(self):
        """Test token refill over time"""
        # Configure 10 requests per 2 seconds (5 tokens/second)
        self.limiter.configure("test", max_requests=10, time_window_seconds=2.0)
        
        # Consume all tokens
        self.assertTrue(self.limiter.check_and_consume("test", 10.0))
        remaining = self.limiter.get_remaining("test")
        self.assertAlmostEqual(remaining, 0.0, places=1)
        
        # Wait 1 second (should refill ~5 tokens)
        time.sleep(1.1)
        remaining = self.limiter.get_remaining("test")
        self.assertGreater(remaining, 4.0)
        self.assertLess(remaining, 7.0)
    
    def test_burst_allowance(self):
        """Test burst allowance"""
        # 5 requests/min with 3 burst
        self.limiter.configure("test", max_requests=5, time_window_seconds=60, burst_allowance=3)
        
        # Should have 8 tokens (5 + 3)
        remaining = self.limiter.get_remaining("test")
        self.assertEqual(remaining, 8.0)
        
        # Consume all
        self.assertTrue(self.limiter.check_and_consume("test", 8.0))
        remaining = self.limiter.get_remaining("test")
        self.assertAlmostEqual(remaining, 0.0, places=1)
    
    def test_reset(self):
        """Test resetting rate limit"""
        self.limiter.configure("test", max_requests=5, time_window_seconds=60)
        
        # Consume tokens
        self.limiter.check_and_consume("test", 3.0)
        remaining = self.limiter.get_remaining("test")
        self.assertAlmostEqual(remaining, 2.0, places=1)
        
        # Reset
        self.limiter.reset("test")
        self.assertEqual(self.limiter.get_remaining("test"), 5.0)
    
    def test_multiple_scopes(self):
        """Test multiple rate limit scopes"""
        self.limiter.configure("global", max_requests=100, time_window_seconds=60)
        self.limiter.configure("email", max_requests=10, time_window_seconds=60)
        
        # Both scopes should be independent
        self.assertTrue(self.limiter.check_and_consume("global", 50.0))
        self.assertTrue(self.limiter.check_and_consume("email", 5.0))
        
        self.assertAlmostEqual(self.limiter.get_remaining("global"), 50.0, places=1)
        self.assertAlmostEqual(self.limiter.get_remaining("email"), 5.0, places=1)
    
    def test_no_config_allows_all(self):
        """Test that unconfigured scope allows all requests"""
        # Should allow request without configuration
        self.assertTrue(self.limiter.check_and_consume("unconfigured", 100.0))
    
    def test_persistence(self):
        """Test state persistence across instances"""
        # Configure and consume
        self.limiter.configure("test", max_requests=10, time_window_seconds=60)
        self.limiter.check_and_consume("test", 7.0)
        
        # Create new instance with same database
        limiter2 = RateLimiter(db_path=self.db_path)
        limiter2.configure("test", max_requests=10, time_window_seconds=60)
        
        # Should have same remaining tokens (approximately)
        remaining = limiter2.get_remaining("test")
        self.assertGreater(remaining, 2.0)
        self.assertLess(remaining, 4.0)
    
    def test_get_stats(self):
        """Test getting rate limit statistics"""
        self.limiter.configure("test", max_requests=10, time_window_seconds=60)
        
        # Make some requests
        for _ in range(5):
            self.limiter.check_and_consume("test", 1.0)
        
        # Get stats
        stats = self.limiter.get_stats("test", hours=1)
        self.assertEqual(stats["scope"], "test")
        self.assertEqual(stats["total_events"], 5)
        self.assertEqual(stats["exceeded_count"], 0)


if __name__ == "__main__":
    unittest.main()
