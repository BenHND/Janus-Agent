"""
TICKET-406 - Pre-Flight Checks (Validation Sémantique Pré-Exécution)

Tests for pre-execution validation that ensures:
1. Browser/App: Actions execute in the correct frontmost application
2. Files: File existence is verified before open operations
3. Navigation: Duplicate URL navigation is detected and optimized
4. Heavy Apps: Dynamic timeouts are applied for slow-starting applications

Test Scenario (from ticket):
"Ouvre Teams et clique sur Chat"
- If Teams takes 5s to open, executor waits for Teams to be ready
- Before clicking, validates that Teams is frontmost
- Does not click blindly after 500ms
"""

import asyncio
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Mock missing modules if not available
for module_name in ['pyautogui', 'PIL', 'PIL.Image', 'cv2', 'numpy']:
    if module_name not in sys.modules:
        sys.modules[module_name] = MagicMock()

from janus.runtime.core.agent_executor_v3 import AgentExecutorV3
from janus.runtime.core.agent_registry import AgentRegistry
from janus.runtime.core.contracts import Intent


def async_test(coro):
    """Decorator to run async tests"""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper


class TestPreFlightValidation(unittest.TestCase):
    """Test pre-flight validation rules"""
    
    def setUp(self):
        """Set up test environment"""
        self.executor = AgentExecutorV3()
    
    @async_test
    async def test_validate_preconditions_browser_action_not_frontmost(self):
        """Test: Browser action fails when app not frontmost"""
        context = {
            "app": "Safari",
            "surface": "browser",
            "url": "https://youtube.com",
            "domain": "youtube.com"
        }
        
        with patch('janus.os.foreground_app_sync.get_active_app', return_value="Finder"):
            result = await self.executor._validate_action_preconditions(
                module="browser",
                action="click",
                args={"element": "button"},
                context=context
            )
        
        # Should fail validation because Safari is not frontmost
        self.assertFalse(result["valid"])
        self.assertIn("not frontmost", result["error"])
        self.assertEqual(result["recovery_action"]["type"], "focus_app")
        self.assertEqual(result["recovery_action"]["app_name"], "Safari")
    
    @async_test
    async def test_validate_preconditions_browser_action_frontmost(self):
        """Test: Browser action succeeds when app is frontmost"""
        context = {
            "app": "Safari",
            "surface": "browser",
            "url": "https://youtube.com",
            "domain": "youtube.com"
        }
        
        with patch('janus.os.foreground_app_sync.get_active_app', return_value="Safari"):
            result = await self.executor._validate_action_preconditions(
                module="browser",
                action="click",
                args={"element": "button"},
                context=context
            )
        
        # Should pass validation
        self.assertTrue(result["valid"])
        self.assertIsNone(result["error"])
    
    @async_test
    async def test_validate_preconditions_file_not_exists(self):
        """Test: File operation fails when file doesn't exist"""
        context = {"app": "Finder"}
        
        result = await self.executor._validate_action_preconditions(
            module="files",
            action="open_file",
            args={"path": "/nonexistent/file.txt"},
            context=context
        )
        
        # Should fail validation
        self.assertFalse(result["valid"])
        self.assertIn("does not exist", result["error"])
        self.assertIsNone(result["recovery_action"])  # No recovery possible
    
    @async_test
    async def test_validate_preconditions_file_exists(self):
        """Test: File operation succeeds when file exists"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            context = {"app": "Finder"}
            
            result = await self.executor._validate_action_preconditions(
                module="files",
                action="open_file",
                args={"path": tmp_path},
                context=context
            )
            
            # Should pass validation
            self.assertTrue(result["valid"])
            self.assertIsNone(result["error"])
        finally:
            # Clean up
            os.unlink(tmp_path)
    
    @async_test
    async def test_validate_preconditions_duplicate_url_navigation(self):
        """Test: Duplicate URL navigation detected as no-op"""
        context = {
            "app": "Safari",
            "url": "https://youtube.com",
            "domain": "youtube.com"
        }
        
        result = await self.executor._validate_action_preconditions(
            module="browser",
            action="open_url",
            args={"url": "https://youtube.com"},
            context=context
        )
        
        # Should detect no-op
        self.assertTrue(result["valid"])
        self.assertEqual(result["recovery_action"]["type"], "no_op")
    
    @async_test
    async def test_validate_preconditions_heavy_app_timeout(self):
        """Test: Heavy application gets dynamic timeout"""
        context = {}
        
        result = await self.executor._validate_action_preconditions(
            module="system",
            action="open_application",
            args={"app_name": "Microsoft Teams"},
            context=context
        )
        
        # Should suggest extended wait time
        self.assertTrue(result["valid"])
        self.assertIsNotNone(result["suggested_wait"])
        self.assertGreaterEqual(result["suggested_wait"], 3.0)  # Teams needs at least 3s
    
    @async_test
    async def test_validate_preconditions_regular_app_no_timeout(self):
        """Test: Regular application gets no special timeout"""
        context = {}
        
        result = await self.executor._validate_action_preconditions(
            module="system",
            action="open_application",
            args={"app_name": "Calculator"},
            context=context
        )
        
        # Should not suggest wait time for simple apps
        self.assertTrue(result["valid"])
        self.assertIsNone(result["suggested_wait"])


class TestPreFlightRecovery(unittest.TestCase):
    """Test automatic recovery from precondition failures"""
    
    def setUp(self):
        """Set up test environment"""
        self.executor = AgentExecutorV3()
        self.executor.agent_registry = MagicMock(spec=AgentRegistry)
    
    @async_test
    async def test_recovery_focus_app_success(self):
        """Test: Successfully recover by focusing app"""
        precondition_result = {
            "valid": False,
            "error": "App not frontmost",
            "recovery_action": {
                "type": "focus_app",
                "app_name": "Safari"
            }
        }
        context = {"app": "Safari"}
        
        # Mock successful app focus
        self.executor.agent_registry.execute_async = AsyncMock(
            return_value={"status": "success"}
        )
        
        result = await self.executor._attempt_precondition_recovery(
            precondition_result, context
        )
        
        self.assertTrue(result)
        self.executor.agent_registry.execute_async.assert_called_once()
    
    @async_test
    async def test_recovery_focus_app_failure(self):
        """Test: Recovery fails if app cannot be focused"""
        precondition_result = {
            "valid": False,
            "error": "App not frontmost",
            "recovery_action": {
                "type": "focus_app",
                "app_name": "Safari"
            }
        }
        context = {"app": "Safari"}
        
        # Mock failed app focus
        self.executor.agent_registry.execute_async = AsyncMock(
            return_value={"status": "error", "error": "App not found"}
        )
        
        result = await self.executor._attempt_precondition_recovery(
            precondition_result, context
        )
        
        self.assertFalse(result)
    
    @async_test
    async def test_recovery_no_op(self):
        """Test: No-op recovery always succeeds"""
        precondition_result = {
            "valid": True,
            "recovery_action": {
                "type": "no_op"
            }
        }
        context = {}
        
        result = await self.executor._attempt_precondition_recovery(
            precondition_result, context
        )
        
        self.assertTrue(result)
    
    @async_test
    async def test_recovery_no_action(self):
        """Test: Recovery fails when no recovery action available"""
        precondition_result = {
            "valid": False,
            "error": "File not found",
            "recovery_action": None
        }
        context = {}
        
        result = await self.executor._attempt_precondition_recovery(
            precondition_result, context
        )
        
        self.assertFalse(result)


class TestPreFlightIntegration(unittest.TestCase):
    """Test pre-flight checks in full execution flow"""
    
    @async_test
    async def test_execution_with_preflight_success(self):
        """Test: Execution proceeds when pre-flight checks pass"""
        executor = AgentExecutorV3()
        executor.agent_registry = MagicMock(spec=AgentRegistry)
        
        # Mock successful validation and execution
        executor.agent_registry.execute_async = AsyncMock(
            return_value={
                "status": "success",
                "output": "Action completed"
            }
        )
        
        with patch('janus.os.foreground_app_sync.get_active_app', return_value="Safari"):
            steps = [
                {
                    "module": "browser",
                    "action": "search",
                    "args": {"query": "test"},
                    "context": {"app": "Safari", "surface": "browser"}
                }
            ]
            
            intent = Intent(
                action="search",
                confidence=0.9,
                raw_command="Search for test"
            )
            
            result = await executor.execute_plan(
                steps=steps,
                intent=intent,
                session_id="test-session",
                request_id="test-request"
            )
            
            # Should succeed
            self.assertTrue(result.success)
    
    @async_test
    async def test_execution_with_preflight_failure_no_recovery(self):
        """Test: Execution fails when pre-flight checks fail and no recovery"""
        executor = AgentExecutorV3()
        executor.agent_registry = MagicMock(spec=AgentRegistry)
        
        steps = [
            {
                "module": "files",
                "action": "open_file",
                "args": {"path": "/nonexistent/file.txt"},
                "context": {}
            }
        ]
        
        intent = Intent(
            action="open_file",
            confidence=0.9,
            raw_command="Open file"
        )
        
        result = await executor.execute_plan(
            steps=steps,
            intent=intent,
            session_id="test-session",
            request_id="test-request"
        )
        
        # Should fail due to file not existing
        self.assertFalse(result.success)
        self.assertEqual(len(result.action_results), 1)
        self.assertIn("does not exist", result.action_results[0].error)
    
    @async_test
    async def test_execution_with_dynamic_timeout(self):
        """Test: Heavy app launch includes dynamic timeout"""
        executor = AgentExecutorV3()
        executor.agent_registry = MagicMock(spec=AgentRegistry)
        
        # Track sleep calls to verify dynamic timeout
        sleep_times = []
        original_sleep = asyncio.sleep
        
        async def mock_sleep(duration):
            sleep_times.append(duration)
            # Don't actually sleep in tests
            await original_sleep(0)
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            executor.agent_registry.execute_async = AsyncMock(
                return_value={"status": "success"}
            )
            
            steps = [
                {
                    "module": "system",
                    "action": "open_application",
                    "args": {"app_name": "Microsoft Teams"},
                    "context": {}
                }
            ]
            
            intent = Intent(
                action="open_application",
                confidence=0.9,
                raw_command="Open Teams"
            )
            
            result = await executor.execute_plan(
                steps=steps,
                intent=intent,
                session_id="test-session",
                request_id="test-request"
            )
            
            # Should succeed and have applied dynamic timeout
            self.assertTrue(result.success)
            # Verify that a significant sleep was called (Teams timeout)
            self.assertTrue(any(t >= 3.0 for t in sleep_times), 
                          f"Expected sleep >= 3.0s for Teams, got: {sleep_times}")


class TestPreFlightScenarios(unittest.TestCase):
    """Test specific scenarios from TICKET-406"""
    
    @async_test
    async def test_scenario_teams_click_chat(self):
        """
        Test: "Ouvre Teams et clique sur Chat"
        
        If Teams takes 5s to open, executor waits for Teams to be ready
        before attempting to click, not clicking blindly after 500ms.
        """
        executor = AgentExecutorV3()
        executor.agent_registry = MagicMock(spec=AgentRegistry)
        
        # Track execution timing
        execution_times = []
        
        async def mock_execute(module, action, args, context):
            execution_times.append(time.perf_counter())
            return {"status": "success"}
        
        executor.agent_registry.execute_async = mock_execute
        
        with patch('janus.os.foreground_app_sync.get_active_app', return_value="Microsoft Teams"):
            steps = [
                {
                    "module": "system",
                    "action": "open_application",
                    "args": {"app_name": "Microsoft Teams"},
                    "context": {}
                },
                {
                    "module": "ui",
                    "action": "click",
                    "args": {"element": "Chat"},
                    "context": {"app": "Microsoft Teams"}
                }
            ]
            
            intent = Intent(
                action="click",
                confidence=0.9,
                raw_command="Ouvre Teams et clique sur Chat"
            )
            
            start_time = time.perf_counter()
            
            result = await executor.execute_plan(
                steps=steps,
                intent=intent,
                session_id="test-session",
                request_id="test-request"
            )
            
            end_time = time.perf_counter()
            total_duration = end_time - start_time
            
            # Should succeed
            self.assertTrue(result.success)
            
            # Should have applied Teams timeout (5s minimum)
            # Verify total duration includes the dynamic timeout
            self.assertGreaterEqual(total_duration, 5.0, 
                                  "Should have waited at least 5s for Teams to be ready")
            
            # Should have executed both open_application and click
            self.assertGreaterEqual(len(execution_times), 2, 
                                  "Should have executed both open_application and click")


if __name__ == "__main__":
    unittest.main()
