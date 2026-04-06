"""
Linux OCR Engine - RapidOCR with ONNX Runtime

Uses RapidOCR with ONNX runtime for lightweight, CPU-optimized OCR on Linux.

Performance:
- RAM Overhead: ~50-80 MB (ONNX model in memory)
- Latency: 150-300ms on CPU
- Good balance between speed and accuracy for server/Docker environments

Requirements:
- rapidocr_onnxruntime package
"""

import io
import logging
from typing import List, Union

import numpy as np
from PIL import Image

from .interface import OCREngine, OCRResult

logger = logging.getLogger(__name__)

# Constants
CONFIDENCE_SCALE = 100.0  # Convert RapidOCR confidence (0-1) to percentage (0-100)


class LinuxEngine(OCREngine):
    """
    Linux OCR using RapidOCR with ONNX runtime
    
    This engine uses RapidOCR which provides:
    - Fast CPU-based text recognition
    - Good accuracy without GPU
    - Lightweight ONNX models
    - Suitable for Docker/server deployments
    """
    
    def __init__(self):
        """Initialize RapidOCR engine"""
        self._available = False
        self._ocr_engine = None
        self._initialized = False
        
    def initialize(self) -> None:
        """Lazy initialization of RapidOCR"""
        if self._initialized:
            return
            
        if not self.is_available():
            raise RuntimeError("RapidOCR not available on this platform")
        
        try:
            from rapidocr_onnxruntime import RapidOCR
            
            # Initialize with default parameters optimized for performance
            self._ocr_engine = RapidOCR()
            self._initialized = True
            
            logger.info("✓ RapidOCR (ONNX) initialized for Linux")
            
        except ImportError as e:
            logger.error(f"Failed to import RapidOCR: {e}")
            raise RuntimeError(
                "RapidOCR not available. Install with: pip install rapidocr_onnxruntime"
            )
        except Exception as e:
            logger.error(f"Failed to initialize RapidOCR: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if RapidOCR is available"""
        if self._available:
            return True
        
        try:
            import rapidocr_onnxruntime
            self._available = True
            return True
        except ImportError:
            logger.debug("RapidOCR not available (install rapidocr_onnxruntime)")
            return False
    
    def process_image(self, image: Union[Image.Image, str, bytes]) -> List[OCRResult]:
        """
        Process image using RapidOCR
        
        Args:
            image: PIL Image, file path, or image bytes
        
        Returns:
            List of OCRResult objects with detected text
        """
        if not self._initialized:
            self.initialize()
        
        # Convert input to format RapidOCR can handle
        if isinstance(image, Image.Image):
            # RapidOCR can work with PIL Image directly or numpy array
            image_input = np.array(image)
        elif isinstance(image, str):
            # File path - RapidOCR can handle this directly
            image_input = image
        elif isinstance(image, bytes):
            # Convert bytes to PIL Image first, then to numpy
            pil_image = Image.open(io.BytesIO(image))
            image_input = np.array(pil_image)
        else:
            logger.error(f"Unsupported image type: {type(image)}")
            return []
        
        try:
            # Run OCR
            # RapidOCR returns: (dt_boxes, rec_res, time_dict)
            # where rec_res is a list of (text, confidence) tuples
            result, elapse = self._ocr_engine(image_input)
            
            if not result:
                logger.debug("No text found in image")
                return []
            
            # Parse results into OCRResult objects
            results = []
            
            for item in result:
                # RapidOCR returns: [box_coords, (text, confidence)]
                # box_coords is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                box_coords = item[0]
                text = item[1]
                confidence = item[2] * CONFIDENCE_SCALE  # Convert to 0-100
                
                # Convert box coordinates to (x, y, width, height)
                # box_coords is a 4-point polygon, we need bounding box
                xs = [point[0] for point in box_coords]
                ys = [point[1] for point in box_coords]
                
                x = int(min(xs))
                y = int(min(ys))
                width = int(max(xs) - x)
                height = int(max(ys) - y)
                
                results.append(OCRResult(
                    text=text,
                    confidence=confidence,
                    bbox=(x, y, width, height)
                ))
            
            logger.debug(f"RapidOCR found {len(results)} text regions")
            return results
            
        except Exception as e:
            logger.error(f"Error during RapidOCR processing: {e}", exc_info=True)
            return []
    
    def shutdown(self) -> None:
        """Clean up resources"""
        self._initialized = False
        self._ocr_engine = None
        logger.debug("RapidOCR shut down")
