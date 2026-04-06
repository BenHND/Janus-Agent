"""
Unit tests for Set-of-Marks Vision System - TICKET-AUDIT-006

Tests proactive element detection, ID generation, and caching.
"""

import json
import time
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image


class TestInteractiveElement(unittest.TestCase):
    """Test InteractiveElement dataclass"""
    
    def test_create_element(self):
        """Test creating an interactive element"""
        from janus.vision.set_of_marks import InteractiveElement
        
        element = InteractiveElement(
            element_id="button_1",
            element_type="button",
            text="Submit",
            bbox=(100, 200, 80, 40),
            confidence=0.95,
            attributes={"disabled": False},
        )
        
        self.assertEqual(element.element_id, "button_1")
        self.assertEqual(element.element_type, "button")
        self.assertEqual(element.text, "Submit")
        self.assertEqual(element.bbox, (100, 200, 80, 40))
        self.assertEqual(element.confidence, 0.95)
        self.assertEqual(element.attributes, {"disabled": False})
    
    def test_element_to_dict(self):
        """Test converting element to dictionary"""
        from janus.vision.set_of_marks import InteractiveElement
        
        element = InteractiveElement(
            element_id="input_1",
            element_type="input",
            text="Enter email",
            bbox=(50, 100, 200, 30),
            confidence=0.88,
        )
        
        data = element.to_dict()
        
        self.assertEqual(data["id"], "input_1")
        self.assertEqual(data["type"], "input")
        self.assertEqual(data["text"], "Enter email")
        self.assertEqual(data["bbox"], (50, 100, 200, 30))
        self.assertEqual(data["confidence"], 0.88)
    
    def test_element_to_reasoner_format(self):
        """Test converting element to reasoner format (compact)"""
        from janus.vision.set_of_marks import InteractiveElement
        
        # Create a long text to test truncation
        LONG_TEXT_MULTIPLIER = 10  # Repeat text 10 times to exceed 100 char limit
        long_text = "This is a very long text that should be truncated for the reasoner " * LONG_TEXT_MULTIPLIER
        
        element = InteractiveElement(
            element_id="text_1",
            element_type="text",
            text=long_text,
            bbox=(10, 20, 300, 50),
            confidence=0.92,
        )
        
        reasoner_data = element.to_reasoner_format()
        
        self.assertEqual(reasoner_data["id"], "text_1")
        self.assertEqual(reasoner_data["type"], "text")
        # Text should be truncated to 100 chars
        self.assertLessEqual(len(reasoner_data["text"]), 100)


class TestScreenCapture(unittest.TestCase):
    """Test ScreenCapture dataclass"""
    
    def test_create_capture(self):
        """Test creating a screen capture"""
        from janus.vision.set_of_marks import ScreenCapture, InteractiveElement
        
        elements = [
            InteractiveElement("button_1", "button", "Click me", (0, 0, 100, 50), 0.9),
            InteractiveElement("input_1", "input", "Name", (0, 60, 200, 30), 0.85),
        ]
        
        capture = ScreenCapture(
            timestamp=time.time(),
            elements=elements,
            screenshot_hash="abc123",
            capture_duration_ms=250,
        )
        
        self.assertEqual(len(capture.elements), 2)
        self.assertEqual(capture.screenshot_hash, "abc123")
        self.assertEqual(capture.capture_duration_ms, 250)
    
    def test_capture_expiration(self):
        """Test capture expiration based on TTL"""
        from janus.vision.set_of_marks import ScreenCapture
        
        # Create old capture
        old_capture = ScreenCapture(
            timestamp=time.time() - 5.0,  # 5 seconds ago
            elements=[],
            screenshot_hash="old",
            capture_duration_ms=100,
        )
        
        # Create fresh capture
        fresh_capture = ScreenCapture(
            timestamp=time.time(),
            elements=[],
            screenshot_hash="fresh",
            capture_duration_ms=100,
        )
        
        # Test with 2 second TTL
        self.assertTrue(old_capture.is_expired(ttl_seconds=2.0))
        self.assertFalse(fresh_capture.is_expired(ttl_seconds=2.0))


class TestSetOfMarksEngine(unittest.TestCase):
    """Test Set-of-Marks engine"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock vision components to avoid dependencies
        self.mock_screenshot = MagicMock()
        self.mock_ocr = MagicMock()
        self.mock_locator = MagicMock()
    
    def test_engine_initialization_without_vision(self):
        """Test engine initialization when vision not available"""
        from janus.vision.set_of_marks import SetOfMarksEngine
        
        # Initialize without vision components
        engine = SetOfMarksEngine()
        
        # Should handle missing vision gracefully
        self.assertIsInstance(engine, SetOfMarksEngine)
    
    def test_element_id_generation(self):
        """Test unique element ID generation"""
        from janus.vision.set_of_marks import SetOfMarksEngine
        
        engine = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            element_locator=self.mock_locator,
        )
        
        # Generate IDs for different element types
        id1 = engine._generate_element_id("button")
        id2 = engine._generate_element_id("button")
        id3 = engine._generate_element_id("input")
        id4 = engine._generate_element_id("button")
        
        self.assertEqual(id1, "button_1")
        self.assertEqual(id2, "button_2")
        self.assertEqual(id3, "input_1")
        self.assertEqual(id4, "button_3")
    
    def test_element_type_classification(self):
        """Test element type classification based on text"""
        from janus.vision.set_of_marks import SetOfMarksEngine
        
        engine = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            element_locator=self.mock_locator,
        )
        
        # Test button classification
        self.assertEqual(engine._classify_element_type("Submit"), "button")
        self.assertEqual(engine._classify_element_type("Click here"), "button")
        self.assertEqual(engine._classify_element_type("Login"), "button")
        
        # Test link classification
        self.assertEqual(engine._classify_element_type("https://example.com"), "link")
        self.assertEqual(engine._classify_element_type("www.example.com"), "link")
        
        # Test input classification
        self.assertEqual(engine._classify_element_type("Enter your name"), "input")
        self.assertEqual(engine._classify_element_type("Email address"), "input")
        
        # Test default (text)
        self.assertEqual(engine._classify_element_type("Some random text"), "text")
        self.assertEqual(engine._classify_element_type("Company Information"), "text")
    
    @patch("janus.vision.set_of_marks.Image")
    def test_screenshot_hash_computation(self, mock_image):
        """Test screenshot hash computation"""
        from janus.vision.set_of_marks import SetOfMarksEngine
        
        engine = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            element_locator=self.mock_locator,
        )
        
        # Create mock screenshot
        mock_screenshot = MagicMock(spec=Image.Image)
        mock_screenshot.tobytes.return_value = b"screenshot_data"
        
        # Compute hash
        hash1 = engine._compute_screenshot_hash(mock_screenshot)
        hash2 = engine._compute_screenshot_hash(mock_screenshot)
        
        # Same screenshot should produce same hash
        self.assertEqual(hash1, hash2)
        self.assertIsInstance(hash1, str)
        self.assertEqual(len(hash1), 16)  # Truncated to 16 chars
    
    def test_cache_invalidation(self):
        """Test vision cache invalidation"""
        from janus.vision.set_of_marks import SetOfMarksEngine, ScreenCapture
        
        engine = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            element_locator=self.mock_locator,
        )
        
        # Set a cache entry
        engine._last_capture = ScreenCapture(
            timestamp=time.time(),
            elements=[],
            screenshot_hash="test",
            capture_duration_ms=100,
        )
        
        self.assertIsNotNone(engine._last_capture)
        
        # Invalidate cache
        engine.invalidate_cache()
        
        self.assertIsNone(engine._last_capture)
    
    def test_get_element_by_id(self):
        """Test getting element by ID"""
        from janus.vision.set_of_marks import (
            SetOfMarksEngine,
            ScreenCapture,
            InteractiveElement,
        )
        
        engine = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            element_locator=self.mock_locator,
        )
        
        # Create capture with elements
        elements = [
            InteractiveElement("button_1", "button", "Submit", (0, 0, 100, 50), 0.9),
            InteractiveElement("input_1", "input", "Name", (0, 60, 200, 30), 0.85),
        ]
        
        engine._last_capture = ScreenCapture(
            timestamp=time.time(),
            elements=elements,
            screenshot_hash="test",
            capture_duration_ms=100,
        )
        
        # Find element
        button = engine.get_element_by_id("button_1")
        self.assertIsNotNone(button)
        self.assertEqual(button.element_id, "button_1")
        self.assertEqual(button.text, "Submit")
        
        # Non-existent element
        none_elem = engine.get_element_by_id("nonexistent")
        self.assertIsNone(none_elem)
    
    def test_capture_without_vision_returns_empty(self):
        """Test that capture returns empty list when vision not available"""
        from janus.vision.set_of_marks import SetOfMarksEngine
        
        # Initialize without vision components
        engine = SetOfMarksEngine()
        
        # Capture should return empty list
        elements = engine.capture_elements()
        
        self.assertEqual(elements, [])
        self.assertFalse(engine.is_available())
    
    def test_statistics(self):
        """Test getting engine statistics"""
        from janus.vision.set_of_marks import SetOfMarksEngine, ScreenCapture
        
        engine = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            element_locator=self.mock_locator,
            cache_ttl=2.0,
            enable_cache=True,
        )
        
        # Get stats without capture
        stats = engine.get_statistics()
        
        self.assertTrue(stats["vision_available"])
        self.assertTrue(stats["cache_enabled"])
        self.assertEqual(stats["cache_ttl"], 2.0)
        self.assertIsNone(stats["last_capture"])
        
        # Add a capture
        engine._last_capture = ScreenCapture(
            timestamp=time.time(),
            elements=[],
            screenshot_hash="test",
            capture_duration_ms=150,
        )
        
        # Get stats with capture
        stats = engine.get_statistics()
        
        self.assertIsNotNone(stats["last_capture"])
        self.assertEqual(stats["last_capture"]["element_count"], 0)
        self.assertEqual(stats["last_capture"]["capture_duration_ms"], 150)


class TestFlorenceIntegration(unittest.TestCase):
    """Test Florence-2 integration for icon detection - TICKET-VIS-001"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_screenshot = MagicMock()
        self.mock_ocr = MagicMock()
        self.mock_locator = MagicMock()
        self.mock_florence = MagicMock()
    
    def test_florence_engine_initialization(self):
        """Test that florence_engine parameter is accepted"""
        from janus.vision.set_of_marks import SetOfMarksEngine
        
        engine = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            florence_engine=self.mock_florence,
        )
        
        self.assertEqual(engine.florence_engine, self.mock_florence)
    
    def test_classify_object_type(self):
        """Test object type classification from Florence-2 labels"""
        from janus.vision.set_of_marks import SetOfMarksEngine
        
        engine = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            florence_engine=self.mock_florence,
        )
        
        # Test icon classification (menu burger, etc.)
        self.assertEqual(engine._classify_object_type("hamburger menu"), "icon")
        self.assertEqual(engine._classify_object_type("menu icon"), "icon")
        self.assertEqual(engine._classify_object_type("trash icon"), "icon")
        
        # Test button classification
        self.assertEqual(engine._classify_object_type("button"), "button")
        self.assertEqual(engine._classify_object_type("play button"), "button")
        
        # Test default (icon)
        self.assertEqual(engine._classify_object_type("unknown element"), "icon")
    
    def test_create_elements_from_florence(self):
        """Test creation of elements from Florence-2 object detection"""
        from janus.vision.set_of_marks import SetOfMarksEngine
        
        engine = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            florence_engine=self.mock_florence,
        )
        
        # Mock Florence-2 detection results
        florence_result = {
            "objects": [
                {
                    "label": "button",
                    "bbox": (100, 200, 150, 250),
                },
                {
                    "label": "menu icon",
                    "bbox": (10, 10, 50, 50),
                },
                {
                    "label": "play button",
                    "bbox": (200, 300, 250, 350),
                },
            ]
        }
        
        elements = engine._create_elements_from_florence(florence_result)
        
        # Should create 3 elements
        self.assertEqual(len(elements), 3)
        
        # Check first element (button)
        self.assertEqual(elements[0].element_type, "button")
        self.assertEqual(elements[0].element_id, "button_1")
        self.assertEqual(elements[0].text, "button")
        self.assertEqual(elements[0].attributes["source"], "florence2")
        self.assertEqual(elements[0].bbox, (100, 200, 150, 250))
        
        # Check second element (icon)
        self.assertEqual(elements[1].element_type, "icon")
        self.assertEqual(elements[1].element_id, "icon_1")
        self.assertEqual(elements[1].text, "menu icon")
        
        # Check third element (button)
        self.assertEqual(elements[2].element_type, "button")
        self.assertEqual(elements[2].element_id, "button_2")
    
    def test_create_elements_from_ocr_with_source_tag(self):
        """Test that OCR elements are tagged with source='ocr'"""
        from janus.vision.set_of_marks import SetOfMarksEngine
        
        engine = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            florence_engine=self.mock_florence,
        )
        
        # Mock OCR results
        ocr_result = {
            "texts": ["Submit", "Menu"],
            "boxes": [(100, 200, 80, 40), (50, 100, 60, 30)],
            "confidence": [95, 88],
        }
        
        elements = engine._create_elements_from_ocr(ocr_result)
        
        # Should create 2 elements
        self.assertEqual(len(elements), 2)
        
        # Both should be tagged with source='ocr'
        self.assertEqual(elements[0].attributes["source"], "ocr")
        self.assertEqual(elements[1].attributes["source"], "ocr")
    
    def test_parallel_detection_integration(self):
        """Test that OCR and Florence-2 run in parallel and merge results"""
        from janus.vision.set_of_marks import SetOfMarksEngine
        
        # Setup mock Florence engine
        self.mock_florence.is_available.return_value = True
        self.mock_florence.detect_objects.return_value = {
            "objects": [
                {
                    "label": "trash icon",
                    "bbox": (10, 10, 50, 50),
                },
            ]
        }
        
        # Setup mock OCR
        self.mock_ocr.extract_text.return_value = {
            "texts": ["Submit"],
            "boxes": [(100, 200, 80, 40)],
            "confidence": [95],
        }
        
        engine = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            florence_engine=self.mock_florence,
        )
        
        # Create mock screenshot
        mock_screenshot = MagicMock()
        
        # Detect elements (should call both OCR and Florence-2)
        elements = engine._detect_elements(mock_screenshot)
        
        # Should have 2 elements (1 from OCR, 1 from Florence-2)
        self.assertEqual(len(elements), 2)
        
        # Verify both methods were called
        self.mock_ocr.extract_text.assert_called_once()
        self.mock_florence.detect_objects.assert_called_once()
        
        # Check that one element is from OCR and one from Florence-2
        sources = [elem.attributes["source"] for elem in elements]
        self.assertIn("ocr", sources)
        self.assertIn("florence2", sources)


class TestSetOfMarksCaching(unittest.TestCase):
    """Test caching behavior of Set-of-Marks engine"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_screenshot = MagicMock()
        self.mock_ocr = MagicMock()
        self.mock_locator = MagicMock()
    
    def test_cache_hit_within_ttl(self):
        """Test that cache is used within TTL window"""
        from janus.vision.set_of_marks import (
            SetOfMarksEngine,
            ScreenCapture,
            InteractiveElement,
        )
        
        engine = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            element_locator=self.mock_locator,
            cache_ttl=2.0,
            enable_cache=True,
        )
        
        # Create cached elements
        cached_elements = [
            InteractiveElement("button_1", "button", "Cached", (0, 0, 100, 50), 0.9),
        ]
        
        engine._last_capture = ScreenCapture(
            timestamp=time.time(),  # Fresh capture
            elements=cached_elements,
            screenshot_hash="cached",
            capture_duration_ms=100,
        )
        
        # Mock OCR to return different elements (should not be called)
        self.mock_screenshot.capture_screen.return_value = Image.new("RGB", (800, 600))
        self.mock_ocr.extract_text.return_value = {
            "texts": ["Fresh Button"],
            "boxes": [(0, 0, 100, 50)],
            "confidence": [95],
        }
        
        # Capture elements - should use cache
        elements = engine.capture_elements(force_refresh=False)
        
        # Should return cached elements
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].text, "Cached")
        
        # OCR should not have been called (cache hit)
        self.mock_ocr.extract_text.assert_not_called()
    
    def test_cache_miss_after_ttl(self):
        """Test that cache is refreshed after TTL expires"""
        from janus.vision.set_of_marks import (
            SetOfMarksEngine,
            ScreenCapture,
            InteractiveElement,
        )
        
        engine = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            element_locator=self.mock_locator,
            cache_ttl=1.0,  # 1 second TTL
            enable_cache=True,
        )
        
        # Create expired cache
        old_elements = [
            InteractiveElement("button_1", "button", "Old", (0, 0, 100, 50), 0.9),
        ]
        
        engine._last_capture = ScreenCapture(
            timestamp=time.time() - 2.0,  # 2 seconds ago (expired)
            elements=old_elements,
            screenshot_hash="old",
            capture_duration_ms=100,
        )
        
        # Mock OCR to return fresh elements
        mock_image = Image.new("RGB", (800, 600))
        self.mock_screenshot.capture_screen.return_value = mock_image
        self.mock_ocr.extract_text.return_value = {
            "texts": ["Fresh Button"],
            "boxes": [[0, 0, 100, 50]],
            "confidence": [95],
        }
        
        # Capture elements - should refresh cache
        elements = engine.capture_elements(force_refresh=False)
        
        # Should call OCR for fresh capture
        self.mock_ocr.extract_text.assert_called_once()
        
        # Should have new cache
        self.assertIsNotNone(engine._last_capture)
        self.assertEqual(len(engine._last_capture.elements), 1)
    
    def test_force_refresh_ignores_cache(self):
        """Test that force_refresh bypasses cache"""
        from janus.vision.set_of_marks import (
            SetOfMarksEngine,
            ScreenCapture,
            InteractiveElement,
        )
        
        engine = SetOfMarksEngine(
            screenshot_engine=self.mock_screenshot,
            ocr_engine=self.mock_ocr,
            element_locator=self.mock_locator,
            cache_ttl=10.0,  # Long TTL
            enable_cache=True,
        )
        
        # Create fresh cache
        cached_elements = [
            InteractiveElement("button_1", "button", "Cached", (0, 0, 100, 50), 0.9),
        ]
        
        engine._last_capture = ScreenCapture(
            timestamp=time.time(),
            elements=cached_elements,
            screenshot_hash="cached",
            capture_duration_ms=100,
        )
        
        # Mock OCR
        mock_image = Image.new("RGB", (800, 600))
        self.mock_screenshot.capture_screen.return_value = mock_image
        self.mock_ocr.extract_text.return_value = {
            "texts": ["Fresh Button"],
            "boxes": [[0, 0, 100, 50]],
            "confidence": [95],
        }
        
        # Force refresh - should ignore cache
        elements = engine.capture_elements(force_refresh=True)
        
        # Should call OCR despite fresh cache
        self.mock_ocr.extract_text.assert_called_once()


class TestSetOfMarksSorting(unittest.TestCase):
    """Test Set-of-Marks element sorting improvements (TICKET-ARCHI)"""
    
    def test_element_limit_increased_to_50(self):
        """Test that element limit is increased from 20 to 50 (TICKET-ARCHI)"""
        from janus.vision.set_of_marks import SetOfMarksEngine, InteractiveElement
        
        # Create mock dependencies
        mock_screenshot = MagicMock()
        mock_ocr = MagicMock()
        mock_locator = MagicMock()
        
        # Create 60 elements
        elements = []
        for i in range(60):
            elements.append(InteractiveElement(
                element_id=f"button_{i}",
                element_type="button",
                text=f"Button {i}",
                bbox=(10, 10 + i * 50, 100, 40),
                confidence=0.9
            ))
        
        mock_locator.find_interactive_elements.return_value = elements
        mock_screenshot.capture_screen.return_value = MagicMock(spec=Image.Image)
        mock_ocr.extract_text.return_value = {"texts": [], "boxes": [], "confidence": []}
        
        engine = SetOfMarksEngine(
            screenshot_engine=mock_screenshot,
            ocr_engine=mock_ocr,
            element_locator=mock_locator,
        )
        
        # Get elements for reasoner
        result_json = engine.get_elements_for_reasoner(force_refresh=True)
        result = json.loads(result_json)
        
        # Should be limited to 50 (not 20)
        self.assertEqual(len(result), 50)
    
    def test_spatial_sorting_prioritizes_center_content(self):
        """Test that spatial sorting prioritizes center content over header (TICKET-ARCHI)"""
        from janus.vision.set_of_marks import SetOfMarksEngine, InteractiveElement
        
        # Create mock dependencies
        mock_screenshot = MagicMock()
        mock_ocr = MagicMock()
        mock_locator = MagicMock()
        
        # Create elements:
        # - Header buttons at y=50 (top 5% of 1000px screen)
        # - Content links at y=500 (middle of screen)
        elements = []
        
        # 10 header buttons (navigation)
        for i in range(10):
            elements.append(InteractiveElement(
                element_id=f"header_btn_{i}",
                element_type="button",
                text=f"Header Button {i}",
                bbox=(10 + i * 100, 50, 80, 30),  # y=50 (header)
                confidence=0.9
            ))
        
        # 10 content links (main content - e.g., YouTube videos)
        for i in range(10):
            elements.append(InteractiveElement(
                element_id=f"video_link_{i}",
                element_type="link",
                text=f"Video Title {i}",
                bbox=(10, 300 + i * 100, 200, 80),  # y=300-1200 (center)
                confidence=0.9
            ))
        
        mock_locator.find_interactive_elements.return_value = elements
        mock_screenshot.capture_screen.return_value = MagicMock(spec=Image.Image)
        mock_ocr.extract_text.return_value = {"texts": [], "boxes": [], "confidence": []}
        
        engine = SetOfMarksEngine(
            screenshot_engine=mock_screenshot,
            ocr_engine=mock_ocr,
            element_locator=mock_locator,
        )
        
        # Get elements for reasoner
        result_json = engine.get_elements_for_reasoner(force_refresh=True)
        result = json.loads(result_json)
        
        # Extract IDs
        result_ids = [elem["id"] for elem in result]
        
        # Content links should appear in results (not all truncated out)
        video_links = [id for id in result_ids if id.startswith("video_link_")]
        self.assertGreater(len(video_links), 0, "Video links should be included in results")


if __name__ == "__main__":
    unittest.main()
