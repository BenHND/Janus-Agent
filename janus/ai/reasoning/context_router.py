"""
AI Context Router - Smart Context Pruning for Janus
TICKET-305: Performance optimization through intelligent context filtering
TICKET-P2-03: Extended with command_history key for TF-IDF-based context pruning

ARCH-002: Updated to use UnifiedLLMClient from settings (no hardcoded llama3.2)
- Uses the same model configured in settings.llm.model (e.g., qwen2.5:7b-instruct)
- Optional/disableable routing for performance
- No hidden LLM calls - uses centralized client

This module implements a lightweight context router that determines which context
modules (vision, clipboard, browser_content, file_history, command_history) are 
needed for a given command. This reduces token usage and latency by avoiding 
unnecessary context injection into the LLM prompt.

Strategy:
- Use UnifiedLLMClient configured from settings
- Ultra-light system prompt with max_tokens=50 for fast responses
- Return only required context keys as JSON list
- Zero regex - pure LLM classification
- Can be disabled via settings for zero-LLM routing
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from janus.logging import get_logger

logger = get_logger("context_router")


# Valid context keys that can be returned
# TICKET-P2-03: Added 'command_history' for TF-IDF-based context pruning
VALID_CONTEXT_KEYS = frozenset([
    "vision", 
    "clipboard", 
    "browser_content", 
    "file_history",
    "command_history",  # TICKET-P2-03: For TF-IDF-based context pruning
])

# System prompt for context routing (ultra-light)
ROUTER_SYSTEM_PROMPT = """You are a context optimizer. Analyze the user request. Reply ONLY with a JSON list of required context keys among: ['vision', 'clipboard', 'browser_content', 'file_history', 'command_history'].

Examples:
User: 'Copie ça' -> Output: ["clipboard"]
User: 'Qu'est-ce qu'il y a à l'écran ?' -> Output: ["vision"]
User: 'Résume cette page' -> Output: ["browser_content"]
User: 'Ouvre Safari' -> Output: []
User: 'Colle le texte copié dans le fichier' -> Output: ["clipboard", "file_history"]
User: 'Lis le texte visible' -> Output: ["vision"]
User: 'Copie ce texte et va sur YouTube' -> Output: ["clipboard", "browser_content"]
User: 'Refais la même chose' -> Output: ["command_history"]
User: 'Continue' -> Output: ["command_history"]

Reply with ONLY a valid JSON array. No explanation."""


class ContextRouter:
    """
    AI-powered context router for smart pruning.
    
    ARCH-002: Uses UnifiedLLMClient from settings - no hardcoded model.
    
    Determines which context modules are needed for a given command
    using lightweight LLM classification.
    
    Features:
    - Uses UnifiedLLMClient configured in settings.llm.*
    - Ultra-light system prompt for minimal latency
    - max_tokens=50 for fast responses
    - Returns list of required context keys
    - Graceful fallback on errors (returns all keys)
    - Can be disabled for zero-LLM routing
    
    Performance:
    - Target latency: <100ms on M-series, <300ms on CPU
    - Reduces average context size by ~60% for simple commands
    """
    
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        enabled: bool = True,
        timeout_ms: int = 2000,
    ):
        """
        Initialize ContextRouter.
        
        Args:
            llm_client: Optional UnifiedLLMClient instance.
                        If not provided, routing will be disabled (fallback to all context).
            enabled: Whether to enable LLM-based routing. If False, always returns all context.
            timeout_ms: Timeout for routing requests in milliseconds.
        """
        self.llm_client = llm_client
        self.enabled = enabled
        self.timeout_ms = timeout_ms
        self.available = False
        
        # Performance metrics
        self.metrics = {
            "total_calls": 0,
            "total_time_ms": 0.0,
            "avg_latency_ms": 0.0,
            "fallback_count": 0,
            "error_count": 0,
        }
        
        # Check if LLM client is provided and routing is enabled
        if self.llm_client is not None and self.enabled:
            self.available = True
            logger.info("ContextRouter initialized with provided LLM client (enabled)")
        elif not self.enabled:
            logger.info("ContextRouter disabled - will return all context keys")
            self.available = False
        else:
            logger.info("ContextRouter: No LLM client provided - routing disabled (fallback to all context)")
            self.available = False
    
    def get_requirements(
        self,
        raw_command: str,
        language: str = "auto",
    ) -> List[str]:
        """
        Determine required context modules for a command.
        
        Args:
            raw_command: Raw user command text.
            language: Language hint (unused, LLM auto-detects).
        
        Returns:
            List of required context keys (e.g., ["vision", "clipboard"]).
            Empty list if no special context needed.
            Returns all keys if routing is disabled or on error (safe fallback).
        
        Performance:
            Target: <100ms on M-series, <300ms on CPU
        """
        start_time = time.time()
        self.metrics["total_calls"] += 1
        
        # If not available or disabled, return all context (safe fallback)
        if not self.available or self.llm_client is None or not self.enabled:
            logger.debug("ContextRouter not available/disabled, returning all context keys")
            self.metrics["fallback_count"] += 1
            return list(VALID_CONTEXT_KEYS)
        
        try:
            # Build prompt
            prompt = f"User: '{raw_command}' -> Output:"
            
            # TICKET: P1 - Use fast mode for lightweight classification
            # Run lightweight inference using UnifiedLLMClient with reflex model
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=ROUTER_SYSTEM_PROMPT,
                max_tokens=50,
                temperature=0.1,
                mode="fast",  # TICKET: P1 - Use reflex model for fast routing
            )
            
            # Parse response
            requirements = self._parse_response(response)
            
            latency_ms = (time.time() - start_time) * 1000
            self._update_metrics(latency_ms)
            
            logger.debug(
                f"ContextRouter: '{raw_command[:30]}...' -> {requirements} "
                f"({latency_ms:.1f}ms)"
            )
            
            return requirements
            
        except Exception as e:
            logger.warning(f"ContextRouter error: {e}, returning all context keys")
            self.metrics["error_count"] += 1
            self.metrics["fallback_count"] += 1
            
            latency_ms = (time.time() - start_time) * 1000
            self._update_metrics(latency_ms)
            
            return list(VALID_CONTEXT_KEYS)
    
    def _parse_response(self, response: str) -> List[str]:
        """
        Parse LLM response into list of context keys.
        
        Args:
            response: Raw LLM response string.
        
        Returns:
            List of valid context keys.
        """
        # Try to extract JSON array from response
        response = response.strip()
        
        # Handle common response formats
        # 1. Clean JSON array: ["vision", "clipboard"]
        # 2. Array in text: The required keys are ["vision"]
        # 3. Just brackets: []
        
        try:
            # Find JSON array in response
            start = response.find("[")
            end_bracket = response.rfind("]")
            
            # Validate both brackets found
            if start < 0 or end_bracket < 0 or end_bracket < start:
                logger.debug(f"ContextRouter: No valid JSON array in response: {response[:100]}")
                return []
            
            end = end_bracket + 1
            json_str = response[start:end]
            parsed = json.loads(json_str)
            
            if isinstance(parsed, list):
                # Filter to only valid keys
                valid_keys = [
                    key for key in parsed 
                    if isinstance(key, str) and key in VALID_CONTEXT_KEYS
                ]
                return valid_keys
            
            # No valid JSON found, return empty (no special context needed)
            logger.debug(f"ContextRouter: No valid JSON in response: {response[:100]}")
            return []
            
        except json.JSONDecodeError:
            logger.debug(f"ContextRouter: JSON parse error: {response[:100]}")
            return []
    
    def _update_metrics(self, latency_ms: float):
        """Update performance metrics."""
        self.metrics["total_time_ms"] += latency_ms
        if self.metrics["total_calls"] > 0:
            self.metrics["avg_latency_ms"] = (
                self.metrics["total_time_ms"] / self.metrics["total_calls"]
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            **self.metrics,
            "available": self.available,
            "enabled": self.enabled,
        }
    
    def reset_metrics(self):
        """Reset performance metrics."""
        self.metrics = {
            "total_calls": 0,
            "total_time_ms": 0.0,
            "avg_latency_ms": 0.0,
            "fallback_count": 0,
            "error_count": 0,
        }


class MockContextRouter(ContextRouter):
    """
    Mock ContextRouter for testing and production use.
    
    Uses keyword-based classification instead of LLM for instant routing (0ms).
    TICKET-315: This is now the default for production to eliminate LLM latency.
    """
    
    def __init__(self):
        """Initialize mock router (no LLM needed, no network calls)."""
        # Skip parent __init__ to avoid LLM client initialization
        # which would cause latency by connecting to Ollama
        self.llm_client = None
        self.model_name = "mock"
        self.timeout_ms = 0
        self.available = True  # Mock is always available
        
        # Initialize metrics
        self.metrics = {
            "total_calls": 0,
            "total_time_ms": 0.0,
            "avg_latency_ms": 0.0,
            "fallback_count": 0,
            "error_count": 0,
        }
        
        logger.debug("MockContextRouter initialized (keyword-based, 0ms latency)")
    
    def get_requirements(
        self,
        raw_command: str,
        language: str = "auto",
        is_first_iteration: bool = False,
    ) -> List[str]:
        """
        Keyword-based context detection for instant routing (0ms).
        
        TICKET-315: This is the default for production - uses keyword matching
        instead of LLM for zero-latency context routing.
        
        TICKET-ARCHI: Vision is now enabled by default on first iteration to allow
        LLM to see the screen context for any UI workflow. After first iteration,
        LLM controls vision via needs_vision flag.
        """
        start_time = time.time()
        self.metrics["total_calls"] += 1
        
        command_lower = raw_command.lower()
        requirements = []
        
        # TICKET-ARCHI: Enable vision by default on first iteration
        # This allows the LLM to see the screen for UI workflows without requiring
        # specific keywords like "écran", "see", etc.
        if is_first_iteration:
            requirements.append("vision")
            logger.debug("Vision enabled by default for first iteration")
        
        # Vision keywords (French and English) - still useful for non-first iterations
        vision_keywords = [
            "écran", "screen", "vois", "see", "lis", "read", 
            "visible", "affiche", "display", "montre", "show",
            "qu'est-ce qu", "what's", "what is", "regarde", "look"
        ]
        if any(kw in command_lower for kw in vision_keywords):
            if "vision" not in requirements:
                requirements.append("vision")
        
        # Clipboard keywords
        clipboard_keywords = [
            "copie", "copy", "colle", "paste", "clipboard",
            "presse-papier", "copié", "copied"
        ]
        if any(kw in command_lower for kw in clipboard_keywords):
            requirements.append("clipboard")
        
        # Browser content keywords
        browser_keywords = [
            "page", "site", "website", "url", "résume", "summarize",
            "article", "contenu", "content", "browser", "navigateur",
            "web"
        ]
        if any(kw in command_lower for kw in browser_keywords):
            requirements.append("browser_content")
        
        # File history keywords
        file_keywords = [
            "fichier", "file", "document", "dernier", "last",
            "récent", "recent", "historique", "history", "ouvert",
            "opened"
        ]
        if any(kw in command_lower for kw in file_keywords):
            requirements.append("file_history")
        
        # TICKET-P2-03: Command history keywords (for context-dependent commands)
        # These are commands that reference previous actions or need context
        command_history_keywords = [
            "refais", "redo", "encore", "again", "continue", 
            "pareil", "same", "précédent", "previous", "avant",
            "before", "dernière commande", "last command",
            "comme tout à l'heure", "like before", "répète", "repeat"
        ]
        if any(kw in command_lower for kw in command_history_keywords):
            requirements.append("command_history")
        
        latency_ms = (time.time() - start_time) * 1000
        self._update_metrics(latency_ms)
        
        logger.debug(
            f"MockContextRouter: '{raw_command[:30]}...' -> {requirements}"
        )
        
        return requirements
