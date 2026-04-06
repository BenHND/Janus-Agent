"""
Conversation Manager - Multi-turn dialogue management.

Handles:
- Conversation lifecycle (create, update, complete)
- Turn management
- Clarification questions
- Context carryover
- Implicit reference resolution
- Analytics tracking
"""
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .contracts import Intent

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    """Conversation state enumeration"""
    ACTIVE = "active"
    NEEDS_CLARIFICATION = "needs_clarification"
    COMPLETED = "completed"
    IDLE = "idle"


@dataclass
class ClarificationQuestion:
    """Clarification question data structure"""
    question: str
    options: List[str]
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationTurn:
    """Single turn in a conversation"""
    turn_id: str
    turn_number: int
    command: str
    intent: Optional[Intent] = None
    result: Optional[str] = None
    clarification: Optional[ClarificationQuestion] = None
    state: ConversationState = ConversationState.ACTIVE
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Conversation:
    """Conversation data structure"""
    conversation_id: str
    session_id: str
    state: ConversationState
    turns: List[ConversationTurn] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class ConversationManager:
    """
    Manages multi-turn conversations with context carryover and clarification support.
    
    Features:
    - Multi-turn dialogue tracking
    - Context carryover between turns
    - Clarification question generation and resolution
    - Implicit reference resolution ("it", "that", etc.)
    - Persistent storage via MemoryEngine
    """
    
    def __init__(self, memory, analytics=None):
        """
        Initialize conversation manager.
        
        Args:
            memory: MemoryEngine instance for persistence
            analytics: Optional ConversationAnalytics instance
        """
        self.memory = memory
        self.analytics = analytics
        self._active_conversations: Dict[str, Conversation] = {}
        logger.info("ConversationManager initialized")
    
    def start_conversation(self, session_id: str) -> Conversation:
        """
        Start a new conversation for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            New Conversation object
        """
        # Persist to database using MemoryEngine and get the conversation ID
        try:
            db_conv_id = self.memory.start_conversation(session_id)
            conversation_id = db_conv_id if db_conv_id else f"conv_{uuid.uuid4().hex[:16]}"
        except Exception as e:
            logger.warning(f"Failed to persist conversation start: {e}")
            conversation_id = f"conv_{uuid.uuid4().hex[:16]}"
        
        conversation = Conversation(
            conversation_id=conversation_id,
            session_id=session_id,
            state=ConversationState.ACTIVE,
        )
        
        # Store in memory
        self._active_conversations[session_id] = conversation
        
        # Start analytics tracking
        if self.analytics:
            self.analytics.start_tracking(conversation_id, session_id)
        
        logger.info(f"Started conversation {conversation_id} for session {session_id}")
        return conversation
    
    def get_active_conversation(self, session_id: str) -> Optional[Conversation]:
        """
        Get active conversation for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Active conversation or None
        """
        return self._active_conversations.get(session_id)
    
    def add_turn(
        self,
        conversation_id: str,
        command: str,
        intent: Optional[Intent] = None,
        result: Optional[str] = None,
        clarification: Optional[ClarificationQuestion] = None,
        state: ConversationState = ConversationState.ACTIVE,
    ) -> ConversationTurn:
        """
        Add a turn to a conversation.
        
        Args:
            conversation_id: Conversation ID
            command: User command
            intent: Parsed intent
            result: Execution result
            clarification: Clarification question if needed
            state: Turn state
            
        Returns:
            ConversationTurn object
        """
        # Find conversation
        conversation = None
        for conv in self._active_conversations.values():
            if conv.conversation_id == conversation_id:
                conversation = conv
                break
        
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        turn_number = len(conversation.turns) + 1
        turn = ConversationTurn(
            turn_id=f"turn_{uuid.uuid4().hex[:12]}",
            turn_number=turn_number,
            command=command,
            intent=intent,
            result=result,
            clarification=clarification,
            state=state,
        )
        
        conversation.turns.append(turn)
        conversation.updated_at = datetime.now()
        
        # Update conversation state if needed
        if state == ConversationState.NEEDS_CLARIFICATION:
            conversation.state = ConversationState.NEEDS_CLARIFICATION
        
        # Persist to database
        try:
            # Use the conversation_id from our conversation object
            system_response = f"{intent.action if intent else 'unknown'}: {result}" if result else None
            self.memory.add_conversation_turn(
                conversation.conversation_id,
                command,
                system_response,
            )
        except Exception as e:
            logger.warning(f"Failed to persist turn: {e}")
        
        # Track analytics
        if self.analytics:
            success = result and "success" in result.lower() if isinstance(result, str) else False
            has_clarification = clarification is not None
            self.analytics.record_turn(conversation_id, success, has_clarification)
        
        logger.debug(f"Added turn {turn_number} to conversation {conversation_id}")
        return turn
    
    def generate_clarification(
        self,
        original_command: str,
        ambiguity_type: str,
        options: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> ClarificationQuestion:
        """
        Generate a clarification question.
        
        Args:
            original_command: Original ambiguous command
            ambiguity_type: Type of ambiguity (multiple_files, ambiguous_app, etc.)
            options: List of possible options
            context: Additional context
            
        Returns:
            ClarificationQuestion object
        """
        if context is None:
            context = {}
        
        # Generate question based on ambiguity type
        if ambiguity_type == "multiple_files":
            question = "Plusieurs fichiers correspondent. Lequel voulez-vous ?"
        elif ambiguity_type == "ambiguous_app":
            question = "Plusieurs applications correspondent. Laquelle voulez-vous ouvrir ?"
        elif ambiguity_type == "missing_context":
            question = "Informations manquantes. Que voulez-vous faire ?"
        else:
            question = f"Clarification nécessaire pour '{original_command}'. Choisissez une option :"
        
        return ClarificationQuestion(
            question=question,
            options=options,
            context=context,
        )
    
    def resolve_clarification(
        self, conversation_id: str, user_response: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Resolve a clarification question with user's response.
        
        Args:
            conversation_id: Conversation ID
            user_response: User's response (numeric index or text match)
            
        Returns:
            Tuple of (success, context_dict or None)
        """
        # Find conversation
        conversation = None
        for conv in self._active_conversations.values():
            if conv.conversation_id == conversation_id:
                conversation = conv
                break
        
        if not conversation:
            return False, None
        
        # Get last turn that needs clarification
        clarification_turn = None
        for turn in reversed(conversation.turns):
            if turn.state == ConversationState.NEEDS_CLARIFICATION and turn.clarification:
                clarification_turn = turn
                break
        
        if not clarification_turn:
            return False, None
        
        clarification = clarification_turn.clarification
        selected_option = None
        
        # Try numeric selection first
        try:
            index = int(user_response) - 1  # 1-indexed
            if 0 <= index < len(clarification.options):
                selected_option = clarification.options[index]
        except ValueError:
            # Try text matching
            for option in clarification.options:
                if user_response.lower() in option.lower() or option.lower() in user_response.lower():
                    selected_option = option
                    break
        
        if selected_option:
            # Update conversation state
            conversation.state = ConversationState.ACTIVE
            clarification_turn.state = ConversationState.ACTIVE
            
            # Track analytics
            if self.analytics:
                self.analytics.record_clarification_resolved(conversation_id, True)
            
            context = {
                "selected_option": selected_option,
                "original_command": clarification_turn.command,
                **clarification.context,
            }
            
            logger.info(f"Clarification resolved: {selected_option}")
            return True, context
        
        return False, None
    
    def get_context_for_command(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get context summary for a command.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Context dictionary with recent commands, entities, etc.
        """
        # Find conversation
        conversation = None
        for conv in self._active_conversations.values():
            if conv.conversation_id == conversation_id:
                conversation = conv
                break
        
        if not conversation:
            return {}
        
        # Build context summary
        last_commands = [turn.command for turn in conversation.turns[-5:]]  # Last 5 turns
        
        # Extract recent entities from intents
        recent_entities = {}
        for turn in reversed(conversation.turns):
            if turn.intent and turn.intent.parameters:
                for key, value in turn.intent.parameters.items():
                    if key not in recent_entities:
                        recent_entities[key] = value
        
        return {
            "turn_count": len(conversation.turns),
            "state": conversation.state.value,
            "last_commands": last_commands,
            "recent_entities": recent_entities,
            "conversation_id": conversation.conversation_id,
        }
    
    def resolve_implicit_references(
        self, command: str, conversation_id: str
    ) -> str:
        """
        Resolve implicit references in a command using conversation context.
        
        Resolves: "it", "that", "this", "ça", "cela", "the previous one"
        
        Args:
            command: Command with potential implicit references
            conversation_id: Conversation ID
            
        Returns:
            Command with resolved references
        """
        # Find conversation
        conversation = None
        for conv in self._active_conversations.values():
            if conv.conversation_id == conversation_id:
                conversation = conv
                break
        
        if not conversation or not conversation.turns:
            return command
        
        # Get last turn's entities
        last_turn = conversation.turns[-1]
        if not last_turn.intent or not last_turn.intent.parameters:
            return command
        
        # Check for implicit references
        implicit_refs = ["it", "that", "this", "ça", "cela", "le précédent", "la précédente"]
        command_lower = command.lower()
        
        has_reference = any(ref in command_lower for ref in implicit_refs)
        if not has_reference:
            return command
        
        # Try to resolve with most relevant entity
        params = last_turn.intent.parameters
        
        # Priority: file_path > app_name > url > target
        if "file_path" in params:
            reference = params["file_path"]
        elif "app_name" in params:
            reference = params["app_name"]
        elif "url" in params:
            reference = params["url"]
        elif "target" in params:
            reference = params["target"]
        else:
            # Use first available parameter value
            reference = next(iter(params.values())) if params else None
        
        if reference:
            # Replace implicit reference with actual value using word boundaries
            for ref in implicit_refs:
                # Use word boundary matching to avoid partial replacements
                pattern = r'\b' + re.escape(ref) + r'\b'
                if re.search(pattern, command_lower):
                    # Replace case-insensitively
                    command = re.sub(pattern, str(reference), command, flags=re.IGNORECASE)
                    logger.info(f"Resolved implicit reference '{ref}' to '{reference}'")
                    
                    # Track analytics
                    if self.analytics:
                        self.analytics.record_implicit_reference(conversation_id)
                    
                    break
        
        return command
    
    def complete_conversation(self, conversation_id: str) -> bool:
        """
        Mark a conversation as completed.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if successful
        """
        # Find and remove from active conversations
        session_id_to_remove = None
        for session_id, conv in self._active_conversations.items():
            if conv.conversation_id == conversation_id:
                conv.state = ConversationState.COMPLETED
                session_id_to_remove = session_id
                break
        
        if session_id_to_remove:
            # Save context before removing from active
            self._save_context_for_session(session_id_to_remove, conv)
            
            # End analytics tracking
            if self.analytics:
                self.analytics.end_tracking(conversation_id)
            
            del self._active_conversations[session_id_to_remove]
            
            # Persist completion
            try:
                self.memory.end_conversation(conversation_id, "completed")
            except Exception as e:
                logger.warning(f"Failed to persist conversation completion: {e}")
            
            logger.info(f"Completed conversation {conversation_id}")
            return True
        
        return False
    
    def _save_context_for_session(self, session_id: str, conversation: Conversation):
        """
        Save conversation context for multi-session persistence.
        
        Args:
            session_id: Session ID
            conversation: Conversation to save
        """
        try:
            # Extract context summary
            context = self.get_context_for_command(conversation.conversation_id)
            
            # Save to a persistent context store (could be extended to use MemoryEngine)
            context_data = {
                "session_id": session_id,
                "conversation_id": conversation.conversation_id,
                "last_commands": context.get("last_commands", []),
                "recent_entities": context.get("recent_entities", {}),
                "turn_count": context.get("turn_count", 0),
                "saved_at": datetime.now().isoformat(),
            }
            
            # For now, log the context - could be extended to store in DB
            logger.info(f"Saved context for session {session_id}: {len(context_data['last_commands'])} commands")
            
        except Exception as e:
            logger.warning(f"Failed to save context for session: {e}")
    
    def load_context_from_previous_session(
        self, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load conversation context from a previous session.
        
        This enables multi-session context carryover.
        
        Args:
            session_id: Session ID to load context for
            
        Returns:
            Context dict or None if no previous context found
        """
        try:
            # Query conversation history from MemoryEngine
            # This is a placeholder - would need actual implementation in MemoryEngine
            logger.info(f"Loading context for session {session_id}")
            
            # Could query last N conversations for this session
            # and extract relevant context
            
            return None  # Placeholder
            
        except Exception as e:
            logger.warning(f"Failed to load previous session context: {e}")
            return None
    
    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Dict with session statistics
        """
        stats = {
            "session_id": session_id,
            "active_conversation": None,
            "total_turns": 0,
            "clarifications_used": 0,
            "references_resolved": 0,
        }
        
        # Check active conversation
        conv = self.get_active_conversation(session_id)
        if conv:
            stats["active_conversation"] = conv.conversation_id
            stats["total_turns"] = len(conv.turns)
            stats["clarifications_used"] = sum(
                1 for turn in conv.turns 
                if turn.clarification is not None
            )
        
        return stats
