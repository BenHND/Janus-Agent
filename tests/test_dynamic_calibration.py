"""
Tests for Phase 15.4 - Dynamic Calibration
Simulates noise variations and threshold adaptation
"""
import shutil
import tempfile
import unittest

from janus.io.stt.calibration_manager import CalibrationManager, CalibrationProfile, NoiseStatistics


class TestDynamicCalibration(unittest.TestCase):
    """Test cases for dynamic calibration (Phase 15.4)"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = CalibrationManager(profile_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_noise_statistics_initialization(self):
        """Test NoiseStatistics initialization"""
        stats = NoiseStatistics(window_size=100)

        self.assertEqual(len(stats.amplitude_history), 0)
        self.assertEqual(stats.mean, 0.0)
        self.assertEqual(stats.variance, 0.0)

    def test_noise_statistics_add_sample(self):
        """Test adding samples to noise statistics"""
        stats = NoiseStatistics(window_size=10)

        # Add samples
        for i in range(5):
            stats.add_sample(float(i * 10))

        self.assertEqual(len(stats.amplitude_history), 5)
        self.assertGreater(stats.mean, 0)

    def test_noise_statistics_calculation(self):
        """Test statistical calculations"""
        stats = NoiseStatistics(window_size=100)

        # Add known values
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for v in values:
            stats.add_sample(v)

        # Mean should be 30.0
        self.assertAlmostEqual(stats.mean, 30.0, places=1)

        # Should have variance
        self.assertGreater(stats.variance, 0)
        self.assertGreater(stats.std_dev, 0)

    def test_noise_statistics_rolling_window(self):
        """Test that statistics use rolling window"""
        stats = NoiseStatistics(window_size=5)

        # Add more samples than window size
        for i in range(10):
            stats.add_sample(float(i))

        # Should only keep last 5
        self.assertEqual(len(stats.amplitude_history), 5)

        # Mean should be based on last 5 samples (5,6,7,8,9)
        self.assertAlmostEqual(stats.mean, 7.0, places=1)

    def test_has_significant_deviation_false(self):
        """Test deviation detection when noise is stable"""
        stats = NoiseStatistics(window_size=100)

        # Add stable noise samples
        for i in range(50):
            stats.add_sample(100.0 + (i % 5))  # Small variation around 100

        # Should not detect significant deviation
        has_deviation = stats.has_significant_deviation(threshold_std_devs=2.0)
        self.assertFalse(has_deviation)

    def test_has_significant_deviation_true(self):
        """Test deviation detection when noise changes"""
        stats = NoiseStatistics(window_size=100)

        # Add stable noise samples
        for i in range(50):
            stats.add_sample(100.0)

        # Add sudden spike in recent samples
        for i in range(10):
            stats.add_sample(200.0)  # 2x increase

        # Should detect significant deviation
        has_deviation = stats.has_significant_deviation(threshold_std_devs=2.0)
        self.assertTrue(has_deviation)

    def test_update_noise_stats(self):
        """Test updating noise stats in CalibrationManager"""
        # Add noise samples
        for i in range(10):
            self.manager.update_noise_stats(100.0 + i)

        stats = self.manager.noise_stats.get_statistics()

        self.assertEqual(stats["sample_count"], 10)
        self.assertGreater(stats["mean"], 0)

    def test_consecutive_deviations_tracking(self):
        """Test tracking of consecutive deviations"""
        stats = NoiseStatistics(window_size=100)

        # Build baseline
        for i in range(50):
            stats.add_sample(100.0)

        self.manager.noise_stats = stats

        # Add deviating samples
        for i in range(10):
            self.manager.update_noise_stats(200.0)

        # Should track consecutive deviations
        self.assertGreater(self.manager.consecutive_deviations, 0)

    def test_should_recalibrate_false(self):
        """Test recalibration not triggered with stable noise"""
        # Add stable samples
        for i in range(20):
            self.manager.update_noise_stats(100.0)

        # Should not trigger recalibration
        self.assertFalse(self.manager.should_recalibrate())

    def test_should_recalibrate_true(self):
        """Test recalibration triggered after deviations"""
        # Manually trigger consecutive deviations
        self.manager.consecutive_deviations = 0
        self.manager.recalibration_threshold_deviations = 3

        # Directly set consecutive deviations to trigger
        self.manager.consecutive_deviations = 3

        # Should trigger recalibration
        self.assertTrue(self.manager.should_recalibrate())

    def test_auto_adjust_silence_quiet_environment(self):
        """Test silence threshold adjustment for quiet, stable environment"""
        # Create profile
        profile = self.manager._create_default_profile("test_user", "fr")

        # Simulate quiet, stable environment with low variance
        for i in range(30):
            self.manager.noise_stats.add_sample(50.0 + (i % 3))  # Low, stable noise

        # Auto-adjust
        adjusted = self.manager.auto_adjust_calibration(profile)

        # Should use shorter silence threshold for stable environment
        self.assertGreater(adjusted.silence_threshold, 50)
        self.assertLess(adjusted.silence_threshold, 150)
        self.assertGreater(adjusted.noise_mean, 0)

    def test_auto_adjust_silence_noisy_environment(self):
        """Test silence threshold adjustment for noisy, variable environment"""
        # Create profile
        profile = self.manager._create_default_profile("test_user", "fr")

        # Simulate noisy, variable environment with high variance
        import random

        random.seed(42)  # For reproducibility
        values = [random.uniform(50.0, 250.0) for _ in range(30)]
        for noise in values:
            self.manager.noise_stats.add_sample(noise)

        # Auto-adjust
        adjusted = self.manager.auto_adjust_calibration(profile)

        # Should use longer silence threshold for variable noise
        self.assertGreater(adjusted.silence_threshold, 100)

    def test_auto_adjust_ambient_noise_increase(self):
        """Test ambient noise level adjustment when noise increases"""
        # Create profile with baseline noise
        profile = self.manager._create_default_profile("test_user", "fr")
        profile.ambient_noise_level = 100.0

        # Simulate significantly increased noise (>1.5x baseline)
        for i in range(30):
            self.manager.noise_stats.add_sample(170.0)  # 1.7x baseline

        # Auto-adjust
        adjusted = self.manager.auto_adjust_calibration(profile)

        # Ambient noise should be updated to new level
        self.assertGreater(adjusted.ambient_noise_level, 100.0)
        self.assertGreater(adjusted.silence_threshold, 0)

    def test_auto_adjust_ambient_noise_decrease(self):
        """Test ambient noise level adjustment when noise decreases"""
        # Create profile with high baseline noise
        profile = self.manager._create_default_profile("test_user", "fr")
        profile.ambient_noise_level = 200.0

        # Simulate decreased noise (<0.7x baseline)
        for i in range(30):
            self.manager.noise_stats.add_sample(130.0)  # 0.65x baseline

        # Auto-adjust
        adjusted = self.manager.auto_adjust_calibration(profile)

        # Ambient noise level should be updated
        self.assertLess(adjusted.ambient_noise_level, 200.0)
        # Silence threshold should be reasonable
        self.assertGreater(adjusted.silence_threshold, 50)

    def test_auto_adjust_recalibration_tracking(self):
        """Test that recalibration is tracked"""
        profile = self.manager._create_default_profile("test_user", "fr")
        initial_count = profile.recalibration_count

        # Add samples
        for i in range(30):
            self.manager.noise_stats.add_sample(100.0)

        # Auto-adjust
        adjusted = self.manager.auto_adjust_calibration(profile)

        # Should increment recalibration count
        self.assertEqual(adjusted.recalibration_count, initial_count + 1)
        self.assertGreater(adjusted.last_recalibration, 0)

    def test_get_calibration_parameters_api(self):
        """Test API exposure of calibration parameters"""
        # Create and save profile
        profile = self.manager._create_default_profile("test_user", "fr")
        self.manager.save_profile(profile)

        # Add noise samples
        for i in range(20):
            self.manager.noise_stats.add_sample(100.0 + i)

        # Get parameters
        params = self.manager.get_calibration_parameters(profile)

        # Verify all expected fields (removed deprecated VAD fields)
        self.assertIn("user_id", params)
        self.assertIn("silence_threshold", params)
        self.assertIn("ambient_noise_level", params)
        self.assertIn("language", params)
        self.assertIn("current_noise_mean", params)
        self.assertIn("current_noise_variance", params)
        self.assertIn("current_noise_std_dev", params)
        self.assertIn("should_recalibrate", params)

        # Verify values
        self.assertEqual(params["user_id"], "test_user")
        self.assertEqual(params["language"], "fr")
        self.assertGreater(params["current_noise_mean"], 0)

    def test_profile_persistence_with_new_fields(self):
        """Test that dynamic calibration fields (noise_mean, noise_variance, 
        last_recalibration, recalibration_count) are saved and loaded correctly"""
        # Create profile
        profile = CalibrationProfile(
            user_id="test_user",
            calibration_phrases=["test"],
            silence_threshold=125,
            ambient_noise_level=80.0,
            sample_count=5,
            language="fr",
            noise_mean=85.0,
            noise_variance=10.0,
            last_recalibration=12345.0,
            recalibration_count=3,
        )

        # Save
        self.manager.save_profile(profile)

        # Load
        loaded = self.manager.load_profile("test_user")

        # Verify fields
        self.assertEqual(loaded.noise_mean, 85.0)
        self.assertEqual(loaded.noise_variance, 10.0)
        self.assertEqual(loaded.last_recalibration, 12345.0)
        self.assertEqual(loaded.recalibration_count, 3)

    def test_legacy_profile_compatibility(self):
        """Test backward compatibility with legacy profiles (with deprecated fields)"""
        # Create legacy profile dict (with deprecated fields that should be ignored)
        legacy_data = {
            "user_id": "legacy_user",
            "calibration_phrases": ["test"],
            "voice_activation_threshold": 100.0,  # Deprecated - will be removed
            "vad_aggressiveness": 2,  # Deprecated - will be removed
            "silence_threshold": 125,
            "ambient_noise_level": 80.0,
            "sample_count": 5,
            "language": "fr",
        }

        # Should load successfully with deprecated fields removed
        profile = CalibrationProfile.from_dict(legacy_data)
        
        # Verify it loaded
        self.assertEqual(profile.user_id, "legacy_user")
        self.assertEqual(profile.silence_threshold, 125)
        
        # Verify deprecated fields are not present
        self.assertFalse(hasattr(profile, "voice_activation_threshold"))
        self.assertFalse(hasattr(profile, "vad_aggressiveness"))
        
        # Verify default Phase 15.4 fields are added
        self.assertEqual(profile.noise_mean, 0.0)
        self.assertEqual(profile.noise_variance, 0.0)
        self.assertEqual(profile.last_recalibration, 0.0)
        self.assertEqual(profile.recalibration_count, 0)


if __name__ == "__main__":
    unittest.main()
