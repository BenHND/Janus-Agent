#!/usr/bin/env python3
"""
Standalone test for TICKET 005 - ExecutionEngineV3

This script tests the new execution engine without requiring all dependencies.
Run with: python3 tests/test_ticket_005_standalone.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_agent_registry():
    """Test AgentRegistry functionality"""
    print("\n=== Testing AgentRegistry ===")
    
    # Import directly to avoid dependency issues
    from janus.runtime.core.agent_registry import AgentRegistry
    
    # Create registry
    registry = AgentRegistry()
    print("✓ Created AgentRegistry")
    
    # Create mock agent
    class MockAgent:
        def __init__(self, name):
            self.name = name
        
        def execute(self, action, args):
            return {
                "status": "success",
                "message": f"{self.name} executed {action}",
                "data": args,
            }
    
    # Register agents
    system_agent = MockAgent("SystemAgent")
    browser_agent = MockAgent("BrowserAgent")
    
    registry.register("system", system_agent)
    registry.register("browser", browser_agent)
    print("✓ Registered system and browser agents")
    
    # Test retrieval
    assert registry.has_agent("system")
    assert registry.has_agent("browser")
    assert registry.get_agent("system") == system_agent
    print("✓ Agent retrieval works")
    
    # Test aliases
    assert registry.get_agent("chrome") == browser_agent  # chrome -> browser alias
    print("✓ Agent aliases work (chrome → browser)")
    
    # Test execution
    result = registry.execute("system", "open_app", {"app_name": "Safari"})
    assert result["status"] == "success"
    assert "SystemAgent" in result["message"]
    print("✓ Action execution works")
    
    # Test unknown module
    result = registry.execute("unknown", "action", {})
    assert result["status"] == "error"
    assert "unknown" in result["error"].lower()
    print("✓ Unknown module handling works")
    
    # List modules
    modules = registry.list_modules()
    assert "system" in modules
    assert "browser" in modules
    print(f"✓ Module listing works: {list(modules.keys())}")
    
    print("✅ AgentRegistry tests passed!\n")
    return True


def test_step_validator():
    """Test StepValidator functionality"""
    print("=== Testing StepValidator ===")
    
    from janus.runtime.core.execution_engine_v3 import StepValidator
    
    validator = StepValidator()
    print("✓ Created StepValidator")
    
    # Test valid step
    valid_step = {
        "module": "browser",
        "action": "open_url",
        "args": {"url": "https://youtube.com"},
        "context": {"app": "Safari"},
    }
    result = validator.validate_step(valid_step)
    assert result.is_valid
    print("✓ Valid step passes validation")
    
    # Test missing module
    invalid_step = {
        "action": "open_url",
        "args": {},
    }
    result = validator.validate_step(invalid_step)
    assert not result.is_valid
    assert "module" in result.error_message.lower()
    print("✓ Missing module detected")
    
    # Test missing action
    invalid_step = {
        "module": "browser",
        "args": {},
    }
    result = validator.validate_step(invalid_step)
    assert not result.is_valid
    assert "action" in result.error_message.lower()
    print("✓ Missing action detected")
    
    # Test invalid args type
    invalid_step = {
        "module": "browser",
        "action": "open_url",
        "args": "not_a_dict",
    }
    result = validator.validate_step(invalid_step)
    assert not result.is_valid
    assert "args" in result.error_message.lower()
    print("✓ Invalid args type detected")
    
    print("✅ StepValidator tests passed!\n")
    return True


def test_error_classifier():
    """Test ErrorClassifier functionality"""
    print("=== Testing ErrorClassifier ===")
    
    from janus.runtime.core.execution_engine_v3 import ErrorClassifier
    
    classifier = ErrorClassifier()
    print("✓ Created ErrorClassifier")
    
    # Test timeout error
    result = classifier.classify_error("Connection timeout after 30s")
    assert result["recoverable"]
    assert result["retry_recommended"]
    assert result["error_category"] == "timeout"
    print("✓ Timeout error classified correctly")
    
    # Test network error
    result = classifier.classify_error("Network connection failed")
    assert result["recoverable"]
    assert result["retry_recommended"]
    assert result["error_category"] == "network"
    print("✓ Network error classified correctly")
    
    # Test permission error
    result = classifier.classify_error("Access denied: permission required")
    assert not result["recoverable"]
    assert not result["retry_recommended"]
    assert result["error_category"] == "permission"
    print("✓ Permission error classified correctly")
    
    # Test element not found
    result = classifier.classify_error("Element not found with selector #button")
    assert result["recoverable"]
    assert result["retry_recommended"]
    assert result["replan_recommended"]
    assert result["error_category"] == "element_not_found"
    print("✓ Element not found classified correctly")
    
    # Test module not found
    result = classifier.classify_error("Module 'unknown' not registered")
    assert not result["recoverable"]
    assert result["replan_recommended"]
    assert result["error_category"] == "module_not_found"
    print("✓ Module not found classified correctly")
    
    print("✅ ErrorClassifier tests passed!\n")
    return True


def test_execution_engine_v3():
    """Test ExecutionEngineV3 basic functionality"""
    print("=== Testing ExecutionEngineV3 ===")
    
    from janus.runtime.core.execution_engine_v3 import ExecutionEngineV3
    from janus.runtime.core.agent_registry import AgentRegistry
    from janus.runtime.core.contracts import Intent
    
    # Create mock agent
    class MockAgent:
        def execute(self, action, args):
            if action == "fail_action":
                return {"status": "error", "error": "Intentional failure"}
            return {
                "status": "success",
                "message": f"Executed {action}",
                "data": {"result": "test_data"},
            }
    
    # Setup registry
    registry = AgentRegistry()
    registry.register("test_module", MockAgent())
    print("✓ Created registry with mock agent")
    
    # Create engine
    engine = ExecutionEngineV3(
        agent_registry=registry,
        max_retries=0,
        enable_replanning=False,
        enable_context_validation=False,
    )
    print("✓ Created ExecutionEngineV3")
    
    # Create test intent
    intent = Intent(
        action="test_action",
        confidence=1.0,
        raw_command="Test command",
    )
    
    # Test simple execution (mock mode)
    steps = [
        {"module": "test_module", "action": "test_action", "args": {}},
    ]
    result = engine.execute_plan(
        steps=steps,
        intent=intent,
        session_id="test_session",
        request_id="test_request",
        mock_execution=True,
    )
    assert result.success
    assert len(result.action_results) == 1
    print("✓ Mock execution works")
    
    # Test real execution
    result = engine.execute_plan(
        steps=steps,
        intent=intent,
        session_id="test_session",
        request_id="test_request",
        mock_execution=False,
    )
    assert result.success
    assert len(result.action_results) == 1
    assert result.action_results[0].success
    print("✓ Real execution works")
    
    # Test invalid step
    invalid_steps = [
        {"action": "test_action"},  # Missing module
    ]
    result = engine.execute_plan(
        steps=invalid_steps,
        intent=intent,
        session_id="test_session",
        request_id="test_request",
        mock_execution=False,
    )
    assert not result.success
    assert len(result.action_results) == 1
    assert not result.action_results[0].success
    print("✓ Invalid step detection works")
    
    # Test multi-step execution
    multi_steps = [
        {"module": "test_module", "action": "step1", "args": {}, "step_id": "step1"},
        {"module": "test_module", "action": "step2", "args": {"input_from": "step1"}},
    ]
    result = engine.execute_plan(
        steps=multi_steps,
        intent=intent,
        session_id="test_session",
        request_id="test_request",
        mock_execution=False,
    )
    assert result.success
    assert len(result.action_results) == 2
    print("✓ Multi-step execution works")
    
    print("✅ ExecutionEngineV3 tests passed!\n")
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("TICKET 005 - ExecutionEngineV3 Standalone Tests")
    print("=" * 60)
    
    all_passed = True
    
    try:
        all_passed = test_agent_registry() and all_passed
    except Exception as e:
        print(f"❌ AgentRegistry tests failed: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        all_passed = test_step_validator() and all_passed
    except Exception as e:
        print(f"❌ StepValidator tests failed: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        all_passed = test_error_classifier() and all_passed
    except Exception as e:
        print(f"❌ ErrorClassifier tests failed: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        all_passed = test_execution_engine_v3() and all_passed
    except Exception as e:
        print(f"❌ ExecutionEngineV3 tests failed: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
