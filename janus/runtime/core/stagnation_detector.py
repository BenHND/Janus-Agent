"""
StagnationDetector - Detect OODA Loop Stagnation

Extracted from ActionCoordinator to separate stagnation detection concerns.
CORE-FOUNDATION-002: Stagnation detection for Burst OODA mode.
ARCH-004: Uses SystemState.__hash__() for consistent state comparison.
"""

import logging
from typing import List

from janus.runtime.core.contracts import SystemState, BurstMetrics

logger = logging.getLogger(__name__)


class StagnationDetector:
    """
    Detects if the OODA loop is stuck in the same state.
    
    ARCH-004: Uses SystemState.__hash__() for consistent state comparison.
    Maintains a rolling history of recent state hashes to detect repetition.
    """
    
    def __init__(self, stagnation_threshold: int = 3):
        """
        Initialize StagnationDetector.
        
        Args:
            stagnation_threshold: Number of identical states to consider stagnation
        """
        self.stagnation_threshold = stagnation_threshold
        self._state_history: List[int] = []  # Recent state hashes
    
    def detect_stagnation(self, system_state: SystemState, burst_metrics: BurstMetrics) -> bool:
        """
        Detect if we're stuck in the same state.
        
        ARCH-004: Uses SystemState.__hash__() for consistent state comparison.
        
        Args:
            system_state: Current SystemState snapshot
            burst_metrics: Burst metrics to update
        
        Returns:
            True if the state hash has been seen N times in a row.
        """
        state_hash = hash(system_state)
        self._state_history.append(state_hash)
        
        # Keep only recent history (last 10 states)
        if len(self._state_history) > 10:
            self._state_history.pop(0)
        
        # Check if last N states are identical
        if len(self._state_history) >= self.stagnation_threshold:
            recent = self._state_history[-self.stagnation_threshold:]
            if len(set(recent)) == 1:  # All identical
                burst_metrics.stagnation_events += 1
                logger.warning(f"⚠️ Stagnation detected! State unchanged for {self.stagnation_threshold} observations")
                return True
        
        return False
    
    def reset(self):
        """Reset stagnation detection state."""
        self._state_history.clear()
