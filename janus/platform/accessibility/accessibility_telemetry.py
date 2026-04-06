"""
Accessibility Telemetry - Track method usage and performance

Phase 3: Optimization
- Tracks accessibility vs vision usage
- Records performance metrics
- Identifies failure patterns
- Provides insights for optimization
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AccessibilityMetric:
    """Single accessibility operation metric."""
    method: str  # "accessibility", "vision", "som_fast_path"
    operation: str  # "find_element", "click_element", "get_state"
    success: bool
    duration_ms: float
    element_name: Optional[str] = None
    element_role: Optional[str] = None
    app_name: Optional[str] = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class AccessibilityTelemetry:
    """
    Telemetry tracking for accessibility operations.
    
    Tracks:
        - Method usage (accessibility vs vision vs SOM)
        - Success/failure rates
        - Performance metrics
        - Failure patterns
        - App compatibility
    
    Usage:
        telemetry = AccessibilityTelemetry()
        
        # Record metric
        telemetry.record_metric(
            method="accessibility",
            operation="find_element",
            success=True,
            duration_ms=45.2,
            element_role="button"
        )
        
        # Get insights
        stats = telemetry.get_summary()
    """
    
    def __init__(self, max_metrics: int = 1000):
        """
        Initialize telemetry.
        
        Args:
            max_metrics: Maximum metrics to keep in memory
        """
        self.max_metrics = max_metrics
        self._metrics: List[AccessibilityMetric] = []
        
        # Quick lookup counters
        self._method_counts: Dict[str, int] = defaultdict(int)
        self._success_counts: Dict[str, int] = defaultdict(int)
        self._failure_counts: Dict[str, int] = defaultdict(int)
        
        logger.debug(f"AccessibilityTelemetry initialized (max_metrics={max_metrics})")
    
    def record_metric(
        self,
        method: str,
        operation: str,
        success: bool,
        duration_ms: float,
        element_name: Optional[str] = None,
        element_role: Optional[str] = None,
        app_name: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        Record an accessibility operation metric.
        
        Args:
            method: Method used (accessibility, vision, som_fast_path)
            operation: Operation performed (find_element, click_element, etc.)
            success: Whether operation succeeded
            duration_ms: Duration in milliseconds
            element_name: Element name (optional)
            element_role: Element role (optional)
            app_name: Application name (optional)
            error: Error message if failed (optional)
        """
        metric = AccessibilityMetric(
            method=method,
            operation=operation,
            success=success,
            duration_ms=duration_ms,
            element_name=element_name,
            element_role=element_role,
            app_name=app_name,
            error=error
        )
        
        # Add to metrics list
        self._metrics.append(metric)
        
        # Trim if exceeds max
        if len(self._metrics) > self.max_metrics:
            self._metrics = self._metrics[-self.max_metrics:]
        
        # Update counters
        self._method_counts[method] += 1
        
        if success:
            self._success_counts[f"{method}_{operation}"] += 1
        else:
            self._failure_counts[f"{method}_{operation}"] += 1
        
        logger.debug(
            f"Telemetry: {method}.{operation} "
            f"{'✓' if success else '✗'} "
            f"{duration_ms:.1f}ms"
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics.
        
        Returns:
            Dictionary with telemetry summary
        """
        if not self._metrics:
            return {"total_operations": 0}
        
        # Calculate method usage
        total_ops = len(self._metrics)
        method_usage = {
            method: (count / total_ops * 100)
            for method, count in self._method_counts.items()
        }
        
        # Calculate success rates per method
        success_rates = {}
        for method in self._method_counts.keys():
            successes = sum(1 for m in self._metrics if m.method == method and m.success)
            total = sum(1 for m in self._metrics if m.method == method)
            success_rates[method] = (successes / total * 100) if total > 0 else 0
        
        # Calculate average durations per method
        avg_durations = {}
        for method in self._method_counts.keys():
            durations = [m.duration_ms for m in self._metrics if m.method == method]
            avg_durations[method] = sum(durations) / len(durations) if durations else 0
        
        # Find most common failures
        failures = [m for m in self._metrics if not m.success]
        failure_reasons = defaultdict(int)
        for f in failures:
            if f.error:
                failure_reasons[f.error[:50]] += 1  # Truncate long errors
        
        # Most problematic apps
        app_failures = defaultdict(int)
        for f in failures:
            if f.app_name:
                app_failures[f.app_name] += 1
        
        return {
            "total_operations": total_ops,
            "method_usage_percent": method_usage,
            "success_rates_percent": success_rates,
            "avg_duration_ms": avg_durations,
            "top_failure_reasons": dict(sorted(
                failure_reasons.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]),
            "problematic_apps": dict(sorted(
                app_failures.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]),
            "recent_metrics_count": len(self._metrics)
        }
    
    def get_performance_comparison(self) -> Dict[str, Any]:
        """
        Get performance comparison between methods.
        
        Returns:
            Performance comparison data
        """
        methods = ["accessibility", "vision", "som_fast_path"]
        comparison = {}
        
        for method in methods:
            method_metrics = [m for m in self._metrics if m.method == method]
            
            if not method_metrics:
                continue
            
            durations = [m.duration_ms for m in method_metrics]
            successes = sum(1 for m in method_metrics if m.success)
            
            comparison[method] = {
                "count": len(method_metrics),
                "avg_duration_ms": sum(durations) / len(durations),
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
                "success_rate_percent": (successes / len(method_metrics) * 100) if method_metrics else 0
            }
        
        # Calculate speedup
        if "accessibility" in comparison and "vision" in comparison:
            acc_avg = comparison["accessibility"]["avg_duration_ms"]
            vis_avg = comparison["vision"]["avg_duration_ms"]
            comparison["accessibility_speedup"] = vis_avg / acc_avg if acc_avg > 0 else 0
        
        return comparison
    
    def get_role_insights(self) -> Dict[str, Any]:
        """
        Get insights about which roles work best with accessibility.
        
        Returns:
            Role-based insights
        """
        role_stats = defaultdict(lambda: {"total": 0, "accessibility_success": 0, "vision_fallback": 0})
        
        for metric in self._metrics:
            if metric.element_role:
                role = metric.element_role
                role_stats[role]["total"] += 1
                
                if metric.method == "accessibility" and metric.success:
                    role_stats[role]["accessibility_success"] += 1
                elif metric.method == "vision":
                    role_stats[role]["vision_fallback"] += 1
        
        # Calculate success rates
        insights = {}
        for role, stats in role_stats.items():
            if stats["total"] > 0:
                insights[role] = {
                    "total_uses": stats["total"],
                    "accessibility_success_rate": (
                        stats["accessibility_success"] / stats["total"] * 100
                    ),
                    "vision_fallback_rate": (
                        stats["vision_fallback"] / stats["total"] * 100
                    )
                }
        
        # Sort by most used
        return dict(sorted(
            insights.items(),
            key=lambda x: x[1]["total_uses"],
            reverse=True
        ))
    
    def export_metrics(self) -> List[Dict[str, Any]]:
        """
        Export all metrics as dictionaries.
        
        Returns:
            List of metric dictionaries
        """
        return [
            {
                "method": m.method,
                "operation": m.operation,
                "success": m.success,
                "duration_ms": m.duration_ms,
                "element_name": m.element_name,
                "element_role": m.element_role,
                "app_name": m.app_name,
                "error": m.error,
                "timestamp": m.timestamp
            }
            for m in self._metrics
        ]
    
    def clear(self):
        """Clear all metrics and counters."""
        self._metrics.clear()
        self._method_counts.clear()
        self._success_counts.clear()
        self._failure_counts.clear()
        logger.debug("Telemetry cleared")
