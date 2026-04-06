"""
Integration tests for SemanticRouter in Pipeline
TICKET-401: Semantic Gatekeeper integration with pipeline
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from janus.runtime.core.contracts import ExecutionResult, Intent
from janus.runtime.core.pipeline import JanusPipeline
from janus.runtime.core import MemoryEngine
from janus.runtime.core.settings import DatabaseSettings, Settings


class TestSemanticRouterPipelineIntegration(unittest.TestCase):
    """Test SemanticRouter integration with JanusPipeline"""

    def setUp(self):
        """Set up test pipeline with mocked components"""
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_semantic_router.db"
        
        # Create settings and memory service
        self.settings = Settings()
        db_settings = DatabaseSettings(path=str(self.db_path))
        self.memory = MemoryEngine(db_settings)
        
        # Create pipeline with minimal features enabled
        self.pipeline = JanusPipeline(
            settings=self.settings,
            memory=self.memory,
            enable_voice=False,
            enable_llm_reasoning=False,  # Disable LLM for faster tests
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
        )

    def tearDown(self):
        """Clean up after tests"""
        import shutil
        # Clean up temp directory
        if hasattr(self, 'temp_dir'):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_noise_input_ignored(self):
        """Test NOISE input is ignored and doesn't reach reasoner (TICKET-401 acceptance)"""
        # "Merci beaucoup" should be classified as NOISE and return immediately
        result = self.pipeline.process_command("Merci beaucoup", mock_execution=True)
        
        self.assertIsInstance(result, ExecutionResult)
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Ignored (Noise)")
        self.assertEqual(result.intent.action, "noise_ignored")
        # Verify it completed fast (should be <50ms, but allow more for test overhead)
        self.assertLess(result.total_duration_ms, 1000)

    def test_noise_merci(self):
        """Test 'Merci' is ignored"""
        result = self.pipeline.process_command("Merci", mock_execution=True)
        
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Ignored (Noise)")
        self.assertEqual(result.intent.action, "noise_ignored")

    def test_noise_bonjour(self):
        """Test 'Bonjour' is ignored"""
        result = self.pipeline.process_command("Bonjour", mock_execution=True)
        
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Ignored (Noise)")

    def test_noise_ok(self):
        """Test 'Ok' is ignored"""
        result = self.pipeline.process_command("Ok", mock_execution=True)
        
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Ignored (Noise)")

    def test_chat_input_not_implemented(self):
        """Test CHAT input returns appropriate message"""
        result = self.pipeline.process_command("Raconte une blague", mock_execution=True)
        
        self.assertIsInstance(result, ExecutionResult)
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Chat detected (Not implemented)")
        self.assertEqual(result.intent.action, "chat_detected")

    def test_chat_question(self):
        """Test question is classified as CHAT"""
        result = self.pipeline.process_command("Quel temps fait-il ?", mock_execution=True)
        
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Chat detected (Not implemented)")

    def test_empty_input_noise(self):
        """Test empty input is treated as NOISE"""
        result = self.pipeline.process_command("", mock_execution=True)
        
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Ignored (Noise)")

    def test_whitespace_input_noise(self):
        """Test whitespace-only input is treated as NOISE"""
        result = self.pipeline.process_command("   ", mock_execution=True)
        
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Ignored (Noise)")

    def test_semantic_router_lazy_loading(self):
        """Test semantic router is lazy-loaded"""
        # Access the property to trigger lazy loading
        router = self.pipeline.semantic_router
        
        self.assertIsNotNone(router)
        self.assertIsNotNone(router.noise_keywords)
        self.assertIsNotNone(router.action_keywords)


class TestSemanticRouterPerformance(unittest.TestCase):
    """Performance tests for SemanticRouter"""

    def setUp(self):
        """Set up test pipeline"""
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_semantic_router_perf.db"
        
        self.settings = Settings()
        db_settings = DatabaseSettings(path=str(self.db_path))
        self.memory = MemoryEngine(db_settings)
        
        self.pipeline = JanusPipeline(
            settings=self.settings,
            memory=self.memory,
            enable_voice=False,
            enable_llm_reasoning=False,
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
        )

    def tearDown(self):
        """Clean up after tests"""
        import shutil
        # Clean up temp directory
        if hasattr(self, 'temp_dir'):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_noise_filtering_is_fast(self):
        """Test NOISE filtering completes in <100ms (should be <50ms target)"""
        import time
        
        start = time.time()
        result = self.pipeline.process_command("Merci beaucoup", mock_execution=True)
        elapsed_ms = (time.time() - start) * 1000
        
        # Should be very fast compared to full reasoning (2-10s)
        self.assertLess(elapsed_ms, 100)
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Ignored (Noise)")

    def test_batch_noise_filtering_performance(self):
        """Test batch noise filtering is consistently fast"""
        noise_inputs = ["Merci", "Salut", "Ok", "Bonjour", "D'accord"]
        
        for input_text in noise_inputs:
            with self.subTest(input=input_text):
                import time
                start = time.time()
                result = self.pipeline.process_command(input_text, mock_execution=True)
                elapsed_ms = (time.time() - start) * 1000
                
                self.assertLess(elapsed_ms, 100)
                self.assertEqual(result.message, "Ignored (Noise)")


if __name__ == "__main__":
    unittest.main()
