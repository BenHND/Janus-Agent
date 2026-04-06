"""
Tests for Agent Action Decorator

TICKET-ARCH-AGENT: Architecture Agentique - Solution propre, stable et extensible

Tests for the @agent_action decorator that handles:
- Validation of required arguments
- Logging before and after execution
- Error handling and structured error results
- Performance tracking
- Metadata collection
"""

import asyncio
import pytest
from typing import Any, Dict

from janus.capabilities.agents.base_agent import BaseAgent
from janus.capabilities.agents.decorators import (
    agent_action,
    get_action_metadata,
    list_agent_actions,
    ActionMetadata,
)


class TestAgent(BaseAgent):
    """Test agent for decorator testing."""
    
    def __init__(self):
        super().__init__("test")
    
    @agent_action(
        description="Test action with required args",
        required_args=["arg1", "arg2"],
        optional_args={"arg3": "default_value"},
        examples=["test.test_action(arg1='a', arg2='b')"]
    )
    async def _test_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Test action implementation."""
        return self._success_result(data={
            "arg1": args["arg1"],
            "arg2": args["arg2"],
            "arg3": args["arg3"],
        })
    
    @agent_action(
        description="Test action that raises an error",
        required_args=["input"]
    )
    async def _error_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Test action that raises an error."""
        raise ValueError("Test error")
    
    @agent_action(
        description="Test action with providers",
        required_args=["platform", "message"],
        providers=["slack", "teams", "discord"]
    )
    async def _multi_provider_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Test action with multiple providers."""
        return self._success_result(data={
            "platform": args["platform"],
            "message": args["message"],
        })


@pytest.mark.asyncio
async def test_decorator_validation_success():
    """Test that decorator validates required arguments successfully."""
    agent = TestAgent()
    
    # Valid arguments
    args = {"arg1": "value1", "arg2": "value2"}
    context = {}
    
    result = await agent._test_action(args, context)
    
    assert result["status"] == "success"
    assert result["data"]["arg1"] == "value1"
    assert result["data"]["arg2"] == "value2"
    assert result["data"]["arg3"] == "default_value"  # Optional arg default


@pytest.mark.asyncio
async def test_decorator_validation_failure():
    """Test that decorator catches missing required arguments."""
    agent = TestAgent()
    
    # Missing required arg2
    args = {"arg1": "value1"}
    context = {}
    
    result = await agent._test_action(args, context)
    
    assert result["status"] == "error"
    assert "Missing required arguments" in result["error"]
    assert "arg2" in result["error"]


@pytest.mark.asyncio
async def test_decorator_error_handling():
    """Test that decorator handles exceptions properly."""
    agent = TestAgent()
    
    args = {"input": "test"}
    context = {}
    
    result = await agent._error_action(args, context)
    
    assert result["status"] == "error"
    assert "Test error" in result["error"]
    assert result["module"] == "test"
    assert result["action"] == "error_action"


@pytest.mark.asyncio
async def test_decorator_optional_args():
    """Test that decorator provides default values for optional args."""
    agent = TestAgent()
    
    args = {"arg1": "value1", "arg2": "value2"}
    context = {}
    
    result = await agent._test_action(args, context)
    
    assert result["data"]["arg3"] == "default_value"
    
    # Test with provided optional arg
    args = {"arg1": "value1", "arg2": "value2", "arg3": "custom_value"}
    result = await agent._test_action(args, context)
    
    assert result["data"]["arg3"] == "custom_value"


def test_metadata_collection():
    """Test that decorator stores metadata correctly."""
    agent = TestAgent()
    
    # Get metadata from decorated method
    metadata = get_action_metadata(agent._test_action)
    
    assert metadata is not None
    assert metadata.name == "test_action"
    assert metadata.description == "Test action with required args"
    assert "arg1" in metadata.required_args
    assert "arg2" in metadata.required_args
    assert metadata.optional_args["arg3"] == "default_value"
    assert len(metadata.examples) == 1


def test_list_agent_actions():
    """Test that we can list all actions for an agent."""
    agent = TestAgent()
    
    actions = list_agent_actions(agent)
    
    assert len(actions) == 3
    action_names = {action.name for action in actions}
    assert "test_action" in action_names
    assert "error_action" in action_names
    assert "multi_provider_action" in action_names


def test_provider_metadata():
    """Test that provider information is captured in metadata."""
    agent = TestAgent()
    
    metadata = get_action_metadata(agent._multi_provider_action)
    
    assert metadata is not None
    assert "slack" in metadata.providers
    assert "teams" in metadata.providers
    assert "discord" in metadata.providers


def test_metadata_to_dict():
    """Test that metadata can be serialized to dictionary."""
    metadata = ActionMetadata(
        name="test_action",
        description="Test description",
        required_args=["arg1", "arg2"],
        optional_args={"arg3": "default"},
        providers=["slack", "teams"],
        examples=["example1", "example2"],
        agent_name="test"
    )
    
    data = metadata.to_dict()
    
    assert data["name"] == "test_action"
    assert data["description"] == "Test description"
    assert data["required_args"] == ["arg1", "arg2"]
    assert data["optional_args"] == {"arg3": "default"}
    assert data["providers"] == ["slack", "teams"]
    assert data["examples"] == ["example1", "example2"]
    assert data["agent_name"] == "test"


@pytest.mark.asyncio
async def test_decorator_context_logging():
    """Test that decorator logs context properly."""
    agent = TestAgent()
    
    args = {"arg1": "value1", "arg2": "value2"}
    context = {"app": "Safari", "surface": "browser", "provider": "google"}
    
    result = await agent._test_action(args, context)
    
    # Should succeed - logging is internal, just verify execution works
    assert result["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
