"""
Tool Specification Generator - RAG-001

Automatically generates ToolSpec catalog from module_action_schema.py and registered agents.
This ensures:
- Single source of truth (module_action_schema.py + agent decorators)
- No manual duplication in tools_registry.py
- Automatic versioning via schema hash
- Compact and stable tool definitions

Architecture:
- Reads ALL_MODULES from module_action_schema for legacy compatibility
- Scans registered agents with @agent_action decorators for dynamic tools
- Converts each ActionDefinition and ActionMetadata to ToolSpec format
- Generates version hash for cache invalidation
- Supports delta-only updates for minimal prompts
"""

import hashlib
import json
from typing import Any, Dict, List, Optional

from janus.runtime.core.module_action_schema import (
    ALL_MODULES,
    ActionDefinition,
    ActionParameter,
    ModuleDefinition,
)


# Stop words for keyword extraction
_STOP_WORDS = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or"}


def _generate_tool_signature(module_name: str, action: ActionDefinition) -> str:
    """
    Generate compact tool signature from action definition.
    
    Format: module.action(param1: type, param2: type)
    Example: browser.open_url(url: string)
    
    Args:
        module_name: Name of the module
        action: Action definition
        
    Returns:
        Formatted signature string
    """
    # Build parameter list
    params = []
    for param in action.parameters:
        param_str = f"{param.name}: {param.type}"
        if param.required:
            params.append(param_str)
        else:
            params.append(f"{param_str}?")  # Optional params marked with ?
    
    params_str = ", ".join(params)
    return f"{module_name}.{action.name}({params_str})"


def _generate_tool_keywords(module_name: str, module_desc: str, action: ActionDefinition) -> str:
    """
    Generate semantic keywords for RAG matching.
    
    Combines:
    - Module name
    - Action name
    - Action description key terms
    - Action aliases
    
    Args:
        module_name: Name of the module
        module_desc: Module description
        action: Action definition
        
    Returns:
        Space-separated keywords string
    """
    keywords = [
        module_name,
        action.name,
    ]
    
    # Add aliases
    keywords.extend(action.aliases)
    
    # Extract key terms from description (simple heuristic)
    # Remove common stop words and take meaningful terms
    desc_words = [
        w.lower().strip(",.()") 
        for w in action.description.split() 
        if len(w) > 3 and w.lower() not in _STOP_WORDS
    ]
    keywords.extend(desc_words[:5])  # Top 5 meaningful words
    
    # Add module description key terms
    module_words = [
        w.lower().strip(",.()") 
        for w in module_desc.split() 
        if len(w) > 3 and w.lower() not in _STOP_WORDS
    ]
    keywords.extend(module_words[:3])  # Top 3 module words
    
    return " ".join(keywords)


def generate_tool_spec_from_action(
    module_name: str,
    module_desc: str,
    action: ActionDefinition
) -> Dict[str, str]:
    """
    Generate a ToolSpec entry from an ActionDefinition.
    
    Args:
        module_name: Name of the module (e.g., "browser")
        module_desc: Description of the module
        action: Action definition from module_action_schema
        
    Returns:
        Tool specification dictionary with:
        - id: Unique identifier (module_action)
        - signature: Full function signature
        - description: Clear description
        - keywords: Space-separated keywords for RAG
    """
    tool_id = f"{module_name}_{action.name}"
    signature = _generate_tool_signature(module_name, action)
    description = action.description
    keywords = _generate_tool_keywords(module_name, module_desc, action)
    
    return {
        "id": tool_id,
        "signature": signature,
        "description": description,
        "keywords": keywords,
    }


def generate_tools_catalog() -> List[Dict[str, str]]:
    """
    Generate complete tools catalog from module_action_schema.
    
    This is the auto-generated replacement for the manual tools_registry.py.
    Legacy function - kept for backward compatibility.
    Use generate_tools_catalog_from_agents() for new code.
    
    Returns:
        List of tool specifications ready for ToolRetrievalService
    """
    catalog = []
    
    for module_name, module in ALL_MODULES.items():
        for action in module.actions:
            tool_spec = generate_tool_spec_from_action(
                module_name,
                module.description,
                action
            )
            catalog.append(tool_spec)
    
    return catalog


def generate_tools_catalog_from_agents() -> List[Dict[str, str]]:
    """
    Generate tools catalog by scanning registered agents with @agent_action decorators.
    
    This is the NEW unified approach that eliminates duplication between
    tools_registry.py and module_action_schema.py.
    
    Returns:
        List of tool specifications from all registered agents
    """
    from janus.runtime.core.agent_registry import get_global_agent_registry
    from janus.capabilities.agents.decorators import list_agent_actions
    
    catalog = []
    registry = get_global_agent_registry()
    
    # Scan all registered agents
    for module_name, agent in registry._agents.items():
        # Get all actions from this agent
        actions = list_agent_actions(agent)
        
        # Convert each action metadata to tool spec
        for metadata in actions:
            try:
                tool_spec = metadata.to_tool_spec()
                catalog.append(tool_spec)
            except ValueError as e:
                # Skip actions without agent_name set
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Skipping action {metadata.name}: {e}")
                continue
    
    return catalog


def generate_catalog_version_hash(catalog: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Generate a version hash for the tools catalog.
    
    This hash changes whenever the schema changes, enabling:
    - Cache invalidation on schema updates
    - Version tracking for debugging
    - Delta detection between versions
    
    Args:
        catalog: Optional catalog to hash. If None, generates from current schema.
        
    Returns:
        SHA256 hash of the catalog (first 16 chars)
    """
    if catalog is None:
        catalog = generate_tools_catalog()
    
    # Create deterministic JSON representation
    catalog_json = json.dumps(catalog, sort_keys=True)
    
    # Compute SHA256 hash
    hash_obj = hashlib.sha256(catalog_json.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()
    
    # Return first 16 characters for compact version ID
    return hash_hex[:16]


def get_catalog_stats() -> Dict[str, Any]:
    """
    Get statistics about the generated catalog.
    
    Returns:
        Statistics dictionary with:
        - total_tools: Number of tools
        - total_modules: Number of modules
        - tools_per_module: Dict of module -> tool count
        - version_hash: Current version hash
    """
    catalog = generate_tools_catalog()
    
    tools_per_module = {}
    for module_name, module in ALL_MODULES.items():
        tools_per_module[module_name] = len(module.actions)
    
    return {
        "total_tools": len(catalog),
        "total_modules": len(ALL_MODULES),
        "tools_per_module": tools_per_module,
        "version_hash": generate_catalog_version_hash(catalog),
    }


def get_compact_tools_for_prompt(
    tools: List[Dict[str, str]], 
    language: str = "en",
    max_tools: Optional[int] = None
) -> str:
    """
    Format tools in a compact way for LLM prompts.
    
    This replaces the hardcoded schemas in prompt templates with
    dynamically generated content from the actual tool catalog.
    
    Args:
        tools: List of tool specifications
        language: Language for formatting ("en" or "fr")
        max_tools: Optional limit on number of tools to include
        
    Returns:
        Formatted string for inclusion in LLM prompt
    """
    if max_tools:
        tools = tools[:max_tools]
    
    if language == "fr":
        prompt = "**OUTILS DISPONIBLES:**\n\n"
    else:
        prompt = "**AVAILABLE TOOLS:**\n\n"
    
    # Group tools by module/agent
    tools_by_module = {}
    for tool in tools:
        # Extract module from id (e.g., "crm_search_contact" -> "crm")
        tool_id = tool.get("id", "")
        parts = tool_id.split("_", 1)
        if len(parts) == 2:
            module = parts[0]
        else:
            module = "other"
        
        if module not in tools_by_module:
            tools_by_module[module] = []
        tools_by_module[module].append(tool)
    
    # Format each module's tools
    for module, module_tools in sorted(tools_by_module.items()):
        prompt += f"**{module.upper()}:**\n"
        for tool in module_tools:
            signature = tool.get("signature", "")
            description = tool.get("description", "")
            prompt += f"  - `{signature}`: {description}\n"
        prompt += "\n"
    
    return prompt


# Pre-generate catalog for import
GENERATED_TOOLS_CATALOG = generate_tools_catalog()
CATALOG_VERSION_HASH = generate_catalog_version_hash(GENERATED_TOOLS_CATALOG)


if __name__ == "__main__":
    # CLI for testing/debugging
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        stats = get_catalog_stats()
        print("=" * 60)
        print("Tool Catalog Statistics")
        print("=" * 60)
        print(f"Total Tools: {stats['total_tools']}")
        print(f"Total Modules: {stats['total_modules']}")
        print(f"Version Hash: {stats['version_hash']}")
        print("\nTools per Module:")
        for module, count in stats['tools_per_module'].items():
            print(f"  {module}: {count} tools")
        print("=" * 60)
    elif len(sys.argv) > 1 and sys.argv[1] == "--export":
        # Export catalog as JSON
        catalog = generate_tools_catalog()
        print(json.dumps(catalog, indent=2))
    else:
        # Show sample
        catalog = generate_tools_catalog()
        print(f"Generated {len(catalog)} tools from module_action_schema")
        print("\nSample tools:")
        for tool in catalog[:5]:
            print(f"\n  {tool['id']}")
            print(f"  Signature: {tool['signature']}")
            print(f"  Description: {tool['description'][:60]}...")
