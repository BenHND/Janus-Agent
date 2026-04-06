"""
OCR Adapter - Compatibility layer for new native OCR engines

This module provides a compatibility adapter that makes the new platform-native
OCR engines work with existing code that expects the old OCREngine interface.

TICKET-OCR-NATIVE: This adapter allows gradual migration from the old monolithic
OCR system to the new platform-specific factory system.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

from .ocr.factory import get_ocr_engine
from .ocr.interface import OCRResult as NativeOCRResult

logger = logging.getLogger(__name__)


class OCRResult:
    """
    Compatibility wrapper for OCRResult
    
    This class maintains the same interface as the old OCRResult class
    while using the new native OCR results internally.
    """
    
    def __init__(
        self, 
        text: str, 
        confidence: float, 
        bbox: Optional[Tuple[int, int, int, int]] = None
    ):
        """
        Initialize OCR result
        
        Args:
            text: Recognized text
            confidence: Confidence score (0-100)
            bbox: Bounding box as (x, y, width, height)
        """
        self.text = text
        self.confidence = confidence
        self.bbox = bbox
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bbox": self.bbox
        }


class NativeOCRAdapter:
    """
    Adapter that provides the old OCREngine interface using new native engines
    
    This class wraps the new platform-native OCR factory and provides the same
    interface as the old OCREngine class, ensuring backward compatibility.
    
    TICKET-OCR-NATIVE: This is the bridge between old and new OCR systems.
    """
    
    def __init__(
        self,
        backend: str = "auto",
        language: str = "eng",
        enable_async: bool = False,
        max_workers: int = 2,
        enable_cache: bool = True,
        cache_ttl: int = 3,
    ):
        """
        Initialize native OCR adapter
        
        Args:
            backend: Backend selection ("auto" uses factory, "tesseract" forces Tesseract)
            language: Language code (currently only used for Tesseract fallback)
            enable_async: Legacy parameter (ignored, kept for compatibility)
            max_workers: Legacy parameter (ignored, kept for compatibility)
            enable_cache: Whether to enable caching (currently not implemented)
            cache_ttl: Cache TTL in seconds (currently not implemented)
        """
        self.backend = backend
        self.language = language
        
        # Initialize the native OCR engine using factory
        if backend == "auto" or backend == "native":
            # Use the factory to get the platform-specific OCR engine
            # No fallback - fail fast if native engine not available
            self._engine = get_ocr_engine()
            self._engine.initialize()
            logger.info("✓ Native OCR adapter initialized with platform-specific engine")
        elif backend == "tesseract":
            # Legacy tesseract backend no longer supported
            raise ValueError(
                "Tesseract backend is no longer supported. "
                "Please use 'auto' or 'native' backend for platform-specific OCR."
            )
        else:
            raise ValueError(f"Unsupported backend: {backend}")
        
        # Cache support (TODO: implement caching in native engines)
        self.enable_cache = enable_cache
        self._cache = None
    
    def recognize_text(self, image: Image.Image) -> str:
        """
        Recognize all text in an image
        
        Args:
            image: PIL Image to process
        
        Returns:
            Recognized text as string
        """
        return self._engine.recognize_text(image)
    
    def find_text(
        self,
        image: Image.Image,
        search_text: str,
        case_sensitive: bool = False
    ) -> List[OCRResult]:
        """
        Find specific text in an image and return its location
        
        Args:
            image: PIL Image to search
            search_text: Text to find
            case_sensitive: Whether search should be case sensitive
        
        Returns:
            List of OCRResult objects with matches
        """
        # Use native engine's find_text
        native_results = self._engine.find_text(image, search_text, case_sensitive)
        
        # Convert to old OCRResult format
        return [
            OCRResult(r.text, r.confidence, r.bbox)
            for r in native_results
        ]
    
    def get_all_text_with_boxes(self, image: Image.Image) -> List[OCRResult]:
        """
        Get all text with bounding boxes from an image
        
        Args:
            image: PIL Image
        
        Returns:
            List of OCRResult objects with all detected text
        """
        # Use native engine's process_image
        native_results = self._engine.process_image(image)
        
        # Convert to old OCRResult format
        return [
            OCRResult(r.text, r.confidence, r.bbox)
            for r in native_results
        ]
    
    def extract_text(self, image: Image.Image) -> Dict[str, Any]:
        """
        Extract all text with bounding boxes from an image
        
        Returns a dictionary format compatible with Set-of-Marks engine.
        
        Args:
            image: PIL Image
        
        Returns:
            Dictionary with:
            - texts: List of detected text strings
            - boxes: List of bounding boxes (x, y, width, height)
            - confidence: List of confidence scores
        """
        results = self.get_all_text_with_boxes(image)
        
        texts = []
        boxes = []
        confidences = []
        
        for result in results:
            texts.append(result.text)
            boxes.append(result.bbox)
            confidences.append(result.confidence)
        
        return {
            "texts": texts,
            "boxes": boxes,
            "confidence": confidences,
        }
    
    def shutdown(self):
        """
        Shutdown the OCR engine and cleanup resources
        """
        if self._engine:
            self._engine.shutdown()
