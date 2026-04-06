"""
Tests for Agent Auto-Discovery

TICKET-ARCH-AGENT: Architecture Agentique - Solution propre, stable et extensible

Tests for the automatic agent discovery and registration mechanism.
"""

import pytest
from typing import Any, Dict

from janus.capabilities.agents.discovery import AgentDiscovery, get_agent_discovery
from janus.capabilities.agents.base_agent import BaseAgent
from janus.capabilities.agents.decorators import agent_action
from janus.runtime.core.agent_registry import AgentRegistry


def test_discover_agents():
    """Test that discovery finds all agent classes."""
    discovery = AgentDiscovery()
    agents = discovery.discover_agents()
    
    # Should find at least the core agents
    assert len(agents) > 0
    
    # Check for specific core agents
    expected_agents = {"system", "browser", "messaging", "files", "code", "ui", "llm"}
    found_agents = set(agents.keys())
    
    # At least some of these should be found
    assert len(expected_agents.intersection(found_agents)) > 0


def test_agent_name_derivation():
    """Test that agent names are correctly derived from class names."""
    discovery = AgentDiscovery()
    
    class TestAgentClass(BaseAgent):
        def __init__(self):
            super().__init__("test")
        
        async def execute(self, action, args, context):
            return {}
    
    name = discovery._get_agent_name(TestAgentClass)
    assert name == "testagentclass"


def test_collect_metadata():
    """Test that metadata is collected from agent instances."""
    class TestAgentWithActions(BaseAgent):
        def __init__(self):
            super().__init__("test")
        
        @agent_action(
            description="Test action 1",
            required_args=["arg1"]
        )
        async def _action1(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
            return self._success_result()
        
        @agent_action(
            description="Test action 2",
            required_args=["arg2"]
        )
        async def _action2(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
            return self._success_result()
        
        async def execute(self, action, args, context):
            return {}
    
    discovery = AgentDiscovery()
    agent = TestAgentWithActions()
    
    metadata = discovery.collect_metadata(agent)
    
    assert len(metadata) == 2
    action_names = {m.name for m in metadata}
    assert "action1" in action_names
    assert "action2" in action_names


def test_auto_register_agents():
    """Test automatic registration of discovered agents."""
    discovery = AgentDiscovery()
    registry = AgentRegistry()
    
    # Discover agents
    discovery.discover_agents()
    
    # Auto-register
    count = discovery.auto_register_agents(registry)
    
    # Should register multiple agents
    assert count > 0
    
    # Verify some agents are registered
    assert registry.has_agent("system") or registry.has_agent("browser")


def test_global_discovery_singleton():
    """Test that global discovery is a singleton."""
    discovery1 = get_agent_discovery()
    discovery2 = get_agent_discovery()
    
    assert discovery1 is discovery2


def test_generate_documentation():
    """Test that documentation generation works."""
    discovery = AgentDiscovery()
    
    # Create a test agent with actions
    class DocTestAgent(BaseAgent):
        def __init__(self):
            super().__init__("doctest")
        
        @agent_action(
            description="Test action for documentation",
            required_args=["input"],
            optional_args={"output": "default"},
            providers=["test_provider"],
            examples=["doctest.test_action(input='value')"]
        )
        async def _test_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
            return self._success_result()
        
        async def execute(self, action, args, context):
            return {}
    
    # Manually register for testing
    discovery._discovered_agents["doctest"] = DocTestAgent
    agent = DocTestAgent()
    discovery.collect_metadata(agent)
    
    # Generate documentation
    doc = discovery.generate_documentation()
    
    # Verify documentation contains expected content
    assert "Janus Agent Documentation" in doc
    assert "doctest" in doc.lower()
    assert "test_action" in doc
    assert "Test action for documentation" in doc
    assert "Required Arguments" in doc
    assert "Optional Arguments" in doc
    assert "Supported Providers" in doc


def test_instantiate_agent_with_args():
    """Test that agents can be instantiated with constructor arguments."""
    class AgentWithArgs(BaseAgent):
        def __init__(self, required_param: str, optional_param: str = "default"):
            super().__init__("withargs")
            self.required_param = required_param
            self.optional_param = optional_param
        
        async def execute(self, action, args, context):
            return {}
    
    discovery = AgentDiscovery()
    
    # Instantiate with required parameter
    agent = discovery._instantiate_agent(
        AgentWithArgs,
        "withargs",
        required_param="test_value"
    )
    
    assert agent.required_param == "test_value"
    assert agent.optional_param == "default"


def test_instantiate_agent_without_args():
    """Test that agents without constructor args can be instantiated."""
    class SimpleAgent(BaseAgent):
        def __init__(self):
            super().__init__("simple")
        
        async def execute(self, action, args, context):
            return {}
    
    discovery = AgentDiscovery()
    
    # Should work without any arguments
    agent = discovery._instantiate_agent(SimpleAgent, "simple")
    
    assert agent.agent_name == "simple"


def test_skip_duplicate_registration():
    """Test that already registered agents are skipped."""
    discovery = AgentDiscovery()
    registry = AgentRegistry()
    
    # Create a simple agent
    class SkipTestAgent(BaseAgent):
        def __init__(self):
            super().__init__("skiptest")
        
        async def execute(self, action, args, context):
            return {}
    
    # Register manually first
    agent1 = SkipTestAgent()
    registry.register("skiptest", agent1)
    
    # Add to discovery
    discovery._discovered_agents["skiptest"] = SkipTestAgent
    
    # Try to auto-register - should skip
    count = discovery.auto_register_agents(registry)
    
    # Should not register (already exists)
    assert count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
