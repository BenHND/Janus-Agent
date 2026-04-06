"""
Tests for ReplanningService

TICKET-REFACTOR-003: Tests for extracted replanning functionality
"""

import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch, Mock

from janus.services.replanning_service import ReplanningService
from janus.runtime.core.contracts import ActionResult, ExecutionResult, Intent


def async_test(coro):
    """Decorator to run async tests"""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


class TestReplanningService(unittest.TestCase):
    """Test ReplanningService functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_validator = MagicMock()
        self.service = ReplanningService(validator_agent=self.mock_validator)
    
    def test_initialization_no_reasoner(self):
        """Test: Service initializes without pre-configured reasoner"""
        service = ReplanningService()
        self.assertIsNone(service._reasoner)
    
    def test_initialization_with_reasoner(self):
        """Test: Service accepts pre-configured reasoner"""
        mock_reasoner = MagicMock()
        service = ReplanningService(reasoner=mock_reasoner)
        self.assertEqual(service._reasoner, mock_reasoner)
    
    @async_test
    async def test_replanning_without_reasoner(self):
        """Test: Replanning fails gracefully when reasoner unavailable"""
        service = ReplanningService(validator_agent=self.mock_validator)
        # Prevent lazy loading
        service._reasoner = None
        
        failed_step = {"module": "browser", "action": "navigate", "args": {"url": "test.com"}}
        error = "Navigation failed"
        context = {"app": "Safari"}
        executed_steps = []
        intent = Intent(action="test_action", confidence=0.95, raw_command="test command")
        result = ExecutionResult(intent=intent, success=True, session_id="test", request_id="test")
        
        execute_callback = AsyncMock()
        update_callback = MagicMock()
        
        with patch.object(ReplanningService, 'reasoner', property(lambda self: None)):
            success = await service.attempt_replanning(
                failed_step, error, context, executed_steps, result,
                execute_callback, update_callback
            )
        
        self.assertFalse(success)
    
    @async_test
    async def test_replanning_without_validator(self):
        """Test: Replanning fails when validator not available"""
        mock_reasoner = MagicMock()
        service = ReplanningService(reasoner=mock_reasoner, validator_agent=None)
        
        failed_step = {"module": "browser", "action": "navigate", "args": {"url": "test.com"}}
        error = "Navigation failed"
        context = {"app": "Safari"}
        executed_steps = []
        intent = Intent(action="test_action", confidence=0.95, raw_command="test command")
        result = ExecutionResult(intent=intent, success=True, session_id="test", request_id="test")
        
        execute_callback = AsyncMock()
        update_callback = MagicMock()
        
        success = await service.attempt_replanning(
            failed_step, error, context, executed_steps, result,
            execute_callback, update_callback
        )
        
        self.assertFalse(success)
    
    @async_test
    async def test_replanning_reasoner_error(self):
        """Test: Replanning handles reasoner errors gracefully"""
        mock_reasoner = MagicMock()
        mock_reasoner.replan.return_value = {"error": "Reasoner failed"}
        
        service = ReplanningService(reasoner=mock_reasoner, validator_agent=self.mock_validator)
        
        failed_step = {"module": "browser", "action": "navigate", "args": {"url": "test.com"}}
        error = "Navigation failed"
        context = {"app": "Safari"}
        executed_steps = []
        intent = Intent(action="test_action", confidence=0.95, raw_command="test command")
        result = ExecutionResult(intent=intent, success=True, session_id="test", request_id="test")
        
        execute_callback = AsyncMock()
        update_callback = MagicMock()
        
        success = await service.attempt_replanning(
            failed_step, error, context, executed_steps, result,
            execute_callback, update_callback
        )
        
        self.assertFalse(success)
    
    @async_test
    async def test_replanning_empty_steps(self):
        """Test: Replanning fails when no alternative steps generated"""
        mock_reasoner = MagicMock()
        mock_reasoner.replan.return_value = {
            "steps": [],
            "explanation": "No alternatives found"
        }
        
        service = ReplanningService(reasoner=mock_reasoner, validator_agent=self.mock_validator)
        
        failed_step = {"module": "browser", "action": "navigate", "args": {"url": "test.com"}}
        error = "Navigation failed"
        context = {"app": "Safari"}
        executed_steps = []
        intent = Intent(action="test_action", confidence=0.95, raw_command="test command")
        result = ExecutionResult(intent=intent, success=True, session_id="test", request_id="test")
        
        execute_callback = AsyncMock()
        update_callback = MagicMock()
        
        success = await service.attempt_replanning(
            failed_step, error, context, executed_steps, result,
            execute_callback, update_callback
        )
        
        self.assertFalse(success)
    
    @async_test
    async def test_replanning_success(self):
        """Test: Replanning succeeds with valid alternative steps"""
        mock_reasoner = MagicMock()
        mock_reasoner.replan.return_value = {
            "steps": [
                {"module": "browser", "action": "refresh", "args": {}, "context": {}},
                {"module": "browser", "action": "navigate", "args": {"url": "test.com"}, "context": {}}
            ],
            "explanation": "Retry with refresh"
        }
        
        self.mock_validator.validate_step.return_value = {
            "valid": True,
            "step": {"module": "browser", "action": "refresh", "args": {}, "context": {}}
        }
        
        service = ReplanningService(reasoner=mock_reasoner, validator_agent=self.mock_validator)
        
        failed_step = {"module": "browser", "action": "navigate", "args": {"url": "test.com"}}
        error = "Navigation failed"
        context = {"app": "Safari"}
        executed_steps = []
        intent = Intent(action="test_action", confidence=0.95, raw_command="test command")
        result = ExecutionResult(intent=intent, success=True, session_id="test", request_id="test")
        
        # Mock successful execution
        mock_action_result = ActionResult(
            action_type="browser.refresh",
            success=True,
            data={}
        )
        execute_callback = AsyncMock(return_value=mock_action_result)
        update_callback = MagicMock()
        
        success = await service.attempt_replanning(
            failed_step, error, context, executed_steps, result,
            execute_callback, update_callback
        )
        
        self.assertTrue(success)
        self.assertTrue(result.success)
        # At least one step with source="replan" should be in executed_steps
        self.assertTrue(any(step.get("source") == "replan" for step in executed_steps))
    
    @async_test
    async def test_replanning_invalid_steps_skipped(self):
        """Test: Invalid replanned steps are skipped"""
        mock_reasoner = MagicMock()
        mock_reasoner.replan.return_value = {
            "steps": [
                {"module": "invalid", "action": "bad", "args": {}, "context": {}},
                {"module": "browser", "action": "refresh", "args": {}, "context": {}}
            ],
            "explanation": "Mixed valid/invalid steps"
        }
        
        # First step invalid, second valid
        self.mock_validator.validate_step.side_effect = [
            {"valid": False, "errors": ["Invalid module"]},
            {"valid": True, "step": {"module": "browser", "action": "refresh", "args": {}, "context": {}}}
        ]
        
        service = ReplanningService(reasoner=mock_reasoner, validator_agent=self.mock_validator)
        
        failed_step = {"module": "browser", "action": "navigate", "args": {"url": "test.com"}}
        error = "Navigation failed"
        context = {"app": "Safari"}
        executed_steps = []
        intent = Intent(action="test_action", confidence=0.95, raw_command="test command")
        result = ExecutionResult(intent=intent, success=True, session_id="test", request_id="test")
        
        # Mock successful execution for valid step
        mock_action_result = ActionResult(
            action_type="browser.refresh",
            success=True,
            data={}
        )
        execute_callback = AsyncMock(return_value=mock_action_result)
        update_callback = MagicMock()
        
        success = await service.attempt_replanning(
            failed_step, error, context, executed_steps, result,
            execute_callback, update_callback
        )
        
        self.assertTrue(success)
        # Only one step should have been executed (the valid one)
        self.assertEqual(len(executed_steps), 1)
    
    @async_test
    async def test_replanning_context_updates(self):
        """Test: Context is properly updated from replanned steps"""
        mock_reasoner = MagicMock()
        mock_reasoner.replan.return_value = {
            "steps": [
                {
                    "module": "browser",
                    "action": "navigate",
                    "args": {"url": "test.com"},
                    "context": {"domain": "test.com"}
                }
            ],
            "explanation": "Alternative navigation"
        }
        
        self.mock_validator.validate_step.return_value = {
            "valid": True,
            "step": {
                "module": "browser",
                "action": "navigate",
                "args": {"url": "test.com"},
                "context": {"domain": "test.com"}
            }
        }
        
        service = ReplanningService(reasoner=mock_reasoner, validator_agent=self.mock_validator)
        
        failed_step = {"module": "browser", "action": "navigate", "args": {"url": "old.com"}}
        error = "Navigation failed"
        context = {"app": "Safari", "domain": "old.com"}
        executed_steps = []
        intent = Intent(action="test_action", confidence=0.95, raw_command="test command")
        result = ExecutionResult(intent=intent, success=True, session_id="test", request_id="test")
        
        # Mock successful execution with context updates
        mock_action_result = ActionResult(
            action_type="browser.navigate",
            success=True,
            data={"context_updates": {"url": "https://test.com"}}
        )
        execute_callback = AsyncMock(return_value=mock_action_result)
        update_callback = MagicMock()
        
        success = await service.attempt_replanning(
            failed_step, error, context, executed_steps, result,
            execute_callback, update_callback
        )
        
        self.assertTrue(success)
        # Verify context update callback was called
        self.assertGreaterEqual(update_callback.call_count, 1)


if __name__ == '__main__':
    unittest.main()
