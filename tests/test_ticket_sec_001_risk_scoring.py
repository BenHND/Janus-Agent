"""
Tests for TICKET-SEC-001: Risk Scoring & Human-in-the-Loop

Tests the risk scoring system and confirmation flow for high-risk actions.
"""

import unittest
from unittest.mock import MagicMock, patch

from janus.runtime.core.agent_registry import AgentRegistry
from janus.runtime.core.contracts import ConfirmationResponse, Intent, RequestConfirmation
from janus.runtime.core.execution_engine_v3 import ExecutionEngineV3
from janus.runtime.core.module_action_schema import RiskLevel, get_module
from janus.safety.validation.strict_action_validator import StrictActionValidator


class TestRiskLevelAssignment(unittest.TestCase):
    """Test that risk levels are properly assigned to actions"""

    def test_low_risk_actions(self):
        """Test that read/view actions are LOW risk"""
        # Browser read actions
        browser_module = get_module("browser")
        self.assertIsNotNone(browser_module)
        
        extract_text = browser_module.get_action("extract_text")
        self.assertIsNotNone(extract_text)
        self.assertEqual(extract_text.risk_level, RiskLevel.LOW)
        
        # Files read actions
        files_module = get_module("files")
        self.assertIsNotNone(files_module)
        
        search_files = files_module.get_action("search_files")
        self.assertIsNotNone(search_files)
        self.assertEqual(search_files.risk_level, RiskLevel.LOW)
        
        open_file = files_module.get_action("open_file")
        self.assertIsNotNone(open_file)
        self.assertEqual(open_file.risk_level, RiskLevel.LOW)

    def test_medium_risk_actions(self):
        """Test that click/navigate actions are MEDIUM risk"""
        # UI click actions
        ui_module = get_module("ui")
        self.assertIsNotNone(ui_module)
        
        click = ui_module.get_action("click")
        self.assertIsNotNone(click)
        self.assertEqual(click.risk_level, RiskLevel.MEDIUM)
        
        # System close app
        system_module = get_module("system")
        self.assertIsNotNone(system_module)
        
        close_app = system_module.get_action("close_application")
        self.assertIsNotNone(close_app)
        self.assertEqual(close_app.risk_level, RiskLevel.MEDIUM)

    def test_high_risk_actions(self):
        """Test that delete/send actions are HIGH risk"""
        # Files delete
        files_module = get_module("files")
        self.assertIsNotNone(files_module)
        
        delete_file = files_module.get_action("delete_file")
        self.assertIsNotNone(delete_file)
        self.assertEqual(delete_file.risk_level, RiskLevel.HIGH)
        
        # Messaging send
        messaging_module = get_module("messaging")
        self.assertIsNotNone(messaging_module)
        
        send_message = messaging_module.get_action("send_message")
        self.assertIsNotNone(send_message)
        self.assertEqual(send_message.risk_level, RiskLevel.HIGH)
        
        # CRM update
        crm_module = get_module("crm")
        self.assertIsNotNone(crm_module)
        
        update_field = crm_module.get_action("update_field")
        self.assertIsNotNone(update_field)
        self.assertEqual(update_field.risk_level, RiskLevel.HIGH)


class TestValidatorRiskScoring(unittest.TestCase):
    """Test that StrictActionValidator returns risk levels"""

    def setUp(self):
        self.validator = StrictActionValidator()

    def test_validator_returns_risk_level_for_valid_action(self):
        """Test that validator returns risk level for valid actions"""
        step = {
            "module": "files",
            "action": "delete_file",
            "args": {"path": "/tmp/test.txt"}
        }
        
        is_valid, corrected_step, error, risk_level = self.validator.validate_step(step)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        self.assertEqual(risk_level, RiskLevel.HIGH)

    def test_validator_returns_risk_level_for_low_risk_action(self):
        """Test validator returns LOW risk for read actions"""
        step = {
            "module": "files",
            "action": "search_files",
            "args": {"query": "*.txt"}
        }
        
        is_valid, corrected_step, error, risk_level = self.validator.validate_step(step)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        self.assertEqual(risk_level, RiskLevel.LOW)

    def test_validator_returns_none_for_invalid_action(self):
        """Test validator returns None risk level for invalid actions"""
        step = {
            "module": "files",
            "action": "invalid_action",
            "args": {}
        }
        
        is_valid, corrected_step, error, risk_level = self.validator.validate_step(step)
        
        # With auto_correct enabled, this might be corrected or rejected
        # Risk level should be None or the corrected action's risk level
        if not is_valid:
            self.assertIsNone(risk_level)


class TestExecutionEngineConfirmation(unittest.TestCase):
    """Test execution engine confirmation flow for high-risk actions"""

    def setUp(self):
        # Create mock registry with mock agent
        self.registry = AgentRegistry()
        self.mock_agent = MagicMock()
        self.mock_agent.__class__.__name__ = "MockAgent"
        self.mock_agent.execute.return_value = {
            "status": "success",
            "message": "Action completed",
        }
        self.registry.register("files", self.mock_agent)
        self.registry.register("messaging", self.mock_agent)
        
        # Create test intent
        self.intent = Intent(
            action="test_action",
            confidence=1.0,
            raw_command="Test command",
        )

    def test_high_risk_action_requests_confirmation(self):
        """Test that HIGH risk actions trigger confirmation request"""
        confirmation_called = False
        confirmation_request_captured = None
        
        def mock_confirmation_handler(request: RequestConfirmation) -> ConfirmationResponse:
            nonlocal confirmation_called, confirmation_request_captured
            confirmation_called = True
            confirmation_request_captured = request
            return ConfirmationResponse(request_id=request.request_id, confirmed=True)
        
        engine = ExecutionEngineV3(
            agent_registry=self.registry,
            enable_context_validation=False,
            confirmation_handler=mock_confirmation_handler,
            language="en"  # Use English for consistent test assertions
        )
        
        steps = [
            {
                "module": "files",
                "action": "delete_file",
                "args": {"path": "/tmp/test.txt"}
            }
        ]
        
        result = engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=False
        )
        
        # Confirmation should have been requested
        self.assertTrue(confirmation_called)
        self.assertIsNotNone(confirmation_request_captured)
        self.assertEqual(confirmation_request_captured.action_type, "files.delete_file")
        self.assertEqual(confirmation_request_captured.risk_level, "HIGH")
        self.assertIn("deletion", confirmation_request_captured.confirmation_prompt.lower())
        
        # Execution should succeed since we confirmed
        self.assertTrue(result.success)

    def test_high_risk_action_denied_stops_execution(self):
        """Test that denying confirmation stops execution"""
        def mock_confirmation_handler(request: RequestConfirmation) -> ConfirmationResponse:
            return ConfirmationResponse(request_id=request.request_id, confirmed=False)
        
        engine = ExecutionEngineV3(
            agent_registry=self.registry,
            enable_context_validation=False,
            confirmation_handler=mock_confirmation_handler
        )
        
        steps = [
            {
                "module": "files",
                "action": "delete_file",
                "args": {"path": "/tmp/test.txt"}
            }
        ]
        
        result = engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=False
        )
        
        # Execution should fail
        self.assertFalse(result.success)
        self.assertEqual(len(result.action_results), 1)
        self.assertFalse(result.action_results[0].success)
        self.assertIn("denied", result.action_results[0].error.lower())
        
        # Agent should not have been called
        self.mock_agent.execute.assert_not_called()

    def test_low_risk_action_no_confirmation(self):
        """Test that LOW risk actions don't trigger confirmation"""
        confirmation_called = False
        
        def mock_confirmation_handler(request: RequestConfirmation) -> ConfirmationResponse:
            nonlocal confirmation_called
            confirmation_called = True
            return ConfirmationResponse(request_id=request.request_id, confirmed=True)
        
        engine = ExecutionEngineV3(
            agent_registry=self.registry,
            enable_context_validation=False,
            confirmation_handler=mock_confirmation_handler
        )
        
        steps = [
            {
                "module": "files",
                "action": "search_files",
                "args": {"query": "*.txt"}
            }
        ]
        
        result = engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=False
        )
        
        # Confirmation should NOT have been requested
        self.assertFalse(confirmation_called)
        
        # Execution should succeed
        self.assertTrue(result.success)

    def test_medium_risk_action_no_confirmation(self):
        """Test that MEDIUM risk actions don't trigger confirmation"""
        confirmation_called = False
        
        def mock_confirmation_handler(request: RequestConfirmation) -> ConfirmationResponse:
            nonlocal confirmation_called
            confirmation_called = True
            return ConfirmationResponse(request_id=request.request_id, confirmed=True)
        
        # Register UI module
        self.registry.register("ui", self.mock_agent)
        
        engine = ExecutionEngineV3(
            agent_registry=self.registry,
            enable_context_validation=False,
            confirmation_handler=mock_confirmation_handler
        )
        
        steps = [
            {
                "module": "ui",
                "action": "click",
                "args": {"target": "Submit"}
            }
        ]
        
        result = engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=False
        )
        
        # Confirmation should NOT have been requested
        self.assertFalse(confirmation_called)
        
        # Execution should succeed
        self.assertTrue(result.success)

    def test_no_confirmation_handler_denies_by_default(self):
        """Test that without a handler, high-risk actions are denied"""
        # No confirmation handler
        engine = ExecutionEngineV3(
            agent_registry=self.registry,
            enable_context_validation=False,
            confirmation_handler=None  # No handler
        )
        
        steps = [
            {
                "module": "files",
                "action": "delete_file",
                "args": {"path": "/tmp/test.txt"}
            }
        ]
        
        result = engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=False
        )
        
        # Execution should fail (denied by default)
        self.assertFalse(result.success)
        self.assertEqual(len(result.action_results), 1)
        self.assertFalse(result.action_results[0].success)

    def test_mock_execution_skips_confirmation(self):
        """Test that mock execution doesn't require confirmation"""
        confirmation_called = False
        
        def mock_confirmation_handler(request: RequestConfirmation) -> ConfirmationResponse:
            nonlocal confirmation_called
            confirmation_called = True
            return ConfirmationResponse(request_id=request.request_id, confirmed=True)
        
        engine = ExecutionEngineV3(
            agent_registry=self.registry,
            enable_context_validation=False,
            confirmation_handler=mock_confirmation_handler
        )
        
        steps = [
            {
                "module": "files",
                "action": "delete_file",
                "args": {"path": "/tmp/test.txt"}
            }
        ]
        
        result = engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=True  # Mock mode
        )
        
        # Confirmation should NOT be requested in mock mode
        self.assertFalse(confirmation_called)
        
        # Execution should succeed
        self.assertTrue(result.success)

    def test_send_message_confirmation_prompt(self):
        """Test confirmation prompt for send_message action"""
        confirmation_request_captured = None
        
        def mock_confirmation_handler(request: RequestConfirmation) -> ConfirmationResponse:
            nonlocal confirmation_request_captured
            confirmation_request_captured = request
            return ConfirmationResponse(request_id=request.request_id, confirmed=True)
        
        engine = ExecutionEngineV3(
            agent_registry=self.registry,
            enable_context_validation=False,
            confirmation_handler=mock_confirmation_handler,
            language="en"  # Use English for consistent test assertions
        )
        
        steps = [
            {
                "module": "messaging",
                "action": "send_message",
                "args": {"message": "Hello world", "recipient": "John"}
            }
        ]
        
        result = engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=False
        )
        
        # Check confirmation prompt is specific to send_message
        self.assertIsNotNone(confirmation_request_captured)
        prompt = confirmation_request_captured.confirmation_prompt
        self.assertIn("message", prompt.lower())
        self.assertIn("John", prompt)
        self.assertIn("Hello world", prompt)

    def test_french_confirmation_prompt(self):
        """Test that French localization works for confirmation prompts"""
        confirmation_request_captured = None
        
        def mock_confirmation_handler(request: RequestConfirmation) -> ConfirmationResponse:
            nonlocal confirmation_request_captured
            confirmation_request_captured = request
            return ConfirmationResponse(request_id=request.request_id, confirmed=True)
        
        engine = ExecutionEngineV3(
            agent_registry=self.registry,
            enable_context_validation=False,
            confirmation_handler=mock_confirmation_handler,
            language="fr"  # Use French
        )
        
        steps = [
            {
                "module": "files",
                "action": "delete_file",
                "args": {"path": "/tmp/test.txt"}
            }
        ]
        
        result = engine.execute_plan(
            steps=steps,
            intent=self.intent,
            session_id="test_session",
            request_id="test_request",
            mock_execution=False
        )
        
        # Check confirmation prompt is in French
        self.assertIsNotNone(confirmation_request_captured)
        prompt = confirmation_request_captured.confirmation_prompt
        self.assertIn("suppression", prompt.lower())  # "suppression" is French for "deletion"
        self.assertIn("/tmp/test.txt", prompt)


class TestRequestConfirmationEvent(unittest.TestCase):
    """Test RequestConfirmation and ConfirmationResponse data structures"""

    def test_request_confirmation_creation(self):
        """Test creating a RequestConfirmation event"""
        request = RequestConfirmation(
            action_type="files.delete_file",
            action_details={"module": "files", "action": "delete_file", "args": {"path": "/tmp/test.txt"}},
            risk_level="HIGH",
            confirmation_prompt="Confirm deletion of file: /tmp/test.txt",
            request_id="test_request"
        )
        
        self.assertEqual(request.action_type, "files.delete_file")
        self.assertEqual(request.risk_level, "HIGH")
        self.assertIsNotNone(request.timestamp)

    def test_request_confirmation_to_dict(self):
        """Test converting RequestConfirmation to dict"""
        request = RequestConfirmation(
            action_type="files.delete_file",
            action_details={"module": "files", "action": "delete_file"},
            risk_level="HIGH",
            confirmation_prompt="Test prompt",
            request_id="test_request"
        )
        
        data = request.to_dict()
        
        self.assertEqual(data["event_type"], "request_confirmation")
        self.assertEqual(data["action_type"], "files.delete_file")
        self.assertEqual(data["risk_level"], "HIGH")
        self.assertIn("timestamp", data)

    def test_confirmation_response_creation(self):
        """Test creating a ConfirmationResponse"""
        response = ConfirmationResponse(
            request_id="test_request",
            confirmed=True
        )
        
        self.assertEqual(response.request_id, "test_request")
        self.assertTrue(response.confirmed)
        self.assertIsNotNone(response.timestamp)


if __name__ == "__main__":
    unittest.main()
