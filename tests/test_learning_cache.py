"""
Unit tests for LearningCache
"""

import os
import tempfile
import unittest

from janus.learning.learning_cache import LearningCache


class TestLearningCache(unittest.TestCase):
    """Test cases for LearningCache"""

    def setUp(self):
        """Set up test environment"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.cache = LearningCache(cache_path=self.temp_file.name, profile_name="test_user")

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_profile_creation(self):
        """Test that profile is created on initialization"""
        profile = self.cache.get_profile()

        self.assertIsNotNone(profile)
        self.assertIn("created_at", profile)
        self.assertIn("heuristics", profile)
        self.assertIn("preferences", profile)
        self.assertIn("statistics", profile)

    def test_store_and_get_heuristic(self):
        """Test storing and retrieving heuristic"""
        self.cache.store_heuristic("wait_time_click", 500, metadata={"source": "learned"})

        value = self.cache.get_heuristic("wait_time_click")
        self.assertEqual(value, 500)

    def test_get_heuristic_default(self):
        """Test getting heuristic with default value"""
        value = self.cache.get_heuristic("nonexistent", default=100)
        self.assertEqual(value, 100)

    def test_store_and_get_preference(self):
        """Test storing and retrieving preference"""
        self.cache.store_preference("preferred_browser", "chrome", context={"platform": "macos"})

        value = self.cache.get_preference("preferred_browser")
        self.assertEqual(value, "chrome")

    def test_get_preference_default(self):
        """Test getting preference with default value"""
        value = self.cache.get_preference("nonexistent", default="safari")
        self.assertEqual(value, "safari")

    def test_increment_action_count(self):
        """Test incrementing action count"""
        initial_stats = self.cache.get_statistics()
        initial_count = initial_stats.get("total_actions", 0)

        self.cache.increment_action_count(5)

        new_stats = self.cache.get_statistics()
        self.assertEqual(new_stats["total_actions"], initial_count + 5)

    def test_increment_correction_count(self):
        """Test incrementing correction count"""
        initial_stats = self.cache.get_statistics()
        initial_count = initial_stats.get("total_corrections", 0)

        self.cache.increment_correction_count(3)

        new_stats = self.cache.get_statistics()
        self.assertEqual(new_stats["total_corrections"], initial_count + 3)

    def test_get_all_heuristics(self):
        """Test getting all heuristics"""
        self.cache.store_heuristic("heuristic1", 100)
        self.cache.store_heuristic("heuristic2", 200)

        all_heuristics = self.cache.get_all_heuristics()

        self.assertEqual(len(all_heuristics), 2)
        self.assertIn("heuristic1", all_heuristics)
        self.assertIn("heuristic2", all_heuristics)

    def test_get_all_preferences(self):
        """Test getting all preferences"""
        self.cache.store_preference("pref1", "value1")
        self.cache.store_preference("pref2", "value2")

        all_preferences = self.cache.get_all_preferences()

        self.assertEqual(len(all_preferences), 2)
        self.assertIn("pref1", all_preferences)
        self.assertIn("pref2", all_preferences)

    def test_clear_old_data(self):
        """Test clearing old cached data"""
        # Store some data
        self.cache.store_heuristic("old_heuristic", 100)
        self.cache.store_preference("old_preference", "value")

        # Clear old data (keep only last 0 days, so everything is old)
        self.cache.clear_old_data(days=0)

        # Data should be cleared
        all_heuristics = self.cache.get_all_heuristics()
        all_preferences = self.cache.get_all_preferences()

        self.assertEqual(len(all_heuristics), 0)
        self.assertEqual(len(all_preferences), 0)

    def test_export_profile(self):
        """Test exporting profile to file"""
        # Store some data
        self.cache.store_heuristic("test_heuristic", 123)
        self.cache.store_preference("test_pref", "test_value")

        # Export to temp file
        export_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        export_file.close()

        try:
            success = self.cache.export_profile(export_file.name)
            self.assertTrue(success)

            # Verify file exists and has content
            self.assertTrue(os.path.exists(export_file.name))
            self.assertGreater(os.path.getsize(export_file.name), 0)
        finally:
            if os.path.exists(export_file.name):
                os.unlink(export_file.name)

    def test_import_profile(self):
        """Test importing profile from file"""
        # Create a profile with data
        self.cache.store_heuristic("import_test", 999)

        # Export it
        export_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        export_file.close()

        try:
            self.cache.export_profile(export_file.name)

            # Create new cache with different profile
            new_cache = LearningCache(cache_path=self.temp_file.name, profile_name="new_profile")

            # Import the exported profile
            success = new_cache.import_profile(export_file.name)
            self.assertTrue(success)

            # Verify data was imported
            value = new_cache.get_heuristic("import_test")
            self.assertEqual(value, 999)
        finally:
            if os.path.exists(export_file.name):
                os.unlink(export_file.name)

    def test_list_profiles(self):
        """Test listing all profiles"""
        # Create additional profiles
        cache1 = LearningCache(cache_path=self.temp_file.name, profile_name="profile1")
        cache1.store_heuristic("test1", 1)  # Force save

        cache2 = LearningCache(cache_path=self.temp_file.name, profile_name="profile2")
        cache2.store_heuristic("test2", 2)  # Force save

        # Reload cache to get fresh data
        self.cache = LearningCache(cache_path=self.temp_file.name, profile_name="test_user")

        # List profiles
        profiles = self.cache.list_profiles()

        self.assertIn("test_user", profiles)
        self.assertIn("profile1", profiles)
        self.assertIn("profile2", profiles)
        self.assertGreaterEqual(len(profiles), 3)

    def test_switch_profile(self):
        """Test switching between profiles"""
        # Store data in current profile
        self.cache.store_heuristic("profile1_data", 111)

        # Switch to new profile
        self.cache.switch_profile("profile2")

        # Data from profile1 should not be accessible
        value = self.cache.get_heuristic("profile1_data", default=None)
        self.assertIsNone(value)

        # Store data in profile2
        self.cache.store_heuristic("profile2_data", 222)

        # Switch back to profile1
        self.cache.switch_profile("test_user")

        # Profile1 data should be accessible again
        value = self.cache.get_heuristic("profile1_data")
        self.assertEqual(value, 111)

        # Profile2 data should not be accessible
        value = self.cache.get_heuristic("profile2_data", default=None)
        self.assertIsNone(value)

    def test_get_cache_summary(self):
        """Test getting cache summary"""
        # Store some data
        self.cache.store_heuristic("h1", 1)
        self.cache.store_heuristic("h2", 2)
        self.cache.store_preference("p1", "v1")
        self.cache.increment_action_count(10)

        summary = self.cache.get_cache_summary()

        self.assertEqual(summary["profile_name"], "test_user")
        self.assertEqual(summary["heuristics_count"], 2)
        self.assertEqual(summary["preferences_count"], 1)
        self.assertIn("statistics", summary)
        self.assertEqual(summary["statistics"]["total_actions"], 10)

    def test_learning_updates_tracked(self):
        """Test that learning updates are tracked in statistics"""
        initial_stats = self.cache.get_statistics()
        initial_updates = initial_stats.get("learning_updates", 0)

        # Store multiple heuristics
        self.cache.store_heuristic("h1", 1)
        self.cache.store_heuristic("h2", 2)
        self.cache.store_heuristic("h3", 3)

        new_stats = self.cache.get_statistics()
        self.assertEqual(new_stats["learning_updates"], initial_updates + 3)

    def test_persistence(self):
        """Test that cache is persisted to disk"""
        # Store data
        self.cache.store_heuristic("persist_test", 555)
        self.cache.store_preference("persist_pref", "persist_value")

        # Create new cache instance with same file
        new_cache = LearningCache(cache_path=self.temp_file.name, profile_name="test_user")

        # Data should be loaded
        heuristic_value = new_cache.get_heuristic("persist_test")
        preference_value = new_cache.get_preference("persist_pref")

        self.assertEqual(heuristic_value, 555)
        self.assertEqual(preference_value, "persist_value")

    def test_update_profile(self):
        """Test updating profile with custom data"""
        custom_data = {"custom_field": "custom_value", "another_field": 123}

        self.cache.update_profile(custom_data)

        profile = self.cache.get_profile()
        self.assertEqual(profile["custom_field"], "custom_value")
        self.assertEqual(profile["another_field"], 123)


if __name__ == "__main__":
    unittest.main()
