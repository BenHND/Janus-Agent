"""
Unit tests for OmniParser Vision Adapter

Tests:
1. Model initialization
2. Object detection
3. OCR extraction
4. Integration with Visual Grounding Engine
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestOmniParserAdapter(unittest.TestCase):
    """Test OmniParser Vision Adapter"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_image = Mock()
        self.mock_image.size = (1920, 1080)
        self.mock_image.width = 1920
        self.mock_image.height = 1080
    
    @patch('janus.vision.omniparser_adapter.YOLO')
    @patch('janus.vision.omniparser_adapter.AutoModelForCausalLM')
    @patch('janus.vision.omniparser_adapter.AutoProcessor')
    def test_initialization_lazy_load(self, mock_processor, mock_model, mock_yolo):
        """Test lazy loading initialization"""
        from janus.vision.omniparser_adapter import OmniParserVisionEngine
        
        engine = OmniParserVisionEngine(lazy_load=True)
        
        # Should not load models on init
        self.assertIsNone(engine.detection_model)
        self.assertIsNone(engine.caption_model)
        self.assertFalse(engine._models_loaded)
    
    @patch('janus.vision.omniparser_adapter.torch')
    @patch('janus.vision.omniparser_adapter.YOLO')
    @patch('janus.vision.omniparser_adapter.AutoModelForCausalLM')
    @patch('janus.vision.omniparser_adapter.AutoProcessor')
    def test_detect_objects_without_models(self, mock_processor, mock_model, mock_yolo, mock_torch):
        """Test object detection without loaded models"""
        from janus.vision.omniparser_adapter import OmniParserVisionEngine
        
        engine = OmniParserVisionEngine(lazy_load=True)
        result = engine.detect_objects(self.mock_image)
        
        self.assertIn("error", result)
        self.assertEqual(result["count"], 0)
        self.assertEqual(len(result["objects"]), 0)
    
    @patch('janus.vision.omniparser_adapter.torch')
    def test_device_detection_cpu(self, mock_torch):
        """Test CPU device detection"""
        from janus.vision.omniparser_adapter import OmniParserVisionEngine
        
        mock_torch.backends.mps.is_available.return_value = False
        mock_torch.cuda.is_available.return_value = False
        
        engine = OmniParserVisionEngine(device="auto", lazy_load=True)
        self.assertEqual(engine.device, "cpu")
    
    @patch('janus.vision.omniparser_adapter.torch')
    def test_device_detection_mps(self, mock_torch):
        """Test MPS (Apple Silicon) device detection"""
        from janus.vision.omniparser_adapter import OmniParserVisionEngine
        
        mock_torch.backends.mps.is_available.return_value = True
        mock_torch.cuda.is_available.return_value = False
        
        engine = OmniParserVisionEngine(device="auto", lazy_load=True)
        self.assertEqual(engine.device, "mps")
    
    def test_get_info_not_loaded(self):
        """Test get_info when models not loaded"""
        from janus.vision.omniparser_adapter import OmniParserVisionEngine
        
        with patch('janus.vision.omniparser_adapter.torch'):
            engine = OmniParserVisionEngine(lazy_load=True)
            info = engine.get_info()
            
            self.assertEqual(info["engine"], "omniparser")
            self.assertFalse(info["available"])
            self.assertIsNone(info["detection_model"])


class TestOmniParserIntegration(unittest.TestCase):
    """Test OmniParser integration with Visual Grounding Engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_image = Mock()
        self.mock_image.size = (1920, 1080)
    
    @patch('janus.vision.visual_grounding_engine.OmniParserVisionEngine')
    def test_visual_grounding_prefers_omniparser(self, mock_omni_class):
        """Test that VisualGroundingEngine prefers OmniParser over Florence"""
        from janus.vision.visual_grounding_engine import VisualGroundingEngine
        
        # Mock OmniParser engine
        mock_omni_engine = Mock()
        mock_omni_engine.is_available.return_value = True
        mock_omni_engine.detect_objects.return_value = {
            "objects": [
                {
                    "label": "button",
                    "bbox": (100, 100, 200, 140),
                    "confidence": 0.9,
                    "center": (150, 120),
                    "width": 100,
                    "height": 40,
                }
            ],
            "count": 1,
            "method": "omniparser_yolo",
        }
        mock_omni_engine.extract_text.return_value = {
            "text": "Submit",
            "regions": [{"text": "Submit", "bbox": [100, 100, 200, 140]}],
        }
        
        mock_omni_class.return_value = mock_omni_engine
        
        # Create engine with OmniParser
        engine = VisualGroundingEngine(
            use_omniparser=True,
            use_florence=False,
        )
        
        # Should use OmniParser
        self.assertTrue(engine.use_omniparser)
        self.assertIsNotNone(engine.omniparser_engine)


class TestVisualGroundingWithOmniParser(unittest.TestCase):
    """Test Visual Grounding Engine with OmniParser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_ocr = Mock()
        self.mock_ocr.get_all_text_with_boxes.return_value = []
        
        self.mock_omniparser = Mock()
        self.mock_omniparser.is_available.return_value = True
        
        self.mock_image = Mock()
        self.mock_image.size = (1920, 1080)
        self.mock_image.crop = Mock(return_value=self.mock_image)
    
    def test_detect_with_omniparser(self):
        """Test element detection using OmniParser"""
        from janus.vision.visual_grounding_engine import VisualGroundingEngine
        
        # Mock OmniParser detection results
        self.mock_omniparser.detect_objects.return_value = {
            "objects": [
                {
                    "label": "button",
                    "bbox": (100, 100, 200, 140),
                    "confidence": 0.92,
                    "center": (150, 120),
                    "width": 100,
                    "height": 40,
                }
            ],
            "count": 1,
        }
        self.mock_omniparser.extract_text.return_value = {
            "text": "",
            "regions": [],
        }
        
        # Create engine
        engine = VisualGroundingEngine(
            ocr_engine=self.mock_ocr,
            omniparser_engine=self.mock_omniparser,
            use_omniparser=True,
            use_florence=False,
        )
        
        # Detect elements
        elements = engine.detect_interactive_elements(self.mock_image)
        
        # Verify
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].type, "button")
        self.assertEqual(elements[0].id, 1)  # Should be assigned ID


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestOmniParserAdapter))
    suite.addTests(loader.loadTestsFromTestCase(TestOmniParserIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestVisualGroundingWithOmniParser))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
