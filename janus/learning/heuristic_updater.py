"""
HeuristicUpdater - Dynamically adjusts parameters based on feedback
Updates wait times, OCR thresholds, and other heuristics
"""

import json
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from janus.logging import get_logger


class HeuristicUpdater:
    """
    Manages dynamic parameter adjustments based on performance feedback
    Continuously optimizes wait times, thresholds, and success probabilities
    """

    def __init__(
        self,
        feedback_manager,
        config_path: str = "heuristics_config.json",
        update_threshold: int = 10,  # Minimum samples before updating
    ):
        """
        Initialize heuristic updater

        Args:
            feedback_manager: FeedbackManager instance for accessing feedback data
            config_path: Path to heuristics configuration file
            update_threshold: Minimum number of samples before updating heuristics
        """
        self.feedback_manager = feedback_manager
        self.config_path = Path(config_path)
        self.update_threshold = update_threshold
        self.logger = get_logger("heuristic_updater")
        self.heuristics = self._load_heuristics()

    def _load_heuristics(self) -> Dict[str, Any]:
        """Load heuristics configuration from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load heuristics: {e}")

        # Return default heuristics
        return {
            "wait_times": {
                # Action type -> average wait time in ms
                "default": 500,
            },
            "ocr_thresholds": {
                # OCR confidence thresholds
                "default": 0.7,
                "text_detection": 0.7,
                "element_locator": 0.75,
            },
            "retry_counts": {
                # Number of retries per action type
                "default": 2,
            },
            "timeout_values": {
                # Timeout values in seconds
                "default": 10.0,
            },
            "success_probabilities": {
                # Expected success rates by action type
            },
            "last_updated": datetime.now().isoformat(),
            "update_count": 0,
        }

    def _save_heuristics(self) -> bool:
        """Save heuristics configuration to file"""
        try:
            self.heuristics["last_updated"] = datetime.now().isoformat()
            self.heuristics["update_count"] = self.heuristics.get("update_count", 0) + 1

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.heuristics, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.warning(f"Could not save heuristics: {e}")
            return False

    def get_wait_time(self, action_type: str) -> int:
        """
        Get recommended wait time for action type

        Args:
            action_type: Type of action

        Returns:
            Wait time in milliseconds
        """
        wait_times = self.heuristics.get("wait_times", {})
        return wait_times.get(action_type, wait_times.get("default", 500))

    def get_ocr_threshold(self, ocr_type: str = "default") -> float:
        """
        Get OCR confidence threshold

        Args:
            ocr_type: Type of OCR operation

        Returns:
            Confidence threshold (0.0-1.0)
        """
        thresholds = self.heuristics.get("ocr_thresholds", {})
        return thresholds.get(ocr_type, thresholds.get("default", 0.7))

    def get_retry_count(self, action_type: str) -> int:
        """
        Get recommended retry count for action type

        Args:
            action_type: Type of action

        Returns:
            Number of retries
        """
        retry_counts = self.heuristics.get("retry_counts", {})
        return retry_counts.get(action_type, retry_counts.get("default", 2))

    def get_timeout(self, action_type: str) -> float:
        """
        Get timeout value for action type

        Args:
            action_type: Type of action

        Returns:
            Timeout in seconds
        """
        timeouts = self.heuristics.get("timeout_values", {})
        return timeouts.get(action_type, timeouts.get("default", 10.0))

    def update_wait_times(self, days: int = 7) -> Dict[str, Any]:
        """
        Update wait times based on actual execution durations

        Args:
            days: Number of days of data to analyze

        Returns:
            Dictionary of updated wait times
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        # Get all action types from feedback
        from janus.learning.feedback_manager import FeedbackManager

        with self.feedback_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT action_type, duration_ms
                FROM action_feedback
                WHERE timestamp >= ?
                  AND success = 1
                  AND duration_ms IS NOT NULL
            """,
                (cutoff_date,),
            )

            # Group durations by action type
            durations_by_type = defaultdict(list)
            for row in cursor.fetchall():
                action_type, duration = row
                durations_by_type[action_type].append(duration)

        # Update wait times
        wait_times = self.heuristics.get("wait_times", {})
        updated = {}

        for action_type, durations in durations_by_type.items():
            if len(durations) >= self.update_threshold:
                # Use median + 20% safety margin
                median_duration = statistics.median(durations)
                new_wait_time = int(median_duration * 1.2)

                # Don't change drastically (max 50% change per update)
                old_wait_time = wait_times.get(action_type, wait_times.get("default", 500))
                max_change = old_wait_time * 0.5
                new_wait_time = max(
                    old_wait_time - max_change, min(new_wait_time, old_wait_time + max_change)
                )

                # Ensure minimum wait time
                new_wait_time = max(100, int(new_wait_time))

                wait_times[action_type] = new_wait_time
                updated[action_type] = {
                    "old": old_wait_time,
                    "new": new_wait_time,
                    "change_pct": (
                        ((new_wait_time - old_wait_time) / old_wait_time * 100)
                        if old_wait_time > 0
                        else 0
                    ),
                    "sample_count": len(durations),
                }

        self.heuristics["wait_times"] = wait_times
        self._save_heuristics()

        return updated

    def update_success_probabilities(self, days: int = 30) -> Dict[str, float]:
        """
        Update expected success probabilities for action types

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary of updated success probabilities
        """
        # Get statistics for each action type
        with self.feedback_manager._get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            cursor.execute(
                """
                SELECT
                    action_type,
                    COUNT(*) as total,
                    SUM(success) as successes
                FROM action_feedback
                WHERE timestamp >= ?
                GROUP BY action_type
                HAVING COUNT(*) >= ?
            """,
                (cutoff_date, self.update_threshold),
            )

            probabilities = {}
            for row in cursor.fetchall():
                action_type, total, successes = row
                probability = successes / total if total > 0 else 0.0
                probabilities[action_type] = probability

        self.heuristics["success_probabilities"] = probabilities
        self._save_heuristics()

        return probabilities

    def update_ocr_thresholds(
        self, ocr_type: str = "default", target_success_rate: float = 0.85, days: int = 7
    ) -> Optional[float]:
        """
        Adjust OCR confidence thresholds to achieve target success rate

        Args:
            ocr_type: Type of OCR operation
            target_success_rate: Desired success rate (0.0-1.0)
            days: Days of data to analyze

        Returns:
            New threshold or None if not enough data
        """
        # Get OCR-related feedback
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self.feedback_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(success) as successes
                FROM action_feedback
                WHERE timestamp >= ?
                  AND action_type LIKE '%ocr%'
                  OR action_type LIKE '%vision%'
            """,
                (cutoff_date,),
            )

            row = cursor.fetchone()
            total, successes = row

            if total < self.update_threshold:
                return None

            current_success_rate = successes / total if total > 0 else 0.0
            current_threshold = self.get_ocr_threshold(ocr_type)

            # Adjust threshold based on success rate
            if current_success_rate < target_success_rate:
                # Lower threshold to be more permissive
                new_threshold = max(0.5, current_threshold - 0.05)
            elif current_success_rate > target_success_rate + 0.1:
                # Raise threshold to be more strict
                new_threshold = min(0.95, current_threshold + 0.05)
            else:
                # Success rate is good, keep current threshold
                new_threshold = current_threshold

            thresholds = self.heuristics.get("ocr_thresholds", {})
            thresholds[ocr_type] = new_threshold
            self.heuristics["ocr_thresholds"] = thresholds
            self._save_heuristics()

            return new_threshold

    def update_retry_counts(self, days: int = 14) -> Dict[str, int]:
        """
        Update retry counts based on failure patterns

        Args:
            days: Days to analyze

        Returns:
            Dictionary of updated retry counts
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self.feedback_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    action_type,
                    AVG(success) as success_rate,
                    COUNT(*) as total
                FROM action_feedback
                WHERE timestamp >= ?
                GROUP BY action_type
                HAVING COUNT(*) >= ?
            """,
                (cutoff_date, self.update_threshold),
            )

            retry_counts = self.heuristics.get("retry_counts", {})
            updated = {}

            for row in cursor.fetchall():
                action_type, success_rate, total = row

                # Adjust retry count based on success rate
                if success_rate < 0.7:
                    # Low success rate - increase retries
                    new_retry_count = min(5, retry_counts.get(action_type, 2) + 1)
                elif success_rate > 0.95:
                    # High success rate - reduce retries
                    new_retry_count = max(1, retry_counts.get(action_type, 2) - 1)
                else:
                    # Keep current
                    new_retry_count = retry_counts.get(action_type, 2)

                retry_counts[action_type] = new_retry_count
                updated[action_type] = new_retry_count

        self.heuristics["retry_counts"] = retry_counts
        self._save_heuristics()

        return updated

    def update_all_heuristics(self, days: int = 7) -> Dict[str, Any]:
        """
        Update all heuristics based on recent feedback

        Args:
            days: Days of data to analyze

        Returns:
            Summary of all updates
        """
        updates = {
            "wait_times": self.update_wait_times(days),
            "success_probabilities": self.update_success_probabilities(days * 4),
            "retry_counts": self.update_retry_counts(days * 2),
            "timestamp": datetime.now().isoformat(),
        }

        return updates

    def get_heuristics_summary(self) -> Dict[str, Any]:
        """
        Get summary of current heuristics

        Returns:
            Dictionary with all current heuristics
        """
        return {
            "wait_times": self.heuristics.get("wait_times", {}),
            "ocr_thresholds": self.heuristics.get("ocr_thresholds", {}),
            "retry_counts": self.heuristics.get("retry_counts", {}),
            "timeout_values": self.heuristics.get("timeout_values", {}),
            "success_probabilities": self.heuristics.get("success_probabilities", {}),
            "last_updated": self.heuristics.get("last_updated"),
            "update_count": self.heuristics.get("update_count", 0),
        }
