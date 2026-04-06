"""
JanusAgent - Single Entry Point for Janus (TICKET-AUDIT-003)

This module provides the ONLY public API for Janus:
- Simple initialization
- Single execute() method  
- Clean integration of all components via ActionCoordinator
- Comprehensive logging

This replaces multiple entry points (Pipeline, ExecutionEngine, AgentExecutor, etc.)
with a single, clear interface implementing the OODA Loop.

Usage:
    ```python
    from janus.runtime.core import JanusAgent
    
    # Initialize agent
    agent = JanusAgent()
    
    # Execute command
    result = await agent.execute("find CEO and send email")
    
    # Check result
    if result.success:
        print(f"Success: {result.message}")
    else:
        print(f"Failed: {result.message}")
    ```

Architecture (per ARCHITECTURE_AUDIT_COMPREHENSIVE_EN.md):
- JanusAgent: Public API (this file)
- ActionCoordinator: OODA loop coordination (TICKET-AUDIT-001)
- ReasonerLLM: Decision making
- AgentRegistry: Action execution
- VisionEngine: Observation
- MemoryEngine: Persistence (TICKET-AUDIT-005: Unified memory system)
"""

import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .action_coordinator import ActionCoordinator
from .agent_registry import get_global_agent_registry
from .contracts import ExecutionResult, Intent
from .settings import Settings

logger = logging.getLogger(__name__)


class JanusAgent:
    """
    Single entry point for Janus - the voice-controlled computer automation agent.
    
    This is the ONLY public API for Janus. All other classes are internal implementation details.
    
    Architecture (per ARCHITECTURE_AUDIT_COMPREHENSIVE_EN.md):
    ```
    JanusAgent
    ├── ActionCoordinator (OODA/ReAct Loop)
    │   ├── ReasonerLLM (decisions)
    │   ├── AgentRegistry (execution)
    │   └── VisionEngine (observation)
    └── MemoryEngine (persistence - TICKET-AUDIT-005)
    ```
    
    Features:
    - Simple initialization with optional config
    - Single execute() method implementing OODA/ReAct Loop
    - Automatic component management (Reasoner, Agents, Vision, Memory)
    - Session management
    - Comprehensive logging
    
    Example:
        ```python
        # Basic usage
        agent = JanusAgent()
        result = await agent.execute("open Calculator")
        
        # With custom config
        agent = JanusAgent(config_path="my_config.ini")
        result = await agent.execute("search for Python tutorials")
        
        # With explicit settings
        agent = JanusAgent(
            enable_vision=True,
            enable_llm=True,
            enable_learning=False
        )
        result = await agent.execute("open Safari and go to example.com")
        ```
    
    Attributes:
        session_id: Current session ID for memory tracking
        settings: Agent configuration settings
        available: Whether agent is ready to execute commands
    """
    
    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        session_id: Optional[str] = None,
        enable_voice: bool = False,
        enable_llm: bool = True,
        enable_vision: bool = True,
        enable_learning: bool = True,
        enable_tts: bool = False,
        language: Optional[str] = None,
        max_iterations: int = 20,
        **kwargs
    ):
        """
        Initialize Janus agent with optional configuration.
        
        Args:
            config_path: Path to config.ini file (optional)
            session_id: Session ID for memory (auto-generated if None)
            enable_voice: Enable voice input via STT (default: False)
            enable_llm: Enable LLM reasoning for complex commands (default: True)
            enable_vision: Enable vision for verification (default: True)
            enable_learning: Enable learning from corrections (default: True)
            enable_tts: Enable text-to-speech feedback (default: False)
            language: Language code (e.g., "fr", "en") - uses config default if None
            max_iterations: Maximum OODA loop iterations (default: 20)
            **kwargs: Additional settings overrides
        
        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If required dependencies are missing
        
        Example:
            ```python
            # Minimal initialization
            agent = JanusAgent()
            
            # Custom configuration
            agent = JanusAgent(
                config_path="config.ini",
                enable_vision=True,
                enable_llm=True
            )
            
            # Text-only mode (for testing)
            agent = JanusAgent(
                enable_voice=False,
                enable_vision=False,
                enable_tts=False
            )
            ```
        """
        logger.info("Initializing JanusAgent (TICKET-AUDIT-003: Single Entry Point)")
        
        # Initialize settings
        self.settings = Settings(config_path=config_path, **kwargs)
        
        # Override language if specified
        if language:
            self.settings.language.default = language
        
        # Initialize memory engine (TICKET-AUDIT-005: Unified memory system)
        from .memory_engine import MemoryEngine
        db_path = str(self.settings.database.path) if hasattr(self.settings.database, 'path') else "janus_memory.db"
        self.memory = MemoryEngine(db_path=db_path, session_id=session_id)
        
        # Use session ID from MemoryEngine
        self.session_id = self.memory.session_id
        
        # Store feature flags
        self._enable_voice = enable_voice
        self._enable_llm = enable_llm
        self._enable_vision = enable_vision
        self._enable_learning = enable_learning
        self._enable_tts = enable_tts
        
        # Initialize ActionCoordinator (OODA Loop)
        self._coordinator: Optional[ActionCoordinator] = None
        self._max_iterations = max_iterations
        
        logger.info(
            f"JanusAgent initialized - session={self.session_id}, "
            f"llm={enable_llm}, vision={enable_vision}, voice={enable_voice}"
        )
    
    @property
    def coordinator(self) -> ActionCoordinator:
        """
        Lazy-load ActionCoordinator for OODA loop execution.
        
        Internal implementation detail - DO NOT use directly in external code.
        Use agent.execute() instead.
        """
        if self._coordinator is None:
            logger.debug("Initializing ActionCoordinator...")
            agent_registry = get_global_agent_registry()
            self._coordinator = ActionCoordinator(
                agent_registry=agent_registry,
                max_iterations=self._max_iterations,
                settings=self.settings,  # PERF-FOUNDATION-001: Pass settings for vision policy
            )
            logger.debug("ActionCoordinator initialized")
        
        return self._coordinator
    
    @property
    def available(self) -> bool:
        """
        Check if agent is ready to execute commands.
        
        Returns:
            True if agent is initialized and ready, False otherwise
        
        Example:
            ```python
            agent = JanusAgent()
            if agent.available:
                result = await agent.execute("open Calculator")
            ```
        """
        # Cache availability check - once coordinator initializes successfully, 
        # agent remains available for the session
        if hasattr(self, '_availability_cached'):
            return self._availability_cached
        
        try:
            # Agent is available if coordinator can be initialized
            _ = self.coordinator
            self._availability_cached = True
            return True
        except Exception as e:
            logger.error(f"Agent not available: {e}")
            self._availability_cached = False
            return False
    
    async def execute(
        self,
        command: str,
        request_id: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Execute a command using Janus via the OODA/ReAct Loop (Observe, Orient, Decide, Act).
        
        This is the MAIN method to use Janus. It:
        1. Creates an intent from the command
        2. Calls ActionCoordinator to execute via OODA loop
        3. ActionCoordinator handles: Observation, Decision (Reasoner), Action (Agents)
        4. Returns execution result
        
        Note: extra_context is reserved for future use. The OODA loop observes context
        dynamically rather than receiving it pre-provided.
        
        Args:
            command: Natural language command (e.g., "open Calculator")
            request_id: Optional request ID for tracking (auto-generated if None)
            extra_context: Reserved for future use (currently not passed to OODA loop)
        
        Returns:
            ExecutionResult with success status, message, and details
        
        Raises:
            ValueError: If command is empty or invalid
            RuntimeError: If agent is not available
        
        Example:
            ```python
            # Basic command
            result = await agent.execute("open Safari")
            
            # With request ID
            result = await agent.execute(
                "search for Python",
                request_id="req-123"
            )
            
            # Check result
            if result.success:
                print(f"✓ {result.message}")
            else:
                print(f"✗ {result.message}")
            ```
        """
        # Validate input
        if not command or not command.strip():
            raise ValueError("Command cannot be empty")
        
        # Check availability
        if not self.available:
            raise RuntimeError("Agent is not available - check logs for errors")
        
        # Generate descriptive request ID if not provided
        # Format: session_prefix-timestamp-random for better traceability
        if request_id is None:
            timestamp = int(time.time() * 1000)  # milliseconds for uniqueness
            random_suffix = str(uuid.uuid4()).split('-')[0]  # First part of UUID
            request_id = f"{self.session_id.split('-')[0]}-{timestamp}-{random_suffix}"
        
        logger.info(f"JanusAgent.execute: '{command}' (request_id={request_id})")
        
        try:
            # Create intent for the command
            intent = Intent(
                action="user_command",
                confidence=1.0,
                raw_command=command,
            )
            
            # Get language from settings
            language = self.settings.language.default
            
            # Execute via ActionCoordinator's OODA loop
            result = await self.coordinator.execute_goal(
                user_goal=command,
                intent=intent,
                session_id=self.session_id,
                request_id=request_id,
                language=language,
            )
            
            # Log result
            if result.success:
                logger.info(f"✓ Command succeeded: {result.message}")
            else:
                logger.warning(f"✗ Command failed: {result.message}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing command: {e}", exc_info=True)
            
            # Create error result
            error_intent = Intent(
                action="error",
                confidence=0.0,
                raw_command=command,
            )
            
            error_result = ExecutionResult(
                intent=error_intent,
                success=False,
                message=f"Execution error: {str(e)}",
                session_id=self.session_id,
                request_id=request_id,
            )
            
            return error_result
    
    async def cleanup(self):
        """
        Clean up agent resources.
        
        Call this when done using the agent to properly release resources
        (coordinator, memory connections, etc.).
        
        Example:
            ```python
            agent = JanusAgent()
            try:
                result = await agent.execute("open Calculator")
            finally:
                await agent.cleanup()
            ```
        """
        logger.info("Cleaning up JanusAgent resources...")
        
        if self._coordinator is not None:
            try:
                # ActionCoordinator doesn't need explicit cleanup currently
                # but we log it for consistency
                logger.debug("ActionCoordinator cleanup complete")
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")
        
        logger.info("JanusAgent cleanup complete")
    
    async def __aenter__(self):
        """Support async context manager usage."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Support async context manager usage."""
        await self.cleanup()
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"JanusAgent(session={self.session_id}, "
            f"llm={self._enable_llm}, vision={self._enable_vision}, "
            f"available={self.available})"
        )


# Convenience function for one-shot execution
async def execute_command(
    command: str,
    config_path: Optional[Union[str, Path]] = None,
    **kwargs
) -> ExecutionResult:
    """
    Execute a single command with automatic setup and cleanup.
    
    Convenience function for one-shot command execution without
    managing agent lifecycle manually.
    
    Args:
        command: Command to execute
        config_path: Optional config file path
        **kwargs: Additional agent initialization arguments
    
    Returns:
        ExecutionResult with execution status
    
    Example:
        ```python
        from janus.runtime.core.janus_agent import execute_command
        
        # One-shot execution
        result = await execute_command("open Calculator")
        print(f"Success: {result.success}")
        ```
    """
    async with JanusAgent(config_path=config_path, **kwargs) as agent:
        return await agent.execute(command)
