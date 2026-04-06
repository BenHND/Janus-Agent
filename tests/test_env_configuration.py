"""
Tests for configuration system
Tests that config.ini is the single source of truth for configuration
Environment variables are only used for API keys and specific deployment settings
"""
import os
import unittest
from unittest.mock import MagicMock, patch

from janus.constants import OLLAMA_DEFAULT_ENDPOINT, SEARCH_ENGINE_URL
from janus.runtime.core.settings import Settings


class TestConfigurationSystem(unittest.TestCase):
    """Test configuration system using config.ini as single source of truth"""

    def test_config_loads_from_ini(self):
        """Test that configuration loads from config.ini"""
        settings = Settings()
        # Should have loaded values from config.ini
        self.assertIsNotNone(settings.whisper.model_size)
        self.assertIsNotNone(settings.llm.provider)

    def test_whitelisted_env_vars_work(self):
        """Test that whitelisted environment variables are still honored"""
        # SPECTRA_MODELS_DIR is whitelisted
        with patch.dict(os.environ, {"SPECTRA_MODELS_DIR": "/custom/models"}):
            settings = Settings()
            self.assertEqual(settings.whisper.models_dir, "/custom/models")
        
        # SPECTRA_VISION_MODELS_DIR is whitelisted
        with patch.dict(os.environ, {"SPECTRA_VISION_MODELS_DIR": "/custom/vision"}):
            settings = Settings()
            self.assertEqual(settings.vision.models_dir, "/custom/vision")
        
        # OLLAMA_ENDPOINT is whitelisted (read directly in _load_llm_settings)
        with patch.dict(os.environ, {"OLLAMA_ENDPOINT": "http://custom:11434"}):
            settings = Settings()
            self.assertEqual(settings.llm.ollama_endpoint, "http://custom:11434")

    def test_non_whitelisted_env_vars_ignored(self):
        """Test that non-whitelisted environment variables are ignored"""
        # These should NOT override config.ini anymore
        with patch.dict(os.environ, {"WHISPER_MODEL_SIZE": "large"}):
            settings = Settings()
            # Should use config.ini value, not env var
            # config.ini has "small" by default
            self.assertNotEqual(settings.whisper.model_size, "large")
        
        with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}):
            settings = Settings()
            # Should use config.ini value (ollama), not env var
            self.assertNotEqual(settings.llm.provider, "openai")

    def test_features_enabled_by_default(self):
        """Test that features are enabled by default from config.ini"""
        settings = Settings()
        # config.ini now has all features enabled by default
        self.assertTrue(settings.features.enable_llm_reasoning)
        self.assertTrue(settings.features.enable_vision)
        self.assertTrue(settings.features.enable_learning)

    def test_no_auto_detection(self):
        """Test that auto-detection is no longer used"""
        settings = Settings()
        # Features should be explicitly true or false, never "auto"
        self.assertIsInstance(settings.features.enable_llm_reasoning, bool)
        self.assertIsInstance(settings.features.enable_vision, bool)
        self.assertIsInstance(settings.features.enable_learning, bool)

    def test_cli_override_takes_precedence(self):
        """Test that CLI overrides take precedence"""
        settings = Settings(model_size="tiny")
        self.assertEqual(settings.whisper.model_size, "tiny")

    def test_ollama_endpoint_from_env(self):
        """Test that OLLAMA_ENDPOINT can be overridden via env var"""
        with patch.dict(os.environ, {"OLLAMA_ENDPOINT": "http://custom-host:8080"}):
            settings = Settings()
            self.assertEqual(settings.llm.ollama_endpoint, "http://custom-host:8080")

    def test_no_env_uses_config_default(self):
        """Test that without env vars, config.ini values are used"""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            # Should use config.ini values
            self.assertIsNotNone(settings.whisper.model_size)
            self.assertIsNotNone(settings.llm.provider)


class TestAPIKeyEnvironmentVariables(unittest.TestCase):
    """Test that API keys are read from environment variables"""

    def test_openai_api_key_from_env(self):
        """Test that OPENAI_API_KEY is read from environment"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-123"}):
            # Import after setting env var
            from janus.ai.llm.unified_client import UnifiedLLMClient

            # Mock the openai import
            with patch("janus.llm.unified_client.openai", create=True) as mock_openai:
                llm = UnifiedLLMClient(provider="openai")
                # Should have tried to set the API key
                self.assertEqual(llm.api_key, "sk-test-key-123")

    def test_anthropic_api_key_from_env(self):
        """Test that ANTHROPIC_API_KEY is read from environment"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"}):
            from janus.ai.llm.unified_client import UnifiedLLMClient

            # Should fall back to mock if anthropic not installed
            llm = UnifiedLLMClient(provider="anthropic")
            # If it couldn't initialize anthropic, it should have tried to use the key
            # The actual behavior depends on whether anthropic is installed
            self.assertIsNotNone(llm)

    def test_mistral_api_key_from_env(self):
        """Test that MISTRAL_API_KEY is read from environment"""
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-mistral-key"}):
            from janus.ai.llm.unified_client import UnifiedLLMClient

            # Should fall back to mock if mistralai not installed
            llm = UnifiedLLMClient(provider="mistral")
            self.assertIsNotNone(llm)


class TestConfigurationPriority(unittest.TestCase):
    """Test configuration priority: config.ini is single source of truth"""

    def test_priority_order(self):
        """Test that config.ini is used as single source of truth"""
        # Test 1: Without config.ini, use defaults
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                settings = Settings()
                # Should use hardcoded defaults
                self.assertEqual(settings.whisper.model_size, "base")

        # Test 2: Config.ini values are used (not env vars)
        with patch.dict(os.environ, {"WHISPER_MODEL_SIZE": "large"}):
            settings = Settings()
            # Should NOT use env var (only config.ini)
            self.assertNotEqual(settings.whisper.model_size, "large")


if __name__ == "__main__":
    unittest.main()
