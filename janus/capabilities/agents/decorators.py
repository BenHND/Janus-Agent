"""
Agent Action Decorator - Factorize Common Boilerplate

TICKET-ARCH-AGENT: Architecture Agentique - Solution propre, stable et extensible

This module provides the @agent_action decorator that handles common concerns
for agent actions including:
- Logging (before/after execution)
- Validation (required arguments, types)
- Error handling (structured errors)
- Help/documentation metadata
- Performance tracking

Goal: Reduce boilerplate and standardize agent action implementation across all agents.
"""

import functools
import inspect
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set, get_type_hints

logger = logging.getLogger(__name__)


class ActionMetadata:
    """
    Metadata for an agent action.
    
    This is used for auto-discovery, documentation generation, and validation.
    
    Attributes:
        name: Action name (e.g., "open_url", "send_message")
        description: Human-readable description
        required_args: List of required argument names
        optional_args: Dict of optional argument names to default values
        providers: List of supported providers (e.g., ["slack", "teams"])
        examples: List of usage examples
        agent_name: Name of the agent that owns this action
        risk_level: Risk level for the action (low, medium, high, critical)
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        required_args: Optional[List[str]] = None,
        optional_args: Optional[Dict[str, Any]] = None,
        providers: Optional[List[str]] = None,
        examples: Optional[List[str]] = None,
        agent_name: Optional[str] = None,
        risk_level: str = "low"
    ):
        self.name = name
        self.description = description
        self.required_args = required_args or []
        self.optional_args = optional_args or {}
        self.providers = providers or []
        self.examples = examples or []
        self.agent_name = agent_name
        self.risk_level = risk_level
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "required_args": self.required_args,
            "optional_args": self.optional_args,
            "providers": self.providers,
            "examples": self.examples,
            "agent_name": self.agent_name,
            "risk_level": self.risk_level,
        }
    
    def to_tool_spec(self) -> Dict[str, str]:
        """
        Generate ToolSpec format for LLM prompts.
        
        Returns:
            Tool specification with id, signature, description, and keywords
        """
        import re
        
        if not self.agent_name:
            raise ValueError(f"Cannot generate tool spec for {self.name}: agent_name not set")
        
        # Generate parameter signature
        params = ', '.join([f"{arg}: str" for arg in self.required_args])
        
        # Generate tool ID
        tool_id = f"{self.agent_name}_{self.name}"
        
        # Generate signature
        signature = f"{self.agent_name}.{self.name}({params})"
        
        # Generate keywords from agent name, action name, and examples
        keywords = [self.agent_name, self.name]
        # Add keywords from examples (take first 2 examples)
        for example in self.examples[:2]:
            # Extract meaningful words using regex (alphanumeric + underscore, 3+ chars)
            words = re.findall(r'\b\w{3,}\b', example.lower())
            # Filter out common words and already included terms
            filtered_words = [
                w for w in words 
                if w not in keywords and w not in {'the', 'and', 'for', 'with', 'from'}
            ]
            keywords.extend(filtered_words[:3])  # Max 3 keywords per example
        
        keywords_str = ' '.join(keywords)
        
        return {
            "id": tool_id,
            "signature": signature,
            "description": self.description,
            "keywords": keywords_str,
        }
    
    def __repr__(self) -> str:
        return f"ActionMetadata(name={self.name}, agent={self.agent_name})"


def agent_action(
    description: str,
    required_args: Optional[List[str]] = None,
    optional_args: Optional[Dict[str, Any]] = None,
    providers: Optional[List[str]] = None,
    examples: Optional[List[str]] = None,
    risk_level: str = "low"
) -> Callable:
    """
    Decorator for agent actions that handles common boilerplate.
    
    This decorator:
    1. Validates required arguments before execution
    2. Logs before and after execution with timing
    3. Handles errors with structured error results
    4. Stores metadata for auto-discovery and documentation
    5. Tracks performance metrics
    
    Usage:
        @agent_action(
            description="Send a message to a channel",
            required_args=["platform", "channel", "text"],
            optional_args={"thread_ts": None},
            providers=["slack", "teams"],
            examples=["messaging.send_message(platform='slack', channel='#general', text='Hello')"],
            risk_level="high"
        )
        async def _send_message(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
            # Implementation here
            platform = args["platform"]
            channel = args["channel"]
            text = args["text"]
            
            # ... actual logic ...
            
            return self._success_result(data={"sent": True})
    
    Args:
        description: Human-readable description of what the action does
        required_args: List of required argument names
        optional_args: Dict of optional argument names to default values
        providers: List of supported providers (for multi-provider actions)
        examples: List of usage examples for documentation
        risk_level: Risk level (low, medium, high, critical) - default is "low"
    
    Returns:
        Decorated function with validation, logging, and metadata
    """
    def decorator(func: Callable) -> Callable:
        # Store metadata on the function for auto-discovery
        action_name = func.__name__.lstrip("_")
        metadata = ActionMetadata(
            name=action_name,
            description=description,
            required_args=required_args or [],
            optional_args=optional_args or {},
            providers=providers or [],
            examples=examples or [],
            risk_level=risk_level
        )
        func._action_metadata = metadata  # type: ignore
        
        @functools.wraps(func)
        async def async_wrapper(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
            """Async wrapper for agent actions."""
            start_time = time.time()
            action_name = metadata.name
            agent_name = getattr(self, 'agent_name', 'unknown')
            
            # Update metadata with agent name if not set
            if not metadata.agent_name:
                metadata.agent_name = agent_name
            
            # Log before execution
            _log_before(agent_name, action_name, args, context)
            
            try:
                # Validate required arguments
                _validate_required_args(agent_name, action_name, args, metadata.required_args)
                
                # Add optional arguments with defaults
                for opt_arg, default_value in metadata.optional_args.items():
                    if opt_arg not in args:
                        args[opt_arg] = default_value
                
                # Execute the action
                result = await func(self, args, context)
                
                # Log after execution
                duration_ms = (time.time() - start_time) * 1000
                success = result.get("status") == "success"
                _log_after(agent_name, action_name, success, duration_ms, result.get("error"))
                
                return result
            
            except Exception as e:
                # Log error
                duration_ms = (time.time() - start_time) * 1000
                _log_after(agent_name, action_name, False, duration_ms, str(e))
                
                # Return structured error result
                return _create_error_result(agent_name, action_name, str(e))
        
        @functools.wraps(func)
        def sync_wrapper(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
            """Sync wrapper for agent actions (for backward compatibility)."""
            start_time = time.time()
            action_name = metadata.name
            agent_name = getattr(self, 'agent_name', 'unknown')
            
            # Update metadata with agent name if not set
            if not metadata.agent_name:
                metadata.agent_name = agent_name
            
            # Log before execution
            _log_before(agent_name, action_name, args, context)
            
            try:
                # Validate required arguments
                _validate_required_args(agent_name, action_name, args, metadata.required_args)
                
                # Add optional arguments with defaults
                for opt_arg, default_value in metadata.optional_args.items():
                    if opt_arg not in args:
                        args[opt_arg] = default_value
                
                # Execute the action
                result = func(self, args, context)
                
                # Log after execution
                duration_ms = (time.time() - start_time) * 1000
                success = result.get("status") == "success"
                _log_after(agent_name, action_name, success, duration_ms, result.get("error"))
                
                return result
            
            except Exception as e:
                # Log error
                duration_ms = (time.time() - start_time) * 1000
                _log_after(agent_name, action_name, False, duration_ms, str(e))
                
                # Return structured error result
                return _create_error_result(agent_name, action_name, str(e))
        
        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def _validate_required_args(agent_name: str, action_name: str, args: Dict[str, Any], required: List[str]) -> None:
    """
    Validate that required arguments are present.
    
    Args:
        agent_name: Name of the agent
        action_name: Name of the action
        args: Arguments dictionary
        required: List of required argument names
    
    Raises:
        ValueError: If required arguments are missing
    """
    # Only check for missing keys, allow None as a valid value
    missing = [arg for arg in required if arg not in args]
    
    if missing:
        raise ValueError(f"Missing required arguments for {agent_name}.{action_name}: {', '.join(missing)}")


def _log_before(agent_name: str, action_name: str, args: Dict[str, Any], context: Dict[str, Any]) -> None:
    """
    Log before action execution.
    
    Args:
        agent_name: Name of the agent
        action_name: Name of the action
        args: Action arguments
        context: Execution context
    """
    # Sanitize sensitive data
    sanitized_args = _sanitize_args(args)
    sanitized_context = _sanitize_context(context)
    
    logger.info(
        f"→ Executing {agent_name}.{action_name} | "
        f"args={sanitized_args} | "
        f"context={sanitized_context}"
    )


def _log_after(
    agent_name: str,
    action_name: str,
    success: bool,
    duration_ms: float,
    error: Optional[str] = None
) -> None:
    """
    Log after action execution.
    
    Args:
        agent_name: Name of the agent
        action_name: Name of the action
        success: Whether action succeeded
        duration_ms: Execution duration in milliseconds
        error: Optional error message
    """
    status_symbol = "✓" if success else "✗"
    log_level = logging.INFO if success else logging.ERROR
    
    message = (
        f"{status_symbol} {agent_name}.{action_name} "
        f"({'success' if success else 'failed'}) | "
        f"duration={duration_ms:.0f}ms"
    )
    
    if error:
        message += f" | error={error}"
    
    logger.log(log_level, message)


def _sanitize_args(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize arguments for logging (remove sensitive data).
    
    Args:
        args: Arguments dictionary
    
    Returns:
        Sanitized arguments
    """
    # Comprehensive sensitive key detection
    sensitive_patterns = {
        "password", "passwd", "pwd",
        "token", "auth", "bearer",
        "api_key", "apikey", "key",
        "secret", "credential", "cred",
        "jwt", "session", "cookie"
    }
    sanitized = {}
    
    for key, value in args.items():
        key_lower = key.lower()
        if any(pattern in key_lower for pattern in sensitive_patterns):
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = value
    
    return sanitized


def _sanitize_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize context for logging (keep only relevant fields).
    
    Args:
        context: Context dictionary
    
    Returns:
        Sanitized context
    """
    # Only log relevant context fields
    relevant_keys = {"app", "surface", "url", "domain", "thread", "record", "provider"}
    return {k: v for k, v in context.items() if k in relevant_keys and v}


def _create_error_result(agent_name: str, action_name: str, error: str) -> Dict[str, Any]:
    """
    Create a structured error result.
    
    Args:
        agent_name: Name of the agent
        action_name: Name of the action
        error: Error message
    
    Returns:
        Error result dictionary
    """
    return {
        "status": "error",
        "module": agent_name,
        "action": action_name,
        "error": error,
        "error_type": "execution_error",
        "recoverable": True,
    }


def get_action_metadata(func: Callable) -> Optional[ActionMetadata]:
    """
    Get action metadata from a decorated function.
    
    Args:
        func: Decorated function
    
    Returns:
        ActionMetadata if available, None otherwise
    """
    return getattr(func, '_action_metadata', None)


def list_agent_actions(agent) -> List[ActionMetadata]:
    """
    List all actions for an agent by scanning for decorated methods.
    
    Args:
        agent: Agent instance
    
    Returns:
        List of ActionMetadata for all decorated actions
    """
    actions = []
    
    # Scan all methods of the agent
    for name in dir(agent):
        if name.startswith('_') and not name.startswith('__'):
            method = getattr(agent, name)
            metadata = get_action_metadata(method)
            if metadata:
                # Update agent name if not set
                if not metadata.agent_name:
                    metadata.agent_name = getattr(agent, 'agent_name', agent.__class__.__name__)
                actions.append(metadata)
    
    return actions


def generate_tool_spec_from_metadata(metadata: ActionMetadata) -> Dict[str, str]:
    """
    Generate a ToolSpec entry from ActionMetadata.
    
    This is a convenience wrapper around ActionMetadata.to_tool_spec()
    for use in tool_spec_generator.py
    
    Args:
        metadata: ActionMetadata instance
        
    Returns:
        Tool specification dictionary with id, signature, description, keywords
    """
    return metadata.to_tool_spec()
