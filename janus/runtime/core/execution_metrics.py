"""
Execution Metrics Tracking - ARCH-001 Phase 2

This module tracks execution engine usage for ActionCoordinator (OODA loop).

Metrics tracked:
- Engine usage counts
- Entry points using the engine
- Execution success/failure rates
- Timestamp of last usage

Usage:
    from janus.runtime.core.execution_metrics import track_execution_engine
    
    track_execution_engine(
        entry_point="JanusAgent.execute",
        success=True
    )
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class EngineMetrics:
    """Metrics for ActionCoordinator execution"""
    
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    entry_points: Dict[str, int] = field(default_factory=dict)  # entry_point -> count
    last_used_timestamp: Optional[float] = None
    
    def record_execution(self, entry_point: str, success: bool):
        """Record an execution"""
        self.total_executions += 1
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
        
        # Track entry point
        self.entry_points[entry_point] = self.entry_points.get(entry_point, 0) + 1
        
        # Update timestamp
        self.last_used_timestamp = time.time()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)"""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging"""
        return {
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": round(self.success_rate, 3),
            "entry_points": self.entry_points,
            "last_used_timestamp": self.last_used_timestamp,
        }


class ExecutionMetricsTracker:
    """
    Global tracker for execution metrics.
    
    Singleton pattern to ensure consistent tracking across the application.
    """
    
    _instance: Optional['ExecutionMetricsTracker'] = None
    
    def __init__(self):
        """Initialize metrics tracker"""
        self.metrics = EngineMetrics()
    
    @classmethod
    def get_instance(cls) -> 'ExecutionMetricsTracker':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def track_execution(
        self,
        entry_point: str,
        success: bool
    ):
        """
        Track an execution.
        
        Args:
            entry_point: Entry point that triggered execution (e.g., "JanusAgent.execute", "ActionCoordinator.execute_goal")
            success: Whether execution was successful
        """
        self.metrics.record_execution(entry_point, success)
        
        logger.debug(
            f"📊 EXECUTION: entry_point={entry_point}, success={success}, "
            f"total_executions={self.metrics.total_executions}"
        )
    
    def get_metrics(self) -> Dict:
        """
        Get execution metrics.
        
        Returns:
            Dictionary with metrics
        """
        return self.metrics.to_dict()
    
    def log_summary(self):
        """Log a summary of metrics"""
        metrics = self.metrics
        if metrics.total_executions > 0:
            logger.info("📊 Execution Metrics Summary:")
            logger.info(
                f"  ActionCoordinator: {metrics.total_executions} executions, "
                f"{metrics.success_rate:.1%} success rate, "
                f"entry_points={list(metrics.entry_points.keys())}"
            )
    
    def reset(self):
        """Reset metrics (for testing)"""
        self.metrics = EngineMetrics()


# Convenience function for tracking
def track_execution_engine(
    entry_point: str,
    success: bool = True
):
    """
    Track execution engine usage.
    
    Convenience function that uses the global tracker singleton.
    
    Args:
        entry_point: Entry point that triggered execution
        success: Whether execution was successful (default: True)
    
    Example:
        >>> track_execution_engine("JanusAgent.execute", success=True)
        >>> track_execution_engine("ActionCoordinator.execute_goal", success=False)
    """
    tracker = ExecutionMetricsTracker.get_instance()
    tracker.track_execution(entry_point, success)


def get_execution_metrics() -> Dict:
    """
    Get execution metrics.
    
    Returns:
        Dictionary with metrics
    
    Example:
        >>> metrics = get_execution_metrics()
        >>> print(metrics["total_executions"])
    """
    tracker = ExecutionMetricsTracker.get_instance()
    return tracker.get_metrics()


def log_execution_metrics_summary():
    """
    Log a summary of execution metrics.
    
    Example:
        >>> log_execution_metrics_summary()
    """
    tracker = ExecutionMetricsTracker.get_instance()
    tracker.log_summary()
