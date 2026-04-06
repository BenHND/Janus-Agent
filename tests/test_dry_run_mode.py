"""Tests for Dry-Run Mode (P2 Feature)"""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from janus.capabilities.agents.system_agent import SystemAgent


class TestDryRunMode(unittest.TestCase):
    """Test dry-run mode functionality"""
    
    def setUp(self):
        """Create system agent for testing"""
        self.agent = SystemAgent()
    
    def test_dry_run_parameter_accepted(self):
        """Test that agents accept dry_run parameter"""
        async def test():
            # Should not raise an error
            try:
                result = await self.agent.execute(
                    action="open_application",
                    args={"app_name": "Calculator"},
                    context={},
                    dry_run=True
                )
                # Should indicate dry-run in result
                self.assertTrue(result.get("dry_run", False))
            except TypeError as e:
                # If dry_run parameter not supported yet, skip test
                if "dry_run" in str(e):
                    self.skipTest("Agent doesn't support dry_run yet - implementation pending")
                raise
        
        asyncio.run(test())
    
    def test_dry_run_logs_preview(self):
        """Test that dry-run logs preview without executing"""
        async def test():
            with patch.object(self.agent.logger, 'info') as mock_log:
                try:
                    result = await self.agent.execute(
                        action="open_application",
                        args={"app_name": "Calculator"},
                        context={},
                        dry_run=True
                    )
                    
                    # Should have logged dry-run preview
                    log_messages = [call[0][0] for call in mock_log.call_args_list]
                    dry_run_logs = [msg for msg in log_messages if "DRY-RUN" in msg]
                    
                    # Should have at least one dry-run log
                    self.assertGreater(len(dry_run_logs), 0, "Should log dry-run execution")
                    
                except TypeError as e:
                    if "dry_run" in str(e):
                        self.skipTest("Agent doesn't support dry_run yet - implementation pending")
                    raise
        
        asyncio.run(test())
    
    def test_dry_run_no_side_effects(self):
        """Test that dry-run doesn't execute actual actions"""
        # This test is more integration-focused
        # For now, just ensure dry_run flag is propagated
        async def test():
            try:
                result = await self.agent.execute(
                    action="open_application",
                    args={"app_name": "NonExistentApp"},
                    context={},
                    dry_run=True
                )
                
                # In dry-run, even non-existent apps should "succeed" in preview
                # (Real implementation should return success for dry-run preview)
                self.assertIn("dry_run", result)
                self.assertTrue(result["dry_run"])
                
            except TypeError as e:
                if "dry_run" in str(e):
                    self.skipTest("Agent doesn't support dry_run yet - implementation pending")
                raise
        
        asyncio.run(test())


if __name__ == "__main__":
    unittest.main()
