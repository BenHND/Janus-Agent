"""
Tools Registry - Central Catalog of Available Backend Tools

RAG-001: Unified tool catalog generated from agent decorators
TICKET-P0: Eliminated duplication with module_action_schema.py

Architecture (NEW):
- PRIMARY SOURCE: Auto-generated from @agent_action decorators on registered agents
- FALLBACK: Legacy manual catalog from module_action_schema.py (if agents not available)
- MERGED CATALOG: Combines both sources with deduplication

This ensures:
- Single source of truth (@agent_action decorators)
- No manual maintenance required
- Automatic versioning and validation
- Zero duplication between tools_registry and module_action_schema

Structure:
    Each tool definition contains:
    - id: Unique identifier (e.g., "crm_search_contact")
    - signature: Full function signature with parameters
    - description: Clear description of what the tool does
    - keywords: Space-separated keywords for semantic matching
"""

# Import auto-generated tools
from janus.runtime.core.tool_spec_generator import (
    generate_tools_catalog,
    generate_tools_catalog_from_agents,
    generate_catalog_version_hash,
    get_catalog_stats,
)

# Try to get tools from registered agents (NEW unified approach)
# This will work after agents are registered in the system
try:
    _AGENT_TOOLS = generate_tools_catalog_from_agents()
except Exception:
    # Agents not yet registered (e.g., during import time)
    # Fall back to empty list - will be populated when agents register
    _AGENT_TOOLS = []

# Get legacy tools from module_action_schema for backward compatibility
_LEGACY_MODULE_TOOLS = generate_tools_catalog()

# ============================================================================
# MERGE CATALOGS
# ============================================================================

def _merge_catalogs():
    """
    Merge agent-based tools with legacy module schema tools.
    
    Strategy:
    1. Start with agent-based tools (primary source)
    2. Add legacy module schema tools as fallback
    3. Deduplicate by 'id' (agent tools override legacy if same ID)
    
    Returns:
        Merged and deduplicated tool catalog
    """
    # Use dict for deduplication (agent tools take precedence)
    tools_dict = {}
    
    # Add legacy module tools first (lower priority)
    for tool in _LEGACY_MODULE_TOOLS:
        tools_dict[tool['id']] = tool
    
    # Add/override with agent tools (higher priority)
    for tool in _AGENT_TOOLS:
        tools_dict[tool['id']] = tool
    
    return list(tools_dict.values())


# Public API: Merged catalog for ToolRetrievalService
TOOLS_CATALOG = _merge_catalogs()

# Export count for validation
TOTAL_TOOLS_COUNT = len(TOOLS_CATALOG)

# Catalog version hash for cache invalidation
CATALOG_VERSION_HASH = generate_catalog_version_hash(TOOLS_CATALOG)


# Helper functions for inspection
def get_tool_by_id(tool_id: str):
    """Get a specific tool by ID"""
    for tool in TOOLS_CATALOG:
        if tool['id'] == tool_id:
            return tool
    return None


def get_tools_by_module(module_name: str):
    """Get all tools for a specific module"""
    return [
        tool for tool in TOOLS_CATALOG
        if tool['id'].startswith(f"{module_name}_")
    ]


def refresh_catalog():
    """
    Refresh the tools catalog by regenerating from agents.
    
    Call this after new agents are registered to update the catalog.
    This is useful for dynamic agent registration scenarios.
    """
    global TOOLS_CATALOG, TOTAL_TOOLS_COUNT, CATALOG_VERSION_HASH, _AGENT_TOOLS
    
    # Regenerate agent tools
    try:
        _AGENT_TOOLS = generate_tools_catalog_from_agents()
    except Exception:
        _AGENT_TOOLS = []
    
    # Merge catalogs
    TOOLS_CATALOG = _merge_catalogs()
    TOTAL_TOOLS_COUNT = len(TOOLS_CATALOG)
    CATALOG_VERSION_HASH = generate_catalog_version_hash(TOOLS_CATALOG)

