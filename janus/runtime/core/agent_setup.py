"""
Agent Registry Setup and Configuration (V3)

This module handles registration of all V3 execution agents with the AgentRegistry.
Provides a centralized place to configure the stable module → agent mappings.

V3 Architecture:
- Each agent inherits from BaseAgent and implements async execute()
- Agents are pure executors - no interpretation or planning
- All 8 agents follow the same interface and logging standards

TICKET-ARCH-AGENT: Added auto-discovery support for automatic agent registration
"""

import logging
from typing import Optional

from .agent_registry import AgentRegistry, get_global_agent_registry

logger = logging.getLogger(__name__)


def setup_agent_registry(
    registry: Optional[AgentRegistry] = None,
    use_v3_agents: bool = True,
    use_auto_discovery: bool = False
) -> AgentRegistry:
    """
    Setup and configure the agent registry with V3 execution agents.
    
    This function:
    1. Creates or uses provided AgentRegistry
    2. Registers all V3 execution agents (manual or auto-discovery)
    3. Handles missing dependencies gracefully
    
    TICKET 201: Removed legacy adapter registration to prevent overwriting V3 agents.
    TICKET-111 (B): Reduced logging verbosity, only log summary.
    TICKET-ARCH-AGENT: Added auto-discovery option for automatic agent registration.
    
    V3 Agent Mappings:
    - system → SystemAgent (macOS system operations)
    - browser → BrowserAgent (web browser automation)
    - messaging → MessagingAgent (Teams, Slack, Discord)
    - files → FilesAgent (file system operations)
    - code → CodeAgent (VSCode automation)
    - ui → UIAgent (generic UI interactions)
    - llm → LLMAgent (text transformations)
    - scheduler → SchedulerAgent (task scheduling)
    - crm → CRMAgent (Salesforce CRM)
    
    Args:
        registry: Optional AgentRegistry instance (creates global if None)
        use_v3_agents: If True, use new V3 agents; if False, use legacy adapters
        use_auto_discovery: If True, use auto-discovery to find and register agents
    
    Returns:
        Configured AgentRegistry with all available agents registered
    """
    if registry is None:
        registry = get_global_agent_registry()
    
    # TICKET-111 (B3): Reduced log level to debug
    mode = "auto-discovery" if use_auto_discovery else ("V3 agents" if use_v3_agents else "legacy adapters")
    logger.debug(f"Setting up agent registry with {mode}...")
    
    if use_auto_discovery:
        # TICKET-ARCH-AGENT: Use auto-discovery to find and register all agents
        _register_via_auto_discovery(registry)
    elif use_v3_agents:
        # Register V3 agents manually (preferred)
        _register_v3_agents(registry)
    else:
        # Register legacy adapters (backward compatibility)
        _register_legacy_adapters(registry)
    
    # Log summary (at info level - only once at boot)
    registered_modules = registry.list_modules()
    logger.info(f"✓ Agent registry ready: {len(registered_modules)} modules")
    logger.debug(f"Registered modules: {', '.join(registered_modules.keys())}")
    
    return registry


def _register_via_auto_discovery(registry: AgentRegistry) -> None:
    """
    Register agents via auto-discovery mechanism.
    
    TICKET-ARCH-AGENT: Use auto-discovery to find and register all agents
    automatically without manual registration.
    
    Args:
        registry: AgentRegistry instance
    """
    try:
        from janus.capabilities.agents.discovery import auto_setup_agents
        
        # Auto-discover and register all agents
        count = auto_setup_agents(registry)
        logger.info(f"✓ Auto-registered {count} agents via discovery")
    except Exception as e:
        logger.error(f"Failed to auto-register agents: {e}")
        # Fallback to manual registration
        logger.warning("Falling back to manual V3 agent registration")
        _register_v3_agents(registry)


def _register_v3_agents(registry: AgentRegistry) -> None:
    """
    Register all V3 execution agents.
    
    TICKET 203 (A2): Skip re-registration if agent already registered.
    TICKET-111 (B3): Reduced logging verbosity.
    
    Args:
        registry: AgentRegistry instance
    """
    # Register SystemAgent (macOS system operations)
    if not registry.has_agent("system"):
        try:
            from janus.capabilities.agents import SystemAgent
            system_agent = SystemAgent()
            registry.register("system", system_agent)
            logger.debug("Registered V3 'system' agent")
        except Exception as e:
            logger.warning(f"Could not register V3 system agent: {e}")
    
    # Register BrowserAgent (web browser automation)
    if not registry.has_agent("browser"):
        try:
            from janus.capabilities.agents import BrowserAgent
            browser_agent = BrowserAgent()
            registry.register("browser", browser_agent)
            logger.debug("Registered V3 'browser' agent")
        except Exception as e:
            logger.warning(f"Could not register V3 browser agent: {e}")
    
    # Register MessagingAgent (messaging platforms)
    if not registry.has_agent("messaging"):
        try:
            from janus.capabilities.agents import MessagingAgent
            messaging_agent = MessagingAgent()
            registry.register("messaging", messaging_agent)
            logger.debug("Registered V3 'messaging' agent")
        except Exception as e:
            logger.warning(f"Could not register V3 messaging agent: {e}")
    
    # Register FilesAgent (file operations)
    if not registry.has_agent("files"):
        try:
            from janus.capabilities.agents import FilesAgent
            files_agent = FilesAgent()
            registry.register("files", files_agent)
            logger.debug("Registered V3 'files' agent")
        except Exception as e:
            logger.warning(f"Could not register V3 files agent: {e}")
    
    # Register CodeAgent (code editor)
    if not registry.has_agent("code"):
        try:
            from janus.capabilities.agents import CodeAgent
            code_agent = CodeAgent()
            registry.register("code", code_agent)
            logger.debug("Registered V3 'code' agent")
        except Exception as e:
            logger.warning(f"Could not register V3 code agent: {e}")
    
    # Register UIAgent (UI interactions)
    if not registry.has_agent("ui"):
        try:
            from janus.capabilities.agents import UIAgent
            ui_agent = UIAgent()
            registry.register("ui", ui_agent)
            logger.debug("Registered V3 'ui' agent")
        except Exception as e:
            logger.warning(f"Could not register V3 ui agent: {e}")
    
    # Register LLMAgent (text transformations)
    if not registry.has_agent("llm"):
        try:
            from janus.capabilities.agents import LLMAgent
            llm_agent = LLMAgent()
            registry.register("llm", llm_agent)
            logger.debug("Registered V3 'llm' agent")
        except Exception as e:
            logger.warning(f"Could not register V3 llm agent: {e}")
    
    # Register SchedulerAgent (task scheduling) - TICKET-FEAT-002
    if not registry.has_agent("scheduler"):
        try:
            from janus.capabilities.agents import SchedulerAgent
            scheduler_agent = SchedulerAgent()
            registry.register("scheduler", scheduler_agent)
            logger.debug("Registered V3 'scheduler' agent")
        except Exception as e:
            logger.warning(f"Could not register V3 scheduler agent: {e}")


def _register_legacy_adapters(registry: AgentRegistry) -> None:
    """
    DEPRECATED (TICKET-AUDIT-002): Legacy adapter registration no longer used.
    
    Register legacy adapters for backward compatibility.
    
    TICKET 201: This function is only called when use_v3_agents=False.
    Legacy adapters should NOT be registered after V3 agents.
    
    TICKET-303: Adapters moved to janus.agents.adapters (now removed)
    TICKET-AUDIT-002: Adapters completely removed from codebase
    
    Args:
        registry: AgentRegistry instance (unused)
    """
    logger.warning("_register_legacy_adapters called but adapters have been removed (TICKET-AUDIT-002)")
    # No-op - adapters are gone
    return
