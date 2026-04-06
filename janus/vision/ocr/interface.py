"""
OCR Interface - Abstract base class for platform-specific OCR engines

This module defines the contract that all OCR engines must implement,
ensuring consistent behavior across platforms.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

from PIL import Image


@dataclass
class OCRResult:
    """
    Unified OCR result container
    
    Attributes:
        text: Recognized text
        confidence: Confidence score (0-100)
        bbox: Bounding box as (x, y, width, height) - top-left corner coordinates
    """
    text: str
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None
    
    def to_dict(self):
        """Convert to dictionary for compatibility"""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bbox": self.bbox
        }


class OCREngine(ABC):
    """
    Abstract base class for OCR engines
    
    All platform-specific OCR implementations must inherit from this class
    and implement the required methods.
    
    Performance Target:
    - RAM Overhead: < 100 MB
    - Latency: < 200ms per image
    - Initialization: < 100ms (lazy loading)
    """
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize OCR engine resources
        
        This method should perform lazy loading of any heavy resources
        (models, frameworks, etc.) and should complete in < 100ms.
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this OCR engine is available on the current platform
        
        Returns:
            True if the engine can be used, False otherwise
        """
        pass
    
    @abstractmethod
    def process_image(
        self, 
        image: Union[Image.Image, str, bytes]
    ) -> List[OCRResult]:
        """
        Process an image and extract all text with bounding boxes
        
        This is the core OCR method that must complete in < 200ms.
        
        Args:
            image: PIL Image, file path, or image bytes
        
        Returns:
            List of OCRResult objects with detected text and bounding boxes
        """
        pass
    
    def recognize_text(self, image: Union[Image.Image, str, bytes]) -> str:
        """
        Recognize all text in an image (convenience method)
        
        Args:
            image: PIL Image, file path, or image bytes
        
        Returns:
            All recognized text as a single string
        """
        results = self.process_image(image)
        return " ".join(r.text for r in results)
    
    def find_text(
        self, 
        image: Union[Image.Image, str, bytes],
        search_text: str,
        case_sensitive: bool = False
    ) -> List[OCRResult]:
        """
        Find specific text in an image
        
        Args:
            image: PIL Image, file path, or image bytes
            search_text: Text to search for
            case_sensitive: Whether to do case-sensitive search
        
        Returns:
            List of OCRResult objects matching the search text
        """
        results = self.process_image(image)
        
        matches = []
        for result in results:
            text = result.text
            search = search_text
            
            if not case_sensitive:
                text = text.lower()
                search = search.lower()
            
            if search in text:
                matches.append(result)
        
        return matches
    
    def shutdown(self) -> None:
        """
        Clean up resources
        
        Override this method if your engine needs cleanup.
        """
        pass
