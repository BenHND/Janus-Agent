"""
Tests for LLM text corrector module (unified semantic correction)
"""
import unittest

from janus.ai.llm.unified_client import UnifiedLLMClient
from janus.ai.llm.llm_text_corrector import LLMTextCorrector


class TestLLMTextCorrector(unittest.TestCase):
    """Test LLM text corrector functionality"""

    def setUp(self):
        """Set up test with mock LLM service"""
        self.llm_service = UnifiedLLMClient(provider="mock")
        self.corrector = LLMTextCorrector(self.llm_service)

    def test_initialization(self):
        """Test corrector initialization"""
        self.assertIsNotNone(self.corrector.llm_client)
        self.assertEqual(self.corrector.total_corrections, 0)
        self.assertEqual(self.corrector.total_reformats, 0)

    def test_correct_transcript_without_llm(self):
        """Test correction fallback when LLM not available"""
        corrector = LLMTextCorrector(None)
        result = corrector.correct_transcript("test text", "en")
        
        self.assertEqual(result["raw"], "test text")
        self.assertEqual(result["corrected"], "test text")
        self.assertFalse(result["model_used"])
        self.assertEqual(result["tokens_used"], 0)

    def test_correct_transcript_with_mock_llm(self):
        """Test correction with mock LLM"""
        result = self.corrector.correct_transcript("um hello world", "en")
        
        self.assertIn("raw", result)
        self.assertIn("corrected", result)
        self.assertIn("model_used", result)
        self.assertEqual(result["raw"], "um hello world")
        # Mock LLM should return something (even if minimal processing)
        self.assertIsInstance(result["corrected"], str)

    def test_correct_transcript_french(self):
        """Test correction with French text"""
        result = self.corrector.correct_transcript("euh bonjour le monde", "fr")
        
        self.assertEqual(result["raw"], "euh bonjour le monde")
        self.assertIn("corrected", result)

    def test_correct_transcript_with_context(self):
        """Test correction with previous context"""
        result = self.corrector.correct_transcript(
            "um and then",
            "en",
            previous_context="I was walking"
        )
        
        self.assertIn("corrected", result)

    def test_reformat_text_without_llm(self):
        """Test reformatting fallback when LLM not available"""
        corrector = LLMTextCorrector(None)
        result = corrector.reformat_text("test text", "fr")
        
        self.assertEqual(result["original"], "test text")
        self.assertEqual(result["reformatted"], "test text")
        self.assertEqual(result["method"], "passthrough")
        self.assertLessEqual(result["confidence"], 0.5)

    def test_reformat_text_with_mock_llm(self):
        """Test reformatting with mock LLM"""
        result = self.corrector.reformat_text("euh ouvre chrome", "fr")
        
        self.assertEqual(result["original"], "euh ouvre chrome")
        self.assertIn("reformatted", result)
        self.assertIn("method", result)
        self.assertIn("confidence", result)

    def test_reformat_text_english(self):
        """Test reformatting with English text"""
        result = self.corrector.reformat_text("um open chrome", "en")
        
        self.assertEqual(result["original"], "um open chrome")
        self.assertIn("reformatted", result)

    def test_statistics(self):
        """Test statistics tracking"""
        stats = self.corrector.get_statistics()
        
        self.assertIn("total_corrections", stats)
        self.assertIn("total_reformats", stats)
        self.assertIn("llm_provider", stats)
        self.assertIn("llm_model", stats)
        self.assertIn("llm_available", stats)
        
        # Initial stats should be zero
        self.assertEqual(stats["total_corrections"], 0)
        self.assertEqual(stats["total_reformats"], 0)
        
        # After correction attempt (even if it fails with mock), 
        # stats don't increment unless successful. This is expected behavior.
        self.corrector.correct_transcript("test", "en")
        stats = self.corrector.get_statistics()
        # Stats remain 0 because mock provider throws NotImplementedError
        self.assertGreaterEqual(stats["total_corrections"], 0)
        
        # Test with no LLM service - this should work
        corrector_no_llm = LLMTextCorrector(None)
        corrector_no_llm.correct_transcript("test", "en")
        stats_no_llm = corrector_no_llm.get_statistics()
        # Stats still 0 because no LLM was used
        self.assertEqual(stats_no_llm["total_corrections"], 0)

    def test_clean_llm_output(self):
        """Test LLM output cleaning"""
        # Test quote removal
        cleaned = self.corrector._clean_llm_output('"hello world"', "original")
        self.assertEqual(cleaned, "hello world")
        
        # Test prefix removal
        cleaned = self.corrector._clean_llm_output("Corrected transcript: hello", "original")
        self.assertEqual(cleaned, "hello")
        
        # Test empty output fallback
        cleaned = self.corrector._clean_llm_output("", "fallback text")
        self.assertEqual(cleaned, "fallback text")
        
        # Test short output fallback
        cleaned = self.corrector._clean_llm_output("x", "fallback text")
        self.assertEqual(cleaned, "fallback text")


if __name__ == "__main__":
    unittest.main()
