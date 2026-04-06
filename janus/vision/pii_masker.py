"""
PII Masker - Visual Data Leak Prevention
Detects and masks Personally Identifiable Information (PII) in screenshots
Ticket: TICKET-PRIV-001
"""

import re
from typing import List, Tuple

from PIL import Image, ImageFilter


class PIIPattern:
    """PII pattern definitions with regex patterns"""

    # Email pattern - matches common email formats
    EMAIL = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

    # IBAN pattern - European bank account numbers
    # Format: 2 letters (country) + 2 digits (check) + up to 30 alphanumeric
    IBAN = r"\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b"

    # Long number sequences (8+ digits) - potential phone numbers or credit cards
    # Matches sequences of 8 or more digits (with optional spaces/dashes)
    # Note: May match product codes, tracking numbers - context validation recommended
    LONG_NUMBER = r"\b\d[\d\s\-]{6,}\d\b"

    # Credit card pattern - more specific (13-19 digits with optional separators)
    CREDIT_CARD = r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4,7}\b"


class PIIMasker:
    """
    Utility for detecting and masking PII in images using OCR results.

    This class helps prevent data leaks by applying Gaussian blur to regions
    containing sensitive information before images are saved to disk.
    """

    def __init__(self, blur_radius: int = 15):
        """
        Initialize PII masker

        Args:
            blur_radius: Radius for Gaussian blur (larger = more blur)
        """
        self.blur_radius = blur_radius
        self._patterns = {
            "email": re.compile(PIIPattern.EMAIL, re.IGNORECASE),
            "iban": re.compile(PIIPattern.IBAN),
            "long_number": re.compile(PIIPattern.LONG_NUMBER),
            "credit_card": re.compile(PIIPattern.CREDIT_CARD),
        }

    def detect_pii_in_text(self, text: str) -> List[Tuple[str, str]]:
        """
        Detect PII patterns in text

        Args:
            text: Text to scan for PII

        Returns:
            List of tuples (pii_type, matched_text)
        """
        detected = []

        for pii_type, pattern in self._patterns.items():
            matches = pattern.findall(text)
            for match in matches:
                detected.append((pii_type, match))

        return detected

    def detect_pii_regions_from_ocr(
        self, ocr_results: List
    ) -> List[Tuple[str, Tuple[int, int, int, int]]]:
        """
        Detect PII regions from OCR results

        Args:
            ocr_results: List of OCRResult objects with text and bbox

        Returns:
            List of tuples (pii_type, bbox) where bbox is (x, y, width, height)
        """
        pii_regions = []

        for ocr_result in ocr_results:
            text = ocr_result.text if hasattr(ocr_result, "text") else str(ocr_result)
            bbox = ocr_result.bbox if hasattr(ocr_result, "bbox") else None

            if not bbox or not text:
                continue

            # Check if this text contains PII
            pii_matches = self.detect_pii_in_text(text)

            if pii_matches:
                # Found PII - add this region for masking
                pii_type = pii_matches[0][0]  # Use first match type
                pii_regions.append((pii_type, bbox))

        return pii_regions

    def mask_regions(
        self, image: Image.Image, regions: List[Tuple[int, int, int, int]]
    ) -> Image.Image:
        """
        Apply Gaussian blur to specific regions of an image

        Args:
            image: PIL Image to mask
            regions: List of bounding boxes (x, y, width, height) to blur

        Returns:
            New PIL Image with masked regions
        """
        # Create a copy to avoid modifying the original
        masked_image = image.copy()

        for region in regions:
            x, y, width, height = region

            # Add padding to ensure coverage (5px on each side)
            padding = 5
            x = max(0, x - padding)
            y = max(0, y - padding)
            width = min(masked_image.width - x, width + 2 * padding)
            height = min(masked_image.height - y, height + 2 * padding)

            # Extract the region
            box = (x, y, x + width, y + height)
            region_img = masked_image.crop(box)

            # Apply Gaussian blur
            blurred_region = region_img.filter(ImageFilter.GaussianBlur(radius=self.blur_radius))

            # Paste back the blurred region
            masked_image.paste(blurred_region, (x, y))

        return masked_image

    def mask_pii_in_image(self, image: Image.Image, ocr_results: List) -> Image.Image:
        """
        Detect and mask PII in an image using OCR results

        This is the main method combining detection and masking.

        Args:
            image: PIL Image to process
            ocr_results: List of OCRResult objects from OCR engine

        Returns:
            New PIL Image with PII regions blurred
        """
        # Detect PII regions
        pii_regions = self.detect_pii_regions_from_ocr(ocr_results)

        if not pii_regions:
            # No PII found, return a copy of original
            return image.copy()

        # Extract just the bounding boxes for masking
        regions_to_mask = [bbox for _, bbox in pii_regions]

        # Apply masking
        return self.mask_regions(image, regions_to_mask)

    def should_mask_text(self, text: str) -> bool:
        """
        Quick check if text contains PII

        Args:
            text: Text to check

        Returns:
            True if PII detected, False otherwise
        """
        return len(self.detect_pii_in_text(text)) > 0
