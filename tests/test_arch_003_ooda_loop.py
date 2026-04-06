"""
TICKET-ARCH-003: OODA Loop Tests

Tests for the new execute_dynamic_loop method in AgentExecutorV3.
This tests the dynamic ReAct/OODA loop execution model.
"""
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from janus.constants import IntentType
from janus.runtime.core.agent_executor_v3 import AgentExecutorV3
from janus.runtime.core.contracts import Intent


class TestOODALoopExecution(unittest.TestCase):
    """Test the OODA loop execution in AgentExecutorV3"""
    
    def setUp(self):
        """Set up test environment"""
        self.executor = AgentExecutorV3(
            enable_vision_recovery=True,
            enable_replanning=True,
            max_retries=1
        )
    
    def test_execute_dynamic_loop_completes_with_done_action(self):
        """Test: OODA loop completes when LLM returns 'done' action"""
        # Mock the reasoner to return a done action immediately
        mock_reasoner = MagicMock()
        mock_reasoner.decide_next_action = MagicMock(return_value={
            "action": "done",
            "args": {},
            "reasoning": "Goal achieved"
        })
        
        # Patch the reasoner property
        with patch.object(self.executor, 'reasoner', mock_reasoner):
            # Create intent
            intent = Intent(
                intent_type=IntentType.QUERY_INFORMATION,
                raw_command="Find CEO of Acme Corp",
                confidence=0.9
            )
            
            # Run the OODA loop
            result = asyncio.run(self.executor.execute_dynamic_loop(
                user_goal="Find CEO of Acme Corp",
                intent=intent,
                session_id="test_session",
                request_id="test_request",
                max_iterations=10
            ))
            
            # Verify result
            self.assertTrue(result.success)
            self.assertEqual(len(result.results), 1)
            self.assertEqual(result.results[0].action_type, "done")
    
    def test_execute_dynamic_loop_respects_max_iterations(self):
        """Test: OODA loop stops at max_iterations"""
        # Mock the reasoner to never return 'done'
        mock_reasoner = MagicMock()
        mock_reasoner.decide_next_action = MagicMock(return_value={
            "action": "click",
            "args": {"element_id": "test"},
            "reasoning": "Clicking element"
        })
        
        # Mock the agent registry to always succeed
        mock_registry = AsyncMock()
        mock_registry.execute_async = AsyncMock(return_value={
            "status": "success",
            "output": "clicked"
        })
        
        # Patch reasoner and agent registry, mock vision capture
        with patch.object(self.executor, 'reasoner', mock_reasoner), \
             patch.object(self.executor, 'agent_registry', mock_registry), \
             patch.object(
                self.executor,
                '_capture_visual_context',
                new_callable=AsyncMock,
                return_value="[]"
             ), patch.object(
                self.executor,
                '_capture_system_state',
                new_callable=AsyncMock,
                return_value={"active_app": "Test"}
             ):
            # Create intent
            intent = Intent(
                intent_type=IntentType.EXECUTE_ACTION,
                raw_command="Test command",
                confidence=0.9
            )
            
            # Run the OODA loop with low max_iterations
            result = asyncio.run(self.executor.execute_dynamic_loop(
                user_goal="Test goal",
                intent=intent,
                session_id="test_session",
                request_id="test_request",
                max_iterations=3
            ))
            
            # Verify it stopped at max iterations
            self.assertFalse(result.success)
            # Should have 3 action results + 1 max_iterations error
            self.assertEqual(len(result.results), 4)
            self.assertEqual(result.results[-1].action_type, "max_iterations")
    
    def test_execute_dynamic_loop_continues_on_error(self):
        """Test: OODA loop continues execution when an action fails"""
        # Mock reasoner to return click -> done
        call_count = [0]
        
        def decide_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {
                    "action": "click",
                    "args": {"element_id": "test"},
                    "reasoning": "Clicking element"
                }
            else:
                return {
                    "action": "done",
                    "args": {},
                    "reasoning": "Goal achieved"
                }
        
        mock_reasoner = MagicMock()
        mock_reasoner.decide_next_action = MagicMock(side_effect=decide_side_effect)
        
        # Mock agent registry: first call fails, second doesn't matter
        mock_registry = AsyncMock()
        mock_registry.execute_async = AsyncMock(return_value={
            "status": "error",
            "error": "Element not found"
        })
        
        # Patch reasoner and agent registry, mock vision capture
        with patch.object(self.executor, 'reasoner', mock_reasoner), \
             patch.object(self.executor, 'agent_registry', mock_registry), \
             patch.object(
                self.executor,
                '_capture_visual_context',
                new_callable=AsyncMock,
                return_value="[]"
             ), patch.object(
                self.executor,
                '_capture_system_state',
                new_callable=AsyncMock,
                return_value={"active_app": "Test"}
             ):
            # Create intent
            intent = Intent(
                intent_type=IntentType.EXECUTE_ACTION,
                raw_command="Test command",
                confidence=0.9
            )
            
            # Run the OODA loop
            result = asyncio.run(self.executor.execute_dynamic_loop(
                user_goal="Test goal",
                intent=intent,
                session_id="test_session",
                request_id="test_request",
                max_iterations=10
            ))
            
            # Verify execution continued after error
            self.assertTrue(result.success)  # Should succeed because of "done"
            self.assertEqual(len(result.results), 2)  # click (failed) + done
            self.assertFalse(result.results[0].success)  # First action failed
            self.assertEqual(result.results[1].action_type, "done")  # But continued to done
    
    def test_execute_dynamic_loop_stores_error_in_memory(self):
        """Test: OODA loop stores errors in memory for LLM visibility"""
        # Mock reasoner to see errors in memory
        memory_snapshots = []
        
        def decide_side_effect(*args, **kwargs):
            # Capture memory state
            memory_snapshots.append(kwargs.get('memory', {}).copy())
            
            if len(memory_snapshots) == 1:
                # First iteration: try click
                return {
                    "action": "click",
                    "args": {"element_id": "test"},
                    "reasoning": "Clicking element"
                }
            else:
                # Second iteration: should see error in memory
                return {
                    "action": "done",
                    "args": {},
                    "reasoning": "Saw error, stopping"
                }
        
        mock_reasoner = MagicMock()
        mock_reasoner.decide_next_action = MagicMock(side_effect=decide_side_effect)
        
        # Mock agent registry to fail
        mock_registry = AsyncMock()
        mock_registry.execute_async = AsyncMock(return_value={
            "status": "error",
            "error": "Element not found"
        })
        
        # Patch reasoner and agent registry, mock vision capture
        with patch.object(self.executor, 'reasoner', mock_reasoner), \
             patch.object(self.executor, 'agent_registry', mock_registry), \
             patch.object(
                self.executor,
                '_capture_visual_context',
                new_callable=AsyncMock,
                return_value="[]"
             ), patch.object(
                self.executor,
                '_capture_system_state',
                new_callable=AsyncMock,
                return_value={"active_app": "Test"}
             ):
            # Create intent
            intent = Intent(
                intent_type=IntentType.EXECUTE_ACTION,
                raw_command="Test command",
                confidence=0.9
            )
            
            # Run the OODA loop
            result = asyncio.run(self.executor.execute_dynamic_loop(
                user_goal="Test goal",
                intent=intent,
                session_id="test_session",
                request_id="test_request",
                max_iterations=10
            ))
            
            # Verify memory was passed to reasoner in second iteration
            self.assertEqual(len(memory_snapshots), 2)
            # Second iteration should have last_error in memory
            self.assertIn("last_error", memory_snapshots[1])
            self.assertEqual(memory_snapshots[1]["last_error"], "Element not found")


class TestOODALoopHelperMethods(unittest.TestCase):
    """Test helper methods for OODA loop"""
    
    def setUp(self):
        """Set up test environment"""
        self.executor = AgentExecutorV3()
    
    def test_capture_system_state(self):
        """Test: _capture_system_state returns expected structure"""
        context = {
            "app": "Safari",
            "surface": "browser",
            "url": "https://example.com",
            "domain": "example.com"
        }
        
        result = asyncio.run(self.executor._capture_system_state(context))
        
        self.assertIn("active_app", result)
        self.assertIn("surface", result)
        self.assertIn("url", result)
        self.assertIn("domain", result)
        self.assertIn("clipboard", result)
        
        self.assertEqual(result["active_app"], "Safari")
        self.assertEqual(result["url"], "https://example.com")
    
    def test_execute_dynamic_action_unknown_action(self):
        """Test: _execute_dynamic_action handles unknown action types"""
        action = {
            "action": "unknown_action",
            "args": {},
            "reasoning": "Test"
        }
        
        result = asyncio.run(self.executor._execute_dynamic_action(
            action=action,
            context={},
            memory={},
            start_time=0
        ))
        
        self.assertFalse(result.success)
        self.assertIn("Unknown action type", result.error)


if __name__ == '__main__':
    unittest.main()
