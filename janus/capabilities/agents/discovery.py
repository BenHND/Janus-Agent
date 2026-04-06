"""
Agent Auto-Discovery - Automatic Registration Without Manual Registry

TICKET-ARCH-AGENT: Architecture Agentique - Solution propre, stable et extensible

This module provides automatic discovery and registration of agents by scanning
the capabilities/agents directory.

Features:
- Auto-discovery of all agent classes
- Auto-registration with AgentRegistry
- Metadata collection from @agent_action decorators
- Documentation generation support
"""

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .base_agent import BaseAgent
from .decorators import list_agent_actions, ActionMetadata

logger = logging.getLogger(__name__)


class AgentDiscovery:
    """
    Auto-discovery mechanism for agents.
    
    Scans the capabilities/agents directory and automatically:
    - Finds all agent classes (subclasses of BaseAgent)
    - Collects metadata from @agent_action decorators
    - Registers agents with the AgentRegistry
    """
    
    def __init__(self):
        """Initialize agent discovery."""
        self._discovered_agents: Dict[str, Type[BaseAgent]] = {}
        self._agent_metadata: Dict[str, List[ActionMetadata]] = {}
    
    def discover_agents(self, package_name: str = "janus.capabilities.agents") -> Dict[str, Type[BaseAgent]]:
        """
        Discover all agent classes in the package.
        
        Args:
            package_name: Package to scan for agents
        
        Returns:
            Dict mapping agent names to agent classes
        """
        logger.info(f"🔍 Discovering agents in package: {package_name}")
        
        try:
            # Import the package
            package = importlib.import_module(package_name)
            package_path = Path(package.__file__).parent
            
            # Scan all modules in the package
            for module_info in pkgutil.iter_modules([str(package_path)]):
                module_name = module_info.name
                
                # Skip special modules
                if module_name.startswith("_") or module_name in ["base_agent", "decorators", "discovery"]:
                    continue
                
                try:
                    # Import the module
                    full_module_name = f"{package_name}.{module_name}"
                    module = importlib.import_module(full_module_name)
                    
                    # Find agent classes in the module
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        # Check if it's a BaseAgent subclass (but not BaseAgent itself)
                        if (
                            issubclass(obj, BaseAgent) and 
                            obj is not BaseAgent and
                            obj.__module__ == full_module_name
                        ):
                            agent_name = self._get_agent_name(obj)
                            self._discovered_agents[agent_name] = obj
                            logger.debug(f"  ✓ Discovered agent: {agent_name} ({obj.__name__})")
                
                except Exception as e:
                    logger.warning(f"  ✗ Failed to scan module {module_name}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to discover agents in {package_name}: {e}")
        
        logger.info(f"✓ Discovered {len(self._discovered_agents)} agents")
        return self._discovered_agents
    
    def _get_agent_name(self, agent_class: Type[BaseAgent]) -> str:
        """
        Get the agent name from the class.
        
        Tries to extract from:
        1. Class attribute 'agent_name'
        2. Class name without 'Agent' suffix
        
        Args:
            agent_class: Agent class
        
        Returns:
            Agent name (lowercase)
        """
        # Try to get from class attribute (if instantiated)
        if hasattr(agent_class, 'agent_name'):
            return agent_class.agent_name
        
        # Derive from class name
        class_name = agent_class.__name__
        if class_name.endswith("Agent"):
            class_name = class_name[:-5]  # Remove "Agent" suffix
        
        return class_name.lower()
    
    def collect_metadata(self, agent_instance: BaseAgent) -> List[ActionMetadata]:
        """
        Collect action metadata from an agent instance.
        
        Args:
            agent_instance: Agent instance
        
        Returns:
            List of ActionMetadata for all decorated actions
        """
        agent_name = agent_instance.agent_name
        
        if agent_name not in self._agent_metadata:
            actions = list_agent_actions(agent_instance)
            self._agent_metadata[agent_name] = actions
            logger.debug(f"  ✓ Collected {len(actions)} actions for agent: {agent_name}")
        
        return self._agent_metadata[agent_name]
    
    def get_all_metadata(self) -> Dict[str, List[ActionMetadata]]:
        """
        Get all collected metadata.
        
        Returns:
            Dict mapping agent names to lists of ActionMetadata
        """
        return self._agent_metadata
    
    def auto_register_agents(self, registry, **kwargs) -> int:
        """
        Automatically register all discovered agents with the registry.
        
        Args:
            registry: AgentRegistry instance
            **kwargs: Additional arguments to pass to agent constructors
        
        Returns:
            Number of agents registered
        """
        logger.info("🚀 Auto-registering discovered agents...")
        
        registered_count = 0
        
        for agent_name, agent_class in self._discovered_agents.items():
            try:
                # Check if already registered
                if registry.has_agent(agent_name):
                    logger.debug(f"  ⊘ Agent '{agent_name}' already registered, skipping")
                    continue
                
                # Instantiate the agent
                # Try to pass relevant kwargs based on agent requirements
                agent_instance = self._instantiate_agent(agent_class, agent_name, **kwargs)
                
                # Register the agent
                registry.register(agent_name, agent_instance)
                
                # Collect metadata
                self.collect_metadata(agent_instance)
                
                registered_count += 1
                logger.debug(f"  ✓ Registered agent: {agent_name}")
            
            except Exception as e:
                logger.warning(f"  ✗ Failed to register agent '{agent_name}': {e}")
        
        logger.info(f"✓ Auto-registered {registered_count} agents")
        return registered_count
    
    def _instantiate_agent(self, agent_class: Type[BaseAgent], agent_name: str, **kwargs) -> BaseAgent:
        """
        Instantiate an agent with appropriate parameters.
        
        Tries to match kwargs to agent constructor parameters.
        
        Args:
            agent_class: Agent class to instantiate
            agent_name: Name of the agent
            **kwargs: Potential arguments for the constructor
        
        Returns:
            Instantiated agent
        """
        # Get constructor signature
        sig = inspect.signature(agent_class.__init__)
        params = sig.parameters
        
        # Build constructor arguments
        constructor_args = {}
        
        for param_name, param in params.items():
            if param_name == "self":
                continue
            
            # Check if we have this parameter in kwargs
            if param_name in kwargs:
                constructor_args[param_name] = kwargs[param_name]
            elif param.default is not inspect.Parameter.empty:
                # Has default value, don't need to provide
                pass
            else:
                # Required parameter not available, will try without it
                pass
        
        # Try to instantiate
        try:
            return agent_class(**constructor_args)
        except TypeError as e:
            # If constructor fails, log warning and try without any arguments
            logger.warning(
                f"Failed to instantiate {agent_name} with constructor args "
                f"(error: {e}), trying without args"
            )
            try:
                return agent_class()
            except Exception as e2:
                logger.error(f"Failed to instantiate {agent_name} even without args: {e2}")
                raise
    
    def generate_documentation(self) -> str:
        """
        Generate documentation for all discovered agents and their actions.
        
        Returns:
            Formatted documentation string
        """
        lines = ["# Janus Agent Documentation\n"]
        lines.append("Auto-generated documentation for all available agents and actions.\n")
        
        for agent_name in sorted(self._discovered_agents.keys()):
            agent_class = self._discovered_agents[agent_name]
            actions = self._agent_metadata.get(agent_name, [])
            
            lines.append(f"\n## {agent_name.capitalize()} Agent\n")
            lines.append(f"**Class**: `{agent_class.__name__}`\n")
            
            if agent_class.__doc__:
                lines.append(f"{agent_class.__doc__.strip()}\n")
            
            if actions:
                lines.append(f"\n### Actions ({len(actions)})\n")
                
                for action in sorted(actions, key=lambda a: a.name):
                    lines.append(f"\n#### `{agent_name}.{action.name}`\n")
                    lines.append(f"{action.description}\n")
                    
                    if action.required_args:
                        lines.append(f"\n**Required Arguments**:\n")
                        for arg in action.required_args:
                            lines.append(f"- `{arg}`\n")
                    
                    if action.optional_args:
                        lines.append(f"\n**Optional Arguments**:\n")
                        for arg, default in action.optional_args.items():
                            lines.append(f"- `{arg}` (default: `{default}`)\n")
                    
                    if action.providers:
                        lines.append(f"\n**Supported Providers**: {', '.join(action.providers)}\n")
                    
                    if action.examples:
                        lines.append(f"\n**Examples**:\n")
                        for example in action.examples:
                            lines.append(f"```python\n{example}\n```\n")
            else:
                lines.append("\nNo actions discovered (agent may not use @agent_action decorator)\n")
        
        return "".join(lines)


# Global singleton
_global_discovery: Optional[AgentDiscovery] = None


def get_agent_discovery() -> AgentDiscovery:
    """
    Get or create the global agent discovery singleton.
    
    Returns:
        Global AgentDiscovery instance
    """
    global _global_discovery
    if _global_discovery is None:
        _global_discovery = AgentDiscovery()
    return _global_discovery


def auto_setup_agents(registry, **kwargs) -> int:
    """
    Convenience function to discover and register all agents.
    
    Args:
        registry: AgentRegistry instance
        **kwargs: Additional arguments to pass to agent constructors
    
    Returns:
        Number of agents registered
    """
    discovery = get_agent_discovery()
    discovery.discover_agents()
    return discovery.auto_register_agents(registry, **kwargs)
