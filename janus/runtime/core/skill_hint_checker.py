"""
SkillHintChecker - Skill Hint Retrieval

Extracted from ActionCoordinator to separate skill hint concerns.
LEARNING-001: Skills are suggestions, never automatic execution.
"""

import logging
import time
from typing import Optional

from janus.runtime.core.contracts import SystemState, SkillMetrics

logger = logging.getLogger(__name__)


class SkillHintChecker:
    """
    Checks for learned skill hints based on user goals.
    
    LEARNING-001: Skills are suggestions, never automatic execution.
    """
    
    def __init__(self, semantic_router=None, skill_metrics: Optional[SkillMetrics] = None):
        """
        Initialize SkillHintChecker.
        
        Args:
            semantic_router: Optional SemanticRouter for skill hints
            skill_metrics: Optional SkillMetrics for tracking
        """
        self.semantic_router = semantic_router
        self.skill_metrics = skill_metrics or SkillMetrics()
    
    def check_skill_hint(self, user_goal: str, system_state: SystemState) -> Optional[str]:
        """
        Check if a learned skill hint exists for this goal.
        
        LEARNING-001: Skills are suggestions, never automatic execution.
        
        Args:
            user_goal: The user's goal
            system_state: Current system state for context
        
        Returns:
            Skill hint string if found, None otherwise
        """
        if not self.semantic_router:
            return None
        
        try:
            retrieval_start = time.time()
            
            # Build context data from system state
            context_data = {
                "active_app": system_state.active_app,
                "url": system_state.url,
                "domain": system_state.domain,
            }
            
            # Check skill cache (returns SkillHint or None)
            skill_hint = self.semantic_router.check_skill_cache(
                text=user_goal,
                context_data=context_data,
                similarity_threshold=0.8
            )
            
            retrieval_time = (time.time() - retrieval_start) * 1000
            
            if skill_hint:
                # Record metrics
                self.skill_metrics.record_hint_retrieved(retrieval_time)
                
                # Convert to context string
                hint_string = skill_hint.to_context_string()
                
                logger.info(
                    f"💡 Skill hint retrieved in {retrieval_time:.2f}ms "
                    f"(confidence: {skill_hint.confidence:.2f}, used {skill_hint.success_count}x)"
                )
                
                return hint_string
            
            return None
            
        except Exception as e:
            logger.warning(f"Error checking skill hint: {e}")
            return None
