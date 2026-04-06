"""Tests for SafeQueue (P2 Feature - Offline Mode)"""

import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from janus.safety.safe_queue import SafeQueue, QueueStatus, QueuedAction


class TestSafeQueue(unittest.TestCase):
    """Test offline mode queue functionality"""
    
    def setUp(self):
        """Create temp database for tests"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db_path = self.test_db.name
        self.queue = SafeQueue(db_path=self.db_path, auto_purge=False)
    
    def tearDown(self):
        """Clean up temp database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_enqueue_action(self):
        """Test enqueuing an action"""
        action_id = self.queue.enqueue(
            action_type="email.send",
            action_data={"to": "test@example.com", "subject": "Test"},
            priority=1
        )
        
        self.assertIsInstance(action_id, int)
        self.assertGreater(action_id, 0)
    
    def test_queue_with_priority(self):
        """Test queue respects priority ordering"""
        # Enqueue with different priorities
        id1 = self.queue.enqueue("test", {"msg": "low"}, priority=5)
        id2 = self.queue.enqueue("test", {"msg": "high"}, priority=1)
        id3 = self.queue.enqueue("test", {"msg": "medium"}, priority=3)
        
        # Mock processor that just returns True
        processed = []
        def processor(data):
            processed.append(data["msg"])
            return True
        
        self.queue.register_processor("test", processor)
        self.queue.process_pending(max_actions=3)
        
        # Should process in priority order: high, medium, low
        self.assertEqual(processed, ["high", "medium", "low"])
    
    def test_delayed_execution(self):
        """Test delayed action execution"""
        # Enqueue with 2 second delay
        self.queue.enqueue(
            "test",
            {"msg": "delayed"},
            delay_seconds=2.0
        )
        
        # Should not process immediately
        def processor(data):
            return True
        
        self.queue.register_processor("test", processor)
        stats = self.queue.process_pending()
        self.assertEqual(stats["processed"], 0)
        
        # Wait and try again
        time.sleep(2.1)
        stats = self.queue.process_pending()
        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["succeeded"], 1)
    
    def test_action_expiration(self):
        """Test action expiration"""
        # Enqueue with short expiration
        self.queue.enqueue(
            "test",
            {"msg": "expires"},
            expires_in_hours=0.0001  # ~0.36 seconds
        )
        
        # Wait for expiration
        time.sleep(0.5)
        
        # Purge expired
        queue2 = SafeQueue(db_path=self.db_path, auto_purge=True)
        
        # Should have 0 pending (expired)
        self.assertEqual(queue2.get_pending_count(), 0)
    
    def test_retry_on_failure(self):
        """Test retry logic on failure"""
        self.queue.enqueue("test", {"msg": "retry"}, max_retries=2)
        
        attempt = [0]
        def processor(data):
            attempt[0] += 1
            return attempt[0] > 2  # Fail first 2 times, succeed on 3rd
        
        self.queue.register_processor("test", processor)
        
        # First attempt - should fail and schedule retry
        stats = self.queue.process_pending()
        self.assertEqual(attempt[0], 1)
        self.assertEqual(stats["failed"], 0)  # Not permanently failed yet
        
        # Note: Retry is scheduled for future, so we'd need to wait
        # This is tested in integration, just checking it doesn't crash
    
    def test_max_retries_exceeded(self):
        """Test max retries handling"""
        self.queue.enqueue("test", {"msg": "fail"}, max_retries=0)
        
        def processor(data):
            return False  # Always fail
        
        self.queue.register_processor("test", processor)
        
        # Should fail immediately (no retries)
        stats = self.queue.process_pending()
        self.assertEqual(stats["failed"], 1)
    
    def test_processor_exception(self):
        """Test handling processor exceptions"""
        self.queue.enqueue("test", {"msg": "exception"}, max_retries=1)
        
        def processor(data):
            raise ValueError("Test exception")
        
        self.queue.register_processor("test", processor)
        
        # Should catch exception and schedule retry
        stats = self.queue.process_pending()
        self.assertEqual(stats["processed"], 1)
        # Should not crash
    
    def test_cancel_action(self):
        """Test cancelling a queued action"""
        action_id = self.queue.enqueue("test", {"msg": "cancel"})
        
        # Cancel it
        self.assertTrue(self.queue.cancel(action_id))
        
        # Should not be processed
        def processor(data):
            return True
        
        self.queue.register_processor("test", processor)
        stats = self.queue.process_pending()
        self.assertEqual(stats["processed"], 0)
    
    def test_queue_stats(self):
        """Test queue statistics"""
        # Add various actions
        self.queue.enqueue("test", {"msg": "1"})
        self.queue.enqueue("test", {"msg": "2"})
        
        # Process one successfully
        def processor(data):
            return True
        
        self.queue.register_processor("test", processor)
        self.queue.process_pending(max_actions=1)
        
        # Check stats
        stats = self.queue.get_stats()
        self.assertEqual(stats["pending"], 1)
        self.assertEqual(stats["completed"], 1)
    
    def test_purge_completed(self):
        """Test purging completed actions"""
        # Add and process action
        self.queue.enqueue("test", {"msg": "purge"})
        
        def processor(data):
            return True
        
        self.queue.register_processor("test", processor)
        self.queue.process_pending()
        
        # Purge completed (with 0 hours threshold for immediate purge)
        self.queue.purge_completed(older_than_hours=0)
        
        # Should have 0 completed
        stats = self.queue.get_stats()
        self.assertEqual(stats["completed"], 0)
    
    def test_no_processor_registered(self):
        """Test behavior when no processor is registered"""
        self.queue.enqueue("unknown", {"msg": "test"})
        
        # Should skip action
        stats = self.queue.process_pending()
        self.assertEqual(stats["skipped"], 1)
    
    def test_max_actions_limit(self):
        """Test max_actions parameter"""
        # Enqueue 5 actions
        for i in range(5):
            self.queue.enqueue("test", {"msg": i})
        
        def processor(data):
            return True
        
        self.queue.register_processor("test", processor)
        
        # Process only 2
        stats = self.queue.process_pending(max_actions=2)
        self.assertEqual(stats["processed"], 2)
        self.assertEqual(stats["succeeded"], 2)
        
        # Should have 3 remaining
        self.assertEqual(self.queue.get_pending_count(), 3)


if __name__ == "__main__":
    unittest.main()
