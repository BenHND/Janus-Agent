"""
MemoryServiceWrapper: Memory and Context Management Service for Pipeline

Handles all memory and context-related operations for the Janus pipeline including:
- Loading recent session context for multi-session memory
- Building pruned context with smart routing
- Loading clipboard, browser, file history, and command history context
- Managing session relationships and summaries

This service wraps MemoryEngine with pipeline-specific operations extracted
from JanusPipeline to improve modularity and testability.
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

# Import Intent for fallback intent creation
from janus.runtime.core.contracts import Intent

if TYPE_CHECKING:
    from janus.runtime.core.memory_engine import MemoryEngine
    from janus.runtime.core.context_ranker import ContextRanker
    from janus.platform.clipboard import ClipboardManager

logger = logging.getLogger(__name__)


class MemoryServiceWrapper:
    """
    Service wrapper for Memory and context operations used by pipeline.
    
    Provides pipeline-specific memory operations including context loading,
    session management, and intelligent history pruning.
    """
    
    def __init__(
        self,
        memory: "MemoryEngine",
        context_ranker: Optional["ContextRanker"] = None,
        clipboard_manager: Optional["ClipboardManager"] = None,
    ):
        """
        Initialize Memory Service Wrapper.
        
        Args:
            memory: MemoryEngine instance
            context_ranker: Optional ContextRanker for intelligent context pruning
            clipboard_manager: Optional ClipboardManager for clipboard operations
        """
        self.memory = memory
        self.context_ranker = context_ranker
        self.clipboard_manager = clipboard_manager
    
    def build_pruned_context(
        self,
        required_keys: List[str],
        request_id: str,
        current_command: Optional[str] = None,
        vision_service=None,
    ) -> Dict[str, Any]:
        """
        Build pruned context containing only required modules (TICKET-305, TICKET-P2-03).
        
        This method implements smart context pruning by only loading the context
        modules that the ContextRouter determined are needed for the current command.
        This reduces token usage and latency for simple commands.
        
        TICKET-P2-03: When command history is required, uses TF-IDF-based ranking
        to select only the 5 most relevant past commands, achieving ~40% prompt
        size reduction for long sessions.
        
        Args:
            required_keys: List of required context keys from ContextRouter.
                          Valid keys: ['vision', 'clipboard', 'browser_content',
                                       'file_history', 'command_history']
            request_id: Request ID for logging.
            current_command: The current user command (for TF-IDF similarity ranking).
            vision_service: Optional VisionService for loading vision context.
        
        Returns:
            Dict with only the required context data.
        """
        context = {}
        
        # If no keys required, return empty context (simple command optimization)
        if not required_keys:
            logger.debug("TICKET-305: No context required - returning empty context")
            return context
        
        logger.debug(f"TICKET-305: Building pruned context with keys: {required_keys}")
        
        # Load vision context if required
        if "vision" in required_keys and vision_service:
            vision_data = vision_service.load_vision_context(request_id)
            if vision_data:
                context["vision_output"] = vision_data
                logger.debug("TICKET-305: Added vision_output to context")
        
        # Load clipboard context if required
        if "clipboard" in required_keys:
            clipboard_data = self.load_clipboard_context(request_id)
            if clipboard_data:
                context["clipboard"] = clipboard_data
                logger.debug("TICKET-305: Added clipboard to context")
        
        # Load browser content if required
        if "browser_content" in required_keys:
            browser_data = self.load_browser_context(request_id)
            if browser_data:
                context["browser_content"] = browser_data
                logger.debug("TICKET-305: Added browser_content to context")
        
        # Load file history if required
        if "file_history" in required_keys:
            file_data = self.load_file_history_context(request_id)
            if file_data:
                context["file_history"] = file_data
                logger.debug("TICKET-305: Added file_history to context")
        
        # TICKET-P2-03: Load command history with TF-IDF-based pruning
        if "command_history" in required_keys and current_command:
            command_history = self.load_pruned_command_history(
                current_command=current_command,
                request_id=request_id,
                max_commands=5,
            )
            if command_history:
                context["command_history"] = command_history
                logger.debug(
                    f"TICKET-P2-03: Added {len(command_history)} relevant commands to context "
                    f"(TF-IDF pruned)"
                )
        
        self.memory.log_structured(
            level="DEBUG",
            logger="MemoryServiceWrapper",
            message=f"Built pruned context with {len(context)} modules",
            session_id=self.memory.session_id,
            request_id=request_id,
            module=__name__,
            function="build_pruned_context",
            extra_data={
                "required_keys": required_keys,
                "loaded_keys": list(context.keys()),
            },
        )
        
        return context
    
    def load_clipboard_context(self, request_id: str) -> Optional[str]:
        """
        Load clipboard content using ClipboardManager (TICKET-323).
        
        Uses the robust ClipboardManager instead of hacky subprocess calls.
        ClipboardManager handles cross-platform clipboard access, history,
        and type detection (text/image/file).
        
        Args:
            request_id: Request ID for logging
        
        Returns:
            Clipboard text or None if unavailable.
        """
        if not self.clipboard_manager:
            return None
        
        try:
            entry = self.clipboard_manager.get_current()
            if entry and entry.content:
                # Truncate to avoid huge clipboard content
                content = entry.content[:2000]
                logger.debug(f"TICKET-323: Loaded clipboard via ClipboardManager ({len(content)} chars)")
                return content
            return None
        except Exception as e:
            logger.debug(f"Failed to load clipboard context: {e}")
            return None
    
    def load_browser_context(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Load current browser content/URL.
        
        Args:
            request_id: Request ID for logging
        
        Returns:
            Browser data dict or None if unavailable.
        """
        try:
            # This would integrate with browser modules to get current page info
            # For now, return None - actual implementation depends on browser adapter
            return None
        except Exception as e:
            logger.warning(f"Failed to load browser context: {e}")
            return None
    
    def load_file_history_context(
        self,
        request_id: str,
        current_intent: Optional["Intent"] = None,
        max_items: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Load recent file history using ContextRanker for intelligent ranking (TICKET-322).
        
        Instead of loading arbitrary recent files, uses ContextRanker to rank
        context items by relevance (temporal decay + type matching). This ensures
        the LLM receives the most pertinent file history, not just the last N files.
        
        Args:
            request_id: Request ID for logging.
            current_intent: Optional current intent for relevance scoring.
            max_items: Maximum number of ranked items to return.
        
        Returns:
            List of ranked file context items or None if unavailable.
        """
        if not self.context_ranker:
            return None
        
        try:
            # Get more raw file history (50 items) to rank from
            recent_commands = self.memory.get_command_history(
                self.memory.session_id, limit=50
            )
            
            # Build context items with proper structure for ContextRanker
            context_items = []
            for cmd in recent_commands:
                intent = cmd.get("intent", "")
                if any(kw in intent.lower() for kw in ["file", "open", "save", "document"]):
                    context_items.append({
                        "type": "file",
                        "data": {
                            "command": cmd.get("raw_command", ""),
                            "intent": intent,
                            "file_path": cmd.get("parameters", {}).get("path", ""),
                        },
                        "timestamp": cmd.get("timestamp"),
                    })
            
            if not context_items:
                return None
            
            # Use ContextRanker for intelligent ranking (TICKET-322)
            # Create a fallback intent if none provided
            if current_intent is None:
                current_intent = Intent(action="file_operation", confidence=0.5, parameters={})
            
            ranked_items = self.context_ranker.rank_context_items(
                context_items,
                current_intent=current_intent,
                max_items=max_items
            )
            
            # Extract ranked file data (discard scores for output)
            ranked_files = []
            for item, score in ranked_items:
                ranked_files.append({
                    "command": item.get("data", {}).get("command", ""),
                    "intent": item.get("data", {}).get("intent", ""),
                    "timestamp": item.get("timestamp"),
                    "relevance_score": round(score, 3),  # Include score for debugging
                })
            
            logger.debug(
                f"TICKET-322: Loaded {len(ranked_files)} ranked file history items "
                f"(from {len(context_items)} candidates)"
            )
            
            return ranked_files if ranked_files else None
        except Exception as e:
            logger.warning(f"Failed to load file history context: {e}")
            return None
    
    def load_pruned_command_history(
        self,
        current_command: str,
        request_id: str,
        max_commands: int = 5,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Load command history using TF-IDF-based pruning (TICKET-P2-03).
        
        This method implements intelligent context pruning by selecting only
        the 5 most relevant past commands based on TF-IDF similarity to the
        current command. This reduces LLM prompt size by ~40% for long sessions.
        
        Args:
            current_command: The current user command for similarity matching.
            request_id: Request ID for logging.
            max_commands: Maximum number of relevant commands to return (default: 5).
        
        Returns:
            List of the most relevant cleaned commands or None if unavailable.
        """
        if not self.context_ranker:
            return None
        
        try:
            # Get command history (up to 50 commands for ranking)
            command_history = self.memory.get_command_history(
                self.memory.session_id, limit=50
            )
            
            if not command_history:
                return None
            
            # Use ContextRanker's TF-IDF-based pruning
            pruned_commands = self.context_ranker.get_pruned_context(
                current_command=current_command,
                command_history=command_history,
                max_commands=max_commands,
            )
            
            if not pruned_commands:
                return None
            
            # Log reduction metrics for debugging
            metrics = self.context_ranker.estimate_prompt_reduction(
                full_history=command_history,
                pruned_history=pruned_commands,
            )
            
            logger.info(
                f"TICKET-P2-03: Context pruning achieved {metrics['reduction_percent']}% reduction "
                f"({metrics['full_command_count']} → {metrics['pruned_command_count']} commands)"
            )
            
            self.memory.log_structured(
                level="INFO",
                logger="MemoryServiceWrapper",
                message="TF-IDF context pruning applied",
                session_id=self.memory.session_id,
                request_id=request_id,
                module=__name__,
                function="load_pruned_command_history",
                extra_data=metrics,
            )
            
            return pruned_commands
            
        except Exception as e:
            logger.warning(f"Failed to load pruned command history: {e}")
            return None
    
    def load_recent_session_context(
        self, max_sessions: int = 3, max_commands_per_session: int = 5
    ):
        """
        Load context from recent sessions for multi-session memory.
        
        This provides continuity across sessions by loading recent commands and patterns.
        
        Args:
            max_sessions: Maximum number of recent sessions to load context from
            max_commands_per_session: Maximum commands to load per session
        """
        try:
            # Get recent sessions (excluding current session)
            recent_sessions = self.memory.list_all_sessions(limit=max_sessions + 1)
            recent_sessions = [
                s for s in recent_sessions if s["session_id"] != self.memory.session_id
            ][:max_sessions]
            
            if not recent_sessions:
                logger.debug("No recent sessions found for context loading")
                return
            
            logger.debug(f"Loading context from {len(recent_sessions)} recent session(s)")
            
            # Load commands from each recent session
            recent_commands = []
            for session in recent_sessions:
                commands = self.memory.get_command_history(
                    session["session_id"], limit=max_commands_per_session
                )
                recent_commands.extend(commands)
            
            if recent_commands:
                # Store loaded context in current session
                self.memory.store_context(
                    session_id=self.memory.session_id,
                    context_type="loaded_recent_context",
                    data={
                        "source_sessions": [s["session_id"] for s in recent_sessions],
                        "loaded_commands": len(recent_commands),
                        "recent_intents": list(
                            set(cmd["intent"] for cmd in recent_commands if cmd.get("intent"))
                        ),
                    },
                )
                
                logger.info(
                    f"Loaded context from {len(recent_sessions)} recent sessions "
                    f"({len(recent_commands)} commands)"
                )
        
        except Exception as e:
            logger.warning(f"Failed to load recent session context: {e}")
    
    def get_related_sessions(self, min_similarity: float = 0.3) -> list:
        """
        Find sessions with similar command patterns.
        
        Args:
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
        
        Returns:
            List of related session IDs with similarity scores
        """
        try:
            # Get current session's intents
            current_commands = self.memory.get_command_history(self.memory.session_id, limit=100)
            current_intents = set(cmd["intent"] for cmd in current_commands if cmd.get("intent"))
            
            if not current_intents:
                return []
            
            # Get all sessions
            all_sessions = self.memory.list_all_sessions(limit=1000)
            
            related = []
            for session in all_sessions:
                if session["session_id"] == self.memory.session_id:
                    continue
                
                # Get intents from this session
                commands = self.memory.get_command_history(session["session_id"], limit=100)
                session_intents = set(cmd["intent"] for cmd in commands if cmd.get("intent"))
                
                if not session_intents:
                    continue
                
                # Calculate Jaccard similarity
                intersection = len(current_intents & session_intents)
                union = len(current_intents | session_intents)
                similarity = intersection / union if union > 0 else 0.0
                
                if similarity >= min_similarity:
                    related.append(
                        {
                            "session_id": session["session_id"],
                            "similarity": round(similarity, 3),
                            "common_intents": list(current_intents & session_intents),
                            "last_accessed": session["last_accessed"],
                        }
                    )
            
            # Sort by similarity
            related.sort(key=lambda x: x["similarity"], reverse=True)
            
            return related
        
        except Exception as e:
            logger.warning(f"Failed to find related sessions: {e}")
            return []
    
    def get_session_summary(self) -> dict:
        """
        Get summary of current session.
        
        Returns:
            Dictionary with session statistics
        """
        try:
            details = self.memory.get_session_details(self.memory.session_id)
            return details if details else {}
        except Exception as e:
            logger.warning(f"Failed to get session summary: {e}")
            return {}
    
    def store_command(
        self, 
        raw_command: str, 
        intent: Intent, 
        request_id: str,
        session_id: Optional[str] = None
    ):
        """
        Store command in history.
        
        Args:
            raw_command: The raw command text from user
            intent: The parsed intent
            request_id: Request ID for tracking
            session_id: Optional session ID (uses current session if not provided)
        """
        if session_id is None:
            session_id = self.memory.session_id
        
        logger.debug("Storing command in history")
        self.memory.log_structured(
            level="DEBUG",
            logger="MemoryServiceWrapper",
            message="Storing command",
            session_id=session_id,
            request_id=request_id,
            module=__name__,
            function="store_command",
        )
        
        self.memory.store_command(
            session_id=session_id,
            request_id=request_id,
            raw_command=raw_command,
            intent=intent,
        )
