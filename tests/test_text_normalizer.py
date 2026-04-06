"""
Unit tests for TextNormalizer
"""
import unittest

from janus.io.stt.text_normalizer import TextNormalizer


class TestTextNormalizer(unittest.TestCase):
    """Test cases for TextNormalizer"""

    def setUp(self):
        """Set up test fixtures"""
        self.normalizer = TextNormalizer()

    def test_remove_fillers_french(self):
        """Test removal of French filler words"""
        text = "euh ouvre euh le navigateur"
        result = self.normalizer.normalize(text)

        self.assertNotIn("euh", result.lower())
        self.assertIn("ouvre", result.lower())
        self.assertIn("navigateur", result.lower())

    def test_remove_fillers_english(self):
        """Test removal of English filler words"""
        text = "um open like the browser you know"
        result = self.normalizer.normalize(text)

        self.assertNotIn("um", result.lower())
        self.assertNotIn("like", result.lower())
        self.assertNotIn("you know", result.lower())
        self.assertIn("open", result.lower())
        self.assertIn("browser", result.lower())

    def test_expand_contractions_french(self):
        """Test expansion of French contractions"""
        text = "j'ouvre l'application"
        result = self.normalizer.normalize(text)

        self.assertIn("je", result.lower())
        self.assertIn("le", result.lower())

    def test_expand_contractions_english(self):
        """Test expansion of English contractions"""
        text = "I'm opening the app, it's ready"
        result = self.normalizer.normalize(text)

        self.assertIn("i am", result.lower())
        self.assertIn("it is", result.lower())

    def test_normalize_whitespace(self):
        """Test whitespace normalization"""
        text = "ouvre   le    navigateur"
        result = self.normalizer.normalize(text)

        # Should have single spaces
        self.assertNotIn("  ", result)

    def test_fix_punctuation_spacing(self):
        """Test fixing punctuation spacing"""
        text = "ouvre le navigateur ,ferme la fenêtre ."
        result = self.normalizer.normalize(text)

        # Should have proper punctuation spacing
        self.assertIn(",", result)
        self.assertNotIn(" ,", result)
        self.assertNotIn(" .", result)

    def test_fix_capitalization(self):
        """Test capitalization fixes"""
        text = "ouvre le navigateur. ferme la fenêtre"
        result = self.normalizer.normalize(text)

        # First letter should be capitalized
        self.assertTrue(result[0].isupper())

        # Letter after period should be capitalized
        self.assertIn(". F", result)

    def test_clean_command_text(self):
        """Test specialized command cleaning"""
        text = "euh ouvre le, navigateur chrome."
        result = self.normalizer.clean_command_text(text)

        # Should be lowercase
        self.assertTrue(result.islower() or not result)

        # Should not have punctuation
        self.assertNotIn(",", result)
        self.assertNotIn(".", result)

        # Should not have fillers
        self.assertNotIn("euh", result)

    def test_remove_repetitions(self):
        """Test removal of word repetitions"""
        text = "ouvre ouvre le navigateur"
        result = self.normalizer.remove_repetitions(text)

        # Should only have one "ouvre"
        words = result.split()
        ouvre_count = sum(1 for w in words if w.lower() == "ouvre")
        self.assertEqual(ouvre_count, 1)

    def test_normalize_numbers_french(self):
        """Test number normalization in French"""
        text = "ouvre trois fenêtres et ferme cinq onglets"
        result = self.normalizer.normalize_numbers(text)

        self.assertIn("3", result)
        self.assertIn("5", result)
        self.assertNotIn("trois", result)
        self.assertNotIn("cinq", result)

    def test_normalize_numbers_english(self):
        """Test number normalization in English"""
        text = "open five windows and close ten tabs"
        result = self.normalizer.normalize_numbers(text)

        self.assertIn("5", result)
        self.assertIn("10", result)
        self.assertNotIn("five", result)
        self.assertNotIn("ten", result)

    def test_full_normalization_pipeline(self):
        """Test complete normalization pipeline"""
        text = "euh j'ouvre euh trois fenêtres. ferme l'application"
        result = self.normalizer.normalize(text)

        # Should be well-formed
        self.assertTrue(result[0].isupper())  # Capitalized
        self.assertNotIn("euh", result.lower())  # No fillers
        self.assertIn("je", result.lower())  # Expanded contractions

    def test_empty_text(self):
        """Test handling of empty text"""
        result = self.normalizer.normalize("")
        self.assertEqual(result, "")

    def test_disable_features(self):
        """Test disabling specific features"""
        normalizer = TextNormalizer(
            remove_fillers=False,
            expand_contractions=False,
            normalize_whitespace=True,
            fix_capitalization=True,
        )

        text = "euh j'ouvre le navigateur"
        result = normalizer.normalize(text)

        # Fillers should still be present
        self.assertIn("euh", result.lower())

        # Contractions should still be present
        self.assertIn("j'", result.lower())

        # But capitalization should be fixed
        self.assertTrue(result[0].isupper())

    def test_preserve_important_words(self):
        """Test that important words are preserved"""
        text = "ouvre vscode et chrome"
        result = self.normalizer.normalize(text)

        self.assertIn("vscode", result.lower())
        self.assertIn("chrome", result.lower())
        self.assertIn("ouvre", result.lower())


if __name__ == "__main__":
    unittest.main()
