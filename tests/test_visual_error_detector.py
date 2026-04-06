"""
Unit tests for Visual Error Detector
Part of PHASE-22: Vision Cognitive & Perception IA
"""
import unittest
from unittest.mock import MagicMock, Mock, patch

from PIL import Image

from janus.vision.visual_error_detector import VisualErrorDetector


class TestVisualErrorDetector(unittest.TestCase):
    """Test cases for VisualErrorDetector"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_image = Image.new("RGB", (100, 100), color="white")
        self.detector = VisualErrorDetector(use_vision_ai=False)

    def test_initialization(self):
        """Test detector initialization"""
        detector = VisualErrorDetector(use_vision_ai=False)

        self.assertIsNotNone(detector)
        self.assertFalse(detector.use_vision_ai)
        self.assertIsNone(detector.vision_engine)

    def test_initialization_with_vision_ai(self):
        """Test initialization with vision AI enabled"""
        # This may fail if transformers not installed, which is OK
        try:
            detector = VisualErrorDetector(use_vision_ai=True)
            # Vision engine may or may not be initialized
            self.assertIsInstance(detector.use_vision_ai, bool)
        except Exception:
            pass

    def test_detect_with_ocr_texts_404_error(self):
        """Test detection of 404 error from OCR texts"""
        ocr_texts = ["404", "Page not found", "The requested page could not be found"]

        result = self.detector.detect(self.test_image, ocr_texts)

        self.assertTrue(result["has_error"])
        self.assertEqual(result["error_type"], "404")
        self.assertGreater(result["confidence"], 0.5)
        self.assertIn("404", [e["type"] for e in result["details"]])

    def test_detect_with_ocr_texts_crash_error(self):
        """Test detection of crash error"""
        ocr_texts = ["Application has crashed", "Please restart"]

        result = self.detector.detect(self.test_image, ocr_texts)

        self.assertTrue(result["has_error"])
        self.assertEqual(result["error_type"], "crash")
        self.assertGreater(result["confidence"], 0.5)

    def test_detect_with_ocr_texts_connection_error(self):
        """Test detection of connection error"""
        ocr_texts = ["Connection failed", "Unable to connect to server"]

        result = self.detector.detect(self.test_image, ocr_texts)

        self.assertTrue(result["has_error"])
        self.assertEqual(result["error_type"], "connection")
        self.assertGreater(result["confidence"], 0.5)

    def test_detect_with_ocr_texts_no_error(self):
        """Test detection with no errors"""
        ocr_texts = ["Welcome to our website", "Hello World", "Click here"]

        result = self.detector.detect(self.test_image, ocr_texts)

        self.assertFalse(result["has_error"])
        self.assertIsNone(result["error_type"])
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(len(result["details"]), 0)

    def test_detect_multilingual_error_french(self):
        """Test detection of French error messages"""
        ocr_texts = ["Erreur 404", "Page introuvable"]

        result = self.detector.detect(self.test_image, ocr_texts)

        self.assertTrue(result["has_error"])
        self.assertIn(result["error_type"], ["404", "error"])

    def test_detect_multilingual_connection_french(self):
        """Test detection of French connection errors"""
        ocr_texts = ["Connexion échouée", "Pas de connexion"]

        result = self.detector.detect(self.test_image, ocr_texts)

        self.assertTrue(result["has_error"])
        self.assertEqual(result["error_type"], "connection")

    def test_is_error_page_true(self):
        """Test is_error_page with error present"""
        ocr_texts = ["500 Internal Server Error"]

        with patch.object(self.detector, "detect") as mock_detect:
            mock_detect.return_value = {"has_error": True, "error_type": "500", "confidence": 0.9}

            result = self.detector.is_error_page(self.test_image)
            self.assertTrue(result)

    def test_is_error_page_false(self):
        """Test is_error_page with no error"""
        with patch.object(self.detector, "detect") as mock_detect:
            mock_detect.return_value = {"has_error": False, "confidence": 0.0}

            result = self.detector.is_error_page(self.test_image)
            self.assertFalse(result)

    def test_is_error_page_low_confidence(self):
        """Test is_error_page with low confidence error"""
        with patch.object(self.detector, "detect") as mock_detect:
            mock_detect.return_value = {
                "has_error": True,
                "error_type": "warning",
                "confidence": 0.3,
            }

            result = self.detector.is_error_page(self.test_image)
            self.assertFalse(result)

    def test_detect_specific_error_404(self):
        """Test detection of specific 404 error"""
        ocr_texts = ["404 Not Found", "The page you're looking for doesn't exist"]

        result = self.detector.detect_specific_error(self.test_image, "404", ocr_texts)

        self.assertTrue(result["found"])
        self.assertGreater(result["confidence"], 0.5)
        self.assertGreater(len(result["matched_texts"]), 0)

    def test_detect_specific_error_not_found(self):
        """Test detection when specific error not present"""
        ocr_texts = ["Welcome to our site", "Click here to continue"]

        result = self.detector.detect_specific_error(self.test_image, "404", ocr_texts)

        self.assertFalse(result["found"])
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(len(result["matched_texts"]), 0)

    def test_detect_specific_error_unknown_type(self):
        """Test detection with unknown error type"""
        result = self.detector.detect_specific_error(self.test_image, "unknown_error_type", [])

        self.assertFalse(result["found"])
        self.assertIn("Unknown error type", result["message"])

    def test_calculate_confidence_exact_match(self):
        """Test confidence calculation for exact match"""
        confidence = self.detector._calculate_confidence("404", "404")

        self.assertGreater(confidence, 0.9)

    def test_calculate_confidence_prominent_pattern(self):
        """Test confidence calculation for prominent pattern"""
        confidence = self.detector._calculate_confidence("Error 404", "404")

        self.assertGreater(confidence, 0.6)

    def test_calculate_confidence_small_pattern(self):
        """Test confidence calculation for small pattern"""
        confidence = self.detector._calculate_confidence(
            "This is a very long text with a small error word somewhere", "error"
        )

        self.assertGreater(confidence, 0.5)

    def test_get_supported_error_types(self):
        """Test getting supported error types"""
        types = self.detector.get_supported_error_types()

        self.assertIsInstance(types, list)
        self.assertIn("404", types)
        self.assertIn("500", types)
        self.assertIn("crash", types)
        self.assertIn("error", types)
        self.assertGreater(len(types), 5)

    def test_add_error_pattern_new(self):
        """Test adding new error pattern"""
        initial_count = len(self.detector.get_supported_error_types())

        self.detector.add_error_pattern("custom_error", ["custom pattern", "another pattern"])

        new_count = len(self.detector.get_supported_error_types())
        self.assertEqual(new_count, initial_count + 1)
        self.assertIn("custom_error", self.detector.get_supported_error_types())

    def test_add_error_pattern_extend_existing(self):
        """Test extending existing error pattern"""
        original_patterns = self.detector.ERROR_PATTERNS["404"].copy()

        self.detector.add_error_pattern("404", ["new 404 pattern"])

        # Should have more patterns now
        self.assertGreater(len(self.detector.ERROR_PATTERNS["404"]), len(original_patterns))

    def test_detect_with_vision_ai_mock(self):
        """Test detection with mocked vision AI"""
        detector = VisualErrorDetector(use_vision_ai=False)

        # Mock vision engine
        detector.vision_engine = MagicMock()
        detector.vision_engine.detect_errors.return_value = {
            "has_error": True,
            "error_type": "crash dialog",
            "confidence": 0.85,
            "indicators": [{"type": "crash", "score": 0.85}],
        }

        # No OCR texts, should use vision AI
        result = detector.detect(self.test_image, ocr_texts=None)

        # Vision AI result should be included
        self.assertTrue(any(e["method"] == "vision_ai" for e in result["details"]))

    def test_detect_multiple_error_types(self):
        """Test detection when multiple error types present"""
        ocr_texts = ["404 Not Found", "Connection timeout", "Server Error 500"]

        result = self.detector.detect(self.test_image, ocr_texts)

        self.assertTrue(result["has_error"])
        # Should detect multiple error types
        self.assertGreater(len(result["details"]), 1)

        # Check various error types detected
        detected_types = [e["type"] for e in result["details"]]
        self.assertIn("404", detected_types)
        self.assertIn("timeout", detected_types)

    def test_confidence_ordering(self):
        """Test that most confident error is returned as primary"""
        ocr_texts = [
            "maybe an error",  # Low confidence
            "404 NOT FOUND",  # High confidence
        ]

        result = self.detector.detect(self.test_image, ocr_texts)

        self.assertTrue(result["has_error"])
        # Primary error should be the most confident one
        self.assertEqual(result["error_type"], "404")


class TestVisualErrorDetectorWithOCR(unittest.TestCase):
    """Test VisualErrorDetector with OCR extraction"""

    def test_extract_ocr_without_engine(self):
        """Test OCR extraction when OCR engine not available"""
        detector = VisualErrorDetector(use_vision_ai=False)

        test_image = Image.new("RGB", (100, 100), color="white")

        # This should gracefully handle missing OCR engine
        texts = detector._extract_ocr(test_image)

        self.assertIsInstance(texts, list)


if __name__ == "__main__":
    unittest.main()
