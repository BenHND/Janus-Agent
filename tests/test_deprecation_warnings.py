"""
Tests for deprecation warnings on legacy components
TICKET B6 - Architecture Legacy Cleanup
"""
import os
import warnings

import pytest


def test_janus_integrated_removed():
    """Test that JanusIntegrated has been removed as part of cleanup"""
    import importlib.util
    
    # JanusIntegrated should no longer exist
    spec = importlib.util.find_spec("janus_integrated")
    assert spec is None, "janus_integrated.py should have been removed"
    
    # File should not exist
    assert not os.path.exists("janus_integrated.py"), "janus_integrated.py file should be removed"


def test_action_executor_removed():
    """Test that ActionExecutor has been removed (migrated to AgentExecutorV3)"""
    import importlib.util
    
    # ActionExecutor should no longer exist
    try:
        from janus.automation.action_executor import ActionExecutor
        assert False, "ActionExecutor should have been removed (migrated to AgentExecutorV3)"
    except ImportError:
        # Expected - ActionExecutor was migrated to AgentExecutorV3
        pass
    
    # File should not exist
    assert not os.path.exists("janus/automation/action_executor.py"), "action_executor.py file should be removed"


def test_orchestrator_module_docstring_has_hierarchy():
    """Test that orchestrator module __init__.py has hierarchy documentation"""
    # Check the module docstring directly from the file
    with open("janus/orchestrator/__init__.py", "r") as f:
        content = f.read()

    # Should contain hierarchy documentation
    assert "Orchestrator Hierarchy" in content
    assert "WorkflowOrchestrator" in content
    assert "SmartOrchestrator" in content
    assert "PersistentOrchestrator" in content
    assert "RECOMMENDED" in content
    assert "state machine" in content.lower()


def test_migration_guide_exists():
    """Test that migration guide document exists"""
    guide_path = "docs/development/migration-legacy-to-modern.md"
    assert os.path.exists(guide_path), f"Migration guide not found at {guide_path}"

    # Check it has content
    with open(guide_path, "r") as f:
        content = f.read()
        assert len(content) > 1000, "Migration guide seems too short"
        assert "JanusIntegrated" in content
        assert "JanusPipeline" in content
        assert "ActionExecutor" in content
        assert "SmartOrchestrator" in content
        assert "WorkflowOrchestrator" in content
        assert "PersistentOrchestrator" in content


def test_migration_guide_has_examples():
    """Test that migration guide has code examples"""
    with open("docs/development/migration-legacy-to-modern.md", "r") as f:
        content = f.read()

    # Should have example code blocks
    assert "```python" in content
    assert "Before (Legacy" in content
    assert "After (Modern" in content
    assert "Migration Examples" in content


def test_readme_has_orchestrator_guidance():
    """Test that README includes orchestrator guidance"""
    readme_path = "README.md"
    assert os.path.exists(readme_path)

    with open(readme_path, "r") as f:
        content = f.read()
        assert "Architecture & Orchestrators" in content or "Orchestrator" in content
        assert "WorkflowOrchestrator" in content
        assert "SmartOrchestrator" in content
        assert "PersistentOrchestrator" in content
        assert "Choosing the Right Orchestrator" in content or "orchestrator" in content.lower()


def test_readme_has_legacy_deprecation_notice():
    """Test that README mentions deprecated legacy code"""
    with open("README.md", "r") as f:
        content = f.read()

    assert "Deprecated" in content or "deprecated" in content
    assert "JanusIntegrated" in content or "Migration Guide" in content


def test_deprecated_modules_package_removed():
    """Test that deprecated modules package has been cleaned up"""
    # The __init__.py with backward compat aliases should be removed
    assert not os.path.exists("janus/modules/__init__.py"), "janus/modules/__init__.py should be removed"


def test_orchestrator_init_exports_key_classes():
    """Test that orchestrator __init__.py exports expected classes in __all__"""
    with open("janus/orchestrator/__init__.py", "r") as f:
        content = f.read()

    # Should export key orchestrator classes
    assert "WorkflowOrchestrator" in content
    assert "SmartOrchestrator" in content
    assert "PersistentOrchestrator" in content or "PersistentWorkflowOrchestrator" in content
    assert "__all__" in content
