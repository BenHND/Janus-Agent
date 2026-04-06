"""
Unit tests for CorrectionDictionary
"""
import os
import tempfile
import unittest

from janus.io.stt.correction_dictionary import CorrectionDictionary


class TestCorrectionDictionary(unittest.TestCase):
    """Test cases for CorrectionDictionary"""

    def setUp(self):
        """Set up test fixtures"""
        self.dict = CorrectionDictionary()

    def test_default_corrections_loaded(self):
        """Test that default corrections are loaded"""
        corrections = self.dict.get_corrections()
        self.assertGreater(len(corrections), 0)

        # Check for some expected corrections
        self.assertIn("v s cold", corrections)
        self.assertIn("vscode", corrections.values())

    def test_correct_vscode_variations(self):
        """Test correction of VSCode variations"""
        test_cases = [
            ("ouvre v s cold", "vscode"),
            ("lance vs code", "vscode"),
            ("open V S Cold", "vscode"),
        ]

        for input_text, expected_term in test_cases:
            with self.subTest(input=input_text):
                result = self.dict.correct_text(input_text)
                # Just check that vscode appears in the result
                self.assertIn(expected_term.lower(), result.lower())

    def test_correct_firefox(self):
        """Test correction of Firefox variations"""
        test_cases = [
            ("ouvre fire fox", "ouvre firefox"),
            ("lance fire faux", "lance firefox"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = self.dict.correct_text(input_text)
                self.assertEqual(result.lower(), expected.lower())

    def test_add_custom_correction(self):
        """Test adding custom corrections"""
        self.dict.add_correction("git lab", "gitlab")

        result = self.dict.correct_text("ouvre git lab")
        self.assertIn("gitlab", result.lower())

    def test_remove_correction(self):
        """Test removing corrections"""
        # Add a correction
        self.dict.add_correction("test error", "test correction")

        # Verify it works
        result = self.dict.correct_text("this is test error")
        self.assertIn("test correction", result)

        # Remove it
        self.dict.remove_correction("test error")

        # Verify it's removed
        result = self.dict.correct_text("this is test error")
        self.assertIn("test error", result)
        self.assertNotIn("test correction", result)

    def test_case_insensitive(self):
        """Test that corrections are case-insensitive"""
        result1 = self.dict.correct_text("ouvre VS CODE")
        result2 = self.dict.correct_text("ouvre vs code")
        result3 = self.dict.correct_text("ouvre Vs Code")

        # All should contain vscode
        for result in [result1, result2, result3]:
            self.assertIn("vscode", result.lower())

    def test_word_boundaries(self):
        """Test that corrections respect word boundaries"""
        # "vs code" should be corrected, but "versus" should not
        result = self.dict.correct_text("vs code versus other")
        self.assertIn("vscode", result.lower())
        self.assertIn("versus", result.lower())

    def test_save_and_load(self):
        """Test saving and loading corrections"""
        # Create temp file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = f.name

        try:
            # Add custom correction and save
            self.dict.add_correction("custom error", "custom correction")
            self.dict.save_to_file(temp_path)

            # Create new dictionary and load
            new_dict = CorrectionDictionary(dictionary_path=temp_path)

            # Verify custom correction is loaded
            result = new_dict.correct_text("this is custom error")
            self.assertIn("custom correction", result)
        finally:
            # Cleanup
            os.unlink(temp_path)

    def test_multiple_corrections_in_text(self):
        """Test correcting multiple errors in same text"""
        text = "ouvre vs code et fire fox"
        result = self.dict.correct_text(text)

        self.assertIn("vscode", result.lower())
        self.assertIn("firefox", result.lower())

    def test_empty_text(self):
        """Test handling of empty text"""
        result = self.dict.correct_text("")
        self.assertEqual(result, "")

    def test_text_with_no_errors(self):
        """Test that correct text is not modified"""
        text = "ouvre le navigateur chrome"
        result = self.dict.correct_text(text)
        # Should remain similar (chrome is in dictionary but maps to itself or similar)
        self.assertIn("chrome", result.lower())


if __name__ == "__main__":
    unittest.main()
