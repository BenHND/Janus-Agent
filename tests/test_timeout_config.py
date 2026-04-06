"""
Test for timeout configuration fix (Issue #423)
Validates that the timeout values are properly configured for LLM cold starts.
"""
import unittest
from janus.ai.reasoning.reasoner_llm import LLMConfig, LLMBackend, ReasonerLLM
from janus.constants import LLM_REQUEST_TIMEOUT, LLM_RETRY_TIMEOUT


class TestTimeoutConfiguration(unittest.TestCase):
    """Test timeout configuration for LLM requests"""
    
    def test_constants_exist(self):
        """Test that LLM timeout constants exist and have reasonable values"""
        # Check constants are defined
        self.assertIsNotNone(LLM_REQUEST_TIMEOUT)
        self.assertIsNotNone(LLM_RETRY_TIMEOUT)
        
        # Check reasonable values (> 60 seconds for cold starts)
        self.assertGreaterEqual(LLM_REQUEST_TIMEOUT, 60, 
            "LLM_REQUEST_TIMEOUT should be >= 60s for cold starts")
        self.assertGreaterEqual(LLM_RETRY_TIMEOUT, 30,
            "LLM_RETRY_TIMEOUT should be >= 30s")
        
        # Retry should be shorter than initial timeout
        self.assertLess(LLM_RETRY_TIMEOUT, LLM_REQUEST_TIMEOUT,
            "Retry timeout should be shorter than initial timeout")
    
    def test_llm_config_defaults(self):
        """Test that LLMConfig has proper default timeout values using constants"""
        config = LLMConfig(backend=LLMBackend.MOCK)
        
        # Check timeout values use the constants (converted to milliseconds)
        self.assertEqual(config.timeout_ms, LLM_REQUEST_TIMEOUT * 1000, 
            f"Default timeout_ms should be {LLM_REQUEST_TIMEOUT}s ({LLM_REQUEST_TIMEOUT * 1000}ms)")
        self.assertEqual(config.short_timeout_ms, LLM_RETRY_TIMEOUT * 1000,
            f"Default short_timeout_ms should be {LLM_RETRY_TIMEOUT}s ({LLM_RETRY_TIMEOUT * 1000}ms)")
    
    def test_custom_timeout_config(self):
        """Test that custom timeout can be configured"""
        config = LLMConfig(
            backend=LLMBackend.MOCK,
            timeout_ms=180000,  # 3 minutes
            short_timeout_ms=90000  # 1.5 minutes
        )
        
        self.assertEqual(config.timeout_ms, 180000)
        self.assertEqual(config.short_timeout_ms, 90000)
    
    def test_reasoner_llm_uses_config_timeout(self):
        """Test that ReasonerLLM uses the timeout from config"""
        config = LLMConfig(
            backend=LLMBackend.MOCK,
            timeout_ms=150000,
            short_timeout_ms=75000
        )
        
        llm = ReasonerLLM(backend="mock", config=config)
        
        self.assertEqual(llm.config.timeout_ms, 150000)
        self.assertEqual(llm.config.short_timeout_ms, 75000)
    
    def test_reasoner_llm_default_config(self):
        """Test that ReasonerLLM uses default config with correct timeouts"""
        llm = ReasonerLLM(backend="mock")
        
        # Should use the constants from janus.constants
        self.assertEqual(llm.config.timeout_ms, LLM_REQUEST_TIMEOUT * 1000)
        self.assertEqual(llm.config.short_timeout_ms, LLM_RETRY_TIMEOUT * 1000)


class TestSettingsIntegration(unittest.TestCase):
    """Test settings integration for timeout configuration"""
    
    def test_settings_load_timeout(self):
        """Test that settings properly loads timeout values"""
        from janus.runtime.core.settings import Settings, LLMSettings
        
        # Check default values in LLMSettings
        default_settings = LLMSettings()
        self.assertEqual(default_settings.request_timeout, 120,
            "Default request_timeout should be 120s")
        self.assertEqual(default_settings.retry_timeout, 60,
            "Default retry_timeout should be 60s")


if __name__ == "__main__":
    unittest.main()


class TestLLMWarmup(unittest.TestCase):
    """Test LLM model warmup/preloading functionality"""
    
    def test_ollama_client_has_warmup_method(self):
        """Test that OllamaClient has warmup_model method"""
        from janus.ai.llm.ollama_client import OllamaClient
        
        client = OllamaClient()
        self.assertTrue(hasattr(client, 'warmup_model'))
        self.assertTrue(callable(getattr(client, 'warmup_model')))
    
    def test_reasoner_has_warmup_async_method(self):
        """Test that ReasonerLLM has warmup_model_async method"""
        from janus.ai.reasoning.reasoner_llm import ReasonerLLM
        
        reasoner = ReasonerLLM(backend="mock")
        self.assertTrue(hasattr(reasoner, 'warmup_model_async'))
        self.assertTrue(callable(getattr(reasoner, 'warmup_model_async')))
    
    def test_mock_backend_warmup_succeeds(self):
        """Test that mock backend warmup returns True"""
        import asyncio
        from janus.ai.reasoning.reasoner_llm import ReasonerLLM
        
        reasoner = ReasonerLLM(backend="mock")
        
        # Run async warmup
        result = asyncio.run(reasoner.warmup_model_async())
        self.assertTrue(result, "Mock backend warmup should succeed")


class TestPipelinePreload(unittest.TestCase):
    """Test that pipeline properly preloads models at startup (Issue #429)"""
    
    def test_pipeline_has_preload_method(self):
        """Test that JanusPipeline has preload_llm_model_async method"""
        from janus.runtime.core.pipeline import JanusPipeline
        
        self.assertTrue(hasattr(JanusPipeline, 'preload_llm_model_async'))
        self.assertTrue(callable(getattr(JanusPipeline, 'preload_llm_model_async')))
    
    def test_pipeline_preload_uses_correct_property(self):
        """Test that preload_llm_model_async uses reasoner_llm property (fixes #429)
        
        This test verifies that the bug where the method used self._reasoner
        (which doesn't exist) has been fixed to use self.reasoner_llm.
        """
        import inspect
        from janus.runtime.core.pipeline import JanusPipeline
        
        # Get the source of the method
        source = inspect.getsource(JanusPipeline.preload_llm_model_async)
        
        # Verify it does NOT use the wrong variable name
        self.assertNotIn('self._reasoner', source,
            "preload_llm_model_async should NOT use self._reasoner (doesn't exist)")
        
        # Verify it DOES use the correct property
        self.assertIn('reasoner_llm', source,
            "preload_llm_model_async should use self.reasoner_llm property")
    
    def test_pipeline_has_warmup_systems_method(self):
        """Test that JanusPipeline has warmup_systems method (Issue #429 fix)
        
        The warmup_systems method forces the LLM model into VRAM by sending
        a dummy inference request during startup.
        """
        from janus.runtime.core.pipeline import JanusPipeline
        
        self.assertTrue(hasattr(JanusPipeline, 'warmup_systems'))
        self.assertTrue(callable(getattr(JanusPipeline, 'warmup_systems')))
    
    def test_warmup_systems_uses_run_inference(self):
        """Test that warmup_systems calls _run_inference to force model load"""
        import inspect
        from janus.runtime.core.pipeline import JanusPipeline
        
        source = inspect.getsource(JanusPipeline.warmup_systems)
        
        # Verify it calls _run_inference to force the model into memory
        self.assertIn('_run_inference', source,
            "warmup_systems should call _run_inference to force model into VRAM")
    
    def test_warmup_systems_initializes_context_router(self):
        """Test that warmup_systems initializes ContextRouter to avoid lazy loading delay"""
        import inspect
        from janus.runtime.core.pipeline import JanusPipeline
        
        source = inspect.getsource(JanusPipeline.warmup_systems)
        
        # Verify it initializes context_router to prevent lazy loading during first command
        self.assertIn('context_router', source,
            "warmup_systems should initialize context_router to prevent lazy loading delay")
