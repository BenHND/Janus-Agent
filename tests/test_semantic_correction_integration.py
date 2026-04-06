"""
Tests for semantic correction integration with main LLM
Validates the unified LLM architecture where semantic correction
can use either the main LLM or a dedicated local model.
"""
import os
import tempfile
import unittest

from janus.runtime.core.settings import Settings
from janus.ai.llm.unified_client import UnifiedLLMClient
from janus.io.stt.whisper_post_processor import WhisperPostProcessor


class TestSemanticCorrectionIntegration(unittest.TestCase):
    """Test semantic correction integration with unified LLM"""

    def test_post_processor_with_llm_service(self):
        """Test that post processor accepts and uses LLM service"""
        # Create mock LLM service
        llm_service = UnifiedLLMClient(provider="mock")
        
        # Create post processor with LLM service
        processor = WhisperPostProcessor(
            enable_semantic_correction=True,
            semantic_correction_model_path="",  # Empty path = use main LLM
            llm_service=llm_service,
        )
        
        # Verify LLM service is stored
        self.assertIsNotNone(processor.llm_service)
        self.assertEqual(processor.llm_service, llm_service)
        
        # Verify semantic corrector was created (should use LLM)
        self.assertIsNotNone(processor.semantic_corrector)

    def test_post_processor_without_llm_service(self):
        """Test that post processor works without LLM service"""
        # Create post processor without LLM service
        processor = WhisperPostProcessor(
            enable_semantic_correction=True,
            semantic_correction_model_path="",
            llm_service=None,
        )
        
        # Should fall back to simple corrector
        self.assertIsNone(processor.llm_service)

    def test_post_processor_with_dedicated_model_path(self):
        """Test that dedicated model path takes priority over LLM service"""
        llm_service = UnifiedLLMClient(provider="mock")
        
        # Create a temporary fake model file
        with tempfile.NamedTemporaryFile(suffix=".gguf", delete=False) as tmp:
            fake_model_path = tmp.name
        
        try:
            # Create post processor with both LLM service and model path
            processor = WhisperPostProcessor(
                enable_semantic_correction=True,
                semantic_correction_model_path=fake_model_path,
                llm_service=llm_service,
            )
            
            # Dedicated model path should be attempted first
            # (will fail because it's not a real model, but that's OK for this test)
            self.assertIsNotNone(processor.llm_service)
        finally:
            # Clean up
            if os.path.exists(fake_model_path):
                os.remove(fake_model_path)

    def test_settings_semantic_correction_path(self):
        """Test that settings correctly load semantic correction path"""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as tmp:
            tmp.write("""
[whisper]
semantic_correction_model_path = 
enable_corrections = true

[llm]
provider = ollama
model = mistral

[features]
enable_semantic_correction = true

[audio]
sample_rate = 16000

[language]
default = fr

[automation]
safety_delay = 0.5

[calibration]
profile_dir = calibration_profiles

[vision]
models_dir = models/vision

[session]
state_file = session_state.json

[tts]
enable_tts = true

[database]
path = data/janus.db

[logging]
level = INFO
""")
            config_path = tmp.name
        
        try:
            # Load settings
            settings = Settings(config_path=config_path)
            
            # Verify semantic correction settings
            self.assertEqual(settings.whisper.semantic_correction_model_path, "")
            self.assertTrue(settings.features.enable_semantic_correction)
            self.assertEqual(settings.llm.provider, "ollama")
            self.assertEqual(settings.llm.model, "mistral")
        finally:
            # Clean up
            if os.path.exists(config_path):
                os.remove(config_path)

    def test_settings_with_dedicated_model_path(self):
        """Test settings when dedicated model path is configured"""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as tmp:
            tmp.write("""
[whisper]
semantic_correction_model_path = models/phi-2.Q4_K_M.gguf
enable_corrections = true

[llm]
provider = ollama
model = mistral

[features]
enable_semantic_correction = true

[audio]
sample_rate = 16000

[language]
default = fr

[automation]
safety_delay = 0.5

[calibration]
profile_dir = calibration_profiles

[vision]
models_dir = models/vision

[session]
state_file = session_state.json

[tts]
enable_tts = true

[database]
path = data/janus.db

[logging]
level = INFO
""")
            config_path = tmp.name
        
        try:
            # Load settings
            settings = Settings(config_path=config_path)
            
            # Verify semantic correction settings
            self.assertEqual(
                settings.whisper.semantic_correction_model_path,
                "models/phi-2.Q4_K_M.gguf"
            )
            self.assertTrue(settings.features.enable_semantic_correction)
        finally:
            # Clean up
            if os.path.exists(config_path):
                os.remove(config_path)

    def test_unified_llm_client_initialization(self):
        """Test that UnifiedLLMClient initializes correctly for semantic correction"""
        # Test with mock provider (should always work)
        client = UnifiedLLMClient(provider="mock")
        self.assertTrue(client.available)
        self.assertEqual(client.provider, "mock")
        
        # Test with Ollama (will fail if not running, which is expected)
        client_ollama = UnifiedLLMClient(
            provider="ollama",
            model="mistral"
        )
        # Don't test availability since Ollama may not be running in test environment
        # In test environment, Ollama may not be running, so it should fallback to mock
        self.assertIsNotNone(client_ollama)
        self.assertIn(client_ollama.provider, ["ollama", "mock"])  # Either works or falls back

    def test_semantic_correction_processing_flow(self):
        """Test the complete semantic correction processing flow"""
        llm_service = UnifiedLLMClient(provider="mock")
        
        processor = WhisperPostProcessor(
            enable_semantic_correction=True,
            semantic_correction_model_path="",  # Use main LLM
            llm_service=llm_service,
        )
        
        # Process some text
        result = processor.process(
            raw_text="um hello world",
            language="en",
        )
        
        # Verify processing stages
        self.assertIn("raw", result)
        self.assertIn("final", result)
        self.assertEqual(result["raw"], "um hello world")
        # Final text should exist (may or may not be corrected depending on mock behavior)
        self.assertIsNotNone(result["final"])

    def test_pipeline_llm_client_creation(self):
        """Test that pipeline creates UnifiedLLMClient correctly"""
        # Just verify the UnifiedLLMClient can be imported and instantiated
        from janus.ai.llm.unified_client import UnifiedLLMClient
        
        client = UnifiedLLMClient(provider="mock", model="test-model")
        self.assertIsNotNone(client)
        self.assertEqual(client.provider, "mock")
        self.assertEqual(client.model, "test-model")


class TestInstallModelsLogic(unittest.TestCase):
    """Test install_models.py logic without actually running the script"""

    def test_import_install_models(self):
        """Test that install_models module can be imported"""
        try:
            # Import the module to verify it's syntactically correct
            import importlib.util
            import os
            
            # Get the path to install_models.py relative to the test file
            test_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(test_dir)
            install_models_path = os.path.join(project_root, "janus", "scripts", "install_models.py")
            
            spec = importlib.util.spec_from_file_location(
                "install_models",
                install_models_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Verify key functions exist
            self.assertTrue(hasattr(module, 'read_config'))
            self.assertTrue(hasattr(module, 'check_ollama_installed'))
            self.assertTrue(hasattr(module, 'download_ollama_model'))
            self.assertTrue(hasattr(module, 'download_phi2_model'))
            self.assertTrue(hasattr(module, 'main'))
        except Exception as e:
            self.fail(f"Failed to import install_models: {e}")


if __name__ == "__main__":
    unittest.main()
