"""
RecoveryManager - Single Owner Recovery State Machine

Extracted from ActionCoordinator to separate recovery concerns.
RELIABILITY-001: Single owner recovery logic with state machine.
CRITICAL-P0: Enhanced with LLM replanning and fallback chain.
"""

import asyncio
import logging
from typing import Optional, List

from janus.runtime.core.contracts import (
    ActionResult,
    RecoveryState,
    SystemState,
)
from janus.utils.retry import RetryConfig, FallbackChain

logger = logging.getLogger(__name__)


class RecoveryManager:
    """
    Manages recovery state machine for ActionCoordinator.
    
    RELIABILITY-001: Single owner recovery logic.
    Handles stagnation detection and intelligent replanning.
    """
    
    def __init__(self, max_recovery_attempts: int = 3):
        """
        Initialize RecoveryManager.
        
        Args:
            max_recovery_attempts: Maximum number of recovery attempts
        """
        self._recovery_state = RecoveryState.IDLE
        self._recovery_lock = asyncio.Lock()
        self._recovery_attempts = 0
        self._max_recovery_attempts = max_recovery_attempts
    
    def get_recovery_state(self) -> RecoveryState:
        """
        Get current recovery state.
        
        Returns:
            Current RecoveryState
        """
        return self._recovery_state
    
    def set_recovery_state(self, new_state: RecoveryState, reason: str = ""):
        """
        Transition to a new recovery state with logging.
        
        RELIABILITY-001: All recovery state transitions are logged for traceability.
        
        Args:
            new_state: New RecoveryState to transition to
            reason: Reason for state transition
        """
        old_state = self._recovery_state
        self._recovery_state = new_state
        
        logger.info(
            f"🔄 Recovery State: {old_state.value} → {new_state.value}"
            + (f" | {reason}" if reason else "")
        )
    
    async def try_recovery(
        self,
        system_state: SystemState,
        reasoner,
        error_context: Optional[str] = None,
        action_history: Optional[List[ActionResult]] = None,
        user_goal: Optional[str] = None
    ) -> bool:
        """
        Attempt recovery from stagnation or error with intelligent replanning.
        
        RELIABILITY-001: Single owner recovery logic.
        CRITICAL-P0: Enhanced with LLM replanning and fallback chain.
        
        Recovery strategy:
        1. LLM replanning with current state
        2. Fallback to accessibility context if vision fails
        3. Force vision re-observation as last resort
        
        Args:
            system_state: Current system state
            reasoner: Reasoner instance for LLM replanning
            error_context: Optional error description
            action_history: Optional action history for replanning context
            user_goal: Optional user goal for replanning
        
        Returns:
            True if recovery successful, False otherwise
        """
        # Check if already recovering (prevent concurrent recovery)
        async with self._recovery_lock:
            if self._recovery_state != RecoveryState.IDLE:
                logger.warning(
                    f"⚠️ Recovery already in progress (state={self._recovery_state.value}), skipping"
                )
                return False
            
            # Check recovery attempts limit
            if self._recovery_attempts >= self._max_recovery_attempts:
                logger.error(
                    f"❌ Max recovery attempts ({self._max_recovery_attempts}) reached, giving up"
                )
                self.set_recovery_state(RecoveryState.FAILED, "max attempts reached")
                return False
            
            # Start recovery
            self._recovery_attempts += 1
            self.set_recovery_state(
                RecoveryState.DETECTING,
                f"attempt {self._recovery_attempts}/{self._max_recovery_attempts}"
            )
            
            try:
                # Transition to RECOVERING
                self.set_recovery_state(
                    RecoveryState.RECOVERING,
                    error_context or "stagnation detected"
                )
                
                # CRITICAL-P0: Use fallback chain for intelligent recovery
                recovery_chain = FallbackChain(log_attempts=True)
                
                # Strategy 1: LLM replanning with current context
                if reasoner.available and user_goal and action_history:
                    def llm_replan():
                        logger.info("🧠 Recovery: Attempting LLM replanning")
                        # Generate replanning prompt
                        replan_prompt = self.build_recovery_prompt(
                            user_goal,
                            system_state,
                            error_context,
                            action_history
                        )
                        # Ask LLM for recovery strategy
                        response = reasoner.run_inference(
                            replan_prompt,
                            max_tokens=256,
                            json_mode=True
                        )
                        logger.info(f"✓ LLM recovery plan generated: {response[:100]}...")
                        return True
                    
                    recovery_chain.add(
                        "llm_replanning",
                        llm_replan,
                        RetryConfig(max_attempts=1)  # No retry for LLM replan
                    )
                
                # Strategy 2: Force vision re-observation
                def force_vision():
                    logger.info("🔍 Recovery: Forcing vision re-observation for next iteration")
                    return True
                
                recovery_chain.add(
                    "force_vision",
                    force_vision,
                    None  # No retry needed
                )
                
                # Execute recovery chain
                try:
                    recovery_chain.execute()
                    
                    # Mark recovery as successful
                    self.set_recovery_state(RecoveryState.RECOVERED, "recovery chain succeeded")
                    
                    # Return to IDLE for next iteration
                    self.set_recovery_state(RecoveryState.IDLE, "recovery complete")
                    
                    return True
                    
                except Exception as e:
                    logger.warning(f"Recovery chain failed: {e}")
                    # Even if chain fails, we can continue with force_vision fallback
                    self.set_recovery_state(RecoveryState.RECOVERED, "partial recovery")
                    self.set_recovery_state(RecoveryState.IDLE, "recovery complete")
                    return True
                
            except Exception as e:
                logger.error(f"❌ Recovery failed: {e}", exc_info=True)
                self.set_recovery_state(RecoveryState.FAILED, f"exception: {e}")
                return False
    
    def build_recovery_prompt(
        self,
        user_goal: str,
        system_state: SystemState,
        error_context: Optional[str],
        action_history: List[ActionResult]
    ) -> str:
        """
        Build prompt for LLM-based recovery replanning.
        
        CRITICAL-P0: Generate recovery strategy based on current state and error.
        
        Args:
            user_goal: Original user goal
            system_state: Current system state
            error_context: Error description
            action_history: Recent action history
            
        Returns:
            Recovery prompt string
        """
        history_txt = "\n".join([
            f"- {res.action_type}: "
            f"{'SUCCÈS' if res.success else 'ÉCHEC'} "
            f"({res.message})"
            for res in action_history[-5:]  # Last 5 actions
        ])
        
        return f"""Tu es un expert en récupération d'erreurs GUI.

OBJECTIF ORIGINAL: {user_goal}

ÉTAT ACTUEL:
- App: {system_state.active_app}
- URL: {system_state.url}
- Titre: {system_state.window_title}

ERREUR/PROBLÈME:
{error_context or "Stagnation détectée - même état observé plusieurs fois"}

HISTORIQUE RÉCENT:
{history_txt}

Ta tâche: Analyse la situation et suggère une stratégie de récupération.
Réponds en JSON avec:
{{
  "diagnosis": "Pourquoi on est bloqué",
  "strategy": "Quelle approche essayer",
  "needs_vision": true/false
}}

Sois concis et pratique."""
    
    def reset_recovery_state(self):
        """
        Reset recovery state to IDLE.
        
        Called at the start of a new goal execution to clear previous state.
        """
        self._recovery_state = RecoveryState.IDLE
        self._recovery_attempts = 0
        logger.debug("Recovery state reset to IDLE")
