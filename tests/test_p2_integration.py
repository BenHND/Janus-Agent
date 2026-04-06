"""
Integration Tests for P2 Features

Tests the integration of rate limiting and dry-run mode.
Lightweight tests that don't require full Janus dependencies.
"""

import asyncio
import tempfile
import os
import unittest

from janus.safety.rate_limiter import RateLimiter
from janus.safety.safe_queue import SafeQueue


class MockAgent:
    """Mock agent for testing dry-run functionality"""
    
    def __init__(self):
        self.agent_name = "test"
        self.is_v3 = True
        self.execute_calls = []
    
    async def execute(self, action, args, context, dry_run=False):
        """Mock execute method with dry_run support"""
        self.execute_calls.append({
            "action": action,
            "args": args,
            "dry_run": dry_run
        })
        
        if dry_run:
            return {
                "status": "success",
                "data": {"preview": True, "action": action},
                "dry_run": True,
                "reversible": action in ["create_file", "schedule_task"],
                "message": f"[DRY-RUN] Would execute {action}"
            }
        
        return {
            "status": "success",
            "data": {"executed": True, "action": action},
            "message": f"Executed {action}"
        }


class TestDryRunIntegration(unittest.TestCase):
    """Test dry-run mode functionality"""
    
    def test_agent_dry_run_execution(self):
        """Test that mock agent respects dry_run flag"""
        async def test():
            agent = MockAgent()
            
            # Execute without dry_run
            result = await agent.execute("test_action", {"arg1": "value1"}, {}, dry_run=False)
            self.assertEqual(result["status"], "success")
            self.assertFalse(result.get("dry_run", False))
            self.assertEqual(len(agent.execute_calls), 1)
            
            # Execute with dry_run
            result = await agent.execute("test_action", {"arg1": "value1"}, {}, dry_run=True)
            self.assertEqual(result["status"], "success")
            self.assertTrue(result.get("dry_run", False))
            self.assertIn("DRY-RUN", result["message"])
            self.assertEqual(len(agent.execute_calls), 2)
        
        asyncio.run(test())
    
    def test_dry_run_reversibility_detection(self):
        """Test that dry-run mode returns reversibility information"""
        async def test():
            agent = MockAgent()
            
            # Test reversible action
            result = await agent.execute("create_file", {}, {}, dry_run=True)
            self.assertTrue(result.get("reversible", False))
            
            # Test non-reversible action
            result = await agent.execute("send_email", {}, {}, dry_run=True)
            self.assertFalse(result.get("reversible", False))
        
        asyncio.run(test())


class TestRateLimitingIntegration(unittest.TestCase):
    """Test rate limiting integration scenarios"""
    
    def setUp(self):
        """Create test fixtures"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db_path = self.test_db.name
    
    def tearDown(self):
        """Cleanup"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_action_execution_with_rate_limiting(self):
        """Test simulated action execution with rate limits"""
        limiter = RateLimiter(db_path=self.db_path)
        
        # Configure tight rate limit
        limiter.configure("global", max_requests=3, time_window_seconds=60)
        
        # Simulate action execution loop
        actions_executed = 0
        actions_rate_limited = 0
        
        for i in range(10):
            if limiter.check_and_consume("global"):
                actions_executed += 1
            else:
                actions_rate_limited += 1
        
        # Should execute 3, rate-limit 7
        self.assertEqual(actions_executed, 3)
        self.assertEqual(actions_rate_limited, 7)
    
    def test_multi_scope_rate_limiting(self):
        """Test rate limiting with multiple scopes (global + module)"""
        limiter = RateLimiter(db_path=self.db_path)
        
        # Configure different limits
        limiter.configure("global", max_requests=10, time_window_seconds=60)
        limiter.configure("agent:email", max_requests=2, time_window_seconds=60)
        limiter.configure("agent:browser", max_requests=5, time_window_seconds=60)
        
        # Email actions - limited to 2
        email_executed = 0
        for i in range(5):
            # Check both global and module limit
            if limiter.check_and_consume("global") and limiter.check_and_consume("agent:email"):
                email_executed += 1
        
        self.assertEqual(email_executed, 2)  # Email limit hit first
        
        # Browser actions - limited to 5
        browser_executed = 0
        for i in range(7):
            if limiter.check_and_consume("global") and limiter.check_and_consume("agent:browser"):
                browser_executed += 1
        
        self.assertEqual(browser_executed, 5)  # Browser limit hit


class TestOfflineQueueIntegration(unittest.TestCase):
    """Test offline queue integration scenarios"""
    
    def setUp(self):
        """Create test fixtures"""
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.db_path = self.test_db.name
    
    def tearDown(self):
        """Cleanup"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_queue_when_rate_limited(self):
        """Test queueing actions when rate limit is exceeded"""
        limiter = RateLimiter(db_path=self.db_path + ".limiter")
        queue = SafeQueue(db_path=self.db_path)
        
        # Configure tight limit
        limiter.configure("test", max_requests=2, time_window_seconds=60)
        
        # Simulate execution with queueing on rate limit
        executed = []
        queued = []
        
        for i in range(5):
            action_data = {"index": i, "action": "test"}
            
            if limiter.check_and_consume("test"):
                executed.append(i)
            else:
                # Queue for later
                queue.enqueue("test.action", action_data, priority=1)
                queued.append(i)
        
        self.assertEqual(len(executed), 2)
        self.assertEqual(len(queued), 3)
        self.assertEqual(queue.get_pending_count(), 3)
        
        # Cleanup
        if os.path.exists(self.db_path + ".limiter"):
            os.unlink(self.db_path + ".limiter")
    
    def test_combined_dry_run_and_queue(self):
        """Test combining dry-run with offline queue"""
        queue = SafeQueue(db_path=self.db_path)
        
        # Enqueue actions with metadata indicating they were dry-run previewed
        for i in range(3):
            queue.enqueue(
                "email.send",
                {
                    "to": f"user{i}@example.com",
                    "subject": "Test",
                    "dry_run_previewed": True  # Metadata
                },
                priority=1
            )
        
        self.assertEqual(queue.get_pending_count(), 3)
        
        # Register processor
        processed = []
        def processor(data):
            processed.append(data["to"])
            return True
        
        queue.register_processor("email.send", processor)
        queue.process_pending()
        
        self.assertEqual(len(processed), 3)
        self.assertEqual(queue.get_pending_count(), 0)


if __name__ == "__main__":
    unittest.main()
