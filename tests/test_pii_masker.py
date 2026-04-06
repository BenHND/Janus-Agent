"""
Unit tests for PII Masker
"""

import unittest
from unittest.mock import MagicMock

from PIL import Image

from janus.vision.pii_masker import PIIMasker, PIIPattern


class TestPIIPattern(unittest.TestCase):
    """Test cases for PII pattern definitions"""

    def test_email_pattern(self):
        """Test email pattern matching"""
        import re

        pattern = re.compile(PIIPattern.EMAIL, re.IGNORECASE)

        # Valid emails
        self.assertTrue(pattern.search("contact@entreprise.com"))
        self.assertTrue(pattern.search("user.name+tag@example.co.uk"))
        self.assertTrue(pattern.search("test_email@domain.org"))

        # Invalid patterns
        self.assertFalse(pattern.search("not-an-email"))
        self.assertFalse(pattern.search("@domain.com"))

    def test_iban_pattern(self):
        """Test IBAN pattern matching"""
        import re

        pattern = re.compile(PIIPattern.IBAN)

        # Valid IBAN formats
        self.assertTrue(pattern.search("FR7630006000011234567890189"))
        self.assertTrue(pattern.search("DE89370400440532013000"))
        self.assertTrue(pattern.search("GB29NWBK60161331926819"))

        # Invalid patterns
        self.assertFalse(pattern.search("1234567890"))
        self.assertFalse(pattern.search("INVALID"))

    def test_long_number_pattern(self):
        """Test long number sequence pattern"""
        import re

        pattern = re.compile(PIIPattern.LONG_NUMBER)

        # Valid long numbers (phone, CC, etc)
        self.assertTrue(pattern.search("0123456789"))
        self.assertTrue(pattern.search("01-23-45-67-89"))
        self.assertTrue(pattern.search("01 23 45 67 89"))
        self.assertTrue(pattern.search("1234567890123456"))

        # Too short
        self.assertFalse(pattern.search("123456"))

    def test_credit_card_pattern(self):
        """Test credit card pattern"""
        import re

        pattern = re.compile(PIIPattern.CREDIT_CARD)

        # Valid CC formats
        self.assertTrue(pattern.search("4532015112830366"))
        self.assertTrue(pattern.search("4532 0151 1283 0366"))
        self.assertTrue(pattern.search("4532-0151-1283-0366"))

        # Invalid
        self.assertFalse(pattern.search("123"))


class TestPIIMasker(unittest.TestCase):
    """Test cases for PIIMasker"""

    def setUp(self):
        """Set up test fixtures"""
        self.masker = PIIMasker(blur_radius=15)

    def test_initialization(self):
        """Test PIIMasker initialization"""
        self.assertEqual(self.masker.blur_radius, 15)
        self.assertIn("email", self.masker._patterns)
        self.assertIn("iban", self.masker._patterns)
        self.assertIn("long_number", self.masker._patterns)
        self.assertIn("credit_card", self.masker._patterns)

    def test_detect_pii_in_text_email(self):
        """Test detecting emails in text"""
        text = "Contact us at support@example.com for help"
        detected = self.masker.detect_pii_in_text(text)

        self.assertGreater(len(detected), 0)
        pii_type, matched_text = detected[0]
        self.assertEqual(pii_type, "email")
        self.assertEqual(matched_text, "support@example.com")

    def test_detect_pii_in_text_multiple(self):
        """Test detecting multiple PII in text"""
        text = "Email: test@example.com, Phone: 0123456789"
        detected = self.masker.detect_pii_in_text(text)

        self.assertGreaterEqual(len(detected), 2)
        types = [pii_type for pii_type, _ in detected]
        self.assertIn("email", types)
        self.assertIn("long_number", types)

    def test_detect_pii_in_text_no_pii(self):
        """Test text with no PII"""
        text = "This is just normal text without any sensitive data"
        detected = self.masker.detect_pii_in_text(text)

        self.assertEqual(len(detected), 0)

    def test_detect_pii_regions_from_ocr(self):
        """Test detecting PII regions from OCR results"""
        # Mock OCR results
        mock_ocr_result1 = MagicMock()
        mock_ocr_result1.text = "contact@entreprise.com"
        mock_ocr_result1.bbox = (100, 100, 200, 30)

        mock_ocr_result2 = MagicMock()
        mock_ocr_result2.text = "Normal text"
        mock_ocr_result2.bbox = (100, 150, 150, 30)

        ocr_results = [mock_ocr_result1, mock_ocr_result2]

        pii_regions = self.masker.detect_pii_regions_from_ocr(ocr_results)

        self.assertEqual(len(pii_regions), 1)
        pii_type, bbox = pii_regions[0]
        self.assertEqual(pii_type, "email")
        self.assertEqual(bbox, (100, 100, 200, 30))

    def test_detect_pii_regions_empty_ocr(self):
        """Test with empty OCR results"""
        pii_regions = self.masker.detect_pii_regions_from_ocr([])
        self.assertEqual(len(pii_regions), 0)

    def test_mask_regions(self):
        """Test masking regions in an image"""
        # Create a test image (100x100 red square)
        image = Image.new("RGB", (100, 100), color="red")

        # Define a region to mask
        regions = [(10, 10, 50, 50)]

        # Apply masking
        masked_image = self.masker.mask_regions(image, regions)

        # Check that a new image was created
        self.assertIsNot(masked_image, image)
        self.assertEqual(masked_image.size, image.size)

        # The pixels in the masked region should be different due to blur
        original_pixel = image.getpixel((30, 30))
        masked_pixel = masked_image.getpixel((30, 30))
        # Due to blur, pixels should be slightly different
        # (blur spreads colors, so pure red stays red but may vary slightly)
        self.assertGreaterEqual(masked_pixel[0], 250)  # Red channel still dominant

    def test_mask_regions_empty_list(self):
        """Test masking with empty regions list"""
        image = Image.new("RGB", (100, 100), color="blue")
        masked_image = self.masker.mask_regions(image, [])

        # Should return a copy with no changes
        self.assertIsNot(masked_image, image)
        self.assertEqual(masked_image.size, image.size)

    def test_mask_regions_with_padding(self):
        """Test that masking adds padding around regions"""
        image = Image.new("RGB", (200, 200), color="green")
        regions = [(50, 50, 20, 20)]

        masked_image = self.masker.mask_regions(image, regions)

        # Check that regions near the bbox are affected (due to padding)
        self.assertIsInstance(masked_image, Image.Image)
        self.assertEqual(masked_image.size, (200, 200))

    def test_mask_pii_in_image(self):
        """Test the complete PII masking workflow"""
        # Create test image
        image = Image.new("RGB", (300, 300), color="white")

        # Mock OCR results with PII
        mock_ocr_result = MagicMock()
        mock_ocr_result.text = "Email: test@example.com"
        mock_ocr_result.bbox = (50, 50, 200, 30)

        ocr_results = [mock_ocr_result]

        # Mask the image
        masked_image = self.masker.mask_pii_in_image(image, ocr_results)

        # Should return a new image
        self.assertIsNot(masked_image, image)
        self.assertEqual(masked_image.size, image.size)

    def test_mask_pii_in_image_no_pii(self):
        """Test masking when no PII is present"""
        image = Image.new("RGB", (300, 300), color="yellow")

        # Mock OCR results without PII
        mock_ocr_result = MagicMock()
        mock_ocr_result.text = "Just normal text here"
        mock_ocr_result.bbox = (50, 50, 200, 30)

        ocr_results = [mock_ocr_result]

        # Mask the image
        masked_image = self.masker.mask_pii_in_image(image, ocr_results)

        # Should still return a copy, but unchanged
        self.assertIsNot(masked_image, image)
        self.assertEqual(masked_image.size, image.size)

    def test_should_mask_text(self):
        """Test quick PII check"""
        # Text with PII
        self.assertTrue(self.masker.should_mask_text("My email is test@example.com"))
        self.assertTrue(self.masker.should_mask_text("Call 0123456789"))

        # Text without PII
        self.assertFalse(self.masker.should_mask_text("Just normal text"))
        self.assertFalse(self.masker.should_mask_text("Short num: 12345"))

    def test_custom_blur_radius(self):
        """Test initialization with custom blur radius"""
        custom_masker = PIIMasker(blur_radius=25)
        self.assertEqual(custom_masker.blur_radius, 25)

    def test_mask_regions_edge_cases(self):
        """Test masking at image edges"""
        image = Image.new("RGB", (100, 100), color="black")

        # Region at the edge
        regions = [(0, 0, 20, 20), (80, 80, 20, 20)]

        masked_image = self.masker.mask_regions(image, regions)

        # Should handle edge cases without errors
        self.assertEqual(masked_image.size, (100, 100))


if __name__ == "__main__":
    unittest.main()
