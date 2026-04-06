"""
Agent Registry for JSON V3 Execution Engine (TICKET 005)

This module provides stable mapping from module names to execution agents/adapters.
Ensures that actions are routed to the correct handler without confusion.

Stable Mappings:
- system → SystemAgent (app opening, system actions)
- browser → BrowserAgent (Chrome/Safari web automation)  
- files → FilesAgent (file operations)
- messaging → MessagingAgent (Slack, email, etc.)
- code → CodeAgent (VSCode, editor actions)
- ui → UIAgent (UI automation, vision-based actions)
- llm → LLMAgent (LLM interactions, summarization)
- terminal → TerminalAgent (shell command execution)
- finder → FinderAgent (macOS Finder operations)
"""

import asyncio
import inspect
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Centralized registry for mapping modules to agents/adapters.
    
    Provides stable, predictable routing for JSON V3 step execution.
    Each module name maps to a specific adapter that handles its actions.
    """

    def __init__(self):
        """
        Initialize empty agent registry.
        
        TICKET-111 (B): This should only be called once via get_global_agent_registry().
        Do not instantiate directly.
        """
        self._agents: Dict[str, Any] = {}
        self._module_aliases: Dict[str, str] = {
            # Common aliases for backward compatibility
            "chrome": "browser",
            "safari": "browser",
            "vscode": "code",
            "slack": "messaging",
            # TICKET-ARCH-002: Removed hardcoded "salesforce" alias
            # CRM module should be accessed generically
            "vision": "ui",
            "default": "system",  # Legacy "default" module
            "automation": "system",  # Legacy "automation" module
            "persistence": "system",  # Undo/redo operations
            "click": "ui",
            "open": "system",  # TICKET-FIX: Map 'open' module to 'system' agent
        }
        # TICKET-111 (B3): Only log at debug level to reduce noise
        logger.debug("AgentRegistry instance created")

    def register(self, module: str, agent: Any) -> None:
        """
        Register an agent for a specific module.
        
        TICKET 201: Prevents legacy adapters from overwriting V3 agents.
        TICKET-111 (B3): Reduced logging verbosity.
        
        Args:
            module: Module name (e.g., "system", "browser", "files")
            agent: Agent/adapter instance that handles this module's actions
        """
        # TICKET 201: Check if a V3 agent is already registered
        if module in self._agents:
            existing_agent = self._agents[module]
            is_existing_v3 = getattr(existing_agent, 'is_v3', False)
            is_new_v3 = getattr(agent, 'is_v3', False)
            
            if is_existing_v3 and not is_new_v3:
                # Trying to overwrite V3 agent with legacy adapter - REFUSE
                logger.warning(
                    f"⚠️  REFUSED: Attempt to overwrite V3 agent for module '{module}' "
                    f"with legacy adapter {agent.__class__.__name__}. "
                    f"Keeping existing V3 agent {existing_agent.__class__.__name__}"
                )
                return
            else:
                # Allow overwriting in other cases (e.g., V3 over legacy, V3 over V3)
                logger.debug(f"Overwriting existing agent for module: {module}")
        
        self._agents[module] = agent
        agent_type = "V3 agent" if getattr(agent, 'is_v3', False) else "adapter"
        # TICKET-111 (B3): Reduced log level to debug to reduce noise
        logger.debug(f"Registered {agent_type} for module '{module}': {agent.__class__.__name__}")

    def get_agent(self, module: str) -> Optional[Any]:
        """
        Get the agent for a given module.
        
        Args:
            module: Module name (e.g., "browser", "code", "llm")
        
        Returns:
            Agent instance or None if not found
        """
        # Normalize module name
        module_normalized = module.lower().strip()
        
        # Check if it's an alias
        if module_normalized in self._module_aliases:
            actual_module = self._module_aliases[module_normalized]
            logger.debug(f"Module alias: '{module}' → '{actual_module}'")
            module_normalized = actual_module
        
        # Get agent
        agent = self._agents.get(module_normalized)
        
        if agent is None:
            logger.warning(
                f"No agent registered for module '{module}'. "
                f"Available modules: {list(self._agents.keys())}"
            )
        
        return agent

    def has_agent(self, module: str) -> bool:
        """
        Check if an agent is registered for a module.
        
        Args:
            module: Module name
        
        Returns:
            True if agent exists, False otherwise
        """
        return self.get_agent(module) is not None

    def list_modules(self) -> Dict[str, str]:
        """
        List all registered modules and their agent classes.
        
        Returns:
            Dictionary mapping module names to agent class names
        """
        return {
            module: agent.__class__.__name__
            for module, agent in self._agents.items()
        }

    async def warmup(self) -> Dict[str, bool]:
        """
        Eagerly initialize all registered agents.
        
        TICKET-336: Pre-load agents at startup to avoid initialization latency
        during command execution. This reduces latency by ~2-4 seconds by
        loading agents upfront rather than on first use.
        
        Returns:
            Dict mapping module names to initialization success status
        """
        results: Dict[str, bool] = {}
        
        logger.info("🚀 Warming up agent registry (eager loading)...")
        
        for module, agent in self._agents.items():
            try:
                # Trigger lazy-loaded properties by calling a no-op method if available
                if hasattr(agent, 'warmup'):
                    warmup_method = getattr(agent, 'warmup')
                    if asyncio.iscoroutinefunction(warmup_method):
                        await warmup_method()
                    else:
                        warmup_method()
                    logger.debug(f"✓ Warmed up agent: {module}")
                    results[module] = True
                elif hasattr(agent, 'is_available'):
                    # Calling is_available often triggers lazy initialization
                    agent.is_available()
                    logger.debug(f"✓ Checked availability for agent: {module}")
                    results[module] = True
                else:
                    # Agent has no warmup method, mark as ready
                    logger.debug(f"✓ Agent {module} ready (no warmup needed)")
                    results[module] = True
            except Exception as e:
                logger.warning(f"✗ Failed to warm up agent {module}: {e}")
                results[module] = False
        
        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        logger.info(f"✓ Agent warmup complete: {success_count}/{total_count} agents ready")
        
        return results

    def execute(self, module: str, action: str, args: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute an action on the appropriate agent.
        
        This is the main routing method for JSON V3 step execution.
        Supports both sync and async agents (V3 agents are async).
        
        CRITICAL FIX (TICKET-FIX-CORE-001): 
        This method now detects if an event loop is already running and raises
        an explicit error instead of crashing with asyncio.run().
        Use execute_async() instead when calling from async context.
        
        Args:
            module: Module name (e.g., "browser", "code")
            action: Action name (e.g., "open_url", "search")
            args: Action arguments as dictionary
            context: Optional execution context (for V3 agents)
        
        Returns:
            Result dictionary with structure:
                {
                    "status": "success" | "error",
                    "data": result_data,
                    "error": error_message (if failed),
                    "module": module_name,
                    "action": action_name
                }
        
        Raises:
            RuntimeError: If called from within an async event loop
        """
        # TICKET-FIX-CORE-001: Safety check to prevent asyncio.run() crash
        # Check if we're already in an async context
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop running - safe to proceed
            loop = None
        
        if loop and loop.is_running():
            # CRITICAL: We're in an async context - cannot use asyncio.run()
            error_msg = (
                f"Cannot call sync execute() for '{module}.{action}' from within an async loop. "
                f"Use execute_async() instead."
            )
            logger.error(f"❌ FATAL ERROR: {error_msg}")
            raise RuntimeError(error_msg)
        
        # Get the agent
        agent = self.get_agent(module)
        
        if agent is None:
            return {
                "status": "error",
                "module": module,
                "action": action,
                "error": (
                    f"Module '{module}' not registered. "
                    f"Available modules: {', '.join(self._agents.keys())}"
                ),
                "error_type": "module_not_found",
                "recoverable": False,
            }
        
        # Check if agent has the execute method
        if not hasattr(agent, 'execute') or not callable(getattr(agent, 'execute', None)):
            return {
                "status": "error",
                "module": module,
                "action": action,
                "error": (
                    f"Agent for '{module}' does not implement execute(action, args) method. "
                    f"Agent class: {agent.__class__.__name__}"
                ),
                "error_type": "agent_error",
                "recoverable": False,
            }
        
        # Execute the action - sync agents only
        # For async agents, use execute_async() instead
        try:
            execute_method = getattr(agent, 'execute')
            is_async = inspect.iscoroutinefunction(execute_method)
            
            if is_async:
                # V3 async agent - safe to use asyncio.run() since we checked for running loop above
                logger.debug(
                    f"Running async agent {module}.{action} via asyncio.run(). "
                    f"Consider using execute_async() for better performance."
                )
                result = asyncio.run(execute_method(action, args, context or {}))
            else:
                # Sync agent - check signature for context support
                sig = inspect.signature(execute_method)
                if 'context' in sig.parameters or len(sig.parameters) >= 3:
                    result = execute_method(action, args, context or {})
                else:
                    result = execute_method(action, args)
            
            # Ensure result has module/action info
            if isinstance(result, dict):
                if "module" not in result:
                    result["module"] = module
                if "action" not in result:
                    result["action"] = action
            
            return result
        except Exception as e:
            # TICKET 002: Proper handling of AgentExecutionError
            # Import here to avoid circular dependency
            from janus.capabilities.agents.base_agent import AgentExecutionError
            
            if isinstance(e, AgentExecutionError):
                # Agent raised a structured error - preserve its details
                logger.warning(f"Agent execution error for {module}.{action}: {e.details}")
                return e.to_dict()
            else:
                # Unexpected exception - log and return generic error
                logger.error(f"Unexpected error executing {module}.{action}: {e}", exc_info=True)
                return {
                    "status": "error",
                    "module": module,
                    "action": action,
                    "error": f"Execution error: {str(e)}",
                    "error_type": "execution_error",
                    "recoverable": True,
                }

    async def execute_async(
        self, module: str, action: str, args: Dict[str, Any], context: Optional[Dict[str, Any]] = None, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute an action asynchronously on the appropriate agent.
        
        This is the async-native method for JSON V3 step execution.
        Properly handles both async (V3) and sync (legacy) agents without
        causing 'RuntimeError: no running event loop' issues.
        
        TICKET 1 (P0): Early-abort if shutdown requested to prevent OS actions after shutdown.
        P2: Added dry_run parameter for safe action previewing.
        
        Args:
            module: Module name (e.g., "browser", "code")
            action: Action name (e.g., "open_url", "search")
            args: Action arguments as dictionary
            context: Optional execution context (for V3 agents)
            dry_run: If True, preview action without executing (P2 feature)
        
        Returns:
            Result dictionary with structure:
                {
                    "status": "success" | "error",
                    "data": result_data,
                    "error": error_message (if failed),
                    "module": module_name,
                    "action": action_name,
                    "dry_run": True/False  # P2: Indicates if dry-run
                }
        """
        # TICKET 1 (P0): Check for global shutdown before executing any action
        from janus.runtime.shutdown import is_shutdown_requested, get_shutdown_reason
        
        if is_shutdown_requested():
            reason = get_shutdown_reason() or "Unknown reason"
            logger.warning(f"🛑 Aborting {module}.{action} - shutdown requested: {reason}")
            return {
                "status": "error",
                "module": module,
                "action": action,
                "error": f"Action aborted - shutdown requested: {reason}",
                "error_type": "shutdown_requested",
                "recoverable": False,
            }
        
        # Get the agent
        agent = self.get_agent(module)
        
        if agent is None:
            return {
                "status": "error",
                "module": module,
                "action": action,
                "error": (
                    f"Module '{module}' not registered. "
                    f"Available modules: {', '.join(self._agents.keys())}"
                ),
                "error_type": "module_not_found",
                "recoverable": False,
            }
        
        # Check if agent has the execute method
        if not hasattr(agent, 'execute') or not callable(getattr(agent, 'execute', None)):
            return {
                "status": "error",
                "module": module,
                "action": action,
                "error": (
                    f"Agent for '{module}' does not implement execute(action, args) method. "
                    f"Agent class: {agent.__class__.__name__}"
                ),
                "error_type": "agent_error",
                "recoverable": False,
            }
        
        # Execute the action
        try:
            execute_method = getattr(agent, 'execute')
            is_async = inspect.iscoroutinefunction(execute_method)
            
            # Check if agent supports dry_run parameter
            sig = inspect.signature(execute_method)
            supports_dry_run = 'dry_run' in sig.parameters
            
            if is_async:
                # V3 agent with async execute(action, args, context, dry_run?)
                # Directly await since we're already in async context
                if supports_dry_run:
                    result = await execute_method(action, args, context or {}, dry_run=dry_run)
                else:
                    result = await execute_method(action, args, context or {})
            else:
                # Legacy adapter with sync execute(action, args)
                # Run in executor to avoid blocking the event loop
                loop = asyncio.get_running_loop()
                
                # Check if agent is V3 (has context parameter) using is_v3 attribute
                # This is more reliable than inspecting method signature
                is_v3 = getattr(agent, 'is_v3', False)
                if is_v3:
                    if supports_dry_run:
                        result = await loop.run_in_executor(
                            None, lambda: execute_method(action, args, context or {}, dry_run=dry_run)
                        )
                    else:
                        result = await loop.run_in_executor(
                            None, lambda: execute_method(action, args, context or {})
                        )
                else:
                    # Legacy adapter - try to call with context, fall back to without
                    try:
                        if 'context' in sig.parameters or len(sig.parameters) >= 3:
                            result = await loop.run_in_executor(
                                None, lambda: execute_method(action, args, context or {})
                            )
                        else:
                            result = await loop.run_in_executor(
                                None, lambda: execute_method(action, args)
                            )
                    except (ValueError, TypeError):
                        # Fallback: try without context first
                        result = await loop.run_in_executor(
                            None, lambda: execute_method(action, args)
                        )
            
            # Ensure result has module/action info
            if isinstance(result, dict):
                if "module" not in result:
                    result["module"] = module
                if "action" not in result:
                    result["action"] = action
            
            return result
        except Exception as e:
            # TICKET 002: Proper handling of AgentExecutionError
            # Import here to avoid circular dependency
            from janus.capabilities.agents.base_agent import AgentExecutionError
            
            if isinstance(e, AgentExecutionError):
                # Agent raised a structured error - preserve its details
                logger.warning(f"Agent execution error for {module}.{action}: {e.details}")
                return e.to_dict()
            else:
                # Unexpected exception - log and return generic error
                logger.error(f"Unexpected error executing {module}.{action}: {e}", exc_info=True)
                return {
                    "status": "error",
                    "module": module,
                    "action": action,
                    "error": f"Execution error: {str(e)}",
                    "error_type": "execution_error",
                    "recoverable": True,
                }


# Global singleton instance for easy access
_global_agent_registry: Optional[AgentRegistry] = None


def get_global_agent_registry() -> AgentRegistry:
    """
    Get or create the global agent registry singleton.
    
    Returns:
        Global AgentRegistry instance
    """
    global _global_agent_registry
    if _global_agent_registry is None:
        _global_agent_registry = AgentRegistry()
    return _global_agent_registry


def reset_global_agent_registry() -> None:
    """Reset the global registry (useful for testing)"""
    global _global_agent_registry
    _global_agent_registry = None
