"""
VisualErrorDetector - Detect visual errors on screen using OmniParser
TICKET-CLEANUP-VISION: Migrated from Florence-2 to OmniParser

Detects common error patterns:
- Error dialogs
- 404 pages
- Crash reports
- Warning messages
"""

import logging
from typing import Any, Dict, List, Optional

from PIL import Image

logger = logging.getLogger(__name__)


class VisualErrorDetector:
    """
    Detect visual error indicators on screen using OmniParser.
    
    TICKET-CLEANUP-VISION: Uses OmniParser (includes Florence-2), no duplicate models.

    Features:
    - Common error pattern detection (404, crash, etc.)
    - Multi-language error detection
    - Confidence scoring
    - Integration with OmniParser vision AI and OCR
    """

    # Error patterns to detect
    ERROR_PATTERNS = {
        "404": ["404", "not found", "page not found", "page introuvable"],
        "500": ["500", "internal server error", "erreur serveur"],
        "crash": ["crash", "crashed", "has stopped", "ne répond pas", "application quit"],
        "connection": [
            "connection failed",
            "no connection",
            "connexion échouée",
            "pas de connexion",
        ],
        "timeout": ["timeout", "timed out", "délai dépassé"],
        "error": ["error", "erreur", "fehler"],
        "warning": ["warning", "avertissement"],
        "exception": ["exception", "uncaught", "traceback"],
    }

    def __init__(self, use_vision_ai: bool = True, ocr_engine=None):
        """
        Initialize Visual Error Detector with OmniParser.

        Args:
            use_vision_ai: Whether to use OmniParser vision AI
            ocr_engine: Optional OCREngine instance
        """
        self.use_vision_ai = use_vision_ai
        self.vision_engine = None
        self._ocr_engine = ocr_engine

        if use_vision_ai:
            self._init_vision_engine()

    def _init_vision_engine(self):
        """Initialize OmniParser vision engine (replaces Florence-2)."""
        try:
            from .omniparser_adapter import OmniParserVisionEngine
            
            self.vision_engine = OmniParserVisionEngine(lazy_load=True)
            logger.info("VisualErrorDetector using OmniParser vision engine")
        except ImportError as e:
            logger.warning(f"OmniParser not available: {e}, using OCR fallback")
            self.vision_engine = None
        except Exception as e:
            logger.warning(f"Could not initialize OmniParser: {e}, using OCR fallback")
            self.vision_engine = None

    def detect(self, image: Image.Image, ocr_texts: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Detect errors in image

        Args:
            image: PIL Image to analyze
            ocr_texts: Optional pre-extracted OCR texts

        Returns:
            Dictionary with:
            - has_error: Boolean indicating error presence
            - error_type: Type of error (404, crash, etc.)
            - confidence: Detection confidence (0-1)
            - details: Additional details about the error
            - detected_texts: Texts that triggered detection
        """
        detected_errors = []
        max_confidence = 0.0
        detected_texts = []

        # Method 1: Use vision AI if available
        if self.vision_engine:
            vision_result = self.vision_engine.detect_errors(image)
            if vision_result.get("has_error"):
                detected_errors.append(
                    {
                        "type": vision_result.get("error_type", "unknown"),
                        "confidence": vision_result.get("confidence", 0.5),
                        "method": "vision_ai",
                    }
                )
                max_confidence = max(max_confidence, vision_result.get("confidence", 0))

        # Method 2: Check OCR texts for error patterns
        if ocr_texts:
            for error_type, patterns in self.ERROR_PATTERNS.items():
                for text in ocr_texts:
                    text_lower = text.lower()
                    for pattern in patterns:
                        if pattern in text_lower:
                            confidence = self._calculate_confidence(text, pattern)
                            detected_errors.append(
                                {
                                    "type": error_type,
                                    "confidence": confidence,
                                    "method": "ocr",
                                    "text": text,
                                }
                            )
                            detected_texts.append(text)
                            max_confidence = max(max_confidence, confidence)

        # Method 3: Extract OCR if not provided
        if not ocr_texts and not self.vision_engine:
            ocr_texts = self._extract_ocr(image)
            if ocr_texts:
                return self.detect(image, ocr_texts)

        # Determine final result
        has_error = len(detected_errors) > 0

        # Get most confident error type
        error_type = None
        if detected_errors:
            most_confident = max(detected_errors, key=lambda x: x["confidence"])
            error_type = most_confident["type"]

        return {
            "has_error": has_error,
            "error_type": error_type,
            "confidence": max_confidence,
            "details": detected_errors,
            "detected_texts": list(set(detected_texts)),
        }

    def is_error_page(self, image: Image.Image) -> bool:
        """
        Quick check if image shows an error page

        Args:
            image: PIL Image to check

        Returns:
            Boolean indicating if page appears to be an error
        """
        result = self.detect(image)
        return result["has_error"] and result["confidence"] > 0.5

    def detect_specific_error(
        self, image: Image.Image, error_type: str, ocr_texts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detect specific error type

        Args:
            image: PIL Image to analyze
            error_type: Specific error type to look for (404, crash, etc.)
            ocr_texts: Optional pre-extracted OCR texts

        Returns:
            Dictionary with detection results for specific error type
        """
        if error_type not in self.ERROR_PATTERNS:
            return {
                "found": False,
                "confidence": 0.0,
                "message": f"Unknown error type: {error_type}",
            }

        patterns = self.ERROR_PATTERNS[error_type]

        # Get OCR texts if not provided
        if not ocr_texts:
            ocr_texts = self._extract_ocr(image)

        # Search for patterns
        found_texts = []
        max_confidence = 0.0

        for text in ocr_texts:
            text_lower = text.lower()
            for pattern in patterns:
                if pattern in text_lower:
                    confidence = self._calculate_confidence(text, pattern)
                    found_texts.append(text)
                    max_confidence = max(max_confidence, confidence)

        return {
            "found": len(found_texts) > 0,
            "confidence": max_confidence,
            "matched_texts": found_texts,
            "patterns": patterns,
        }

    def _calculate_confidence(self, text: str, pattern: str) -> float:
        """
        Calculate confidence score for pattern match

        Args:
            text: Full text containing pattern
            pattern: Matched pattern

        Returns:
            Confidence score (0-1)
        """
        text_lower = text.lower()
        pattern_lower = pattern.lower()

        # Base confidence
        confidence = 0.6

        # Boost if pattern is exact match
        if text_lower == pattern_lower:
            confidence = 0.95
        # Boost if pattern is prominent in text
        elif len(pattern) / max(len(text), 1) > 0.5:
            confidence = 0.85
        # Boost if pattern appears multiple times
        elif text_lower.count(pattern_lower) > 1:
            confidence = 0.75

        return confidence

    def _extract_ocr(self, image: Image.Image) -> List[str]:
        """
        Extract text from image using OCR

        Args:
            image: PIL Image to extract text from

        Returns:
            List of extracted text strings
        """
        try:
            from .native_ocr_adapter import NativeOCRAdapter

            ocr_engine = NativeOCRAdapter(backend="auto")
            result = ocr_engine.extract_text(image)

            if result and "texts" in result:
                return [t.strip() for t in result["texts"] if t.strip()]

        except Exception as e:
            logger.warning(f"OCR extraction failed: {e}")

        return []

    def get_supported_error_types(self) -> List[str]:
        """Get list of supported error types"""
        return list(self.ERROR_PATTERNS.keys())

    def add_error_pattern(self, error_type: str, patterns: List[str]):
        """
        Add custom error pattern

        Args:
            error_type: Type of error
            patterns: List of text patterns to detect
        """
        if error_type in self.ERROR_PATTERNS:
            # Extend existing patterns
            self.ERROR_PATTERNS[error_type].extend(patterns)
        else:
            # Add new error type
            self.ERROR_PATTERNS[error_type] = patterns

        logger.info(f"Added error pattern: {error_type} with {len(patterns)} patterns")
