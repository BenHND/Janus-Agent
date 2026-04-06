"""
macOS OCR Engine - Apple Vision Framework

Uses macOS's native Vision.framework for fast, GPU-accelerated OCR.

Performance:
- RAM Overhead: ~10-20 MB (native framework, minimal Python overhead)
- Latency: 50-100ms on M-series chips
- No model loading time (uses built-in Neural Engine)

Requirements:
- macOS 10.13+ (High Sierra or later)
- pyobjc-framework-Vision
- pyobjc-framework-Quartz
"""

import io
import logging
import platform
from typing import List, Union

from PIL import Image

from .interface import OCREngine, OCRResult

logger = logging.getLogger(__name__)

# Constants
CONFIDENCE_SCALE = 100.0  # Convert Vision framework confidence (0-1) to percentage (0-100)


class MacOSEngine(OCREngine):
    """
    Native macOS OCR using Vision.framework
    
    This engine uses the built-in macOS Vision framework which provides:
    - Fast GPU-accelerated text recognition via Neural Engine
    - High accuracy for printed text
    - No external dependencies or model downloads
    - Minimal memory footprint
    """
    
    def __init__(self, recognition_level: str = "accurate"):
        """
        Initialize macOS OCR engine
        
        Args:
            recognition_level: "fast" for real-time, "accurate" for quality (default)
        """
        self.recognition_level = recognition_level
        self._available = False
        self._vision = None
        self._quartz = None
        self._cocoa = None
        self._initialized = False
        
    def initialize(self) -> None:
        """Lazy initialization of Vision framework"""
        if self._initialized:
            return
            
        if not self.is_available():
            raise RuntimeError("macOS Vision framework not available on this platform")
        
        try:
            import Vision
            import Quartz
            from Cocoa import NSData, NSURL
            from Foundation import NSDictionary
            
            self._vision = Vision
            self._quartz = Quartz
            self._cocoa = (NSData, NSURL, NSDictionary)
            self._initialized = True
            
            logger.info("✓ macOS Vision OCR initialized (Neural Engine acceleration)")
            
        except ImportError as e:
            logger.error(f"Failed to import Vision framework: {e}")
            raise RuntimeError(
                "Vision framework not available. Install with: "
                "pip install pyobjc-framework-Vision pyobjc-framework-Quartz"
            )
    
    def is_available(self) -> bool:
        """Check if Vision framework is available"""
        if self._available:
            return True
            
        if platform.system() != "Darwin":
            logger.debug("Not on macOS, Vision framework not available")
            return False
        
        try:
            import Vision
            self._available = True
            return True
        except ImportError:
            logger.debug("Vision framework not available (install pyobjc-framework-Vision)")
            return False
    
    def process_image(self, image: Union[Image.Image, str, bytes]) -> List[OCRResult]:
        """
        Process image using Vision framework
        
        Args:
            image: PIL Image, file path, or image bytes
        
        Returns:
            List of OCRResult objects with detected text
        """
        if not self._initialized:
            self.initialize()
        
        # Convert input to PIL Image if needed
        if isinstance(image, str):
            image = Image.open(image)
        elif isinstance(image, bytes):
            image = Image.open(io.BytesIO(image))
        
        try:
            import objc
            from Foundation import NSDictionary
            
            NSData, NSURL, _ = self._cocoa
            
            # Convert PIL Image to NSData (PNG format)
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_data = buffer.getvalue()
            ns_data = NSData.dataWithBytes_length_(image_data, len(image_data))
            
            # Create CGImage from NSData
            data_provider = self._quartz.CGDataProviderCreateWithCFData(ns_data)
            cg_image = self._quartz.CGImageCreateWithPNGDataProvider(
                data_provider, None, False, self._quartz.kCGRenderingIntentDefault
            )
            
            if not cg_image:
                logger.error("Failed to create CGImage from image data")
                return []
            
            # Create Vision request handler
            request_handler = self._vision.VNImageRequestHandler.alloc().initWithCGImage_options_(
                cg_image, NSDictionary.dictionary()
            )
            
            # Create text recognition request
            request = self._vision.VNRecognizeTextRequest.alloc().init()
            
            # Set recognition level
            if self.recognition_level == "fast":
                request.setRecognitionLevel_(self._vision.VNRequestTextRecognitionLevelFast)
            else:
                request.setRecognitionLevel_(self._vision.VNRequestTextRecognitionLevelAccurate)
            
            # Perform request
            success = request_handler.performRequests_error_([request], objc.nil)
            
            if not success:
                logger.error("Vision text recognition request failed")
                return []
            
            # Extract results
            observations = request.results()
            if not observations:
                logger.debug("No text found in image")
                return []
            
            # Parse observations into OCRResult objects
            results = []
            img_width, img_height = image.size
            
            for observation in observations:
                # Get recognized text and confidence
                top_candidate = observation.topCandidates_(1)[0]
                text = top_candidate.string()
                confidence = top_candidate.confidence() * CONFIDENCE_SCALE  # Convert to 0-100
                
                # Get bounding box (normalized coordinates, origin bottom-left)
                bbox = observation.boundingBox()
                
                # Convert from Vision's coordinate system (origin bottom-left)
                # to standard top-left origin
                x = int(bbox.origin.x * img_width)
                y = int((1.0 - bbox.origin.y - bbox.size.height) * img_height)
                width = int(bbox.size.width * img_width)
                height = int(bbox.size.height * img_height)
                
                results.append(OCRResult(
                    text=text,
                    confidence=confidence,
                    bbox=(x, y, width, height)
                ))
            
            logger.debug(f"Vision OCR found {len(results)} text regions")
            return results
            
        except Exception as e:
            logger.error(f"Error during Vision OCR processing: {e}", exc_info=True)
            return []
    
    def shutdown(self) -> None:
        """Clean up resources (Vision framework handles this automatically)"""
        self._initialized = False
        logger.debug("macOS Vision OCR shut down")
