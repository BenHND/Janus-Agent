"""
Unit tests for CalibrationManager
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from janus.io.stt.calibration_manager import CalibrationManager, CalibrationProfile


class TestCalibrationManager(unittest.TestCase):
    """Test cases for CalibrationManager"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = CalibrationManager(profile_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_profile_directory_creation(self):
        """Test that profile directory is created"""
        self.assertTrue(Path(self.temp_dir).exists())

    def test_get_calibration_phrases_french(self):
        """Test getting French calibration phrases"""
        phrases = self.manager.get_calibration_phrases("fr")

        self.assertEqual(len(phrases), 5)
        self.assertTrue(all(isinstance(p, str) for p in phrases))
        self.assertTrue(any("Ouvre" in p for p in phrases))

    def test_get_calibration_phrases_english(self):
        """Test getting English calibration phrases"""
        phrases = self.manager.get_calibration_phrases("en")

        self.assertEqual(len(phrases), 5)
        self.assertTrue(all(isinstance(p, str) for p in phrases))
        self.assertTrue(any("Open" in p for p in phrases))

    def test_start_calibration(self):
        """Test starting calibration"""
        phrases, instructions = self.manager.start_calibration("test_user", "fr")

        self.assertEqual(len(phrases), 5)
        self.assertIsInstance(instructions, str)
        self.assertIn("Calibration", instructions)

    def test_create_default_profile(self):
        """Test creating default profile"""
        profile = self.manager._create_default_profile("test_user", "fr")

        self.assertEqual(profile.user_id, "test_user")
        self.assertEqual(profile.language, "fr")
        self.assertEqual(profile.sample_count, 0)
        self.assertGreater(profile.silence_threshold, 0)
        self.assertGreater(profile.ambient_noise_level, 0)

    def test_calibrate_from_samples(self):
        """Test calibration from audio samples"""
        # Create dummy audio samples with varying energy levels
        samples = [
            (b"\x00\x00" * 1000, 100.0),
            (b"\x00\x00" * 1000, 200.0),
            (b"\x00\x00" * 1000, 150.0),
            (b"\x00\x00" * 1000, 180.0),
            (b"\x00\x00" * 1000, 160.0),
        ]

        profile = self.manager.calibrate_from_samples("test_user", samples, "fr")

        self.assertEqual(profile.user_id, "test_user")
        self.assertEqual(profile.sample_count, 5)
        self.assertGreater(profile.silence_threshold, 0)
        self.assertGreater(profile.ambient_noise_level, 0)

    def test_calibrate_with_quiet_environment(self):
        """Test calibration in quiet environment (low noise, high consistency)"""
        # Low ambient noise (50), consistent speech signal (500-530)
        # Low variance should result in shorter silence threshold
        samples = [
            (b"\x00\x00" * 1000, 50.0),  # Ambient/silence
            (b"\x00\x00" * 1000, 500.0),  # Speech
            (b"\x00\x00" * 1000, 520.0),  # Speech
            (b"\x00\x00" * 1000, 510.0),  # Speech
            (b"\x00\x00" * 1000, 530.0),  # Speech
        ]

        profile = self.manager.calibrate_from_samples("quiet_user", samples, "fr")

        # Should have reasonable silence threshold (~2s)
        self.assertGreater(profile.silence_threshold, 50)
        self.assertLess(profile.silence_threshold, 200)

    def test_calibrate_with_noisy_environment(self):
        """Test calibration in noisy environment (high variance)"""
        # High ambient noise with variable levels
        samples = [
            (b"\x00\x00" * 1000, 200.0),
            (b"\x00\x00" * 1000, 180.0),
            (b"\x00\x00" * 1000, 220.0),
            (b"\x00\x00" * 1000, 190.0),
            (b"\x00\x00" * 1000, 210.0),
        ]

        profile = self.manager.calibrate_from_samples("noisy_user", samples, "fr")

        # Should have reasonable ambient noise level
        self.assertGreater(profile.ambient_noise_level, 100)
        self.assertGreater(profile.silence_threshold, 50)

    def test_save_and_load_profile(self):
        """Test saving and loading profiles"""
        # Create a profile
        profile = CalibrationProfile(
            user_id="test_user",
            calibration_phrases=["phrase1", "phrase2"],
            silence_threshold=125,
            ambient_noise_level=100.0,
            sample_count=5,
            language="fr",
        )

        # Save it
        self.manager.save_profile(profile)

        # Load it back
        loaded_profile = self.manager.load_profile("test_user")

        self.assertIsNotNone(loaded_profile)
        self.assertEqual(loaded_profile.user_id, "test_user")
        self.assertEqual(loaded_profile.silence_threshold, 125)
        self.assertEqual(loaded_profile.language, "fr")

    def test_load_nonexistent_profile(self):
        """Test loading a profile that doesn't exist"""
        profile = self.manager.load_profile("nonexistent_user")
        self.assertIsNone(profile)

    def test_get_profile_creates_default(self):
        """Test that get_profile creates default if not exists"""
        profile = self.manager.get_profile("new_user")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.user_id, "new_user")
        self.assertEqual(profile.sample_count, 0)

    def test_list_profiles(self):
        """Test listing all profiles"""
        # Create several profiles
        for i in range(3):
            profile = self.manager._create_default_profile(f"user_{i}", "fr")
            self.manager.save_profile(profile)

        profiles = self.manager.list_profiles()

        self.assertEqual(len(profiles), 3)
        self.assertIn("user_0", profiles)
        self.assertIn("user_1", profiles)
        self.assertIn("user_2", profiles)

    def test_delete_profile(self):
        """Test deleting a profile"""
        # Create and save a profile
        profile = self.manager._create_default_profile("delete_me", "fr")
        self.manager.save_profile(profile)

        # Verify it exists
        self.assertIsNotNone(self.manager.load_profile("delete_me"))

        # Delete it
        result = self.manager.delete_profile("delete_me")
        self.assertTrue(result)

        # Verify it's gone
        self.assertIsNone(self.manager.load_profile("delete_me"))

    def test_delete_nonexistent_profile(self):
        """Test deleting a profile that doesn't exist"""
        result = self.manager.delete_profile("nonexistent")
        self.assertFalse(result)

    def test_generate_calibration_report(self):
        """Test generating calibration report"""
        profile = CalibrationProfile(
            user_id="report_user",
            calibration_phrases=["phrase1", "phrase2", "phrase3", "phrase4", "phrase5"],
            voice_activation_threshold=500.0,
            vad_aggressiveness=2,
            silence_threshold=20,
            ambient_noise_level=100.0,
            sample_count=5,
            language="fr",
        )

        report = self.manager.generate_calibration_report(profile)

        self.assertIsInstance(report, str)
        self.assertIn("report_user", report)
        self.assertIn("silence", report.lower())
        self.assertIn("phrase1", report)

    def test_profile_serialization(self):
        """Test profile to_dict and from_dict"""
        profile = CalibrationProfile(
            user_id="serialize_user",
            calibration_phrases=["p1", "p2"],
            silence_threshold=125,
            ambient_noise_level=100.0,
            sample_count=2,
            language="fr",
        )

        # Convert to dict
        profile_dict = profile.to_dict()
        self.assertIsInstance(profile_dict, dict)

        # Convert back
        restored = CalibrationProfile.from_dict(profile_dict)
        self.assertEqual(restored.user_id, profile.user_id)
        self.assertEqual(restored.silence_threshold, profile.silence_threshold)
    
    def test_profile_backward_compatibility(self):
        """Test loading old profiles with deprecated fields"""
        # Create a profile dict with deprecated fields
        old_profile_dict = {
            "user_id": "legacy_user",
            "calibration_phrases": ["phrase1"],
            "voice_activation_threshold": 500.0,  # Deprecated
            "vad_aggressiveness": 2,  # Deprecated
            "silence_threshold": 125,
            "ambient_noise_level": 100.0,
            "sample_count": 1,
            "language": "fr",
        }
        
        # Should load without errors, ignoring deprecated fields
        profile = CalibrationProfile.from_dict(old_profile_dict)
        self.assertEqual(profile.user_id, "legacy_user")
        self.assertEqual(profile.silence_threshold, 125)
        # Deprecated fields should not exist
        self.assertFalse(hasattr(profile, "voice_activation_threshold"))
        self.assertFalse(hasattr(profile, "vad_aggressiveness"))


if __name__ == "__main__":
    unittest.main()
