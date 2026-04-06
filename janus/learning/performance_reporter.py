"""
PerformanceReporter - Generates performance reports and analytics
Tracks improvements and provides session analytics
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from janus.logging import get_logger


class PerformanceReporter:
    """
    Generates performance reports and tracks improvements over time
    Provides session analytics and learning progress metrics
    """

    def __init__(self, feedback_manager, learning_cache, reports_dir: str = "performance_reports"):
        """
        Initialize performance reporter

        Args:
            feedback_manager: FeedbackManager instance
            learning_cache: LearningCache instance
            reports_dir: Directory for storing reports
        """
        self.logger = get_logger("performance_reporter")
        self.feedback_manager = feedback_manager
        self.learning_cache = learning_cache
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)

    def generate_session_report(self, session_id: str, save_to_file: bool = True) -> Dict[str, Any]:
        """
        Generate performance report for a session

        Args:
            session_id: Session identifier
            save_to_file: Whether to save report to file

        Returns:
            Session report dictionary
        """
        # Get session feedback
        session_feedback = self.feedback_manager.get_feedback_by_session(session_id)

        if not session_feedback:
            return {
                "session_id": session_id,
                "status": "no_data",
                "message": "No feedback data for this session",
            }

        # Calculate session metrics
        total_actions = len(session_feedback)
        successful_actions = sum(1 for f in session_feedback if f["success"])
        failed_actions = total_actions - successful_actions

        # Calculate average duration
        durations = [f["duration_ms"] for f in session_feedback if f.get("duration_ms")]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Group by action type
        actions_by_type = {}
        for feedback in session_feedback:
            action_type = feedback["action_type"]
            if action_type not in actions_by_type:
                actions_by_type[action_type] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "durations": [],
                }

            actions_by_type[action_type]["total"] += 1
            if feedback["success"]:
                actions_by_type[action_type]["successful"] += 1
            else:
                actions_by_type[action_type]["failed"] += 1

            if feedback.get("duration_ms"):
                actions_by_type[action_type]["durations"].append(feedback["duration_ms"])

        # Calculate success rates by type
        for action_type, stats in actions_by_type.items():
            stats["success_rate"] = (
                (stats["successful"] / stats["total"] * 100) if stats["total"] > 0 else 0
            )
            stats["avg_duration_ms"] = (
                sum(stats["durations"]) / len(stats["durations"]) if stats["durations"] else 0
            )
            del stats["durations"]  # Remove raw durations from report

        # Collect errors
        errors = [
            {
                "action_type": f["action_type"],
                "error_type": f.get("error_type"),
                "error_message": f.get("error_message"),
                "timestamp": f["timestamp"],
            }
            for f in session_feedback
            if not f["success"]
        ]

        # Build report
        report = {
            "session_id": session_id,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_actions": total_actions,
                "successful_actions": successful_actions,
                "failed_actions": failed_actions,
                "success_rate": (
                    (successful_actions / total_actions * 100) if total_actions > 0 else 0
                ),
                "avg_duration_ms": avg_duration,
            },
            "actions_by_type": actions_by_type,
            "errors": errors,
            "session_start": session_feedback[0]["timestamp"] if session_feedback else None,
            "session_end": session_feedback[-1]["timestamp"] if session_feedback else None,
        }

        # Save to file if requested
        if save_to_file:
            report_path = (
                self.reports_dir
                / f"session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

        return report

    def generate_improvement_report(
        self, days: int = 30, comparison_days: int = 30
    ) -> Dict[str, Any]:
        """
        Generate report showing improvements over time

        Args:
            days: Recent period to analyze
            comparison_days: Previous period to compare against

        Returns:
            Improvement report
        """
        # Current period
        current_stats = self.feedback_manager.get_action_statistics(days=days)

        # Previous period
        previous_cutoff = datetime.now() - timedelta(days=days + comparison_days)
        previous_end = datetime.now() - timedelta(days=days)

        # Get previous period stats manually
        with self.feedback_manager._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(*) as total, SUM(success) as successes
                FROM action_feedback
                WHERE timestamp >= ? AND timestamp < ?
            """,
                (previous_cutoff.isoformat(), previous_end.isoformat()),
            )

            row = cursor.fetchone()
            prev_total = row[0]
            prev_success = row[1]

            previous_stats = {
                "total_count": prev_total,
                "success_count": prev_success,
                "success_rate": (prev_success / prev_total * 100) if prev_total > 0 else 0,
            }

        # Calculate improvements
        success_rate_change = current_stats["success_rate"] - previous_stats["success_rate"]

        # Get recurring errors reduction
        recent_errors = self.feedback_manager.get_recurring_errors(days=days)
        older_errors = self.feedback_manager.get_recurring_errors(days=comparison_days)

        errors_reduced = len(older_errors) - len(recent_errors)

        # Get wait time accuracy from cache
        profile_stats = self.learning_cache.get_statistics()

        report = {
            "generated_at": datetime.now().isoformat(),
            "analysis_period": {"current_days": days, "comparison_days": comparison_days},
            "current_period": current_stats,
            "previous_period": previous_stats,
            "improvements": {
                "success_rate_change": success_rate_change,
                "success_rate_change_pct": (
                    (success_rate_change / previous_stats["success_rate"] * 100)
                    if previous_stats["success_rate"] > 0
                    else 0
                ),
                "recurring_errors_reduced": errors_reduced,
                "total_learning_updates": profile_stats.get("learning_updates", 0),
            },
            "recurring_errors": {
                "current": recent_errors,
                "count_current": len(recent_errors),
                "count_previous": len(older_errors),
            },
        }

        return report

    def generate_accuracy_report(
        self, action_type: Optional[str] = None, days: int = 30
    ) -> Dict[str, Any]:
        """
        Generate report on wait time and parameter accuracy

        Args:
            action_type: Specific action type (None for all)
            days: Days to analyze

        Returns:
            Accuracy report
        """
        stats = self.feedback_manager.get_action_statistics(action_type=action_type, days=days)

        # Get cached heuristics
        all_heuristics = self.learning_cache.get_all_heuristics()

        # Calculate wait time accuracy
        wait_time_accuracy = {}

        with self.feedback_manager._get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            query = """
                SELECT action_type, duration_ms
                FROM action_feedback
                WHERE timestamp >= ? AND success = 1 AND duration_ms IS NOT NULL
            """
            params = [cutoff_date]

            if action_type:
                query += " AND action_type = ?"
                params.append(action_type)

            cursor.execute(query, params)

            # Group by action type
            durations_by_type = {}
            for row in cursor.fetchall():
                at = row[0]
                duration = row[1]
                if at not in durations_by_type:
                    durations_by_type[at] = []
                durations_by_type[at].append(duration)

            # Calculate accuracy for each type
            for at, durations in durations_by_type.items():
                # Get cached wait time
                cached_wait_key = f"wait_time_{at}"
                cached_wait = self.learning_cache.get_heuristic(cached_wait_key)

                if cached_wait:
                    avg_actual = sum(durations) / len(durations)
                    diff = abs(cached_wait - avg_actual)
                    accuracy_pct = (1 - min(diff / cached_wait, 1)) * 100

                    wait_time_accuracy[at] = {
                        "cached_wait_ms": cached_wait,
                        "avg_actual_ms": avg_actual,
                        "difference_ms": diff,
                        "accuracy_pct": accuracy_pct,
                        "sample_count": len(durations),
                    }

        report = {
            "generated_at": datetime.now().isoformat(),
            "action_type": action_type or "all",
            "period_days": days,
            "overall_statistics": stats,
            "wait_time_accuracy": wait_time_accuracy,
            "total_heuristics_cached": len(all_heuristics),
        }

        return report

    def generate_comprehensive_report(
        self, days: int = 30, save_to_file: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive performance report

        Args:
            days: Days to analyze
            save_to_file: Whether to save to file

        Returns:
            Comprehensive report
        """
        # Gather all sub-reports
        overall_stats = self.feedback_manager.get_action_statistics(days=days)
        improvement_report = self.generate_improvement_report(days=days, comparison_days=days)
        accuracy_report = self.generate_accuracy_report(days=days)

        # Get learning cache summary
        cache_summary = self.learning_cache.get_cache_summary()

        # Get recurring errors
        recurring_errors = self.feedback_manager.get_recurring_errors(days=days)

        report = {
            "generated_at": datetime.now().isoformat(),
            "report_type": "comprehensive",
            "period_days": days,
            "overall_performance": overall_stats,
            "improvements": improvement_report["improvements"],
            "accuracy": {
                "wait_times": accuracy_report.get("wait_time_accuracy", {}),
                "overall_success_rate": overall_stats["success_rate"],
            },
            "learning_status": {
                "profile": cache_summary["profile_name"],
                "heuristics_learned": cache_summary["heuristics_count"],
                "preferences_stored": cache_summary["preferences_count"],
                "total_actions": cache_summary["statistics"].get("total_actions", 0),
                "total_corrections": cache_summary["statistics"].get("total_corrections", 0),
            },
            "issues": {
                "recurring_errors": recurring_errors,
                "recurring_errors_count": len(recurring_errors),
            },
        }

        # Save to file if requested
        if save_to_file:
            report_path = (
                self.reports_dir / f"comprehensive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

        return report

    def list_reports(self) -> List[str]:
        """
        List all generated reports

        Returns:
            List of report file paths
        """
        return [str(p) for p in self.reports_dir.glob("*.json")]

    def load_report(self, report_path: str) -> Optional[Dict[str, Any]]:
        """
        Load a previously generated report

        Args:
            report_path: Path to report file

        Returns:
            Report data or None
        """
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading report: {e}", exc_info=True)
            return None
