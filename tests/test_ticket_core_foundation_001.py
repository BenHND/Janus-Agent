"""
Unit tests for TICKET CORE-FOUNDATION-001 - Strict Action Contract

Tests the strict {module, action, args} contract enforcement in ActionCoordinator:
1. Valid actions with proper module/action are routed correctly
2. Invalid actions without module are rejected
3. Unknown modules trigger validation errors
4. Unknown actions trigger validation errors
5. Re-ask mechanism works (errors added to history for LLM to see)

DoD:
- {"module":"system","action":"open_application","args":{"app_name":"Safari"}} routes to SystemAgent
- {"action":"open_application","args":...} without module is rejected
- Unknown module/action triggers re-ask
"""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from janus.runtime.core.action_coordinator import ActionCoordinator
from janus.runtime.core.agent_registry import AgentRegistry
from janus.runtime.core.contracts import Intent


class TestStrictActionContract(unittest.TestCase):
    """Test strict action contract validation in ActionCoordinator"""
    
    def setUp(self):
        """Set up test environment"""
        self.registry = AgentRegistry()
        
        # Register mock SystemAgent
        self.mock_system_agent = MagicMock()
        self.mock_system_agent.is_v3 = True
        async def mock_system_execute(action, args, context):
            return {
                "status": "success",
                "message": f"Executed {action}",
                "data": {"action": action, "args": args}
            }
        self.mock_system_agent.execute = mock_system_execute
        self.registry.register("system", self.mock_system_agent)
        
        # Register mock BrowserAgent
        self.mock_browser_agent = MagicMock()
        self.mock_browser_agent.is_v3 = True
        async def mock_browser_execute(action, args, context):
            return {
                "status": "success",
                "message": f"Browser executed {action}",
                "data": {"action": action, "args": args}
            }
        self.mock_browser_agent.execute = mock_browser_execute
        self.registry.register("browser", self.mock_browser_agent)
        
        self.coordinator = ActionCoordinator(
            agent_registry=self.registry,
            max_iterations=5
        )
    
    def test_parse_valid_action_with_module(self):
        """Test parsing valid action with module, action, and args"""
        response = json.dumps({
            "module": "system",
            "action": "open_application",
            "args": {"app_name": "Safari"},
            "reasoning": "Opening Safari as requested"
        })
        
        result = self.coordinator._parse_response(response)
        
        self.assertEqual(result["module"], "system")
        self.assertEqual(result["action"], "open_application")
        self.assertEqual(result["args"], {"app_name": "Safari"})
        self.assertEqual(result["reasoning"], "Opening Safari as requested")
        self.assertNotIn("error", result)
    
    def test_parse_rejects_action_without_module(self):
        """Test that action without module field is rejected (DoD requirement)"""
        response = json.dumps({
            "action": "open_application",
            "args": {"app_name": "Safari"}
        })
        
        result = self.coordinator._parse_response(response)
        
        self.assertEqual(result["action"], "error")
        self.assertEqual(result["error_type"], "invalid_action_schema")
        self.assertIn("Missing required field 'module'", result["error"])
    
    def test_parse_rejects_action_without_action_field(self):
        """Test that response without action field is rejected"""
        response = json.dumps({
            "module": "system",
            "args": {"app_name": "Safari"}
        })
        
        result = self.coordinator._parse_response(response)
        
        self.assertEqual(result["action"], "error")
        self.assertEqual(result["error_type"], "invalid_action_schema")
        self.assertIn("Missing required field 'action'", result["error"])
    
    def test_parse_rejects_unknown_module(self):
        """Test that unknown module triggers validation error"""
        response = json.dumps({
            "module": "nonexistent_module",
            "action": "some_action",
            "args": {}
        })
        
        result = self.coordinator._parse_response(response)
        
        self.assertEqual(result["action"], "error")
        self.assertEqual(result["error_type"], "unknown_module")
        self.assertIn("Invalid module", result["error"])
    
    def test_parse_rejects_unknown_action(self):
        """Test that unknown action for valid module triggers validation error"""
        response = json.dumps({
            "module": "system",
            "action": "nonexistent_action",
            "args": {}
        })
        
        result = self.coordinator._parse_response(response)
        
        self.assertEqual(result["action"], "error")
        self.assertEqual(result["error_type"], "unknown_action")
        self.assertIn("Invalid action", result["error"])
    
    def test_parse_rejects_invalid_json(self):
        """Test that invalid JSON triggers error"""
        response = "not valid json {"
        
        result = self.coordinator._parse_response(response)
        
        self.assertEqual(result["action"], "error")
        self.assertEqual(result["error_type"], "invalid_json")
    
    def test_parse_accepts_done_action(self):
        """Test that 'done' action is always accepted"""
        response = json.dumps({
            "module": "system",
            "action": "done",
            "args": {}
        })
        
        result = self.coordinator._parse_response(response)
        
        self.assertEqual(result["action"], "done")
        self.assertNotIn("error", result)
    
    def test_act_routes_to_correct_agent(self):
        """Test that _act routes action to correct agent without module deduction (DoD requirement)"""
        action_plan = {
            "module": "system",
            "action": "open_application",
            "args": {"app_name": "Safari"},
            "reasoning": "Test"
        }
        
        result = asyncio.run(self.coordinator._act(
            action_plan,
            memory={},
            start_time=0,
            system_state={}
        ))
        
        # Verify action was successful and routed to SystemAgent
        self.assertTrue(result.success)
        self.assertEqual(result.action_type, "system.open_application")
        self.assertIn("Executed", result.message)
    
    def test_act_no_module_deduction_from_action_name(self):
        """Test that we NO LONGER deduce module from action name with underscore"""
        # This action has an underscore but module MUST be explicitly provided
        action_plan = {
            "module": "system",  # Explicitly system
            "action": "open_application",  # Has underscore, but we don't split it
            "args": {"app_name": "Safari"}
        }
        
        result = asyncio.run(self.coordinator._act(
            action_plan,
            memory={},
            start_time=0,
            system_state={}
        ))
        
        # Should route to SystemAgent (not "open" agent)
        self.assertTrue(result.success)
        self.assertEqual(result.action_type, "system.open_application")
    
    def test_act_routes_browser_action(self):
        """Test routing browser module action"""
        action_plan = {
            "module": "browser",
            "action": "open_url",
            "args": {"url": "https://example.com"}
        }
        
        result = asyncio.run(self.coordinator._act(
            action_plan,
            memory={},
            start_time=0,
            system_state={}
        ))
        
        self.assertTrue(result.success)
        self.assertEqual(result.action_type, "browser.open_url")
    
    def test_execute_goal_with_valid_action(self):
        """Test full OODA loop with valid action"""
        # Mock reasoner to return valid action
        mock_reasoner = MagicMock()
        mock_reasoner.available = True
        mock_reasoner.run_inference.return_value = json.dumps({
            "module": "system",
            "action": "done",
            "args": {},
            "reasoning": "Goal achieved"
        })
        self.coordinator._reasoner = mock_reasoner
        
        # Mock system bridge
        with patch('janus.os.get_system_bridge') as mock_bridge:
            mock_bridge_instance = MagicMock()
            mock_bridge_instance.get_active_window.return_value = MagicMock(
                status=1, data={"window": MagicMock(app_name="Safari", title="Test")}
            )
            mock_bridge.return_value = mock_bridge_instance
            self.coordinator._system_bridge = mock_bridge_instance
            
            intent = Intent(action="open_app", confidence=0.9, parameters={"app_name": "Safari"})
            result = asyncio.run(self.coordinator.execute_goal(
                user_goal="Open Safari",
                intent=intent,
                session_id="test",
                request_id="test",
                language="en"
            ))
            
            self.assertTrue(result.success)
            self.assertEqual(len(result.action_results), 1)
            self.assertEqual(result.action_results[0].action_type, "done")
    
    def test_execute_goal_reask_on_invalid_action(self):
        """Test that invalid action triggers re-ask (added to history for next iteration)"""
        # Mock reasoner to return invalid action first, then valid
        mock_reasoner = MagicMock()
        mock_reasoner.available = True
        responses = [
            # First: invalid (missing module)
            json.dumps({
                "action": "open_application",
                "args": {"app_name": "Safari"}
            }),
            # Second: valid
            json.dumps({
                "module": "system",
                "action": "done",
                "args": {}
            })
        ]
        mock_reasoner.run_inference.side_effect = responses
        self.coordinator._reasoner = mock_reasoner
        
        # Mock system bridge
        with patch('janus.os.get_system_bridge') as mock_bridge:
            mock_bridge_instance = MagicMock()
            mock_bridge_instance.get_active_window.return_value = MagicMock(
                status=1, data={"window": MagicMock(app_name="Safari", title="Test")}
            )
            mock_bridge.return_value = mock_bridge_instance
            self.coordinator._system_bridge = mock_bridge_instance
            
            intent = Intent(action="open_app", confidence=0.9, parameters={"app_name": "Safari"})
            result = asyncio.run(self.coordinator.execute_goal(
                user_goal="Open Safari",
                intent=intent,
                session_id="test",
                request_id="test",
                language="en"
            ))
            
            # Should have 2 results: validation error + done
            self.assertEqual(len(result.action_results), 2)
            
            # First result should be validation error
            self.assertFalse(result.action_results[0].success)
            self.assertIn("validation_error", result.action_results[0].action_type)
            self.assertIn("Validation failed", result.action_results[0].message)
            
            # Second result should be done
            self.assertTrue(result.action_results[1].success)
            self.assertEqual(result.action_results[1].action_type, "done")
            
            # Reasoner should have been called twice
            self.assertEqual(mock_reasoner.run_inference.call_count, 2)


class TestActionContractValidation(unittest.TestCase):
    """Test validation functions from module_action_schema"""
    
    def test_validate_valid_system_open_application(self):
        """Test validation of system.open_application action"""
        from janus.runtime.core.module_action_schema import validate_action_step
        
        step = {
            "module": "system",
            "action": "open_application",
            "args": {"app_name": "Safari"}
        }
        
        is_valid, error = validate_action_step(step)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_validate_browser_open_url(self):
        """Test validation of browser.open_url action"""
        from janus.runtime.core.module_action_schema import validate_action_step
        
        step = {
            "module": "browser",
            "action": "open_url",
            "args": {"url": "https://example.com"}
        }
        
        is_valid, error = validate_action_step(step)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_validate_invalid_module(self):
        """Test validation rejects invalid module"""
        from janus.runtime.core.module_action_schema import validate_action_step
        
        step = {
            "module": "invalid_module",
            "action": "some_action",
            "args": {}
        }
        
        is_valid, error = validate_action_step(step)
        
        self.assertFalse(is_valid)
        self.assertIn("Invalid module", error)
    
    def test_validate_invalid_action(self):
        """Test validation rejects invalid action for module"""
        from janus.runtime.core.module_action_schema import validate_action_step
        
        step = {
            "module": "system",
            "action": "invalid_action",
            "args": {}
        }
        
        is_valid, error = validate_action_step(step)
        
        self.assertFalse(is_valid)
        self.assertIn("Invalid action", error)
    
    def test_validate_missing_required_param(self):
        """Test validation rejects missing required parameter"""
        from janus.runtime.core.module_action_schema import validate_action_step
        
        step = {
            "module": "system",
            "action": "open_application",
            "args": {}  # Missing required app_name
        }
        
        is_valid, error = validate_action_step(step)
        
        self.assertFalse(is_valid)
        self.assertIn("Missing required parameter", error)


if __name__ == "__main__":
    unittest.main()
