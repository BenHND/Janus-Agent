"""
Unit tests for OCR Engine (Native Adapter)
"""
import unittest
from unittest.mock import MagicMock, Mock, patch

from PIL import Image

from janus.vision.native_ocr_adapter import NativeOCRAdapter as OCREngine
from janus.vision.native_ocr_adapter import OCRResult


class TestOCRResult(unittest.TestCase):
    """Test cases for OCRResult"""

    def test_ocr_result_initialization(self):
        """Test OCRResult initialization"""
        result = OCRResult("Hello", 95.5, (10, 20, 100, 50))

        self.assertEqual(result.text, "Hello")
        self.assertEqual(result.confidence, 95.5)
        self.assertEqual(result.bbox, (10, 20, 100, 50))

    def test_ocr_result_to_dict(self):
        """Test OCRResult to_dict conversion"""
        result = OCRResult("Test", 90.0, (5, 10, 50, 25))

        result_dict = result.to_dict()

        self.assertEqual(result_dict["text"], "Test")
        self.assertEqual(result_dict["confidence"], 90.0)
        self.assertEqual(result_dict["bbox"], (5, 10, 50, 25))


class TestOCREngine(unittest.TestCase):
    """Test cases for OCREngine"""

    @patch("pytesseract.get_tesseract_version")
    @patch("pytesseract.image_to_string")
    def test_initialize_tesseract_backend(self, mock_image_to_string, mock_get_version):
        """Test Tesseract backend initialization"""
        mock_get_version.return_value = "5.0.0"

        engine = OCREngine(backend="tesseract", language="eng")

        self.assertEqual(engine.backend, "tesseract")
        self.assertEqual(engine.language, "eng")
        self.assertIsNotNone(engine._ocr_engine)

    def test_unsupported_backend(self):
        """Test initialization with unsupported backend"""
        with self.assertRaises(ValueError) as context:
            OCREngine(backend="unsupported")

        self.assertIn("Unsupported OCR backend", str(context.exception))

    @patch("pytesseract.get_tesseract_version")
    @patch("pytesseract.image_to_string")
    def test_recognize_text_tesseract(self, mock_image_to_string, mock_get_version):
        """Test text recognition with Tesseract"""
        mock_get_version.return_value = "5.0.0"
        mock_image_to_string.return_value = "  Hello World  "

        engine = OCREngine(backend="tesseract")
        mock_image = MagicMock(spec=Image.Image)
        mock_image.size = (800, 600)  # TICKET-OCR-NATIVE: Add size for image resizing logic

        result = engine.recognize_text(mock_image)

        self.assertEqual(result, "Hello World")
        mock_image_to_string.assert_called_once()

    @patch("pytesseract.get_tesseract_version")
    @patch("pytesseract.image_to_data")
    @patch("pytesseract.Output")
    def test_find_text_tesseract(self, mock_output, mock_image_to_data, mock_get_version):
        """Test finding specific text with Tesseract"""
        mock_get_version.return_value = "5.0.0"

        # Mock image_to_data output
        mock_output.DICT = "dict"
        mock_image_to_data.return_value = {
            "text": ["", "Hello", "World", "Test"],
            "left": [0, 10, 60, 110],
            "top": [0, 20, 20, 20],
            "width": [0, 40, 40, 40],
            "height": [0, 30, 30, 30],
            "conf": [-1, 95, 90, 85],
        }

        engine = OCREngine(backend="tesseract")
        mock_image = MagicMock(spec=Image.Image)
        mock_image.size = (800, 600)  # TICKET-OCR-NATIVE: Add size for image resizing logic

        results = engine.find_text(mock_image, "Hello")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].text, "Hello")
        self.assertEqual(results[0].bbox, (10, 20, 40, 30))

    @patch("pytesseract.get_tesseract_version")
    @patch("pytesseract.image_to_data")
    @patch("pytesseract.Output")
    def test_find_text_case_insensitive(self, mock_output, mock_image_to_data, mock_get_version):
        """Test case-insensitive text search"""
        mock_get_version.return_value = "5.0.0"
        mock_output.DICT = "dict"
        mock_image_to_data.return_value = {
            "text": ["hello"],
            "left": [10],
            "top": [20],
            "width": [40],
            "height": [30],
            "conf": [95],
        }

        engine = OCREngine(backend="tesseract")
        mock_image = MagicMock(spec=Image.Image)
        mock_image.size = (800, 600)  # TICKET-OCR-NATIVE: Add size for image resizing logic

        # Search for uppercase when text is lowercase
        results = engine.find_text(mock_image, "HELLO", case_sensitive=False)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].text, "hello")

    @patch("pytesseract.get_tesseract_version")
    @patch("pytesseract.image_to_data")
    @patch("pytesseract.Output")
    def test_get_all_text_with_boxes(self, mock_output, mock_image_to_data, mock_get_version):
        """Test getting all text with bounding boxes"""
        mock_get_version.return_value = "5.0.0"
        mock_output.DICT = "dict"
        mock_image_to_data.return_value = {
            "text": ["", "Hello", "World"],
            "left": [0, 10, 60],
            "top": [0, 20, 20],
            "width": [0, 40, 50],
            "height": [0, 30, 30],
            "conf": [-1, 95, 90],
        }

        engine = OCREngine(backend="tesseract")
        mock_image = MagicMock(spec=Image.Image)
        mock_image.size = (800, 600)  # TICKET-OCR-NATIVE: Add size for image resizing logic

        results = engine.get_all_text_with_boxes(mock_image)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].text, "Hello")
        self.assertEqual(results[1].text, "World")

    @patch("pytesseract.get_tesseract_version")
    @patch("pytesseract.image_to_string")
    def test_recognize_text_error_handling(self, mock_image_to_string, mock_get_version):
        """Test error handling in text recognition"""
        mock_get_version.return_value = "5.0.0"
        mock_image_to_string.side_effect = Exception("OCR failed")

        engine = OCREngine(backend="tesseract")
        mock_image = MagicMock(spec=Image.Image)
        mock_image.size = (800, 600)  # TICKET-OCR-NATIVE: Add size for image resizing logic

        result = engine.recognize_text(mock_image)

        # Should return empty string on error
        self.assertEqual(result, "")

    @patch("pytesseract.get_tesseract_version")
    @patch("pytesseract.image_to_data")
    @patch("pytesseract.Output")
    def test_confidence_threshold(self, mock_output, mock_image_to_data, mock_get_version):
        """Test that OCR returns all results with confidence > 0"""
        mock_get_version.return_value = "5.0.0"
        mock_output.DICT = "dict"
        mock_image_to_data.return_value = {
            "text": ["LowConf", "HighConf"],
            "left": [10, 60],
            "top": [20, 20],
            "width": [40, 40],
            "height": [30, 30],
            "conf": [30, 95],  # Both above 0
        }

        engine = OCREngine(backend="tesseract")
        mock_image = MagicMock(spec=Image.Image)
        mock_image.size = (800, 600)  # TICKET-OCR-NATIVE: Add size for image resizing logic

        results = engine.get_all_text_with_boxes(mock_image)

        # Both results should be included since both have conf > 0
        # Filtering by confidence threshold happens in ElementLocator
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].text, "LowConf")
        self.assertEqual(results[1].text, "HighConf")
    
    @patch("pytesseract.get_tesseract_version")
    @patch("pytesseract.image_to_data")
    @patch("pytesseract.Output")
    def test_extract_text_format(self, mock_output, mock_image_to_data, mock_get_version):
        """Test extract_text returns format compatible with Set-of-Marks"""
        mock_get_version.return_value = "5.0.0"
        mock_output.DICT = "dict"
        mock_image_to_data.return_value = {
            "text": ["", "Submit", "Cancel"],
            "left": [0, 10, 60],
            "top": [0, 20, 20],
            "width": [0, 40, 50],
            "height": [0, 30, 30],
            "conf": [-1, 95, 90],
        }

        engine = OCREngine(backend="tesseract")
        mock_image = MagicMock(spec=Image.Image)
        mock_image.size = (800, 600)  # TICKET-OCR-NATIVE: Add size for image resizing logic

        result = engine.extract_text(mock_image)

        # Check result structure
        self.assertIn("texts", result)
        self.assertIn("boxes", result)
        self.assertIn("confidence", result)
        
        # Check that we have 2 valid texts (empty string is filtered)
        self.assertEqual(len(result["texts"]), 2)
        self.assertEqual(len(result["boxes"]), 2)
        self.assertEqual(len(result["confidence"]), 2)
        
        # Check values
        self.assertEqual(result["texts"][0], "Submit")
        self.assertEqual(result["texts"][1], "Cancel")
        self.assertEqual(result["boxes"][0], (10, 20, 40, 30))
        self.assertEqual(result["boxes"][1], (60, 20, 50, 30))
        self.assertEqual(result["confidence"][0], 95)
        self.assertEqual(result["confidence"][1], 90)


if __name__ == "__main__":
    unittest.main()
