"""
Basic tests for atomic agents after TICKET-AUDIT-002 refactoring.

These tests validate the basic structure and atomic operations contract
without requiring full dependencies like pyautogui.
"""

import pytest


def test_base_agent_imports():
    """Test that BaseAgent can be imported with atomic operations documentation."""
    from janus.capabilities.agents.base_agent import BaseAgent, AgentExecutionError
    
    # Check that BaseAgent has the atomic operations documentation
    assert "ATOMIC" in BaseAgent.__doc__
    assert "< 20 lines" in BaseAgent.__doc__


def test_browser_agent_structure():
    """Test that BrowserAgent has been refactored to atomic operations."""
    # Import should work even without OS dependencies
    try:
        from janus.capabilities.agents.browser_agent import BrowserAgent
        
        # Check the class has atomic operations documented
        assert "Atomic" in BrowserAgent.__doc__ or "atomic" in BrowserAgent.__doc__
        
        # Agent should have the right name
        agent = BrowserAgent()
        assert agent.agent_name == "browser"
        
        print("✓ BrowserAgent structure validated")
    except ImportError as e:
        pytest.skip(f"BrowserAgent dependencies not available: {e}")


def test_files_agent_structure():
    """Test that FilesAgent has been refactored to atomic operations."""
    try:
        from janus.capabilities.agents.files_agent import FilesAgent
        
        # Check the class has atomic operations documented
        assert "Atomic" in FilesAgent.__doc__ or "atomic" in FilesAgent.__doc__
        
        # Agent should have the right name
        agent = FilesAgent()
        assert agent.agent_name == "files"
        
        print("✓ FilesAgent structure validated")
    except ImportError as e:
        pytest.skip(f"FilesAgent dependencies not available: {e}")


def test_adapters_directory_deleted():
    """Test that the adapters directory has been deleted."""
    import os
    from pathlib import Path
    
    # Get the janus/agents directory
    agents_dir = Path(__file__).parent.parent / "janus" / "agents"
    
    # Check that adapters directory does not exist
    adapters_dir = agents_dir / "adapters"
    assert not adapters_dir.exists(), "adapters directory should be deleted (TICKET-AUDIT-002)"
    
    # But backup should exist
    backup_dir = agents_dir / "adapters_legacy_backup"
    assert backup_dir.exists(), "adapters backup should exist for reference"
    
    print("✓ Adapters directory successfully deleted")


def test_browser_agent_line_count():
    """Test that BrowserAgent is under 500 lines as required."""
    from pathlib import Path
    
    browser_agent_file = Path(__file__).parent.parent / "janus" / "agents" / "browser_agent.py"
    
    with open(browser_agent_file) as f:
        lines = f.readlines()
    
    line_count = len(lines)
    assert line_count < 500, f"BrowserAgent should be < 500 lines, got {line_count}"
    
    print(f"✓ BrowserAgent is {line_count} lines (target: < 500)")


def test_files_agent_line_count():
    """Test that FilesAgent is under 500 lines as required."""
    from pathlib import Path
    
    files_agent_file = Path(__file__).parent.parent / "janus" / "agents" / "files_agent.py"
    
    with open(files_agent_file) as f:
        lines = f.readlines()
    
    line_count = len(lines)
    assert line_count < 500, f"FilesAgent should be < 500 lines, got {line_count}"
    
    print(f"✓ FilesAgent is {line_count} lines (target: < 500)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
