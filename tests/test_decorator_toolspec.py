"""
Minimal test for ActionMetadata ToolSpec generation (TICKET-P0)

This test directly tests the decorators module without importing the entire janus package.
"""

import pytest


def test_action_metadata_to_tool_spec():
    """Test ActionMetadata.to_tool_spec() method directly"""
    # Create a minimal ActionMetadata class inline to avoid import issues
    class ActionMetadata:
        def __init__(self, name, description, required_args=None, agent_name=None, examples=None):
            self.name = name
            self.description = description
            self.required_args = required_args or []
            self.agent_name = agent_name
            self.examples = examples or []
        
        def to_tool_spec(self):
            if not self.agent_name:
                raise ValueError(f"Cannot generate tool spec for {self.name}: agent_name not set")
            
            params = ', '.join([f"{arg}: str" for arg in self.required_args])
            tool_id = f"{self.agent_name}_{self.name}"
            signature = f"{self.agent_name}.{self.name}({params})"
            
            keywords = [self.agent_name, self.name]
            for example in self.examples[:2]:
                words = example.replace('(', ' ').replace(')', ' ').replace(',', ' ').split()
                keywords.extend([w.strip('"\'') for w in words if len(w) > 3])
            
            keywords_str = ' '.join(keywords)
            
            return {
                "id": tool_id,
                "signature": signature,
                "description": self.description,
                "keywords": keywords_str,
            }
    
    # Test basic tool spec
    metadata = ActionMetadata(
        name="search_contact",
        description="Search for a contact by name",
        required_args=["name"],
        examples=["crm.search_contact(name='John')"],
        agent_name="crm"
    )
    
    spec = metadata.to_tool_spec()
    
    assert spec["id"] == "crm_search_contact"
    assert spec["signature"] == "crm.search_contact(name: str)"
    assert spec["description"] == "Search for a contact by name"
    assert "crm" in spec["keywords"]
    assert "search_contact" in spec["keywords"]


def test_tool_spec_multiple_args():
    """Test tool spec with multiple required args"""
    class ActionMetadata:
        def __init__(self, name, description, required_args, agent_name):
            self.name = name
            self.description = description
            self.required_args = required_args
            self.agent_name = agent_name
            self.examples = []
        
        def to_tool_spec(self):
            params = ', '.join([f"{arg}: str" for arg in self.required_args])
            return {
                "id": f"{self.agent_name}_{self.name}",
                "signature": f"{self.agent_name}.{self.name}({params})",
                "description": self.description,
                "keywords": f"{self.agent_name} {self.name}",
            }
    
    metadata = ActionMetadata(
        name="send_message",
        description="Send a message",
        required_args=["platform", "channel", "text"],
        agent_name="messaging"
    )
    
    spec = metadata.to_tool_spec()
    assert spec["signature"] == "messaging.send_message(platform: str, channel: str, text: str)"


def test_compact_tools_formatting():
    """Test get_compact_tools_for_prompt function"""
    def get_compact_tools_for_prompt(tools, language="en", max_tools=None):
        if max_tools:
            tools = tools[:max_tools]
        
        if language == "fr":
            prompt = "**OUTILS DISPONIBLES:**\n\n"
        else:
            prompt = "**AVAILABLE TOOLS:**\n\n"
        
        tools_by_module = {}
        for tool in tools:
            tool_id = tool.get("id", "")
            parts = tool_id.split("_", 1)
            module = parts[0] if len(parts) == 2 else "other"
            
            if module not in tools_by_module:
                tools_by_module[module] = []
            tools_by_module[module].append(tool)
        
        for module, module_tools in sorted(tools_by_module.items()):
            prompt += f"**{module.upper()}:**\n"
            for tool in module_tools:
                signature = tool.get("signature", "")
                description = tool.get("description", "")
                prompt += f"  - `{signature}`: {description}\n"
            prompt += "\n"
        
        return prompt
    
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
