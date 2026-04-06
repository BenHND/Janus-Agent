"""
LearningCache - Persists learning adjustments and user profiles
Maintains local cache of optimizations and preferences
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from janus.logging import get_logger


class LearningCache:
    """
    Persistent cache for learning data and user profiles
    Stores parameter adjustments, preferences, and performance data
    """

    def __init__(
        self,
        cache_path: str = "learning_cache.json",
        profile_name: str = "default",
        max_heuristics: int = 1000,
        max_preferences: int = 500,
    ):
        """
        Initialize learning cache

        Args:
            cache_path: Path to cache file
            profile_name: User profile name
            max_heuristics: Maximum number of heuristics to store (LRU eviction)
            max_preferences: Maximum number of preferences to store (LRU eviction)
        """
        self.cache_path = Path(cache_path)
        self.profile_name = profile_name
        self.max_heuristics = max_heuristics
        self.max_preferences = max_preferences
        self.logger = get_logger("learning_cache")
        self.cache = self._load_cache()
        self._ensure_profile_exists()

    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from file"""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load cache: {e}")

        return {
            "profiles": {},
            "global_settings": {},
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
        }

    def _save_cache(self) -> bool:
        """Save cache to file"""
        try:
            self.cache["last_accessed"] = datetime.now().isoformat()

            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.warning(f"Could not save cache: {e}")
            return False

    def _ensure_profile_exists(self):
        """Ensure current profile exists in cache"""
        if "profiles" not in self.cache:
            self.cache["profiles"] = {}

        if self.profile_name not in self.cache["profiles"]:
            self.cache["profiles"][self.profile_name] = {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "heuristics": {},
                "preferences": {},
                "statistics": {"total_actions": 0, "total_corrections": 0, "learning_updates": 0},
            }
            self._save_cache()

    def get_profile(self) -> Dict[str, Any]:
        """
        Get current user profile

        Returns:
            Profile data
        """
        return self.cache["profiles"].get(self.profile_name, {})

    def update_profile(self, updates: Dict[str, Any]):
        """
        Update current user profile

        Args:
            updates: Profile updates to apply
        """
        profile = self.get_profile()
        profile.update(updates)
        profile["last_updated"] = datetime.now().isoformat()
        self.cache["profiles"][self.profile_name] = profile
        self._save_cache()

    def _evict_oldest_heuristics(self, profile: Dict[str, Any]):
        """Evict oldest heuristics if over limit (LRU)"""
        heuristics = profile.get("heuristics", {})

        if len(heuristics) > self.max_heuristics:
            # Sort by timestamp and keep newest
            sorted_items = sorted(
                heuristics.items(), key=lambda x: x[1].get("timestamp", ""), reverse=True
            )

            profile["heuristics"] = dict(sorted_items[: self.max_heuristics])

    def _evict_oldest_preferences(self, profile: Dict[str, Any]):
        """Evict oldest preferences if over limit (LRU)"""
        preferences = profile.get("preferences", {})

        if len(preferences) > self.max_preferences:
            # Sort by timestamp and keep newest
            sorted_items = sorted(
                preferences.items(), key=lambda x: x[1].get("timestamp", ""), reverse=True
            )

            profile["preferences"] = dict(sorted_items[: self.max_preferences])

    def store_heuristic(
        self, heuristic_name: str, value: Any, metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Store a heuristic value in cache

        Args:
            heuristic_name: Name of heuristic
            value: Heuristic value
            metadata: Optional metadata about the heuristic
        """
        profile = self.get_profile()

        if "heuristics" not in profile:
            profile["heuristics"] = {}

        profile["heuristics"][heuristic_name] = {
            "value": value,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }

        # Evict old entries if over limit
        self._evict_oldest_heuristics(profile)

        profile["statistics"]["learning_updates"] = (
            profile.get("statistics", {}).get("learning_updates", 0) + 1
        )

        self.update_profile(profile)

    def get_heuristic(self, heuristic_name: str, default: Any = None) -> Any:
        """
        Get a heuristic value from cache

        Args:
            heuristic_name: Name of heuristic
            default: Default value if not found

        Returns:
            Heuristic value or default
        """
        profile = self.get_profile()
        heuristics = profile.get("heuristics", {})

        if heuristic_name in heuristics:
            return heuristics[heuristic_name]["value"]

        return default

    def store_preference(
        self, preference_name: str, value: Any, context: Optional[Dict[str, Any]] = None
    ):
        """
        Store a user preference

        Args:
            preference_name: Name of preference
            value: Preference value
            context: Optional context information
        """
        profile = self.get_profile()

        if "preferences" not in profile:
            profile["preferences"] = {}

        profile["preferences"][preference_name] = {
            "value": value,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
        }

        # Evict old entries if over limit
        self._evict_oldest_preferences(profile)

        self.update_profile(profile)

    def get_preference(self, preference_name: str, default: Any = None) -> Any:
        """
        Get a user preference

        Args:
            preference_name: Name of preference
            default: Default value if not found

        Returns:
            Preference value or default
        """
        profile = self.get_profile()
        preferences = profile.get("preferences", {})

        if preference_name in preferences:
            return preferences[preference_name]["value"]

        return default

    def increment_action_count(self, count: int = 1):
        """
        Increment total action count

        Args:
            count: Number to increment by
        """
        profile = self.get_profile()
        stats = profile.get("statistics", {})
        stats["total_actions"] = stats.get("total_actions", 0) + count
        profile["statistics"] = stats
        self.update_profile(profile)

    def increment_correction_count(self, count: int = 1):
        """
        Increment total correction count

        Args:
            count: Number to increment by
        """
        profile = self.get_profile()
        stats = profile.get("statistics", {})
        stats["total_corrections"] = stats.get("total_corrections", 0) + count
        profile["statistics"] = stats
        self.update_profile(profile)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get profile statistics

        Returns:
            Statistics dictionary
        """
        profile = self.get_profile()
        return profile.get(
            "statistics", {"total_actions": 0, "total_corrections": 0, "learning_updates": 0}
        )

    def get_all_heuristics(self) -> Dict[str, Any]:
        """
        Get all cached heuristics

        Returns:
            Dictionary of heuristics
        """
        profile = self.get_profile()
        return profile.get("heuristics", {})

    def get_all_preferences(self) -> Dict[str, Any]:
        """
        Get all user preferences

        Returns:
            Dictionary of preferences
        """
        profile = self.get_profile()
        return profile.get("preferences", {})

    def clear_old_data(self, days: int = 90):
        """
        Clear old cached data

        Args:
            days: Keep data from last N days
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        profile = self.get_profile()

        # Clear old heuristics
        heuristics = profile.get("heuristics", {})
        updated_heuristics = {
            name: data for name, data in heuristics.items() if data.get("timestamp", "") >= cutoff
        }
        profile["heuristics"] = updated_heuristics

        # Clear old preferences
        preferences = profile.get("preferences", {})
        updated_preferences = {
            name: data for name, data in preferences.items() if data.get("timestamp", "") >= cutoff
        }
        profile["preferences"] = updated_preferences

        self.update_profile(profile)

    def export_profile(self, output_path: str) -> bool:
        """
        Export profile to file

        Args:
            output_path: Path to export file

        Returns:
            True if successful
        """
        try:
            profile = self.get_profile()

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            self.logger.error(f"Error exporting profile: {e}", exc_info=True)
            return False

    def import_profile(self, input_path: str) -> bool:
        """
        Import profile from file

        Args:
            input_path: Path to import file

        Returns:
            True if successful
        """
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                imported_profile = json.load(f)

            # Merge with existing profile
            profile = self.get_profile()
            profile.update(imported_profile)
            profile["last_updated"] = datetime.now().isoformat()

            self.cache["profiles"][self.profile_name] = profile
            self._save_cache()

            return True
        except Exception as e:
            self.logger.error(f"Error importing profile: {e}", exc_info=True)
            return False

    def list_profiles(self) -> List[str]:
        """
        List all available profiles

        Returns:
            List of profile names
        """
        return list(self.cache.get("profiles", {}).keys())

    def switch_profile(self, profile_name: str):
        """
        Switch to a different profile

        Args:
            profile_name: Name of profile to switch to
        """
        self.profile_name = profile_name
        self._ensure_profile_exists()

    def get_cache_summary(self) -> Dict[str, Any]:
        """
        Get summary of cache contents

        Returns:
            Cache summary
        """
        profile = self.get_profile()

        return {
            "profile_name": self.profile_name,
            "created_at": profile.get("created_at"),
            "last_updated": profile.get("last_updated"),
            "heuristics_count": len(profile.get("heuristics", {})),
            "preferences_count": len(profile.get("preferences", {})),
            "statistics": profile.get("statistics", {}),
            "total_profiles": len(self.cache.get("profiles", {})),
        }
