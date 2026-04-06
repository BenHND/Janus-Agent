"""
Tests for Phase 15.5 - Semantic Correction
Checks correction of raw vs. improved transcript
"""
import unittest

from janus.io.stt.semantic_corrector import SimpleSemanticCorrector


class TestSemanticCorrection(unittest.TestCase):
    """Test cases for semantic correction (Phase 15.5)"""

    def setUp(self):
        """Set up test fixtures"""
        # Use SimpleSemanticCorrector since it doesn't require LLM
        self.corrector = SimpleSemanticCorrector()

    def test_initialization(self):
        """Test corrector initialization"""
        self.assertIsNotNone(self.corrector)
        self.assertEqual(self.corrector.total_corrections, 0)

    def test_remove_filler_words_english(self):
        """Test removal of English filler words"""
        raw = "um I want to uh open the browser"

        result = self.corrector.correct_transcript(raw, language="en")

        self.assertNotIn("um", result["corrected"].lower())
        self.assertNotIn("uh", result["corrected"].lower())
        self.assertIn("want", result["corrected"].lower())
        self.assertIn("open", result["corrected"].lower())
        self.assertIn("browser", result["corrected"].lower())

    def test_remove_filler_words_french(self):
        """Test removal of French filler words"""
        raw = "euh je veux euh ouvrir le navigateur"

        result = self.corrector.correct_transcript(raw, language="fr")

        self.assertNotIn("euh", result["corrected"].lower())
        self.assertIn("je", result["corrected"].lower())
        self.assertIn("veux", result["corrected"].lower())
        self.assertIn("ouvrir", result["corrected"].lower())

    def test_capitalization(self):
        """Test basic capitalization"""
        raw = "open the browser window"

        result = self.corrector.correct_transcript(raw, language="en")

        # First letter should be capitalized
        self.assertTrue(result["corrected"][0].isupper())

    def test_result_structure(self):
        """Test that result has expected structure"""
        raw = "test transcript"

        result = self.corrector.correct_transcript(raw, language="en")

        self.assertIn("corrected", result)
        self.assertIn("raw", result)
        self.assertIn("model_used", result)
        self.assertIn("tokens_used", result)

        self.assertEqual(result["raw"], raw)
        self.assertFalse(result["model_used"])
        self.assertEqual(result["tokens_used"], 0)

    def test_empty_text(self):
        """Test handling of empty text"""
        raw = ""

        result = self.corrector.correct_transcript(raw, language="en")

        self.assertEqual(result["corrected"], "")
        self.assertEqual(result["raw"], "")

    def test_text_with_no_fillers(self):
        """Test text without filler words"""
        raw = "open the browser"

        result = self.corrector.correct_transcript(raw, language="en")

        # Should still process (capitalize, etc.)
        self.assertTrue(result["corrected"][0].isupper())

    def test_multiple_fillers(self):
        """Test removal of multiple filler words"""
        raw = "um like I um want to like open it"

        result = self.corrector.correct_transcript(raw, language="en")

        # Single-word fillers should be removed
        corrected_lower = result["corrected"].lower()
        self.assertNotIn("um", corrected_lower)
        self.assertNotIn("like", corrected_lower)
        # Note: "you know" is a phrase and requires more sophisticated handling

    def test_french_fillers_comprehensive(self):
        """Test comprehensive French filler removal"""
        raw = "bah euh genre je veux ben ouvrir quoi le navigateur voilà"

        result = self.corrector.correct_transcript(raw, language="fr")

        corrected_lower = result["corrected"].lower()
        # French fillers should be removed
        for filler in ["bah", "euh", "genre", "ben", "quoi", "voilà"]:
            self.assertNotIn(filler, corrected_lower)

        # Content words should remain
        self.assertIn("je", corrected_lower)
        self.assertIn("veux", corrected_lower)
        self.assertIn("ouvrir", corrected_lower)

    def test_statistics_tracking(self):
        """Test that statistics are tracked"""
        initial_count = self.corrector.total_corrections

        self.corrector.correct_transcript("test", language="en")
        self.corrector.correct_transcript("test2", language="fr")

        stats = self.corrector.get_statistics()

        self.assertEqual(stats["total_corrections"], initial_count + 2)
        self.assertFalse(stats["model_loaded"])
        self.assertIsNone(stats["model_path"])

    def test_async_correction(self):
        """Test async correction (should work same as sync for simple corrector)"""
        import asyncio

        raw = "um test text"

        async def test_async():
            result = await self.corrector.correct_transcript_async(raw, language="en")
            return result

        result = asyncio.run(test_async())

        self.assertIn("corrected", result)
        self.assertNotIn("um", result["corrected"].lower())

    def test_previous_context_ignored(self):
        """Test that previous context is ignored in simple corrector"""
        raw = "test text"
        context = "some previous context"

        # Should not raise error even with context
        result = self.corrector.correct_transcript(raw, language="en", previous_context=context)

        self.assertIn("corrected", result)

    def test_word_preservation(self):
        """Test that important words are preserved"""
        raw = "open chrome and firefox"

        result = self.corrector.correct_transcript(raw, language="en")

        corrected_lower = result["corrected"].lower()
        self.assertIn("open", corrected_lower)
        self.assertIn("chrome", corrected_lower)
        self.assertIn("firefox", corrected_lower)

    def test_single_word(self):
        """Test handling of single word"""
        raw = "hello"

        result = self.corrector.correct_transcript(raw, language="en")

        self.assertEqual(result["corrected"], "Hello")

    def test_whitespace_handling(self):
        """Test proper whitespace in result"""
        raw = "um open the browser"

        result = self.corrector.correct_transcript(raw, language="en")

        # Should not have double spaces
        self.assertNotIn("  ", result["corrected"])

    def test_case_sensitivity_in_filler_detection(self):
        """Test that filler detection is case-insensitive"""
        raw = "UM I want to UH open it"

        result = self.corrector.correct_transcript(raw, language="en")

        corrected_lower = result["corrected"].lower()
        self.assertNotIn("um", corrected_lower)
        self.assertNotIn("uh", corrected_lower)


class TestSemanticCorrectorInterface(unittest.TestCase):
    """Test the interface requirements for semantic corrector"""

    def test_required_methods(self):
        """Test that corrector has required methods"""
        corrector = SimpleSemanticCorrector()

        # Should have these methods
        self.assertTrue(hasattr(corrector, "correct_transcript"))
        self.assertTrue(hasattr(corrector, "correct_transcript_async"))
        self.assertTrue(hasattr(corrector, "get_statistics"))

    def test_correct_transcript_signature(self):
        """Test correct_transcript method signature"""
        corrector = SimpleSemanticCorrector()

        # Should accept these parameters
        result = corrector.correct_transcript(
            raw_transcript="test", language="en", previous_context=None
        )

        self.assertIsInstance(result, dict)

    def test_result_format(self):
        """Test that result format matches specification"""
        corrector = SimpleSemanticCorrector()

        result = corrector.correct_transcript("test", "en")

        # Must have these fields
        required_fields = ["corrected", "raw", "model_used", "tokens_used"]
        for field in required_fields:
            self.assertIn(field, result)

    def test_statistics_format(self):
        """Test statistics format"""
        corrector = SimpleSemanticCorrector()
        corrector.correct_transcript("test", "en")

        stats = corrector.get_statistics()

        # Must have these fields
        required_fields = ["total_corrections", "model_loaded", "model_path"]
        for field in required_fields:
            self.assertIn(field, stats)


if __name__ == "__main__":
    unittest.main()
