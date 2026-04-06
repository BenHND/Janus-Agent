"""
Unit tests for Vision Cognitive Engine
Part of PHASE-22: Vision Cognitive & Perception IA
"""
import unittest
from unittest.mock import MagicMock, Mock, patch

import numpy as np
from PIL import Image

from janus.vision.vision_cognitive_engine import VisionCognitiveEngine


class TestVisionCognitiveEngine(unittest.TestCase):
    """Test cases for VisionCognitiveEngine"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a simple test image
        self.test_image = Image.new("RGB", (100, 100), color="white")

    def test_initialization(self):
        """Test engine initialization"""
        engine = VisionCognitiveEngine(model_type="blip2", device="cpu")

        self.assertIsNotNone(engine)
        self.assertEqual(engine.model_type, "blip2")
        self.assertEqual(engine.device, "cpu")
        self.assertTrue(engine.enable_cache)

    def test_initialization_without_models(self):
        """Test initialization without AI models (fallback mode)"""
        # This should work even without transformers installed
        engine = VisionCognitiveEngine(model_type="blip2", device="cpu")

        # Engine should initialize even if models aren't available
        self.assertIsNotNone(engine)

    def test_device_detection_auto(self):
        """Test automatic device detection"""
        engine = VisionCognitiveEngine(device="auto")

        # Device should be set to cpu, mps, or cuda
        self.assertIn(engine.device, ["cpu", "mps", "cuda"])

    def test_describe_fallback(self):
        """Test describe with fallback when models unavailable"""
        engine = VisionCognitiveEngine()

        # Mock models as unavailable
        engine.caption_model = None
        engine.processor = None

        result = engine.describe(self.test_image)

        # Should return fallback description
        self.assertIn("description", result)
        self.assertIn("confidence", result)
        self.assertIn("duration_ms", result)
        self.assertEqual(result["method"], "fallback")
        self.assertLess(result["confidence"], 0.5)

    def test_describe_with_cache(self):
        """Test caching mechanism"""
        engine = VisionCognitiveEngine(enable_cache=True)
        engine.caption_model = None  # Force fallback

        # First call
        result1 = engine.describe(self.test_image)
        self.assertFalse(result1.get("cached", False))

        # Second call with same image should be cached
        result2 = engine.describe(self.test_image)
        self.assertTrue(result2.get("cached", False))
        self.assertEqual(result2["duration_ms"], 0)

    def test_find_element_without_clip(self):
        """Test find_element without CLIP model"""
        engine = VisionCognitiveEngine()
        engine.clip_model = None

        result = engine.find_element(self.test_image, "button", threshold=0.5)

        # Should return None when CLIP unavailable
        self.assertIsNone(result)

    def test_answer_question_fallback(self):
        """Test answer_question with fallback"""
        engine = VisionCognitiveEngine()
        engine.caption_model = None

        result = engine.answer_question(self.test_image, "What is this?")

        self.assertIn("answer", result)
        self.assertIn("confidence", result)
        self.assertEqual(result["method"], "fallback")
        self.assertEqual(result["confidence"], 0.0)

    def test_detect_errors_without_models(self):
        """Test error detection without AI models"""
        engine = VisionCognitiveEngine()
        engine.clip_model = None

        result = engine.detect_errors(self.test_image)

        self.assertIn("has_error", result)
        self.assertIn("error_type", result)
        self.assertIn("confidence", result)
        self.assertFalse(result["has_error"])

    def test_verify_action_result_error_detection(self):
        """Test action verification with error detection"""
        engine = VisionCognitiveEngine()
        engine.clip_model = None

        # Mock error detection to return an error
        with patch.object(engine, "detect_errors") as mock_detect:
            mock_detect.return_value = {"has_error": True, "error_type": "404", "confidence": 0.9}

            result = engine.verify_action_result(
                self.test_image, "open_url", {"url": "https://example.com"}
            )

            self.assertFalse(result["verified"])
            self.assertIn("404", result["reason"])

    def test_verify_action_result_open_url(self):
        """Test action verification for open_url intent"""
        engine = VisionCognitiveEngine()
        engine.caption_model = None

        # Mock no errors
        with patch.object(engine, "detect_errors") as mock_detect:
            mock_detect.return_value = {"has_error": False}

            result = engine.verify_action_result(
                self.test_image, "open_url", {"url": "https://example.com"}
            )

            self.assertIn("verified", result)
            self.assertIn("confidence", result)
            self.assertIn("reason", result)

    def test_cache_management(self):
        """Test cache size management"""
        engine = VisionCognitiveEngine(enable_cache=True, cache_size=2)
        engine.caption_model = None  # Use fallback

        # Create 3 different images
        img1 = Image.new("RGB", (100, 100), color="red")
        img2 = Image.new("RGB", (100, 100), color="green")
        img3 = Image.new("RGB", (100, 100), color="blue")

        # Describe all three
        engine.describe(img1)
        engine.describe(img2)
        engine.describe(img3)

        # Cache should only keep 2 most recent
        stats = engine.get_cache_stats()
        self.assertEqual(stats["size"], 2)
        self.assertEqual(stats["max_size"], 2)

    def test_clear_cache(self):
        """Test cache clearing"""
        engine = VisionCognitiveEngine(enable_cache=True)
        engine.caption_model = None

        # Add to cache
        engine.describe(self.test_image)
        self.assertGreater(engine.get_cache_stats()["size"], 0)

        # Clear cache
        engine.clear_cache()
        self.assertEqual(engine.get_cache_stats()["size"], 0)

    def test_is_available(self):
        """Test availability check"""
        engine = VisionCognitiveEngine()

        # is_available should return bool
        available = engine.is_available()
        self.assertIsInstance(available, bool)

    def test_get_info(self):
        """Test engine info"""
        engine = VisionCognitiveEngine(model_type="blip2", device="cpu")

        info = engine.get_info()

        self.assertIn("model_type", info)
        self.assertIn("device", info)
        self.assertIn("blip2_available", info)
        self.assertIn("clip_available", info)
        self.assertIn("cache_enabled", info)
        self.assertIn("cache_stats", info)

        self.assertEqual(info["model_type"], "blip2")
        self.assertEqual(info["device"], "cpu")

    def test_image_hash_consistency(self):
        """Test that image hash is consistent"""
        engine = VisionCognitiveEngine()

        hash1 = engine._get_image_hash(self.test_image)
        hash2 = engine._get_image_hash(self.test_image)

        # Same image should produce same hash
        self.assertEqual(hash1, hash2)

    def test_cache_result(self):
        """Test cache result storage"""
        engine = VisionCognitiveEngine(enable_cache=True)

        result = {"description": "test", "confidence": 0.9}
        key = "test_key"

        engine._cache_result(key, result)

        self.assertIn(key, engine._caption_cache)
        self.assertEqual(engine._caption_cache[key]["description"], "test")


class TestVisionCognitiveEngineIntegration(unittest.TestCase):
    """Integration tests for VisionCognitiveEngine with mocked models"""

    @patch("janus.vision.vision_cognitive_engine.Blip2Processor")
    @patch("janus.vision.vision_cognitive_engine.Blip2ForConditionalGeneration")
    def test_describe_with_mocked_blip2(self, mock_model_class, mock_processor_class):
        """Test describe with mocked BLIP-2 model"""
        # Create mock model and processor
        mock_processor = MagicMock()
        mock_model = MagicMock()

        mock_processor_class.from_pretrained.return_value = mock_processor
        mock_model_class.from_pretrained.return_value = mock_model

        # Mock generation
        mock_model.generate.return_value = [[101, 102, 103]]  # Mock token IDs
        mock_processor.batch_decode.return_value = ["A screenshot of a webpage"]
        mock_processor.return_value = {"input_ids": MagicMock()}

        # Initialize engine (will use mocked models)
        with patch("torch.backends.mps.is_available", return_value=False):
            with patch("torch.cuda.is_available", return_value=False):
                engine = VisionCognitiveEngine(model_type="blip2", device="cpu")

                # Set the mocked models
                engine.caption_model = mock_model
                engine.processor = mock_processor

                # Create test image
                test_image = Image.new("RGB", (100, 100), color="white")

                # Mock torch operations
                with patch("torch.no_grad"):
                    with patch.object(mock_processor, "__call__") as mock_call:
                        mock_call.return_value = {
                            "input_ids": MagicMock(),
                            "attention_mask": MagicMock(),
                        }

                        # Call describe
                        result = engine.describe(test_image)

                        # Verify result structure
                        self.assertIn("description", result)
                        self.assertEqual(result["method"], "blip2")


if __name__ == "__main__":
    unittest.main()
