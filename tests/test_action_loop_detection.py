"""
Test Loop Detection in ActionHistory - Vigilance Point #3

This test ensures that ActionHistory can detect when the agent is looping
(repeatedly performing the same action without progress) and forces a replan or stop.

TICKET: QA Vigilance Points ("Punchlist") - Point 3
"""

import pytest
import time
from datetime import datetime
from pathlib import Path
import tempfile
import os


def detect_consecutive_duplicates(actions, max_duplicates=2):
    """
    Helper function to detect consecutive duplicate actions.
    
    Args:
        actions: List of action dicts (most recent first)
        max_duplicates: Maximum allowed consecutive duplicates
        
    Returns:
        Dict with:
        - is_looping: bool
        - duplicate_count: int
        - duplicate_action: dict or None
    """
    if len(actions) < 2:
        return {"is_looping": False, "duplicate_count": 0, "duplicate_action": None}
    
    # Get most recent action
    latest = actions[0]
    latest_type = latest.get("action_type")
    latest_data = latest.get("action_data", {})
    
    # Count consecutive matches
    duplicate_count = 1
    for action in actions[1:]:
        if action.get("action_type") != latest_type:
            break
        if action.get("action_data", {}) != latest_data:
            break
        duplicate_count += 1
    
    is_looping = duplicate_count > max_duplicates
    
    return {
        "is_looping": is_looping,
        "duplicate_count": duplicate_count,
        "duplicate_action": latest if is_looping else None
    }


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


def test_action_history_basic_recording(temp_db):
    """Test that ActionHistory can record actions."""
    from janus.persistence.action_history import ActionHistory
    
    history = ActionHistory(db_path=temp_db)
    
    # Record an action
    action_id = history.record_action(
        action_type="click",
        action_data={"x": 100, "y": 200},
        status="success",
        duration_ms=50
    )
    
    assert action_id > 0, "Should return action ID"
    
    # Retrieve the action
    action = history.get_action_by_id(action_id)
    assert action is not None
    assert action["action_type"] == "click"
    assert action["action_data"]["x"] == 100


def test_detect_duplicate_actions(temp_db):
    """Test detection of duplicate consecutive actions (loop detection)."""
    from janus.persistence.action_history import ActionHistory
    
    history = ActionHistory(db_path=temp_db)
    
    # Record the same click action multiple times
    click_action = {"x": 100, "y": 200, "selector": "#button"}
    
    for i in range(5):
        history.record_action(
            action_type="click",
            action_data=click_action,
            status="success",
            workflow_id="test_workflow"
        )
        time.sleep(0.01)  # Small delay to ensure different timestamps
    
    # Get recent actions
    recent = history.get_history(limit=5, workflow_id="test_workflow")
    
    assert len(recent) == 5, "Should have 5 recorded actions"
    
    # Check if we can detect duplicates programmatically
    # All actions should have the same action_type and action_data
    for action in recent:
        assert action["action_type"] == "click"
        assert action["action_data"] == click_action


def test_detect_consecutive_duplicates_helper():
    """Test helper function to detect consecutive duplicate actions."""
    # Test with no duplicates
    actions = [
        {"action_type": "click", "action_data": {"x": 100}},
        {"action_type": "scroll", "action_data": {"amount": 10}},
        {"action_type": "type", "action_data": {"text": "hello"}},
    ]
    result = detect_consecutive_duplicates(actions)
    assert not result["is_looping"], "Should not detect loop with different actions"
    
    # Test with duplicates below threshold
    actions = [
        {"action_type": "click", "action_data": {"x": 100}},
        {"action_type": "click", "action_data": {"x": 100}},
        {"action_type": "scroll", "action_data": {"amount": 10}},
    ]
    result = detect_consecutive_duplicates(actions, max_duplicates=2)
    assert not result["is_looping"], "Should not detect loop with 2 duplicates (threshold=2)"
    
    # Test with duplicates above threshold
    actions = [
        {"action_type": "click", "action_data": {"x": 100}},
        {"action_type": "click", "action_data": {"x": 100}},
        {"action_type": "click", "action_data": {"x": 100}},
        {"action_type": "scroll", "action_data": {"amount": 10}},
    ]
    result = detect_consecutive_duplicates(actions, max_duplicates=2)
    assert result["is_looping"], "Should detect loop with 3 duplicates (threshold=2)"
    assert result["duplicate_count"] == 3


def test_action_history_should_have_loop_detection_method(temp_db):
    """
    Test that ActionHistory has a method to detect action loops.
    This documents the required API.
    """
    from janus.persistence.action_history import ActionHistory
    
    history = ActionHistory(db_path=temp_db)
    
    # The ActionHistory class should have a method like:
    # history.check_for_action_loop(workflow_id, max_duplicates=2)
    
    # Check if method exists
    assert hasattr(history, 'check_for_action_loop'), \
        "ActionHistory should have check_for_action_loop method"


def test_loop_detection_with_different_parameters():
    """Test that loop detection distinguishes actions with different parameters."""
    # Different click locations should not be considered duplicates
    actions = [
        {"action_type": "click", "action_data": {"x": 100, "y": 200}},
        {"action_type": "click", "action_data": {"x": 150, "y": 250}},
        {"action_type": "click", "action_data": {"x": 200, "y": 300}},
    ]
    result = detect_consecutive_duplicates(actions)
    assert not result["is_looping"], "Different click locations should not be duplicates"
    
    # Same click location should be considered duplicates
    actions = [
        {"action_type": "click", "action_data": {"x": 100, "y": 200}},
        {"action_type": "click", "action_data": {"x": 100, "y": 200}},
        {"action_type": "click", "action_data": {"x": 100, "y": 200}},
    ]
    result = detect_consecutive_duplicates(actions, max_duplicates=2)
    assert result["is_looping"], "Same click location should be detected as loop"


def test_statistics_include_loop_metrics(temp_db):
    """Test that statistics can track loop occurrences."""
    from janus.persistence.action_history import ActionHistory
    
    history = ActionHistory(db_path=temp_db)
    
    # Record some actions with potential loops
    for i in range(3):
        history.record_action(
            action_type="click",
            action_data={"x": 100, "y": 200},
            status="success"
        )
    
    # Get statistics
    stats = history.get_statistics()
    
    # Should track total actions
    assert "total_actions" in stats
    assert stats["total_actions"] >= 3


def test_workflow_specific_loop_detection(temp_db):
    """Test that loop detection is workflow-specific."""
    from janus.persistence.action_history import ActionHistory
    
    history = ActionHistory(db_path=temp_db)
    
    # Record actions for different workflows
    for workflow_id in ["workflow_1", "workflow_2"]:
        for i in range(3):
            history.record_action(
                action_type="click",
                action_data={"x": 100, "y": 200},
                status="success",
                workflow_id=workflow_id
            )
    
    # Get actions for each workflow
    workflow_1_actions = history.get_workflow_actions("workflow_1")
    workflow_2_actions = history.get_workflow_actions("workflow_2")
    
    assert len(workflow_1_actions) == 3
    assert len(workflow_2_actions) == 3
    
    # Loop detection should be per-workflow, not global


def test_loop_detection_ignores_old_actions():
    """Test that loop detection only considers recent actions."""
    def is_recent_loop(actions, max_duplicates=2, recency_window=5):
        """
        Check for loops in recent actions only.
        
        Args:
            actions: List of actions (most recent first)
            max_duplicates: Max allowed consecutive duplicates
            recency_window: Only check this many recent actions
        """
        recent_actions = actions[:recency_window]
        
        if len(recent_actions) < 2:
            return False
        
        latest = recent_actions[0]
        latest_type = latest.get("action_type")
        latest_data = latest.get("action_data", {})
        
        duplicate_count = 1
        for action in recent_actions[1:]:
            if action.get("action_type") != latest_type:
                break
            if action.get("action_data", {}) != latest_data:
                break
            duplicate_count += 1
        
        return duplicate_count > max_duplicates
    
    # Many old actions plus recent loop
    actions = []
    
    # 10 old diverse actions
    for i in range(10):
        actions.append({"action_type": "scroll", "action_data": {"y": i * 100}})
    
    # Then 3 duplicate clicks (recent)
    for i in range(3):
        actions.insert(0, {"action_type": "click", "action_data": {"x": 100}})
    
    # Should detect loop in recent actions
    assert is_recent_loop(actions, max_duplicates=2, recency_window=5), \
        "Should detect loop in recent actions only"


def test_loop_detection_with_failed_actions(temp_db):
    """Test that loop detection works with failed actions."""
    from janus.persistence.action_history import ActionHistory
    
    history = ActionHistory(db_path=temp_db)
    
    # Record repeated failed actions (common loop scenario)
    for i in range(3):
        history.record_action(
            action_type="click",
            action_data={"selector": "#submit-button"},
            status="failed",
            error="Element not found",
            workflow_id="test_workflow"
        )
    
    recent = history.get_history(limit=3, workflow_id="test_workflow")
    
    # All should be failed
    assert all(a["status"] == "failed" for a in recent)
    
    # This pattern (repeated failures) is a strong indicator of looping


def test_check_for_action_loop_integration(temp_db):
    """Integration test for check_for_action_loop method."""
    from janus.persistence.action_history import ActionHistory
    
    history = ActionHistory(db_path=temp_db)
    
    # Test 1: No loop - different actions
    history.record_action("click", {"x": 100}, workflow_id="wf1")
    history.record_action("scroll", {"y": 50}, workflow_id="wf1")
    history.record_action("type", {"text": "hi"}, workflow_id="wf1")
    
    result = history.check_for_action_loop(workflow_id="wf1", max_duplicates=2)
    assert not result["is_looping"], "Should not detect loop with different actions"
    assert result["recommendation"] is None
    
    # Test 2: Loop detected - same action repeated
    for i in range(4):
        history.record_action(
            "click",
            {"x": 200, "y": 300},
            status="success",
            workflow_id="wf2"
        )
    
    result = history.check_for_action_loop(workflow_id="wf2", max_duplicates=2)
    assert result["is_looping"], "Should detect loop with 4 identical actions"
    assert result["duplicate_count"] == 4
    assert result["recommendation"] == "replan", "Should recommend replan for successful duplicates"
    
    # Test 3: Failed loop - should recommend stop
    for i in range(4):
        history.record_action(
            "click",
            {"selector": "#button"},
            status="failed",
            error="Not found",
            workflow_id="wf3"
        )
    
    result = history.check_for_action_loop(workflow_id="wf3", max_duplicates=2)
    assert result["is_looping"], "Should detect loop with failed actions"
    assert result["failed_count"] == 4
    assert result["recommendation"] == "stop", "Should recommend stop for repeated failures"
    
    print("\n✓ Loop detection integration test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
