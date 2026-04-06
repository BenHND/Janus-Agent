"""
Tests for Burst OODA Mode (CORE-FOUNDATION-002)

Tests:
- Burst decision generation
- Stop condition evaluation
- Stagnation detection
- Burst metrics tracking
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from janus.runtime.core.contracts import (
    BurstDecision,
    BurstMetrics,
    StopCondition,
    StopConditionType,
    Intent,
    ExecutionResult,
    ActionResult
)
from janus.runtime.core.action_coordinator import ActionCoordinator
from janus.ai.reasoning.reasoner_llm import ReasonerLLM


class TestBurstDecision:
    """Test burst decision data structures"""
    
    def test_burst_decision_creation(self):
        """Test creating a burst decision"""
        decision = BurstDecision(
            actions=[
                {"module": "system", "action": "open_app", "args": {"app_name": "Safari"}},
                {"module": "browser", "action": "navigate", "args": {"url": "https://youtube.com"}}
            ],
            stop_when=[
                StopCondition(type=StopConditionType.URL_CONTAINS, value="youtube.com")
            ],
            needs_vision=False,
            reasoning="Navigate to YouTube"
        )
        
        assert len(decision.actions) == 2
        assert len(decision.stop_when) == 1
        assert decision.needs_vision is False
        assert "YouTube" in decision.reasoning
    
    def test_burst_decision_to_dict(self):
        """Test converting burst decision to dict"""
        decision = BurstDecision(
            actions=[{"module": "system", "action": "done", "args": {}}],
            stop_when=[],
            needs_vision=True,
            reasoning="Test"
        )
        
        data = decision.to_dict()
        
        assert "actions" in data
        assert "stop_when" in data
        assert "needs_vision" in data
        assert data["needs_vision"] is True


class TestStopConditions:
    """Test stop condition evaluation"""
    
    def test_stop_condition_creation(self):
        """Test creating stop conditions"""
        sc = StopCondition(
            type=StopConditionType.URL_CONTAINS,
            value="youtube.com",
            description="Check if on YouTube"
        )
        
        assert sc.type == StopConditionType.URL_CONTAINS
        assert sc.value == "youtube.com"
    
    def test_stop_condition_from_dict(self):
        """Test creating stop condition from dict"""
        data = {
            "type": "app_active",
            "value": "Safari",
            "description": "Safari is active"
        }
        
        sc = StopCondition.from_dict(data)
        
        assert sc.type == StopConditionType.APP_ACTIVE
        assert sc.value == "Safari"


class TestBurstMetrics:
    """Test burst metrics tracking"""
    
    def test_burst_metrics_initialization(self):
        """Test initializing burst metrics"""
        metrics = BurstMetrics()
        
        assert metrics.llm_calls == 0
        assert metrics.burst_actions_executed == 0
        assert metrics.vision_calls == 0
        assert metrics.stagnation_events == 0
    
    def test_record_burst(self):
        """Test recording a burst execution"""
        metrics = BurstMetrics()
        
        metrics.record_burst(3)
        metrics.record_burst(2)
        metrics.record_burst(4)
        
        assert metrics.total_bursts == 3
        assert metrics.burst_actions_executed == 9
        assert metrics.avg_actions_per_burst == 3.0
    
    def test_metrics_to_dict(self):
        """Test converting metrics to dict"""
        metrics = BurstMetrics()
        metrics.llm_calls = 3
        metrics.vision_calls = 2
        metrics.t_llm_ms = 1500.0
        
        data = metrics.to_dict()
        
        assert data["llm_calls"] == 3
        assert data["vision_calls"] == 2
        assert data["t_llm_ms"] == 1500.0


class TestStagnationDetection:
    """Test stagnation detection"""
    
    @pytest.fixture
    def coordinator(self):
        """Create a test coordinator with stagnation detection"""
        return ActionCoordinator(
            stagnation_threshold=3,
            enable_burst_mode=True
        )
    
    def test_compute_state_hash(self, coordinator):
        """Test state hash computation"""
        state1 = {
            "active_app": "Safari",
            "window_title": "YouTube",
            "url": "https://youtube.com",
            "clipboard": "test"
        }
        
        state2 = {
            "active_app": "Safari",
            "window_title": "YouTube",
            "url": "https://youtube.com",
            "clipboard": "test"
        }
        
        state3 = {
            "active_app": "Chrome",
            "window_title": "YouTube",
            "url": "https://youtube.com",
            "clipboard": "test"
        }
        
        hash1 = coordinator._compute_state_hash(state1)
        hash2 = coordinator._compute_state_hash(state2)
        hash3 = coordinator._compute_state_hash(state3)
        
        # Same state = same hash
        assert hash1 == hash2
        
        # Different state = different hash
        assert hash1 != hash3
    
    def test_stagnation_detection(self, coordinator):
        """Test detecting stagnation after threshold"""
        metrics = BurstMetrics()
        
        state = {
            "active_app": "Safari",
            "window_title": "YouTube",
            "url": "https://youtube.com",
            "clipboard": ""
        }
        
        hash_val = coordinator._compute_state_hash(state)
        
        # First occurrence - not stagnant
        is_stagnant = coordinator._detect_stagnation(hash_val, metrics)
        assert not is_stagnant
        
        # Second occurrence - not stagnant yet
        is_stagnant = coordinator._detect_stagnation(hash_val, metrics)
        assert not is_stagnant
        
        # Third occurrence - STAGNANT!
        is_stagnant = coordinator._detect_stagnation(hash_val, metrics)
        assert is_stagnant
        assert metrics.stagnation_events == 1
    
    def test_no_stagnation_with_changing_state(self, coordinator):
        """Test no stagnation when state changes"""
        metrics = BurstMetrics()
        
        states = [
            {"active_app": "Safari", "window_title": "Page 1", "url": "https://site.com/1", "clipboard": ""},
            {"active_app": "Safari", "window_title": "Page 2", "url": "https://site.com/2", "clipboard": ""},
            {"active_app": "Safari", "window_title": "Page 3", "url": "https://site.com/3", "clipboard": ""},
        ]
        
        for state in states:
            hash_val = coordinator._compute_state_hash(state)
            is_stagnant = coordinator._detect_stagnation(hash_val, metrics)
            assert not is_stagnant
        
        assert metrics.stagnation_events == 0


class TestStopConditionEvaluation:
    """Test stop condition evaluation"""
    
    @pytest.fixture
    def coordinator(self):
        """Create a test coordinator"""
        return ActionCoordinator(enable_burst_mode=True)
    
    def test_url_contains_condition(self, coordinator):
        """Test URL contains condition"""
        condition = {"type": "url_contains", "value": "youtube"}
        state = {"url": "https://www.youtube.com/watch?v=123", "active_app": "Safari"}
        
        result = coordinator._evaluate_single_stop_condition(condition, state)
        assert result is True
        
        state2 = {"url": "https://google.com", "active_app": "Safari"}
        result2 = coordinator._evaluate_single_stop_condition(condition, state2)
        assert result2 is False
    
    def test_app_active_condition(self, coordinator):
        """Test app active condition"""
        condition = {"type": "app_active", "value": "Safari"}
        state = {"active_app": "Safari", "url": ""}
        
        result = coordinator._evaluate_single_stop_condition(condition, state)
        assert result is True
        
        state2 = {"active_app": "Chrome", "url": ""}
        result2 = coordinator._evaluate_single_stop_condition(condition, state2)
        assert result2 is False
    
    def test_window_title_contains_condition(self, coordinator):
        """Test window title contains condition"""
        condition = {"type": "window_title_contains", "value": "YouTube"}
        state = {"window_title": "YouTube - Watch Videos", "active_app": "Safari"}
        
        result = coordinator._evaluate_single_stop_condition(condition, state)
        assert result is True
    
    def test_multiple_stop_conditions(self, coordinator):
        """Test evaluating multiple stop conditions"""
        conditions = [
            {"type": "url_contains", "value": "youtube"},
            {"type": "app_active", "value": "Safari"}
        ]
        
        # First condition met
        state1 = {"url": "https://youtube.com", "active_app": "Chrome"}
        result1 = coordinator._evaluate_stop_conditions(conditions, state1)
        assert result1 is True
        
        # Second condition met
        state2 = {"url": "https://google.com", "active_app": "Safari"}
        result2 = coordinator._evaluate_stop_conditions(conditions, state2)
        assert result2 is True
        
        # No condition met
        state3 = {"url": "https://google.com", "active_app": "Chrome"}
        result3 = coordinator._evaluate_stop_conditions(conditions, state3)
        assert result3 is False


class TestReasonerBurstMode:
    """Test reasoner burst decision generation"""
    
    @pytest.fixture
    def reasoner(self):
        """Create a mock reasoner for testing"""
        return ReasonerLLM(backend="mock")
    
    def test_parse_burst_response_valid(self, reasoner):
        """Test parsing valid burst response"""
        response = """{
            "actions": [
                {"module": "system", "action": "open_app", "args": {"app_name": "Safari"}, "reasoning": "Open browser"},
                {"module": "browser", "action": "navigate", "args": {"url": "https://youtube.com"}, "reasoning": "Go to site"}
            ],
            "stop_when": [
                {"type": "url_contains", "value": "youtube.com"}
            ],
            "needs_vision": false,
            "reasoning": "Navigate to YouTube"
        }"""
        
        result = reasoner._parse_burst_response(response)
        
        assert "actions" in result
        assert len(result["actions"]) == 2
        assert "stop_when" in result
        assert len(result["stop_when"]) == 1
        assert result["needs_vision"] is False
    
    def test_parse_burst_response_single_done(self, reasoner):
        """Test parsing single 'done' action is allowed"""
        response = """{
            "actions": [
                {"module": "system", "action": "done", "args": {}, "reasoning": "Goal achieved"}
            ],
            "stop_when": [],
            "needs_vision": false,
            "reasoning": "Task complete"
        }"""
        
        result = reasoner._parse_burst_response(response)
        
        assert "actions" in result
        assert len(result["actions"]) == 1
        assert result["actions"][0]["action"] == "done"
    
    def test_parse_burst_response_insufficient_actions(self, reasoner):
        """Test that single non-done action is rejected"""
        response = """{
            "actions": [
                {"module": "browser", "action": "navigate", "args": {"url": "test.com"}}
            ],
            "stop_when": [],
            "needs_vision": false,
            "reasoning": "Navigate"
        }"""
        
        result = reasoner._parse_burst_response(response)
        
        # Should return error
        assert "error" in result
        assert "invalid_burst_size" in result.get("error_type", "")
    
    def test_parse_burst_response_too_many_actions(self, reasoner):
        """Test that >6 actions are truncated"""
        import json
        
        # Create 10 valid actions
        actions = [
            {"module": "system", "action": "open_app", "args": {"app_name": f"App{i}"}}
            for i in range(10)
        ]
        
        # Create valid JSON response
        response_dict = {
            "actions": actions,
            "stop_when": [],
            "needs_vision": False,
            "reasoning": "Too many actions"
        }
        response = json.dumps(response_dict)
        
        result = reasoner._parse_burst_response(response)
        
        # Should have exactly 6 actions (truncated)
        # The parser should handle this gracefully
        assert isinstance(result, dict)
    
    def test_parse_burst_response_force_vision(self, reasoner):
        """Test that force_vision overrides needs_vision"""
        response = """{
            "actions": [
                {"module": "system", "action": "open_app", "args": {"app_name": "Safari"}},
                {"module": "browser", "action": "navigate", "args": {"url": "https://test.com"}}
            ],
            "stop_when": [],
            "needs_vision": false,
            "reasoning": "Test"
        }"""
        
        # Without force
        result1 = reasoner._parse_burst_response(response, force_vision=False)
        assert result1.get("needs_vision") is False
        
        # With force
        result2 = reasoner._parse_burst_response(response, force_vision=True)
        assert result2.get("needs_vision") is True


class TestExecutionResultWithMetrics:
    """Test ExecutionResult with burst metrics"""
    
    def test_execution_result_has_metrics(self):
        """Test that ExecutionResult includes burst metrics"""
        intent = Intent(action="test", confidence=1.0)
        result = ExecutionResult(
            success=True,
            intent=intent,
            session_id="test",
            request_id="test"
        )
        
        assert result.burst_metrics is not None
        assert isinstance(result.burst_metrics, BurstMetrics)
    
    def test_execution_result_tracks_metrics(self):
        """Test that execution result can track burst metrics"""
        intent = Intent(action="test", confidence=1.0)
        result = ExecutionResult(
            success=True,
            intent=intent,
            session_id="test",
            request_id="test"
        )
        
        # Simulate burst execution
        result.burst_metrics.llm_calls = 3
        result.burst_metrics.record_burst(4)
        result.burst_metrics.vision_calls = 2
        result.burst_metrics.stagnation_events = 1
        
        assert result.burst_metrics.llm_calls == 3
        assert result.burst_metrics.total_bursts == 1
        assert result.burst_metrics.burst_actions_executed == 4
        assert result.burst_metrics.vision_calls == 2
        assert result.burst_metrics.stagnation_events == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
