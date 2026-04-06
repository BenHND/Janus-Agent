"""
Apple Vision OCR - Native macOS Vision.framework for fast OCR

PERF-M4-002: This module provides native macOS OCR using Vision.framework,
which is significantly faster than Tesseract and much faster than VLM approaches.

Performance:
- Apple Vision OCR: 50-100ms (native, GPU-accelerated)
- Tesseract OCR: 200-500ms (CPU-based)
- VLM (OmniParser/Florence): 500-1000ms (neural network inference)

The Vision framework is built into macOS 10.13+ and provides:
- Fast, GPU-accelerated text recognition
- High accuracy for printed text
- Support for multiple languages
- Automatic text orientation detection

This should be used as the third fallback in the detection hierarchy:
1. Accessibility API (0-5ms)
2. OCR Cache (0ms if hit)
3. Apple Vision OCR (50-100ms) <- THIS MODULE
4. VLM fallback (500-1000ms)
"""

import logging
import platform
from typing import Any, Dict, List, Optional

from PIL import Image

logger = logging.getLogger(__name__)


class OCRResult:
    """OCR result container"""
    
    def __init__(self, texts: List[Dict[str, Any]], raw_result: Optional[Any] = None):
        """
        Initialize OCR result
        
        Args:
            texts: List of detected text items with bbox and confidence
            raw_result: Raw Vision API result for debugging
        """
        self.texts = texts
        self.raw_result = raw_result


class AppleVisionOCR:
    """
    Native macOS OCR using Vision.framework
    
    This class wraps the macOS Vision framework's text recognition APIs
    to provide fast, accurate OCR without external dependencies.
    
    Features:
    - GPU-accelerated text recognition
    - Fast: 50-100ms per image on M-series chips
    - High accuracy for printed text
    - No external dependencies (built into macOS)
    - Automatic language detection
    
    Requirements:
    - macOS 10.13+ (High Sierra or later)
    - pyobjc-framework-Vision (should be installed with pyobjc)
    """
    
    def __init__(self):
        """Initialize Apple Vision OCR"""
        self._available = False
        self._check_availability()
        
        if self._available:
            logger.info("Apple Vision OCR initialized and available")
        else:
            logger.warning("Apple Vision OCR not available (not on macOS or missing dependencies)")
    
    def _check_availability(self):
        """Check if Vision.framework is available"""
        if platform.system() != "Darwin":
            logger.debug("Not on macOS, Apple Vision OCR not available")
            return
        
        try:
            # Try to import Vision framework
            import Vision
            import Quartz
            from Cocoa import NSData, NSURL
            
            self._available = True
            logger.debug("Vision.framework is available")
            
        except ImportError as e:
            logger.debug(f"Vision.framework not available: {e}")
            logger.info(
                "To enable Apple Vision OCR, install: "
                "pip install pyobjc-framework-Vision pyobjc-framework-Quartz"
            )
    
    def is_available(self) -> bool:
        """Check if Apple Vision OCR is available"""
        return self._available
    
    def recognize_text(
        self, 
        image: Image.Image,
        recognition_level: str = "accurate"
    ) -> Optional[OCRResult]:
        """
        Recognize text in image using Vision.framework
        
        Args:
            image: PIL Image to process
            recognition_level: "fast" or "accurate" (default: "accurate")
        
        Returns:
            OCRResult with detected text and bounding boxes, or None on error
        """
        if not self._available:
            logger.warning("Apple Vision OCR not available")
            return None
        
        try:
            import Vision
            import Quartz
            from Cocoa import NSData, NSURL, NSError
            from Foundation import NSDictionary
            import objc
            
            # Convert PIL Image to NSData
            import io
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_data = buffer.getvalue()
            ns_data = NSData.dataWithBytes_length_(image_data, len(image_data))
            
            # Create CGImage from NSData
            data_provider = Quartz.CGDataProviderCreateWithCFData(ns_data)
            cg_image = Quartz.CGImageCreateWithPNGDataProvider(
                data_provider, None, False, Quartz.kCGRenderingIntentDefault
            )
            
            if not cg_image:
                logger.error("Failed to create CGImage")
                return None
            
            # Create Vision request handler
            request_handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(
                cg_image, NSDictionary.dictionary()
            )
            
            # Create text recognition request
            # Use VNRecognizeTextRequest for high-accuracy OCR
            request = Vision.VNRecognizeTextRequest.alloc().init()
            
            # Set recognition level
            if recognition_level == "fast":
                request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelFast)
            else:
                request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
            
            # Perform request
            error = None
            success = request_handler.performRequests_error_([request], objc.nil)
            
            if not success:
                logger.error("Vision text recognition failed")
                return None
            
            # Extract results
            results = request.results()
            if not results:
                logger.debug("No text found in image")
                return OCRResult(texts=[], raw_result=None)
            
            # Parse observations
            texts = []
            img_width, img_height = image.size
            
            for observation in results:
                # Get recognized text
                top_candidate = observation.topCandidates_(1)[0]
                text = top_candidate.string()
                confidence = top_candidate.confidence() * 100
                
                # Get bounding box (normalized coordinates)
                bbox = observation.boundingBox()
                
                # Convert from Vision's coordinate system (origin bottom-left)
                # to standard top-left origin
                x = int(bbox.origin.x * img_width)
                y = int((1.0 - bbox.origin.y - bbox.size.height) * img_height)
                width = int(bbox.size.width * img_width)
                height = int(bbox.size.height * img_height)
                
                texts.append({
                    'text': text,
                    'bbox': {
                        'x': x,
                        'y': y,
                        'width': width,
                        'height': height,
                    },
                    'confidence': confidence,
                })
            
            logger.debug(f"Apple Vision OCR found {len(texts)} text items")
            return OCRResult(texts=texts, raw_result=results)
            
        except Exception as e:
            logger.error(f"Error during Apple Vision OCR: {e}", exc_info=True)
            return None
    
    def find_text(
        self, 
        image: Image.Image, 
        target_text: str, 
        case_sensitive: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Find specific text in image
        
        Args:
            image: PIL Image to search
            target_text: Text to find
            case_sensitive: Whether to do case-sensitive search
        
        Returns:
            Dict with text and bbox if found, None otherwise
        """
        result = self.recognize_text(image)
        if not result or not result.texts:
            return None
        
        # Search for target text
        target = target_text if case_sensitive else target_text.lower()
        
        for text_item in result.texts:
            text = text_item['text']
            comparison = text if case_sensitive else text.lower()
            
            # Check for exact match or contains
            if target == comparison or target in comparison:
                return text_item
        
        return None
