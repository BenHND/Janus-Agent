"""
Test Tools Registry Unification (TICKET-P0)

Tests for the unified tools registry that generates catalogs from agent decorators
instead of maintaining duplicate manual lists.

Note: These tests may fail if dependencies are not installed. See test_decorator_toolspec.py
for minimal standalone tests that don't require full dependencies.
"""

import pytest


class TestActionMetadataToolSpec:
    """Test ActionMetadata.to_tool_spec() method"""
    
    def test_to_tool_spec_basic(self):
        """Test basic tool spec generation"""
        # Import locally to avoid circular dependencies
        from janus.capabilities.agents.decorators import ActionMetadata
        
        metadata = ActionMetadata(
            name="search_contact",
            description="Search for a contact by name",
            required_args=["name"],
            optional_args={"limit": 10},
            examples=["crm.search_contact(name='John')"],
            agent_name="crm"
        )
        
        spec = metadata.to_tool_spec()
        
        assert spec["id"] == "crm_search_contact"
        assert spec["signature"] == "crm.search_contact(name: str)"
        assert spec["description"] == "Search for a contact by name"
        assert "keywords" in spec
        assert "crm" in spec["keywords"]
        assert "search_contact" in spec["keywords"]
    
    def test_to_tool_spec_multiple_args(self):
        """Test tool spec with multiple required args"""
        from janus.capabilities.agents.decorators import ActionMetadata
        
        metadata = ActionMetadata(
            name="send_message",
            description="Send a message",
            required_args=["platform", "channel", "text"],
            agent_name="messaging"
        )
        
        spec = metadata.to_tool_spec()
        
        assert spec["signature"] == "messaging.send_message(platform: str, channel: str, text: str)"
    
    def test_to_tool_spec_no_args(self):
        """Test tool spec with no arguments"""
        from janus.capabilities.agents.decorators import ActionMetadata
        
        metadata = ActionMetadata(
            name="get_active_app",
            description="Get the active application",
            required_args=[],
            agent_name="system"
        )
        
        spec = metadata.to_tool_spec()
        
        assert spec["signature"] == "system.get_active_app()"
    
    def test_to_tool_spec_without_agent_name_fails(self):
        """Test that tool spec generation fails without agent_name"""
        from janus.capabilities.agents.decorators import ActionMetadata
        
        metadata = ActionMetadata(
            name="test_action",
            description="Test action",
            required_args=[]
        )
        
        with pytest.raises(ValueError, match="agent_name not set"):
            metadata.to_tool_spec()


class TestRiskLevel:
    """Test risk_level parameter in decorators"""
    
    def test_risk_level_in_metadata(self):
        """Test that risk_level is stored in metadata"""
        from janus.capabilities.agents.decorators import ActionMetadata
        
        metadata = ActionMetadata(
            name="delete_file",
            description="Delete a file",
            required_args=["path"],
            agent_name="files",
            risk_level="high"
        )
        
        assert metadata.risk_level == "high"
        
        metadata_dict = metadata.to_dict()
        assert metadata_dict["risk_level"] == "high"
    
    def test_risk_level_default(self):
        """Test that default risk_level is low"""
        from janus.capabilities.agents.decorators import ActionMetadata
        
        metadata = ActionMetadata(
            name="read_file",
            description="Read a file",
            required_args=["path"],
            agent_name="files"
        )
        
        assert metadata.risk_level == "low"


class TestToolSpecFormatting:
    """Test compact tool formatting for prompts"""
    
    def test_get_compact_tools_for_prompt_english(self):
        """Test compact formatting for LLM prompts in English"""
        # Import locally
        from janus.runtime.core.tool_spec_generator import get_compact_tools_for_prompt
        
        tools = [
            {
                "id": "crm_search_contact",
                "signature": "crm.search_contact(name: str)",
                "description": "Search for a contact",
                "keywords": "crm contact search"
            },
            {
                "id": "browser_open_url",
                "signature": "browser.open_url(url: str)",
                "description": "Open a URL",
                "keywords": "browser url open"
            }
        ]
        
        formatted = get_compact_tools_for_prompt(tools, language="en")
        
        assert "AVAILABLE TOOLS" in formatted
        assert "crm.search_contact" in formatted
        assert "browser.open_url" in formatted
        assert "Search for a contact" in formatted
    
    def test_get_compact_tools_for_prompt_french(self):
        """Test compact formatting for LLM prompts in French"""
        from janus.runtime.core.tool_spec_generator import get_compact_tools_for_prompt
        
        tools = [
            {
                "id": "system_open_app",
                "signature": "system.open_app(app_name: str)",
                "description": "Ouvrir une application",
                "keywords": "system application open"
            }
        ]
        
        formatted = get_compact_tools_for_prompt(tools, language="fr")
        
        assert "OUTILS DISPONIBLES" in formatted
        assert "system.open_app" in formatted
    
    def test_get_compact_tools_max_limit(self):
        """Test limiting number of tools in prompt"""
        from janus.runtime.core.tool_spec_generator import get_compact_tools_for_prompt
        
        tools = [
            {"id": f"tool_{i}", "signature": f"tool_{i}()", "description": f"Tool {i}", "keywords": ""}
            for i in range(10)
        ]
        
        formatted = get_compact_tools_for_prompt(tools, max_tools=3)
        
        # Should only include first 3 tools
        assert "tool_0" in formatted
        assert "tool_1" in formatted
        assert "tool_2" in formatted
        assert "tool_3" not in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
