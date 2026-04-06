"""
Integration Test for Agent Architecture

TICKET-ARCH-AGENT: Architecture Agentique - Solution propre, stable et extensible

This test validates the complete agent architecture including:
- @agent_action decorator
- Auto-discovery mechanism
- Auto-registration
- Documentation generation
- Performance benchmarks
"""

import asyncio
import time
from typing import Any, Dict

from janus.capabilities.agents.base_agent import BaseAgent
from janus.capabilities.agents.decorators import agent_action, list_agent_actions
from janus.capabilities.agents.discovery import AgentDiscovery
from janus.runtime.core.agent_registry import AgentRegistry


# ============================================================================
# Test Agent with @agent_action decorators
# ============================================================================

class IntegrationTestAgent(BaseAgent):
    """Test agent for integration testing."""
    
    def __init__(self, provider: str = "test"):
        super().__init__("integration_test")
        self.provider = provider
    
    async def execute(self, action: str, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Route to decorated methods."""
        method_name = f"_{action}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return await method(args, context)
        else:
            return self._error_result(f"Unsupported action: {action}")
    
    @agent_action(
        description="Simple test action with validation",
        required_args=["input"],
        optional_args={"multiplier": 2},
        examples=["test.simple_action(input='hello')"]
    )
    async def _simple_action(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Simple action for testing."""
        return self._success_result(data={
            "input": args["input"],
            "multiplier": args["multiplier"],
            "result": args["input"] * args["multiplier"]
        })
    
    @agent_action(
        description="Multi-provider action",
        required_args=["data"],
        providers=["provider1", "provider2", "provider3"],
        examples=["test.multi_provider(data='test', provider='provider1')"]
    )
    async def _multi_provider(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Multi-provider action for testing."""
        provider = args.get("provider", self.provider)
        return self._success_result(data={
            "provider": provider,
            "data": args["data"],
            "processed": f"{provider}:{args['data']}"
        })
    
    @agent_action(
        description="Action that validates error handling",
        required_args=["should_fail"]
    )
    async def _error_test(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Action that can raise errors for testing."""
        if args["should_fail"]:
            raise ValueError("Intentional test error")
        return self._success_result(data={"status": "ok"})


# ============================================================================
# Integration Tests
# ============================================================================

async def test_decorator_integration():
    """Test that @agent_action decorator works end-to-end."""
    print("\n" + "=" * 80)
    print("TEST 1: @agent_action Decorator Integration")
    print("=" * 80)
    
    agent = IntegrationTestAgent()
    
    # Test 1: Simple action with validation
    print("\n✓ Test simple action with required args")
    result = await agent.execute("simple_action", {"input": "test"}, {})
    assert result["status"] == "success", f"Expected success, got {result}"
    assert result["data"]["input"] == "test"
    assert result["data"]["multiplier"] == 2  # Default value
    print(f"  Result: {result['data']}")
    
    # Test 2: Missing required arg
    print("\n✓ Test missing required arg")
    result = await agent.execute("simple_action", {}, {})
    assert result["status"] == "error", f"Expected error, got {result}"
    assert "Missing required arguments" in result["error"]
    print(f"  Error: {result['error']}")
    
    # Test 3: Optional arg override
    print("\n✓ Test optional arg override")
    result = await agent.execute("simple_action", {"input": "test", "multiplier": 5}, {})
    assert result["status"] == "success"
    assert result["data"]["multiplier"] == 5
    print(f"  Result: {result['data']}")
    
    # Test 4: Multi-provider action
    print("\n✓ Test multi-provider action")
    result = await agent.execute("multi_provider", {"data": "value", "provider": "provider2"}, {})
    assert result["status"] == "success"
    assert result["data"]["provider"] == "provider2"
    print(f"  Result: {result['data']}")
    
    # Test 5: Error handling
    print("\n✓ Test error handling")
    result = await agent.execute("error_test", {"should_fail": True}, {})
    assert result["status"] == "error"
    assert "Intentional test error" in result["error"]
    print(f"  Error handled: {result['error']}")
    
    print("\n✅ All decorator integration tests passed!")


def test_metadata_collection():
    """Test that metadata is collected from decorators."""
    print("\n" + "=" * 80)
    print("TEST 2: Metadata Collection")
    print("=" * 80)
    
    agent = IntegrationTestAgent()
    actions = list_agent_actions(agent)
    
    print(f"\n✓ Found {len(actions)} actions")
    
    # Verify metadata for each action
    for action in actions:
        print(f"\n  Action: {action.name}")
        print(f"    Description: {action.description}")
        print(f"    Required args: {action.required_args}")
        print(f"    Optional args: {action.optional_args}")
        print(f"    Providers: {action.providers}")
        print(f"    Examples: {len(action.examples)} example(s)")
        
        # Validate metadata
        assert action.name, "Action name should not be empty"
        assert action.description, "Description should not be empty"
        assert action.agent_name == "integration_test", f"Agent name should be integration_test, got {action.agent_name}"
    
    print("\n✅ All metadata collection tests passed!")


def test_auto_discovery():
    """Test that auto-discovery finds the agent."""
    print("\n" + "=" * 80)
    print("TEST 3: Auto-Discovery")
    print("=" * 80)
    
    # Note: IntegrationTestAgent is not in the agents package,
    # so we'll test discovery with actual agents
    discovery = AgentDiscovery()
    agents = discovery.discover_agents()
    
    print(f"\n✓ Discovered {len(agents)} agents")
    print(f"  Agents: {sorted(agents.keys())}")
    
    # Verify at least some core agents are found
    assert len(agents) > 0, "Should discover at least some agents"
    
    # Check for specific agents (may vary based on environment)
    expected_agents = {"files", "messaging", "scheduler", "llm"}
    found_agents = set(agents.keys())
    
    common_agents = expected_agents.intersection(found_agents)
    print(f"\n✓ Found {len(common_agents)} expected agents: {sorted(common_agents)}")
    
    assert len(common_agents) > 0, "Should find at least some expected agents"
    
    print("\n✅ Auto-discovery tests passed!")


def test_auto_registration():
    """Test that auto-registration works."""
    print("\n" + "=" * 80)
    print("TEST 4: Auto-Registration")
    print("=" * 80)
    
    discovery = AgentDiscovery()
    registry = AgentRegistry()
    
    # Discover agents
    agents = discovery.discover_agents()
    print(f"\n✓ Discovered {len(agents)} agents")
    
    # Auto-register
    count = discovery.auto_register_agents(registry)
    print(f"✓ Registered {count} agents")
    
    # Verify registration
    modules = registry.list_modules()
    print(f"✓ Registry has {len(modules)} modules: {sorted(modules.keys())}")
    
    assert count > 0, "Should register at least some agents"
    assert len(modules) >= count, "Registry should have all registered agents"
    
    print("\n✅ Auto-registration tests passed!")


def test_documentation_generation():
    """Test that documentation can be generated."""
    print("\n" + "=" * 80)
    print("TEST 5: Documentation Generation")
    print("=" * 80)
    
    discovery = AgentDiscovery()
    
    # Manually add test agent for documentation
    discovery._discovered_agents["integration_test"] = IntegrationTestAgent
    agent = IntegrationTestAgent()
    discovery.collect_metadata(agent)
    
    # Generate documentation
    doc = discovery.generate_documentation()
    
    print("\n✓ Generated documentation:")
    print("-" * 80)
    # Print first 500 chars
    print(doc[:500] + "...")
    print("-" * 80)
    
    # Verify documentation contains expected content
    assert "Janus Agent Documentation" in doc
    assert "integration_test" in doc.lower()
    assert "simple_action" in doc
    assert "multi_provider" in doc
    
    print("\n✅ Documentation generation tests passed!")


async def test_performance_benchmark():
    """Test performance of decorator overhead."""
    print("\n" + "=" * 80)
    print("TEST 6: Performance Benchmark")
    print("=" * 80)
    
    agent = IntegrationTestAgent()
    
    # Warmup
    for _ in range(10):
        await agent.execute("simple_action", {"input": "warmup"}, {})
    
    # Benchmark
    iterations = 100
    start_time = time.time()
    
    for _ in range(iterations):
        result = await agent.execute("simple_action", {"input": "test"}, {})
        assert result["status"] == "success"
    
    elapsed = time.time() - start_time
    avg_ms = (elapsed / iterations) * 1000
    
    print(f"\n✓ Executed {iterations} actions in {elapsed:.3f}s")
    print(f"✓ Average time per action: {avg_ms:.2f}ms")
    
    # Verify performance target (<5ms overhead from decorator)
    # Note: Total time includes actual logic, we're checking it's reasonable
    assert avg_ms < 50, f"Average time {avg_ms:.2f}ms exceeds 50ms threshold"
    
    print(f"\n✅ Performance target met: {avg_ms:.2f}ms per action")


async def run_all_tests():
    """Run all integration tests."""
    print("\n" + "=" * 80)
    print("RUNNING INTEGRATION TESTS FOR AGENT ARCHITECTURE")
    print("=" * 80)
    
    try:
        # Run tests
        await test_decorator_integration()
        test_metadata_collection()
        test_auto_discovery()
        test_auto_registration()
        test_documentation_generation()
        await test_performance_benchmark()
        
        print("\n" + "=" * 80)
        print("✅ ALL INTEGRATION TESTS PASSED!")
        print("=" * 80)
        
        return True
    
    except AssertionError as e:
        print("\n" + "=" * 80)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 80)
        return False
    
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ UNEXPECTED ERROR: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
