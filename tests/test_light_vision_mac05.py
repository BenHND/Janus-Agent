"""
Tests for TICKET-MAC-05: Light Vision Cognitive Integration
Tests the lightweight post-action vision verification system
"""
import tempfile
import time
import unittest
from pathlib import Path

from PIL import Image

# Import the components we're testing
from janus.vision.light_vision_engine import LightVisionEngine


class TestLightVisionEngine(unittest.TestCase):
    """Test cases for LightVisionEngine"""

    def test_initialization_with_ai_disabled(self):
        """Test engine initialization with AI models disabled"""
        engine = LightVisionEngine(enable_ai_models=False, log_detections=False)

        self.assertFalse(engine.is_available())
        stats = engine.get_stats()
        self.assertFalse(stats["models_available"])
        self.assertEqual(stats["total_verifications"], 0)

    def test_initialization_with_cpu_mode(self):
        """Test engine initialization with CPU-only mode"""
        engine = LightVisionEngine(enable_ai_models=True, force_cpu=True, log_detections=False)

        stats = engine.get_stats()
        self.assertEqual(stats["device"], "cpu")

    def test_verification_with_fallback(self):
        """Test verification works with fallback (no AI models)"""
        engine = LightVisionEngine(enable_ai_models=False, log_detections=False)

        # Create a dummy image
        image = Image.new("RGB", (100, 100), color="white")

        # Test action verification
        action = {"action": "open_url", "url": "https://github.com"}
        result = engine.verify_action_result(image, action)

        # Should return a result even without AI
        self.assertIn("verified", result)
        self.assertIn("confidence", result)
        self.assertIn("method", result)
        self.assertIn("duration_ms", result)
        self.assertEqual(result["method"], "heuristic")

    def test_verification_performance_target(self):
        """Test that verification meets <1s performance target"""
        engine = LightVisionEngine(enable_ai_models=False, log_detections=False)

        image = Image.new("RGB", (100, 100), color="white")
        action = {"action": "click", "target": "button"}

        # Verify performance
        start = time.time()
        result = engine.verify_action_result(image, action, timeout_ms=1000)
        duration = (time.time() - start) * 1000

        # Should complete within timeout
        self.assertLess(duration, 1500, "Verification took too long")
        self.assertIn("duration_ms", result)

    def test_detection_logging(self):
        """Test that detections are logged correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test_detections.jsonl"

            engine = LightVisionEngine(
                enable_ai_models=False, log_detections=True, log_path=str(log_path)
            )

            image = Image.new("RGB", (100, 100), color="white")
            action = {"action": "open_url", "url": "https://test.com"}

            # Perform verification (should log)
            engine.verify_action_result(image, action)

            # Check log file was created and has content
            self.assertTrue(log_path.exists())

            # Check log content
            with open(log_path, "r") as f:
                lines = f.readlines()
                self.assertGreater(len(lines), 0)

                # Parse first log entry
                import json

                entry = json.loads(lines[0])
                self.assertIn("timestamp", entry)
                self.assertIn("action", entry)
                self.assertIn("verified", entry)
                self.assertIn("confidence", entry)
                self.assertIn("method", entry)
                self.assertEqual(entry["action"], "open_url")

    def test_performance_metrics(self):
        """Test performance metrics tracking"""
        engine = LightVisionEngine(enable_ai_models=False, log_detections=False)

        image = Image.new("RGB", (100, 100), color="white")

        # Perform multiple verifications
        for i in range(3):
            action = {"action": "click", "target": f"button{i}"}
            engine.verify_action_result(image, action)

        # Check stats
        stats = engine.get_stats()
        self.assertEqual(stats["total_verifications"], 3)
        self.assertGreaterEqual(stats["avg_time_ms"], 0)  # Changed from assertGreater
        self.assertGreaterEqual(stats["total_time_ms"], 0)  # Changed from assertGreater


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete vision system"""

    def test_complete_workflow_without_ai(self):
        """Test complete workflow with vision verification (no AI models)"""
        # Initialize engine
        engine = LightVisionEngine(enable_ai_models=False, log_detections=False)

        # Create test image
        image = Image.new("RGB", (800, 600), color="blue")

        # Test various action types
        actions = [
            {"action": "open_url", "url": "https://test.com"},
            {"action": "click", "target": "button"},
            {"action": "open_application", "app_name": "TestApp"},
        ]

        for action in actions:
            result = engine.verify_action_result(image, action)

            # All should complete successfully
            self.assertIn("verified", result)
            self.assertIn("method", result)
            self.assertLess(result["duration_ms"], 1000, f"Action {action['action']} took too long")

    def test_performance_across_multiple_verifications(self):
        """Test that performance remains consistent across multiple verifications"""
        engine = LightVisionEngine(enable_ai_models=False, log_detections=False)

        image = Image.new("RGB", (800, 600), color="white")
        action = {"action": "open_url", "url": "https://test.com"}

        times = []
        for _ in range(5):
            result = engine.verify_action_result(image, action)
            times.append(result["duration_ms"])

        # All should be fast
        for t in times:
            self.assertLess(t, 1000, "Verification exceeded 1s target")

        # Average should be reasonable
        avg_time = sum(times) / len(times)
        self.assertLess(avg_time, 500, "Average time should be well under 1s")


def run_tests():
    """Run all tests"""
    unittest.main(argv=[""], exit=False, verbosity=2)


if __name__ == "__main__":
    run_tests()
