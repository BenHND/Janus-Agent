"""
UserCorrectionListener - Captures and processes user corrections
Listens for voice corrections and adjusts future behavior
"""

import json
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from janus.logging import get_logger


class UserCorrectionListener:
    """
    Listens for user corrections and updates action preferences
    Handles voice corrections like "non, pas ça" or "not that"
    """

    # Correction phrases in multiple languages
    CORRECTION_PHRASES = {
        "fr": [
            "non",
            "pas ça",
            "pas comme ça",
            "erreur",
            "annule",
            "ce n'est pas ça",
            "mauvais",
            "incorrect",
            "faux",
        ],
        "en": [
            "no",
            "not that",
            "wrong",
            "error",
            "cancel",
            "undo",
            "that's not it",
            "incorrect",
            "false",
            "bad",
        ],
    }

    def __init__(
        self,
        correction_history_path: str = "correction_history.json",
        recent_actions_size: int = 10,
        correction_window_seconds: int = 10,
    ):
        """
        Initialize user correction listener

        Args:
            correction_history_path: Path to correction history file
            recent_actions_size: Number of recent actions to track
            correction_window_seconds: Time window for associating corrections
        """
        self.logger = get_logger("user_correction_listener")
        self.correction_history_path = Path(correction_history_path)
        self.recent_actions = deque(maxlen=recent_actions_size)
        self.correction_window_seconds = correction_window_seconds
        self.corrections = self._load_corrections()

    def _load_corrections(self) -> Dict[str, Any]:
        """Load correction history from file"""
        if self.correction_history_path.exists():
            try:
                with open(self.correction_history_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load corrections: {e}")

        return {
            "corrections": [],
            "correction_patterns": {},
            "action_preferences": {},
            "last_updated": datetime.now().isoformat(),
        }

    def _save_corrections(self) -> bool:
        """Save correction history to file"""
        try:
            self.corrections["last_updated"] = datetime.now().isoformat()

            with open(self.correction_history_path, "w", encoding="utf-8") as f:
                json.dump(self.corrections, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.warning(f"Could not save corrections: {e}")
            return False

    def record_action(self, action: Dict[str, Any]):
        """
        Record a recently executed action

        Args:
            action: Action details (type, parameters, timestamp, etc.)
        """
        action_record = {**action, "timestamp": action.get("timestamp", datetime.now().isoformat())}
        self.recent_actions.append(action_record)

    def is_correction_phrase(self, text: str, language: str = "fr") -> bool:
        """
        Check if text contains a correction phrase

        Args:
            text: User input text
            language: Language code (fr, en)

        Returns:
            True if text contains correction phrase
        """
        text_lower = text.lower().strip()
        phrases = self.CORRECTION_PHRASES.get(language, [])

        # Check for exact matches or contains
        for phrase in phrases:
            if phrase in text_lower or text_lower.startswith(phrase):
                return True

        return False

    def process_correction(
        self,
        correction_text: str,
        language: str = "fr",
        alternative_action: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Process a user correction

        Args:
            correction_text: User's correction input
            language: Language of correction
            alternative_action: User's preferred alternative action

        Returns:
            Corrected action details or None
        """
        if not self.is_correction_phrase(correction_text, language):
            return None

        # Find the most recent action within the correction window
        corrected_action = self._find_recent_action()

        if not corrected_action:
            return None

        # Record the correction
        correction_record = {
            "timestamp": datetime.now().isoformat(),
            "original_action": corrected_action,
            "correction_text": correction_text,
            "alternative_action": alternative_action,
            "language": language,
        }

        self.corrections["corrections"].append(correction_record)

        # Update correction patterns
        self._update_correction_patterns(corrected_action, alternative_action)

        # Update action preferences
        self._update_action_preferences(corrected_action, alternative_action)

        self._save_corrections()

        return correction_record

    def _find_recent_action(self) -> Optional[Dict[str, Any]]:
        """
        Find the most recent action within the correction window

        Returns:
            Recent action or None
        """
        if not self.recent_actions:
            return None

        now = datetime.now()
        cutoff = now - timedelta(seconds=self.correction_window_seconds)

        # Look for the most recent action within window
        for action in reversed(self.recent_actions):
            action_time = datetime.fromisoformat(action["timestamp"])
            if action_time >= cutoff:
                return action

        # If no action in window, return the most recent
        return self.recent_actions[-1] if self.recent_actions else None

    def _update_correction_patterns(
        self, corrected_action: Dict[str, Any], alternative_action: Optional[Dict[str, Any]]
    ):
        """Update correction patterns for learning"""
        action_type = corrected_action.get("action_type")
        if not action_type:
            return

        patterns = self.corrections.get("correction_patterns", {})

        if action_type not in patterns:
            patterns[action_type] = {
                "correction_count": 0,
                "common_contexts": {},
                "alternatives": [],
            }

        patterns[action_type]["correction_count"] += 1

        # Track context that led to correction
        context = corrected_action.get("context", {})
        context_key = json.dumps(context, sort_keys=True)

        common_contexts = patterns[action_type]["common_contexts"]
        common_contexts[context_key] = common_contexts.get(context_key, 0) + 1

        # Track alternatives
        if alternative_action:
            patterns[action_type]["alternatives"].append(
                {
                    "original_context": context,
                    "alternative": alternative_action,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        self.corrections["correction_patterns"] = patterns

    def _update_action_preferences(
        self, corrected_action: Dict[str, Any], alternative_action: Optional[Dict[str, Any]]
    ):
        """Update user's action preferences"""
        action_type = corrected_action.get("action_type")
        if not action_type:
            return

        preferences = self.corrections.get("action_preferences", {})

        if action_type not in preferences:
            preferences[action_type] = {"avoid_contexts": [], "prefer_alternatives": []}

        # Mark context to avoid
        context = corrected_action.get("context", {})
        preferences[action_type]["avoid_contexts"].append(
            {"context": context, "timestamp": datetime.now().isoformat()}
        )

        # Record preferred alternative if provided
        if alternative_action:
            preferences[action_type]["prefer_alternatives"].append(
                {"alternative": alternative_action, "timestamp": datetime.now().isoformat()}
            )

        self.corrections["action_preferences"] = preferences

    def get_correction_count(
        self, action_type: Optional[str] = None, days: Optional[int] = None
    ) -> int:
        """
        Get count of corrections

        Args:
            action_type: Filter by action type
            days: Filter by recent days

        Returns:
            Number of corrections
        """
        corrections = self.corrections.get("corrections", [])

        if days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            corrections = [c for c in corrections if c["timestamp"] >= cutoff]

        if action_type:
            corrections = [
                c
                for c in corrections
                if c.get("original_action", {}).get("action_type") == action_type
            ]

        return len(corrections)

    def get_correction_patterns(self, action_type: str) -> Dict[str, Any]:
        """
        Get correction patterns for an action type

        Args:
            action_type: Type of action

        Returns:
            Correction patterns
        """
        patterns = self.corrections.get("correction_patterns", {})
        return patterns.get(
            action_type, {"correction_count": 0, "common_contexts": {}, "alternatives": []}
        )

    def should_avoid_action(
        self, action_type: str, context: Dict[str, Any], threshold: int = 2
    ) -> bool:
        """
        Check if action should be avoided based on corrections

        Args:
            action_type: Type of action
            context: Action context
            threshold: Minimum corrections to avoid

        Returns:
            True if action should be avoided
        """
        preferences = self.corrections.get("action_preferences", {})
        action_prefs = preferences.get(action_type, {})
        avoid_contexts = action_prefs.get("avoid_contexts", [])

        if not avoid_contexts:
            return False

        # Check if current context matches avoided contexts
        context_str = json.dumps(context, sort_keys=True)
        match_count = sum(
            1
            for avoided in avoid_contexts
            if json.dumps(avoided["context"], sort_keys=True) == context_str
        )

        return match_count >= threshold

    def get_preferred_alternative(
        self, action_type: str, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get preferred alternative for an action

        Args:
            action_type: Type of action
            context: Action context

        Returns:
            Preferred alternative or None
        """
        preferences = self.corrections.get("action_preferences", {})
        action_prefs = preferences.get(action_type, {})
        alternatives = action_prefs.get("prefer_alternatives", [])

        if not alternatives:
            return None

        # Return the most recent alternative
        # In a more sophisticated version, this could match by context
        return alternatives[-1]["alternative"] if alternatives else None

    def get_corrections_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Get summary of corrections

        Args:
            days: Number of days to analyze

        Returns:
            Summary statistics
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        recent_corrections = [
            c for c in self.corrections.get("corrections", []) if c["timestamp"] >= cutoff
        ]

        # Count by action type
        by_type = {}
        for correction in recent_corrections:
            action_type = correction.get("original_action", {}).get("action_type", "unknown")
            by_type[action_type] = by_type.get(action_type, 0) + 1

        return {
            "total_corrections": len(recent_corrections),
            "corrections_by_type": by_type,
            "patterns_tracked": len(self.corrections.get("correction_patterns", {})),
            "preferences_tracked": len(self.corrections.get("action_preferences", {})),
            "period_days": days,
        }
