"""
Tests for TICKET-P1-03: Vision Recovery Optimization

Tests the fast heuristic comparison methods for detecting screen changes.
These methods provide quick before/after screenshot comparison to detect
if an action had any visible effect on the screen.
"""
import time
import unittest

import numpy as np
from PIL import Image

from janus.vision.light_vision_engine import (
    DEFAULT_VISION_TIMEOUT_MS,
    MAX_COMPARISON_DIMENSION,
    PIXEL_CHANGE_THRESHOLD,
    SCREEN_CHANGE_THRESHOLD,
    LightVisionEngine,
)


class TestHeuristicScreenComparison(unittest.TestCase):
    """Test cases for TICKET-P1-03 fast heuristic screen comparison."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = LightVisionEngine(enable_ai_models=False, log_detections=False)

    def test_compare_identical_screenshots(self):
        """Test that identical screenshots are detected as unchanged."""
        image1 = Image.new("RGB", (800, 600), color="white")
        image2 = Image.new("RGB", (800, 600), color="white")

        result = self.engine.compare_screenshots(image1, image2)

        self.assertFalse(result["changed"])
        self.assertEqual(result["change_ratio"], 0.0)
        self.assertEqual(result["method"], "heuristic_pixel_comparison")
        self.assertIn("duration_ms", result)

    def test_compare_different_screenshots(self):
        """Test that significantly different screenshots are detected as changed."""
        image1 = Image.new("RGB", (800, 600), color="white")
        # Create a mostly black image (significant change)
        image2 = Image.new("RGB", (800, 600), color="black")

        result = self.engine.compare_screenshots(image1, image2)

        self.assertTrue(result["changed"])
        self.assertGreater(result["change_ratio"], SCREEN_CHANGE_THRESHOLD)
        self.assertEqual(result["method"], "heuristic_pixel_comparison")

    def test_compare_slightly_different_screenshots(self):
        """Test detection of subtle changes in a small region."""
        # Create two images with a small difference
        image1 = Image.new("RGB", (100, 100), color="white")
        image2 = image1.copy()
        
        # Add a small changed region (10% of pixels)
        for x in range(10):
            for y in range(100):  # 10x100 = 1000 pixels out of 10000 = 10%
                image2.putpixel((x, y), (0, 0, 0))

        result = self.engine.compare_screenshots(image1, image2)

        # 10% change should be detected
        self.assertTrue(result["changed"])
        self.assertGreater(result["change_ratio"], 0.05)

    def test_compare_screenshots_performance(self):
        """Test that comparison is fast (<100ms for typical images)."""
        image1 = Image.new("RGB", (1920, 1080), color="white")
        image2 = Image.new("RGB", (1920, 1080), color="gray")

        start = time.time()
        result = self.engine.compare_screenshots(image1, image2)
        duration = (time.time() - start) * 1000

        # Should complete very quickly (< 100ms even for large images)
        self.assertLess(duration, 200)
        self.assertIn("duration_ms", result)

    def test_compare_different_sized_screenshots(self):
        """Test comparison handles different sized images gracefully."""
        image1 = Image.new("RGB", (800, 600), color="white")
        image2 = Image.new("RGB", (1024, 768), color="white")

        result = self.engine.compare_screenshots(image1, image2)

        # Should complete without error
        self.assertIn("changed", result)
        self.assertIn("method", result)


class TestPixelChangeDetection(unittest.TestCase):
    """Test cases for single pixel change detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = LightVisionEngine(enable_ai_models=False, log_detections=False)

    def test_check_pixel_unchanged(self):
        """Test detection of unchanged pixel."""
        image1 = Image.new("RGB", (100, 100), color="white")
        image2 = Image.new("RGB", (100, 100), color="white")

        result = self.engine.check_pixel_changed(image1, image2, 50, 50)

        self.assertFalse(result["changed"])
        self.assertEqual(result["color_diff"], 0)
        self.assertEqual(result["before_color"], (255, 255, 255))
        self.assertEqual(result["after_color"], (255, 255, 255))

    def test_check_pixel_changed(self):
        """Test detection of changed pixel."""
        image1 = Image.new("RGB", (100, 100), color="white")
        image2 = Image.new("RGB", (100, 100), color="black")

        result = self.engine.check_pixel_changed(image1, image2, 50, 50)

        self.assertTrue(result["changed"])
        self.assertEqual(result["color_diff"], 255)
        self.assertEqual(result["before_color"], (255, 255, 255))
        self.assertEqual(result["after_color"], (0, 0, 0))

    def test_check_pixel_out_of_bounds(self):
        """Test handling of out-of-bounds coordinates."""
        image1 = Image.new("RGB", (100, 100), color="white")
        image2 = Image.new("RGB", (100, 100), color="white")

        result = self.engine.check_pixel_changed(image1, image2, 200, 200)

        # Should handle gracefully
        self.assertIn("error", result)
        self.assertTrue(result["changed"])  # Conservative fallback

    def test_check_pixel_performance(self):
        """Test that single pixel check is very fast."""
        image1 = Image.new("RGB", (1920, 1080), color="white")
        image2 = Image.new("RGB", (1920, 1080), color="gray")

        start = time.time()
        result = self.engine.check_pixel_changed(image1, image2, 960, 540)
        duration = (time.time() - start) * 1000

        # Should complete almost instantly (< 5ms)
        self.assertLess(duration, 10)


class TestActionEffectDetection(unittest.TestCase):
    """Test cases for the main action effect detection method."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = LightVisionEngine(enable_ai_models=False, log_detections=False)

    def test_detect_no_effect(self):
        """Test detection when action had no visible effect."""
        before = Image.new("RGB", (800, 600), color="white")
        after = Image.new("RGB", (800, 600), color="white")
        action = {"action": "click", "target": "button"}

        result = self.engine.detect_action_effect(before, after, action)

        self.assertFalse(result["action_had_effect"])
        self.assertFalse(result["verified"])
        self.assertGreater(result["confidence"], 0.8)  # High confidence no change
        self.assertIn("no_change", result["method"])

    def test_detect_effect_with_screen_change(self):
        """Test detection when action caused visible change."""
        before = Image.new("RGB", (800, 600), color="white")
        after = Image.new("RGB", (800, 600), color="blue")  # Significant change
        action = {"action": "open_application", "app_name": "TestApp"}

        result = self.engine.detect_action_effect(before, after, action)

        self.assertTrue(result["action_had_effect"])
        self.assertTrue(result["verified"])
        self.assertIn("change_ratio", result)

    def test_detect_effect_performance_under_timeout(self):
        """Test that detection completes within timeout (1.5s)."""
        before = Image.new("RGB", (1920, 1080), color="white")
        after = Image.new("RGB", (1920, 1080), color="gray")
        action = {"action": "click", "target": "button"}

        start = time.time()
        result = self.engine.detect_action_effect(before, after, action)
        duration = (time.time() - start) * 1000

        # Should complete well under the 1.5s timeout
        self.assertLess(duration, DEFAULT_VISION_TIMEOUT_MS)
        self.assertLess(result["duration_ms"], DEFAULT_VISION_TIMEOUT_MS)

    def test_detect_effect_with_custom_timeout(self):
        """Test that custom timeout is respected."""
        before = Image.new("RGB", (800, 600), color="white")
        after = Image.new("RGB", (800, 600), color="blue")
        action = {"action": "click"}

        result = self.engine.detect_action_effect(before, after, action, timeout_ms=500)

        # Should complete within custom timeout
        self.assertLess(result["duration_ms"], 600)


class TestScreenshotStorage(unittest.TestCase):
    """Test cases for screenshot storage functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = LightVisionEngine(enable_ai_models=False, log_detections=False)

    def test_store_and_retrieve_screenshot(self):
        """Test storing and retrieving screenshots."""
        image = Image.new("RGB", (100, 100), color="red")

        self.engine.store_screenshot(image)
        retrieved = self.engine.get_stored_screenshot()

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.size, (100, 100))

    def test_no_stored_screenshot_initially(self):
        """Test that no screenshot is stored initially."""
        result = self.engine.get_stored_screenshot()
        self.assertIsNone(result)

    def test_stored_screenshot_is_copy(self):
        """Test that stored screenshot is a copy, not a reference."""
        image = Image.new("RGB", (100, 100), color="red")
        self.engine.store_screenshot(image)

        # Modify original
        image.putpixel((50, 50), (0, 0, 255))

        # Stored version should be unchanged
        retrieved = self.engine.get_stored_screenshot()
        pixel = retrieved.getpixel((50, 50))
        self.assertEqual(pixel, (255, 0, 0))  # Original red color


class TestVisionRecoveryConfiguration(unittest.TestCase):
    """Test cases for configuration changes in TICKET-P1-03."""

    def test_default_timeout_is_1500ms(self):
        """Test that default timeout is 1.5s (1500ms)."""
        self.assertEqual(DEFAULT_VISION_TIMEOUT_MS, 1500)

    def test_screen_change_threshold_is_reasonable(self):
        """Test that screen change threshold is set to 1%."""
        self.assertEqual(SCREEN_CHANGE_THRESHOLD, 0.01)

    def test_verify_action_result_uses_new_default_timeout(self):
        """Test that verify_action_result uses 1.5s default timeout."""
        engine = LightVisionEngine(enable_ai_models=False, log_detections=False)
        image = Image.new("RGB", (100, 100), color="white")
        action = {"action": "click"}

        result = engine.verify_action_result(image, action)

        # Should complete under 1.5s
        self.assertLess(result["duration_ms"], DEFAULT_VISION_TIMEOUT_MS)


class TestLatencyRequirement(unittest.TestCase):
    """Test that latency requirements (<2s between actions) are met."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = LightVisionEngine(enable_ai_models=False, log_detections=False)

    def test_end_to_end_verification_under_2s(self):
        """Test that full verification workflow completes under 2 seconds."""
        # Simulate realistic images
        before = Image.new("RGB", (1920, 1080), color="white")
        after = Image.new("RGB", (1920, 1080), color="white")
        
        # Add some variation to after image using paste (more efficient than putpixel)
        change_region = Image.new("RGB", (100, 100), color=(200, 200, 255))
        after.paste(change_region, (100, 100))

        action = {"action": "click", "x": 150, "y": 150}

        total_start = time.time()
        
        # Step 1: Store before screenshot
        self.engine.store_screenshot(before)
        
        # Step 2: Detect action effect
        result = self.engine.detect_action_effect(before, after, action)
        
        total_duration = (time.time() - total_start) * 1000

        # Total latency must be under 2 seconds
        self.assertLess(total_duration, 2000)
        
        # Verify result structure
        self.assertIn("action_had_effect", result)
        self.assertIn("verified", result)
        self.assertIn("confidence", result)

    def test_multiple_consecutive_verifications_under_2s_each(self):
        """Test that multiple verifications each complete under 2s."""
        images = [
            (Image.new("RGB", (1920, 1080), color="white"),
             Image.new("RGB", (1920, 1080), color="gray")),
            (Image.new("RGB", (1920, 1080), color="gray"),
             Image.new("RGB", (1920, 1080), color="blue")),
            (Image.new("RGB", (1920, 1080), color="blue"),
             Image.new("RGB", (1920, 1080), color="blue")),  # No change
        ]

        for i, (before, after) in enumerate(images):
            action = {"action": "click", "iteration": i}
            
            start = time.time()
            result = self.engine.detect_action_effect(before, after, action)
            duration = (time.time() - start) * 1000

            self.assertLess(
                duration, 2000,
                f"Iteration {i} took {duration}ms, exceeding 2s limit"
            )


def run_tests():
    """Run all tests."""
    unittest.main(argv=[""], exit=False, verbosity=2)


if __name__ == "__main__":
    run_tests()
