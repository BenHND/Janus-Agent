"""
Tests for Hybrid LLM Optimization (TICKET: P1) - FULL MIGRATION

Tests MANDATORY dual-model architecture for Ollama provider.
Hybrid mode is no longer optional - it's the ONLY mode for Ollama.
"""
import unittest
from unittest.mock import Mock, patch

from janus.ai.llm.unified_client import UnifiedLLMClient
from janus.config.model_paths import REASONER_MODEL, REFLEX_MODEL


class TestHybridLLM(unittest.TestCase):
    """Test hybrid LLM dual-model functionality (MANDATORY for Ollama)"""

    def test_model_constants_defined(self):
        """Test that hybrid model constants are defined"""
        self.assertIsNotNone(REASONER_MODEL)
        self.assertIsNotNone(REFLEX_MODEL)
        self.assertIn("qwen2.5", REASONER_MODEL.lower())
        self.assertIn("qwen2.5", REFLEX_MODEL.lower())
        self.assertIn("7b", REASONER_MODEL.lower())
        self.assertIn("1.5b", REFLEX_MODEL.lower())

    def test_non_ollama_providers_use_single_model(self):
        """Test that non-Ollama providers use single-model mode"""
        client = UnifiedLLMClient(provider="mock")
        self.assertIsNone(client.reasoner)
        self.assertIsNone(client.reflex)
        self.assertIsNotNone(client.client)
        
    @patch('janus.ai.llm.unified_client.OllamaClientAdapter')
    def test_ollama_always_uses_hybrid(self, mock_ollama):
        """Test that Ollama ALWAYS uses hybrid mode (FULL MIGRATION)"""
        # Mock OllamaClientAdapter to simulate available models
        mock_reasoner = Mock()
        mock_reasoner.is_available.return_value = True
        mock_reflex = Mock()
        mock_reflex.is_available.return_value = True
        
        mock_ollama.side_effect = [mock_reasoner, mock_reflex]
        
        # Initialize Ollama client - hybrid is MANDATORY
        client = UnifiedLLMClient(
            provider="ollama",
            reasoner_model=REASONER_MODEL,
            reflex_model=REFLEX_MODEL
        )
        
        # Should ALWAYS have both clients initialized for Ollama
        self.assertIsNotNone(client.reasoner)
        self.assertIsNotNone(client.reflex)
        self.assertEqual(client.provider, "ollama")

    @patch('janus.ai.llm.unified_client.OllamaClientAdapter')
    def test_smart_mode_uses_reasoner(self, mock_ollama):
        """Test that smart mode uses reasoner model"""
        mock_reasoner = Mock()
        mock_reasoner.is_available.return_value = True
        mock_reasoner.generate.return_value = "Reasoner response"
        
        mock_reflex = Mock()
        mock_reflex.is_available.return_value = True
        
        mock_ollama.side_effect = [mock_reasoner, mock_reflex]
        
        client = UnifiedLLMClient(
            provider="ollama",
            reasoner_model=REASONER_MODEL,
            reflex_model=REFLEX_MODEL
        )
        
        # Generate with smart mode (default)
        result = client.generate("complex planning task", mode="smart")
        
        # Should use reasoner
        mock_reasoner.generate.assert_called_once()
        mock_reflex.generate.assert_not_called()
        self.assertEqual(result, "Reasoner response")

    @patch('janus.ai.llm.unified_client.OllamaClientAdapter')
    def test_fast_mode_uses_reflex(self, mock_ollama):
        """Test that fast mode uses reflex model"""
        mock_reasoner = Mock()
        mock_reasoner.is_available.return_value = True
        
        mock_reflex = Mock()
        mock_reflex.is_available.return_value = True
        mock_reflex.generate.return_value = "Reflex response"
        
        mock_ollama.side_effect = [mock_reasoner, mock_reflex]
        
        client = UnifiedLLMClient(
            provider="ollama",
            reasoner_model=REASONER_MODEL,
            reflex_model=REFLEX_MODEL
        )
        
        # Generate with fast mode
        result = client.generate("simple summary", mode="fast")
        
        # Should use reflex
        mock_reflex.generate.assert_called_once()
        mock_reasoner.generate.assert_not_called()
        self.assertEqual(result, "Reflex response")

    @patch('janus.ai.llm.unified_client.OllamaClientAdapter')
    def test_chat_with_smart_mode(self, mock_ollama):
        """Test chat generation with smart mode"""
        mock_reasoner = Mock()
        mock_reasoner.is_available.return_value = True
        mock_reasoner.generate_chat.return_value = "Reasoner chat response"
        
        mock_reflex = Mock()
        mock_reflex.is_available.return_value = True
        
        mock_ollama.side_effect = [mock_reasoner, mock_reflex]
        
        client = UnifiedLLMClient(
            provider="ollama",
            reasoner_model=REASONER_MODEL,
            reflex_model=REFLEX_MODEL
        )
        
        # Chat with smart mode
        messages = [{"role": "user", "content": "complex analysis task"}]
        result = client.generate_chat(messages, mode="smart")
        
        mock_reasoner.generate_chat.assert_called_once()
        self.assertEqual(result, "Reasoner chat response")

    @patch('janus.ai.llm.unified_client.OllamaClientAdapter')
    def test_chat_with_fast_mode(self, mock_ollama):
        """Test chat generation with fast mode"""
        mock_reasoner = Mock()
        mock_reasoner.is_available.return_value = True
        
        mock_reflex = Mock()
        mock_reflex.is_available.return_value = True
        mock_reflex.generate_chat.return_value = "Reflex chat response"
        
        mock_ollama.side_effect = [mock_reasoner, mock_reflex]
        
        client = UnifiedLLMClient(
            provider="ollama",
            reasoner_model=REASONER_MODEL,
            reflex_model=REFLEX_MODEL
        )
        
        # Chat with fast mode
        messages = [{"role": "user", "content": "hello"}]
        result = client.generate_chat(messages, mode="fast")
        
        mock_reflex.generate_chat.assert_called_once()
        self.assertEqual(result, "Reflex chat response")

    @patch('janus.ai.llm.unified_client.OllamaClientAdapter')
    def test_error_when_models_unavailable(self, mock_ollama):
        """Test that Ollama raises error when hybrid models are not available (FULL MIGRATION)"""
        # Mock unavailable models
        mock_reasoner = Mock()
        mock_reasoner.is_available.return_value = False
        mock_reflex = Mock()
        mock_reflex.is_available.return_value = False
        
        mock_ollama.side_effect = [mock_reasoner, mock_reflex]
        
        # Should raise RuntimeError since models are mandatory
        with self.assertRaises(RuntimeError) as context:
            client = UnifiedLLMClient(provider="ollama")
        
        self.assertIn("hybrid models not available", str(context.exception).lower())

    def test_mode_parameter_in_non_ollama(self):
        """Test that mode parameter works but is ignored in non-Ollama providers"""
        client = UnifiedLLMClient(provider="mock")
        
        # Both modes should work without error (mode is Ollama-specific)
        result1 = client.generate("test", mode="smart")
        result2 = client.generate("test", mode="fast")
        
        self.assertIsInstance(result1, str)
        self.assertIsInstance(result2, str)


class TestContextRouterFastMode(unittest.TestCase):
    """Test that ContextRouter uses fast mode for classification"""
    
    def test_context_router_uses_fast_mode(self):
        """Test that context router uses fast mode parameter"""
        from janus.ai.reasoning.context_router import ContextRouter
        
        mock_llm = Mock()
        mock_llm.generate.return_value = '["vision"]'
        
        router = ContextRouter(llm_client=mock_llm, enabled=True)
        
        # Call get_requirements
        if router.available:
            router.get_requirements("show me the screen")
            
            # Verify generate was called with mode="fast"
            self.assertTrue(mock_llm.generate.called)
            call_kwargs = mock_llm.generate.call_args[1]
            self.assertEqual(call_kwargs.get('mode'), 'fast')


if __name__ == "__main__":
    unittest.main()
