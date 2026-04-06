"""
Tests for alternative LLM providers - Ticket 009
Tests provider initialization, fallback mechanisms, and API calls
"""
import unittest
from unittest.mock import MagicMock, Mock, patch

from janus.ai.llm.unified_client import UnifiedLLMClient


class TestProviderInitialization(unittest.TestCase):
    """Test initialization of different LLM providers"""

    def test_anthropic_initialization_without_key(self):
        """Test Anthropic initialization fails gracefully without API key"""
        with patch.dict("os.environ", {}, clear=True):
            llm = UnifiedLLMClient(provider="anthropic")
            # Should fallback to mock
            self.assertEqual(llm.provider, "mock")
            self.assertTrue(llm.available)

    def test_local_initialization_without_model_path(self):
        """Test local LLM initialization fails gracefully without model path"""
        llm = UnifiedLLMClient(provider="local")
        # Should fallback to mock
        self.assertEqual(llm.provider, "mock")
        self.assertTrue(llm.available)

    def test_local_initialization_with_invalid_path(self):
        """Test local LLM initialization with invalid model path"""
        llm = UnifiedLLMClient(provider="local", model_path="/nonexistent/model.gguf")
        # Should fallback to mock
        self.assertEqual(llm.provider, "mock")
        self.assertTrue(llm.available)

    def test_ollama_initialization_without_server(self):
        """Test Ollama initialization fails gracefully when server not running"""
        llm = UnifiedLLMClient(provider="ollama", model="mistral:7b")
        # Should fallback to mock (Ollama server not running in test env)
        self.assertEqual(llm.provider, "mock")
        self.assertTrue(llm.available)

    def test_mistral_initialization_without_key(self):
        """Test Mistral initialization fails gracefully without API key"""
        with patch.dict("os.environ", {}, clear=True):
            llm = UnifiedLLMClient(provider="mistral")
            # Should fallback to mock
            self.assertEqual(llm.provider, "mock")
            self.assertTrue(llm.available)


class TestFallbackMechanism(unittest.TestCase):
    """Test automatic fallback mechanism between providers"""

    def test_fallback_to_mock(self):
        """Test fallback to mock when primary provider unavailable"""
        llm = UnifiedLLMClient(provider="openai", fallback_providers=["local", "mock"])
        # OpenAI not available -> local not available -> mock
        self.assertEqual(llm.provider, "mock")
        self.assertTrue(llm.available)

    def test_fallback_chain(self):
        """Test fallback chain with multiple providers"""
        llm = UnifiedLLMClient(provider="anthropic", fallback_providers=["mistral", "ollama", "mock"])
        # All commercial providers should fail -> mock
        self.assertEqual(llm.provider, "mock")
        self.assertTrue(llm.available)

    def test_no_fallback_providers(self):
        """Test behavior when no fallback providers specified"""
        llm = UnifiedLLMClient(provider="anthropic")
        # Should still fallback to mock automatically
        self.assertEqual(llm.provider, "mock")
        self.assertTrue(llm.available)

    def test_mock_always_available(self):
        """Test mock provider is always available"""
        llm = UnifiedLLMClient(provider="mock")
        self.assertEqual(llm.provider, "mock")
        self.assertTrue(llm.available)


class TestProviderInfo(unittest.TestCase):
    """Test provider information methods"""

    def test_get_provider_info_mock(self):
        """Test getting provider info for mock provider"""
        llm = UnifiedLLMClient(provider="mock", model="gpt-4")
        info = llm.get_provider_info()

        self.assertEqual(info["provider"], "mock")
        self.assertEqual(info["model"], "gpt-4")
        self.assertTrue(info["available"])
        self.assertIsInstance(info["fallback_providers"], list)

    def test_get_provider_info_with_fallbacks(self):
        """Test provider info includes fallback providers"""
        llm = UnifiedLLMClient(provider="openai", fallback_providers=["local", "mock"])
        info = llm.get_provider_info()

        # Should have fallen back to mock
        self.assertEqual(info["provider"], "mock")
        self.assertTrue(info["available"])

    def test_provider_info_includes_model_path(self):
        """Test provider info includes model path when specified"""
        model_path = "/path/to/model.gguf"
        llm = UnifiedLLMClient(provider="local", model_path=model_path)
        info = llm.get_provider_info()

        self.assertEqual(info["model_path"], model_path)


class TestProviderEnums(unittest.TestCase):
    """Test LLMProvider enum values"""

    def test_all_providers_defined(self):
        """Test all expected providers are defined in enum"""
        expected_providers = ["openai", "anthropic", "local", "ollama", "mistral", "mock"]
        actual_providers = [p.value for p in LLMProvider]

        for expected in expected_providers:
            self.assertIn(expected, actual_providers)

    def test_provider_enum_values(self):
        """Test specific provider enum values"""
        self.assertEqual("OPENAI.value, "openai")
        self.assertEqual("ANTHROPIC.value, "anthropic")
        self.assertEqual("LOCAL.value, "local")
        self.assertEqual("OLLAMA.value, "ollama")
        self.assertEqual("MISTRAL.value, "mistral")
        self.assertEqual("mock".value, "mock")


class TestMockProviderCalls(unittest.TestCase):
    """Test that mock provider still works with all existing functionality"""

    def setUp(self):
        """Set up mock LLM service"""
        self.llm = UnifiedLLMClient(provider="mock")

    def test_analyze_command_works(self):
        """Test analyze_command works with mock provider"""
        result = self.llm.analyze_command("open chrome")
        self.assertEqual(result["status"], "success")
        self.assertIn("intent", result)

    def test_analyze_content_works(self):
        """Test analyze_content works with mock provider"""
        result = self.llm.analyze_content("test content", "text", "summarize")
        self.assertEqual(result["status"], "success")
        self.assertIn("result", result)

    def test_generate_action_plan_works(self):
        """Test generate_action_plan works with mock provider"""
        plan = self.llm.generate_action_plan("open_app", {"app_name": "Chrome"})
        self.assertIsInstance(plan, list)

    def test_performance_metrics_work(self):
        """Test performance metrics work with mock provider"""
        self.llm.analyze_command("test command")
        metrics = self.llm.get_performance_metrics()

        self.assertIn("total_calls", metrics)
        self.assertGreater(metrics["total_calls"], 0)


class TestProviderParameters(unittest.TestCase):
    """Test provider initialization with various parameters"""

    def test_custom_temperature(self):
        """Test custom temperature parameter"""
        llm = UnifiedLLMClient(provider="mock", temperature=0.9)
        self.assertEqual(llm.temperature, 0.9)

    def test_custom_max_tokens(self):
        """Test custom max_tokens parameter"""
        llm = UnifiedLLMClient(provider="mock", max_tokens=4000)
        self.assertEqual(llm.max_tokens, 4000)

    def test_custom_timeout(self):
        """Test custom request_timeout parameter"""
        llm = UnifiedLLMClient(provider="mock", request_timeout=60)
        self.assertEqual(llm.request_timeout, 60)

    def test_cache_configuration(self):
        """Test cache configuration parameters"""
        llm = UnifiedLLMClient(provider="mock", enable_cache=False, cache_ttl=600)
        self.assertFalse(llm.enable_cache)
        self.assertEqual(llm.cache_ttl, 600)


class TestProviderCallInterfaceConsistency(unittest.TestCase):
    """Test that all providers have consistent call interface"""

    def test_mock_provider_available_flag(self):
        """Test mock provider sets available flag"""
        llm = UnifiedLLMClient(provider="mock")
        self.assertTrue(llm.available)

    def test_unavailable_provider_marked_correctly(self):
        """Test unavailable providers are marked as unavailable before fallback"""
        # This test verifies the fallback mechanism works
        llm = UnifiedLLMClient(provider="openai")
        # Should fallback to mock which is available
        self.assertTrue(llm.available)
        self.assertEqual(llm.provider, "mock")


class TestModelSpecification(unittest.TestCase):
    """Test model specification for different providers"""

    def test_openai_model_specification(self):
        """Test OpenAI model can be specified"""
        llm = UnifiedLLMClient(provider="openai", model="gpt-3.5-turbo")
        self.assertEqual(llm.model, "gpt-3.5-turbo")

    def test_anthropic_model_specification(self):
        """Test Anthropic model can be specified"""
        llm = UnifiedLLMClient(provider="anthropic", model="claude-3-sonnet-20240229")
        self.assertEqual(llm.model, "claude-3-sonnet-20240229")

    def test_ollama_model_specification(self):
        """Test Ollama model can be specified"""
        llm = UnifiedLLMClient(provider="ollama", model="mistral:7b")
        self.assertEqual(llm.model, "mistral:7b")

    def test_mistral_model_specification(self):
        """Test Mistral model can be specified"""
        llm = UnifiedLLMClient(provider="mistral", model="mistral-large-latest")
        self.assertEqual(llm.model, "mistral-large-latest")


if __name__ == "__main__":
    unittest.main()
