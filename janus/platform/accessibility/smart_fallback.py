"""
Smart Fallback Strategies - Intelligent method selection

Phase 3: Optimization
- Learns which methods work best for different scenarios
- Adapts strategy based on success/failure patterns
- App-specific fallback rules
- Role-specific method preferences
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SmartFallbackStrategy:
    """
    Intelligent fallback strategy based on historical performance.
    
    Features:
        - Learns app-specific success patterns
        - Adapts method order based on role type
        - Tracks failure patterns
        - Provides recommended method order
    
    Usage:
        strategy = SmartFallbackStrategy()
        
        # Record outcome
        strategy.record_outcome(
            app_name="Safari",
            role="button",
            method="accessibility",
            success=True
        )
        
        # Get recommended method order
        methods = strategy.get_method_order(app_name="Safari", role="button")
        # Returns: ["accessibility", "vision", "som_fast_path"]
    """
    
    def __init__(self, learning_threshold: int = 10):
        """
        Initialize smart fallback strategy.
        
        Args:
            learning_threshold: Minimum samples before adapting strategy
        """
        self.learning_threshold = learning_threshold
        
        # Track success rates: app -> role -> method -> (success, total)
        self._outcomes: Dict[str, Dict[str, Dict[str, Tuple[int, int]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: (0, 0)))
        )
        
        # Default method order (accessibility first)
        self._default_order = ["accessibility", "som_fast_path", "vision"]
        
        logger.debug(
            f"SmartFallbackStrategy initialized (threshold={learning_threshold})"
        )
    
    def record_outcome(
        self,
        method: str,
        success: bool,
        app_name: Optional[str] = None,
        role: Optional[str] = None
    ):
        """
        Record method outcome for learning.
        
        Args:
            method: Method used
            success: Whether it succeeded
            app_name: Application context (optional)
            role: Element role (optional)
        """
        # Use "general" as default keys
        app_key = app_name or "general"
        role_key = role or "general"
        
        # Get current stats
        successes, total = self._outcomes[app_key][role_key][method]
        
        # Update stats
        if success:
            successes += 1
        total += 1
        
        self._outcomes[app_key][role_key][method] = (successes, total)
        
        logger.debug(
            f"Recorded {method} outcome for {app_key}/{role_key}: "
            f"{'✓' if success else '✗'} ({successes}/{total})"
        )
    
    def get_method_order(
        self,
        app_name: Optional[str] = None,
        role: Optional[str] = None
    ) -> List[str]:
        """
        Get recommended method order based on learned patterns.
        
        Args:
            app_name: Application context (optional)
            role: Element role (optional)
            
        Returns:
            List of methods in recommended order
        """
        app_key = app_name or "general"
        role_key = role or "general"
        
        # Check if we have enough data
        outcomes = self._outcomes.get(app_key, {}).get(role_key, {})
        
        if not outcomes:
            # No data, use default order
            return self._default_order.copy()
        
        # Check if we have enough samples
        total_samples = sum(total for _, total in outcomes.values())
        
        if total_samples < self.learning_threshold:
            # Not enough data yet, use default
            return self._default_order.copy()
        
        # Calculate success rates
        rates = {}
        for method, (successes, total) in outcomes.items():
            if total > 0:
                rates[method] = successes / total
        
        # Sort methods by success rate (descending)
        sorted_methods = sorted(
            rates.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Build ordered list
        ordered = [method for method, _ in sorted_methods]
        
        # Add any missing default methods at the end
        for method in self._default_order:
            if method not in ordered:
                ordered.append(method)
        
        logger.debug(
            f"Recommended order for {app_key}/{role_key}: {ordered} "
            f"(based on {total_samples} samples)"
        )
        
        return ordered
    
    def get_success_rate(
        self,
        method: str,
        app_name: Optional[str] = None,
        role: Optional[str] = None
    ) -> Optional[float]:
        """
        Get success rate for a specific method/app/role combination.
        
        Args:
            method: Method to check
            app_name: Application context (optional)
            role: Element role (optional)
            
        Returns:
            Success rate (0.0-1.0) or None if no data
        """
        app_key = app_name or "general"
        role_key = role or "general"
        
        outcomes = self._outcomes.get(app_key, {}).get(role_key, {})
        
        if method not in outcomes:
            return None
        
        successes, total = outcomes[method]
        return successes / total if total > 0 else None
    
    def get_app_recommendations(self, app_name: str) -> Dict[str, List[str]]:
        """
        Get method recommendations for all roles in an app.
        
        Args:
            app_name: Application to analyze
            
        Returns:
            Dictionary mapping roles to recommended method orders
        """
        recommendations = {}
        
        if app_name in self._outcomes:
            for role in self._outcomes[app_name].keys():
                recommendations[role] = self.get_method_order(app_name, role)
        
        return recommendations
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get strategy statistics.
        
        Returns:
            Dictionary with strategy stats
        """
        total_outcomes = 0
        apps_tracked = set()
        roles_tracked = set()
        
        for app_key, app_data in self._outcomes.items():
            apps_tracked.add(app_key)
            for role_key, role_data in app_data.items():
                roles_tracked.add(role_key)
                for method, (_, total) in role_data.items():
                    total_outcomes += total
        
        # Calculate global success rates
        global_rates = defaultdict(lambda: [0, 0])  # [successes, total]
        for app_data in self._outcomes.values():
            for role_data in app_data.values():
                for method, (successes, total) in role_data.items():
                    global_rates[method][0] += successes
                    global_rates[method][1] += total
        
        global_success_rates = {
            method: (stats[0] / stats[1] * 100) if stats[1] > 0 else 0
            for method, stats in global_rates.items()
        }
        
        return {
            "total_outcomes_recorded": total_outcomes,
            "apps_tracked": len(apps_tracked),
            "roles_tracked": len(roles_tracked),
            "learning_threshold": self.learning_threshold,
            "global_success_rates_percent": global_success_rates,
            "default_method_order": self._default_order
        }
    
    def export_learned_data(self) -> Dict[str, Any]:
        """
        Export learned patterns for analysis.
        
        Returns:
            Dictionary with all learned data
        """
        export = {}
        
        for app_key, app_data in self._outcomes.items():
            export[app_key] = {}
            for role_key, role_data in app_data.items():
                export[app_key][role_key] = {
                    method: {
                        "successes": successes,
                        "total": total,
                        "success_rate": successes / total if total > 0 else 0
                    }
                    for method, (successes, total) in role_data.items()
                }
        
        return export
    
    def clear(self):
        """Clear all learned data."""
        self._outcomes.clear()
        logger.debug("Smart fallback strategy data cleared")
