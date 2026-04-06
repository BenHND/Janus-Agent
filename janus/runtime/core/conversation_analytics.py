"""
Conversation Analytics - Track conversation patterns and success rates.

This module provides analytics for conversation mode to help understand
usage patterns and improve the system.
"""
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConversationMetrics:
    """Metrics for a single conversation"""
    conversation_id: str
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    turn_count: int = 0
    clarification_count: int = 0
    clarifications_resolved: int = 0
    implicit_references_resolved: int = 0
    successful_turns: int = 0
    failed_turns: int = 0
    total_duration_seconds: Optional[float] = None


@dataclass
class AggregateMetrics:
    """Aggregate metrics across all conversations"""
    total_conversations: int = 0
    total_turns: int = 0
    total_clarifications: int = 0
    clarification_success_rate: float = 0.0
    avg_turns_per_conversation: float = 0.0
    avg_clarifications_per_conversation: float = 0.0
    implicit_reference_usage: int = 0
    turn_success_rate: float = 0.0


class ConversationAnalytics:
    """
    Analytics engine for conversation mode.
    
    Tracks metrics like:
    - Conversation success rates
    - Clarification patterns
    - Implicit reference usage
    - Turn completion rates
    """
    
    def __init__(self, memory_engine):
        """
        Initialize analytics engine.
        
        Args:
            memory_engine: MemoryEngine for persistence
        """
        self.memory = memory_engine
        self._active_metrics: Dict[str, ConversationMetrics] = {}
        logger.info("ConversationAnalytics initialized")
    
    def start_tracking(self, conversation_id: str, session_id: str):
        """
        Start tracking a new conversation.
        
        Args:
            conversation_id: Conversation ID
            session_id: Session ID
        """
        metrics = ConversationMetrics(
            conversation_id=conversation_id,
            session_id=session_id,
            start_time=datetime.now(),
        )
        self._active_metrics[conversation_id] = metrics
        logger.debug(f"Started tracking conversation {conversation_id}")
    
    def record_turn(
        self, conversation_id: str, success: bool, had_clarification: bool = False
    ):
        """
        Record a conversation turn.
        
        Args:
            conversation_id: Conversation ID
            success: Whether turn was successful
            had_clarification: Whether this turn involved clarification
        """
        if conversation_id not in self._active_metrics:
            logger.warning(f"Turn recorded for untracked conversation {conversation_id}")
            return
        
        metrics = self._active_metrics[conversation_id]
        metrics.turn_count += 1
        
        if success:
            metrics.successful_turns += 1
        else:
            metrics.failed_turns += 1
        
        if had_clarification:
            metrics.clarification_count += 1
    
    def record_clarification_resolved(self, conversation_id: str, success: bool):
        """
        Record clarification resolution.
        
        Args:
            conversation_id: Conversation ID
            success: Whether clarification was resolved successfully
        """
        if conversation_id not in self._active_metrics:
            return
        
        if success:
            self._active_metrics[conversation_id].clarifications_resolved += 1
    
    def record_implicit_reference(self, conversation_id: str):
        """
        Record implicit reference resolution.
        
        Args:
            conversation_id: Conversation ID
        """
        if conversation_id not in self._active_metrics:
            return
        
        self._active_metrics[conversation_id].implicit_references_resolved += 1
    
    def end_tracking(self, conversation_id: str) -> Optional[ConversationMetrics]:
        """
        End tracking and save metrics.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Final metrics for the conversation
        """
        if conversation_id not in self._active_metrics:
            return None
        
        metrics = self._active_metrics[conversation_id]
        metrics.end_time = datetime.now()
        
        if metrics.start_time and metrics.end_time:
            duration = (metrics.end_time - metrics.start_time).total_seconds()
            metrics.total_duration_seconds = duration
        
        # Persist to database
        self._save_metrics(metrics)
        
        # Remove from active tracking
        del self._active_metrics[conversation_id]
        
        logger.info(
            f"Conversation {conversation_id} completed: "
            f"{metrics.turn_count} turns, {metrics.clarification_count} clarifications"
        )
        
        return metrics
    
    def _save_metrics(self, metrics: ConversationMetrics):
        """Save metrics to database"""
        try:
            # Store as JSON in a simple table
            metrics_json = json.dumps(asdict(metrics), default=str)
            
            # Use memory engine to store
            # For now, just log - could extend MemoryEngine with analytics table
            logger.debug(f"Metrics saved: {metrics_json}")
            
        except Exception as e:
            logger.warning(f"Failed to save metrics: {e}")
    
    def get_conversation_metrics(
        self, conversation_id: str
    ) -> Optional[ConversationMetrics]:
        """
        Get metrics for a specific conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Metrics or None if not found
        """
        return self._active_metrics.get(conversation_id)
    
    def get_aggregate_metrics(self, session_id: Optional[str] = None) -> AggregateMetrics:
        """
        Get aggregate metrics across conversations.
        
        Args:
            session_id: Optional session ID to filter by
            
        Returns:
            Aggregate metrics
        """
        # Filter metrics
        metrics_list = list(self._active_metrics.values())
        if session_id:
            metrics_list = [m for m in metrics_list if m.session_id == session_id]
        
        if not metrics_list:
            return AggregateMetrics()
        
        # Calculate aggregates
        total_conversations = len(metrics_list)
        total_turns = sum(m.turn_count for m in metrics_list)
        total_clarifications = sum(m.clarification_count for m in metrics_list)
        clarifications_resolved = sum(m.clarifications_resolved for m in metrics_list)
        successful_turns = sum(m.successful_turns for m in metrics_list)
        implicit_refs = sum(m.implicit_references_resolved for m in metrics_list)
        
        return AggregateMetrics(
            total_conversations=total_conversations,
            total_turns=total_turns,
            total_clarifications=total_clarifications,
            clarification_success_rate=(
                clarifications_resolved / total_clarifications * 100
                if total_clarifications > 0
                else 0.0
            ),
            avg_turns_per_conversation=(
                total_turns / total_conversations if total_conversations > 0 else 0.0
            ),
            avg_clarifications_per_conversation=(
                total_clarifications / total_conversations
                if total_conversations > 0
                else 0.0
            ),
            implicit_reference_usage=implicit_refs,
            turn_success_rate=(
                successful_turns / total_turns * 100 if total_turns > 0 else 0.0
            ),
        )
    
    def get_summary_report(self, session_id: Optional[str] = None) -> str:
        """
        Generate a human-readable summary report.
        
        Args:
            session_id: Optional session ID to filter by
            
        Returns:
            Formatted summary string
        """
        metrics = self.get_aggregate_metrics(session_id)
        
        report = f"""
Conversation Analytics Summary
{'=' * 50}
Total Conversations: {metrics.total_conversations}
Total Turns: {metrics.total_turns}
Avg Turns/Conversation: {metrics.avg_turns_per_conversation:.1f}

Clarifications:
  Total: {metrics.total_clarifications}
  Avg/Conversation: {metrics.avg_clarifications_per_conversation:.1f}
  Success Rate: {metrics.clarification_success_rate:.1f}%

Implicit References: {metrics.implicit_reference_usage}
Turn Success Rate: {metrics.turn_success_rate:.1f}%
"""
        return report
