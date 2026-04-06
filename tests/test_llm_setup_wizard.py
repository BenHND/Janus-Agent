"""
Unit tests for LLM Setup Wizard
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from janus.ai.reasoning.llm_setup_wizard import LLMSetupWizard


class TestLLMSetupWizard(unittest.TestCase):
    """Test cases for LLMSetupWizard"""

    def setUp(self):
        """Set up test fixtures"""
        self.wizard = LLMSetupWizard()

    def test_initialization(self):
        """Test wizard initialization"""
        self.assertIsNotNone(self.wizard)
        self.assertIsNotNone(self.wizard.system)
        self.assertIsNotNone(self.wizard.arch)

    @patch("subprocess.run")
    def test_detect_ollama_not_installed(self, mock_run):
        """Test Ollama detection when not installed"""
        mock_run.side_effect = FileNotFoundError()

        available, info = self.wizard.detect_ollama()

        self.assertFalse(available)
        self.assertIsNone(info)

    @patch("subprocess.run")
    @patch("requests.get")
    def test_detect_ollama_installed(self, mock_get, mock_run):
        """Test Ollama detection when installed"""
        mock_run.return_value = Mock(returncode=0, stdout="ollama version 0.1.0")
        mock_get.return_value = Mock(status_code=200)

        available, info = self.wizard.detect_ollama()

        self.assertTrue(available)
        self.assertIn("0.1.0", info)

    def test_detect_llama_cpp_not_installed(self):
        """Test llama-cpp detection when not installed"""
        with patch("builtins.__import__", side_effect=ImportError()):
            available, info = self.wizard.detect_llama_cpp()

        self.assertFalse(available)
        self.assertIsNone(info)

    def test_get_installation_instructions_ollama(self):
        """Test getting installation instructions for Ollama"""
        instructions = self.wizard.get_installation_instructions("ollama")

        self.assertIn("ollama", instructions.lower())
        self.assertIn("install", instructions.lower())

    def test_get_installation_instructions_llama_cpp(self):
        """Test getting installation instructions for llama-cpp"""
        instructions = self.wizard.get_installation_instructions("llama-cpp")

        self.assertIn("llama-cpp-python", instructions.lower())
        self.assertIn("pip install", instructions.lower())

    def test_get_recommended_models_ollama(self):
        """Test getting recommended Ollama models"""
        models = self.wizard.get_recommended_models("ollama")

        self.assertIsInstance(models, list)
        self.assertGreater(len(models), 0)

        # Check structure
        for model in models:
            self.assertIn("name", model)
            self.assertIn("display_name", model)
            self.assertIn("size", model)

    def test_get_recommended_models_llama_cpp(self):
        """Test getting recommended llama-cpp models"""
        models = self.wizard.get_recommended_models("llama-cpp")

        self.assertIsInstance(models, list)
        self.assertGreater(len(models), 0)

        # Check structure
        for model in models:
            self.assertIn("name", model)
            self.assertIn("display_name", model)
            self.assertIn("url", model)


class TestAPIKeyValidation(unittest.TestCase):
    """Test cases for API key validation"""

    def setUp(self):
        """Set up test fixtures"""
        self.wizard = LLMSetupWizard()

    @patch("openai.models.list")
    def test_validate_openai_api_key_success(self, mock_list):
        """Test successful OpenAI API key validation"""
        mock_list.return_value = Mock()

        valid, message = self.wizard.validate_openai_api_key("sk-test123")

        self.assertTrue(valid)
        self.assertIn("valid", message.lower())

    def test_validate_openai_api_key_import_error(self):
        """Test OpenAI validation when package not installed"""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'openai'")):
            valid, message = self.wizard.validate_openai_api_key("sk-test123")

        self.assertFalse(valid)
        self.assertIn("not installed", message.lower())

    @patch("openai.models.list")
    def test_validate_openai_api_key_auth_error(self, mock_list):
        """Test OpenAI validation with invalid key"""
        import openai

        mock_list.side_effect = openai.AuthenticationError("Invalid API key")

        valid, message = self.wizard.validate_openai_api_key("sk-invalid")

        self.assertFalse(valid)
        self.assertIn("invalid", message.lower())

    @patch("openai.models.list")
    def test_validate_openai_api_key_rate_limit(self, mock_list):
        """Test OpenAI validation with rate limit (should still be valid)"""
        import openai

        mock_list.side_effect = openai.RateLimitError("Rate limit exceeded")

        valid, message = self.wizard.validate_openai_api_key("sk-test123")

        # Key is valid even if rate limited
        self.assertTrue(valid)
        self.assertIn("valid", message.lower())

    @patch("anthropic.Anthropic")
    def test_validate_anthropic_api_key_success(self, mock_anthropic):
        """Test successful Anthropic API key validation"""
        mock_client = Mock()
        mock_client.messages.create.return_value = Mock()
        mock_anthropic.return_value = mock_client

        valid, message = self.wizard.validate_anthropic_api_key("sk-ant-test123")

        self.assertTrue(valid)
        self.assertIn("valid", message.lower())

    def test_validate_anthropic_api_key_import_error(self):
        """Test Anthropic validation when package not installed"""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'anthropic'")):
            valid, message = self.wizard.validate_anthropic_api_key("sk-ant-test123")

        self.assertFalse(valid)
        self.assertIn("not installed", message.lower())


class TestConfigurationSaving(unittest.TestCase):
    """Test cases for configuration saving"""

    def setUp(self):
        """Set up test fixtures"""
        self.wizard = LLMSetupWizard()
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.json"

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_save_configuration_new_file(self):
        """Test saving configuration to new file"""
        config = {"backend": "ollama", "model_name": "mistral:7b"}

        success = self.wizard.save_configuration(config, str(self.config_path))

        self.assertTrue(success)
        self.assertTrue(self.config_path.exists())

    def test_save_configuration_updates_existing(self):
        """Test that configuration updates existing file"""
        import json

        # Create existing config
        existing = {"other_key": "value"}
        with open(self.config_path, "w") as f:
            json.dump(existing, f)

        config = {"backend": "ollama", "model_name": "mistral:7b"}

        success = self.wizard.save_configuration(config, str(self.config_path))

        self.assertTrue(success)

        # Load and verify
        with open(self.config_path, "r") as f:
            saved = json.load(f)

        self.assertIn("other_key", saved)
        self.assertIn("cognitive_planner", saved)
        self.assertEqual(saved["cognitive_planner"]["backend"], "ollama")

    def test_save_configuration_enables_feature(self):
        """Test that saving configuration enables the feature"""
        import json

        config = {"backend": "ollama", "model_name": "mistral:7b"}

        self.wizard.save_configuration(config, str(self.config_path))

        with open(self.config_path, "r") as f:
            saved = json.load(f)

        self.assertTrue(saved["features"]["cognitive_planner"]["enabled"])


if __name__ == "__main__":
    unittest.main()
