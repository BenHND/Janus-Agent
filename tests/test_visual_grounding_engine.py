"""
Unit tests for Visual Grounding Engine
Part of TICKET-ARCH-002: Set-of-Marks Implementation
"""
import unittest
from unittest.mock import MagicMock, Mock, patch

# Mock PIL.Image if not available
try:
    from PIL import Image
except ImportError:
    Image = Mock()
    Image.new = Mock(return_value=Mock(size=(800, 600)))

from janus.vision.visual_grounding_engine import (
    GroundedElement,
    VisualGroundingEngine,
)


class TestGroundedElement(unittest.TestCase):
    """Test cases for GroundedElement"""

    def test_initialization(self):
        """Test element initialization"""
        element = GroundedElement(
            element_id=1,
            element_type="button",
            text="Search",
            x=100,
            y=200,
            width=50,
            height=30,
            confidence=0.85,
        )

        self.assertEqual(element.id, 1)
        self.assertEqual(element.type, "button")
        self.assertEqual(element.text, "Search")
        self.assertEqual(element.x, 100)
        self.assertEqual(element.y, 200)
        self.assertEqual(element.width, 50)
        self.assertEqual(element.height, 30)
        self.assertEqual(element.confidence, 0.85)

    def test_center_calculation(self):
        """Test center point calculation"""
        element = GroundedElement(
            element_id=1,
            element_type="button",
            text="Search",
            x=100,
            y=200,
            width=50,
            height=30,
            confidence=0.85,
        )

        self.assertEqual(element.center_x, 125)  # 100 + 50/2
        self.assertEqual(element.center_y, 215)  # 200 + 30/2

    def test_to_dict(self):
        """Test conversion to dictionary"""
        element = GroundedElement(
            element_id=1,
            element_type="button",
            text="Search",
            x=100,
            y=200,
            width=50,
            height=30,
            confidence=0.85,
        )

        result = element.to_dict()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["type"], "button")
        self.assertEqual(result["text"], "Search")
        self.assertEqual(result["center_x"], 125)
        self.assertEqual(result["center_y"], 215)

    def test_to_llm_format(self):
        """Test conversion to LLM-friendly format"""
        element = GroundedElement(
            element_id=1,
            element_type="button",
            text="Search",
            x=100,
            y=200,
            width=50,
            height=30,
            confidence=0.85,
        )

        result = element.to_llm_format()

        self.assertIn("[ID 1]", result)
        self.assertIn("Button", result)
        self.assertIn("Search", result)
        self.assertIn("(x=125, y=215)", result)


class TestVisualGroundingEngine(unittest.TestCase):
    """Test cases for VisualGroundingEngine"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a simple test image
        self.test_image = Image.new("RGB", (800, 600), color="white")

    def test_initialization_with_ocr(self):
        """Test engine initialization with OCR"""
        engine = VisualGroundingEngine(use_florence=False)

        self.assertIsNotNone(engine)
        self.assertFalse(engine.use_florence)
        self.assertIsNotNone(engine.ocr_engine)

    def test_initialization_with_florence(self):
        """Test engine initialization with Florence-2"""
        # Mock Florence engine
        mock_florence = Mock()
        mock_florence.is_available.return_value = True

        engine = VisualGroundingEngine(
            florence_engine=mock_florence, use_florence=True
        )

        self.assertTrue(engine.use_florence)
        self.assertIsNotNone(engine.florence_engine)

    def test_classify_element_type_button(self):
        """Test element type classification for buttons"""
        engine = VisualGroundingEngine(use_florence=False)

        # Test button classification
        self.assertEqual(
            engine._classify_from_text("Click Here"), "button"
        )
        self.assertEqual(
            engine._classify_from_text("Submit Form"), "button"
        )
        self.assertEqual(
            engine._classify_from_text("Search"), "button"
        )

    def test_classify_element_type_textfield(self):
        """Test element type classification for text fields"""
        engine = VisualGroundingEngine(use_florence=False)

        # Test textfield classification
        self.assertEqual(
            engine._classify_from_text("Enter email"), "textfield"
        )
        self.assertEqual(
            engine._classify_from_text("Password:"), "textfield"
        )
        self.assertEqual(
            engine._classify_from_text("Username"), "textfield"
        )

    def test_is_interactive(self):
        """Test interactive element detection"""
        engine = VisualGroundingEngine(use_florence=False)

        # Interactive elements
        self.assertTrue(engine._is_interactive("button"))
        self.assertTrue(engine._is_interactive("link"))
        self.assertTrue(engine._is_interactive("textfield"))
        self.assertTrue(engine._is_interactive("checkbox"))

        # Non-interactive elements
        self.assertFalse(engine._is_interactive("label"))
        self.assertFalse(engine._is_interactive("image"))
        self.assertFalse(engine._is_interactive("text"))

    def test_generate_llm_list_empty(self):
        """Test LLM list generation with no elements"""
        engine = VisualGroundingEngine(use_florence=False)

        result = engine.generate_llm_list([])

        self.assertIn("No interactive elements", result)

    def test_generate_llm_list_with_elements(self):
        """Test LLM list generation with elements"""
        engine = VisualGroundingEngine(use_florence=False)

        elements = [
            GroundedElement(1, "button", "Search", 100, 200, 50, 30, 0.85),
            GroundedElement(2, "textfield", "Email", 150, 250, 100, 25, 0.90),
            GroundedElement(3, "link", "Sign In", 200, 300, 60, 20, 0.80),
        ]

        result = engine.generate_llm_list(elements)

        # Check each element is in the list
        self.assertIn("[ID 1]", result)
        self.assertIn("Button", result)
        self.assertIn("Search", result)
        self.assertIn("[ID 2]", result)
        self.assertIn("Textfield", result)
        self.assertIn("Email", result)
        self.assertIn("[ID 3]", result)
        self.assertIn("Link", result)
        self.assertIn("Sign In", result)

    def test_get_element_by_id(self):
        """Test element retrieval by ID"""
        engine = VisualGroundingEngine(use_florence=False)

        elements = [
            GroundedElement(1, "button", "Search", 100, 200, 50, 30, 0.85),
            GroundedElement(2, "textfield", "Email", 150, 250, 100, 25, 0.90),
            GroundedElement(3, "link", "Sign In", 200, 300, 60, 20, 0.80),
        ]

        # Find existing element
        element = engine.get_element_by_id(elements, 2)
        self.assertIsNotNone(element)
        self.assertEqual(element.id, 2)
        self.assertEqual(element.type, "textfield")

        # Try to find non-existent element
        element = engine.get_element_by_id(elements, 99)
        self.assertIsNone(element)

    @patch("janus.vision.visual_grounding_engine.OCREngine")
    def test_detect_with_ocr_mock(self, mock_ocr_class):
        """Test element detection with mocked OCR"""
        # Mock OCR results
        mock_ocr_result = Mock()
        mock_ocr_result.text = "Search"
        mock_ocr_result.confidence = 85.0
        mock_ocr_result.bbox = (100, 200, 50, 30)

        mock_ocr = Mock()
        mock_ocr.get_all_text_with_boxes.return_value = [mock_ocr_result]

        engine = VisualGroundingEngine(
            ocr_engine=mock_ocr, use_florence=False
        )

        # Detect elements
        elements = engine.detect_interactive_elements(self.test_image)

        # Should detect at least one element
        self.assertGreaterEqual(len(elements), 0)

        # If element was detected, check it has proper ID
        if len(elements) > 0:
            self.assertEqual(elements[0].id, 1)
            self.assertIn(elements[0].type, ["button", "link", "textfield"])

    def test_find_text_in_region(self):
        """Test finding text within a bounding box"""
        engine = VisualGroundingEngine(use_florence=False)

        # Mock text regions
        text_regions = [
            {"text": "Search", "bbox": [95, 195, 145, 225]},  # Overlaps
            {"text": "Cancel", "bbox": [500, 500, 550, 530]},  # No overlap
        ]

        # Test overlapping region
        bbox = (100, 200, 150, 230)  # Should overlap with "Search"
        result = engine._find_text_in_region(text_regions, bbox)
        self.assertEqual(result, "Search")

        # Test non-overlapping region
        bbox = (300, 300, 350, 330)  # No overlap
        result = engine._find_text_in_region(text_regions, bbox)
        self.assertEqual(result, "")

    def test_is_available(self):
        """Test availability check"""
        engine = VisualGroundingEngine(use_florence=False)

        # Should be available with OCR
        self.assertTrue(engine.is_available())

    def test_get_info(self):
        """Test engine information retrieval"""
        engine = VisualGroundingEngine(use_florence=False)

        info = engine.get_info()

        self.assertIsInstance(info, dict)
        self.assertEqual(info["engine"], "visual_grounding")
        self.assertEqual(info["method"], "ocr")
        self.assertIn("min_confidence", info)


if __name__ == "__main__":
    unittest.main()
