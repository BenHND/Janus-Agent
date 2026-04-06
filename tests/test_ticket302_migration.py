"""
Tests for FlorenceVisionEngine (TICKET-302)

Tests the Florence-2 based vision adapter for ultra-light screen understanding.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio


class TestFlorenceVisionEngineBasic:
    """Basic tests for FlorenceVisionEngine"""
    
    def test_import_florence_adapter(self):
        """Test that FlorenceVisionEngine can be imported"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        assert FlorenceVisionEngine is not None
    
    def test_class_constants(self):
        """Test class constants are defined correctly"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        # Model variants
        assert FlorenceVisionEngine.MODEL_BASE == "microsoft/Florence-2-base"
        assert FlorenceVisionEngine.MODEL_LARGE == "microsoft/Florence-2-large"
        
        # Task prompts
        assert FlorenceVisionEngine.TASK_CAPTION == "<CAPTION>"
        assert FlorenceVisionEngine.TASK_DETAILED_CAPTION == "<DETAILED_CAPTION>"
        assert FlorenceVisionEngine.TASK_OCR == "<OCR>"
        assert FlorenceVisionEngine.TASK_OCR_WITH_REGION == "<OCR_WITH_REGION>"
        assert FlorenceVisionEngine.TASK_OBJECT_DETECTION == "<OD>"
        assert FlorenceVisionEngine.TASK_PHRASE_GROUNDING == "<CAPTION_TO_PHRASE_GROUNDING>"
    
    def test_init_lazy_load(self):
        """Test initialization with lazy loading"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        # Initialize with lazy loading - should not load models
        engine = FlorenceVisionEngine(lazy_load=True)
        
        assert engine.model is None
        assert engine.processor is None
        assert engine._models_loaded is False
        assert engine._lazy_load is True
    
    def test_init_default_values(self):
        """Test default initialization values"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        engine = FlorenceVisionEngine(lazy_load=True)
        
        assert engine.model_variant == "base"
        assert engine.model_id == FlorenceVisionEngine.MODEL_BASE
        assert engine.enable_cache is True
        assert engine.cache_size == 50
    
    def test_init_large_variant(self):
        """Test initialization with large model variant"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        engine = FlorenceVisionEngine(model_variant="large", lazy_load=True)
        
        assert engine.model_variant == "large"
        assert engine.model_id == FlorenceVisionEngine.MODEL_LARGE
    
    def test_device_detection_cpu(self):
        """Test device detection returns valid values"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        engine = FlorenceVisionEngine(device="cpu", lazy_load=True)
        assert engine.device == "cpu"
    
    def test_is_available_false_when_lazy(self):
        """Test is_available returns False when models not loaded"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        engine = FlorenceVisionEngine(lazy_load=True)
        assert engine.is_available() is False
    
    def test_get_info(self):
        """Test get_info returns correct structure"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        engine = FlorenceVisionEngine(lazy_load=True)
        info = engine.get_info()
        
        assert info["engine"] == "florence2"
        assert info["model_variant"] == "base"
        assert info["model_id"] == "microsoft/Florence-2-base"
        assert info["available"] is False
        assert "cache_enabled" in info
        assert "cache_stats" in info
    
    def test_cache_operations(self):
        """Test cache clear and stats operations"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        engine = FlorenceVisionEngine(lazy_load=True)
        
        # Get initial cache stats
        stats = engine.get_cache_stats()
        assert stats["size"] == 0
        assert stats["max_size"] == 50
        assert stats["enabled"] is True
        
        # Clear cache (should work even if empty)
        engine.clear_cache()
        stats = engine.get_cache_stats()
        assert stats["size"] == 0


class TestFlorenceVisionEngineModuleImport:
    """Test Florence adapter import via vision module"""
    
    def test_lazy_import_from_vision_module(self):
        """Test FlorenceVisionEngine can be imported from vision module"""
        from janus import vision
        
        # Check it's in __all__
        assert "FlorenceVisionEngine" in vision.__all__
        
        # Test lazy import
        FVE = vision.FlorenceVisionEngine
        assert FVE.__name__ == "FlorenceVisionEngine"


class TestFlorenceVisionEngineMocked:
    """Tests with mocked model for functionality testing"""
    
    def test_describe_without_model_returns_fallback(self):
        """Test describe returns fallback when model not loaded"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        engine = FlorenceVisionEngine(lazy_load=True)
        
        # Create mock image
        mock_image = MagicMock()
        mock_image.size = (800, 600)
        
        result = engine.describe(mock_image)
        
        assert "description" in result
        assert result["method"] == "fallback"
        assert result["confidence"] == 0.1
        assert "error" in result
    
    def test_extract_text_without_model_returns_fallback(self):
        """Test extract_text returns fallback when model not loaded"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        engine = FlorenceVisionEngine(lazy_load=True)
        
        # Create mock image
        mock_image = MagicMock()
        mock_image.size = (800, 600)
        
        result = engine.extract_text(mock_image)
        
        assert "text" in result
        assert result["text"] == ""
        assert result["method"] == "fallback"
        assert "error" in result
    
    def test_find_element_without_model_returns_none(self):
        """Test find_element returns None when model not loaded"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        engine = FlorenceVisionEngine(lazy_load=True)
        
        # Create mock image
        mock_image = MagicMock()
        mock_image.size = (800, 600)
        
        result = engine.find_element(mock_image, "button")
        
        # Should return None when model not available
        assert result is None
    
    def test_detect_objects_without_model_returns_error(self):
        """Test detect_objects returns error when model not loaded"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        engine = FlorenceVisionEngine(lazy_load=True)
        
        # Create mock image
        mock_image = MagicMock()
        mock_image.size = (800, 600)
        
        result = engine.detect_objects(mock_image)
        
        assert "objects" in result
        assert result["objects"] == []
        assert "error" in result
    
    def test_detect_errors_without_model(self):
        """Test detect_errors works without model (uses OCR/caption fallback)"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        engine = FlorenceVisionEngine(lazy_load=True)
        
        # Create mock image
        mock_image = MagicMock()
        mock_image.size = (800, 600)
        
        result = engine.detect_errors(mock_image)
        
        assert "has_error" in result
        assert "confidence" in result
        assert "indicators" in result
        assert "duration_ms" in result
    
    def test_verify_action_result_without_model(self):
        """Test verify_action_result returns generic success when model not available"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        engine = FlorenceVisionEngine(lazy_load=True)
        
        # Create mock image
        mock_image = MagicMock()
        mock_image.size = (800, 600)
        
        result = engine.verify_action_result(
            mock_image, 
            "click", 
            {"element": "button"}
        )
        
        assert "verified" in result
        assert "confidence" in result
        assert "reason" in result


class TestFlorenceVisionEngineAsync:
    """Test async functionality"""
    
    @pytest.mark.asyncio
    async def test_preload_models_async_returns_false_on_failure(self):
        """Test preload_models_async returns False when import fails"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        engine = FlorenceVisionEngine(lazy_load=True)
        
        # Mock to simulate import failure
        with patch.object(engine, '_init_models', side_effect=ImportError("No module")):
            result = await engine.preload_models_async()
            # Should return False (models not available after failed load)
            assert result is False or engine._models_loaded is False
    
    @pytest.mark.asyncio
    async def test_preload_models_async_already_loaded(self):
        """Test preload_models_async returns True when already loaded"""
        from janus.vision.florence_adapter import FlorenceVisionEngine
        
        engine = FlorenceVisionEngine(lazy_load=True)
        engine._models_loaded = True  # Simulate already loaded
        
        result = await engine.preload_models_async()
        
        assert result is True


class TestReasonerLLMDefaultModel:
    """Test ReasonerLLM default model for TICKET-MIG-002"""
    
    def test_default_ollama_model_constant(self):
        """Test DEFAULT_OLLAMA_MODEL constant is set to qwen2.5:7b-instruct"""
        from janus.ai.reasoning.reasoner_llm import ReasonerLLM
        
        assert ReasonerLLM.DEFAULT_OLLAMA_MODEL == "qwen2.5:7b-instruct"
    
    def test_ollama_backend_uses_default_model(self):
        """Test Ollama backend uses qwen2.5:7b-instruct as default when no model specified"""
        from janus.ai.reasoning.reasoner_llm import ReasonerLLM
        
        # Create subclass that doesn't initialize backend
        class MockReasonerLLM(ReasonerLLM):
            def _initialize_backend(self):
                self.llm = 'mock'
                self.available = True
        
        # Create with ollama backend but no model_name
        reasoner = MockReasonerLLM(backend='ollama')
        
        assert reasoner.model_name == "qwen2.5:7b-instruct"
    
    def test_ollama_backend_respects_explicit_model(self):
        """Test Ollama backend uses explicit model when provided"""
        from janus.ai.reasoning.reasoner_llm import ReasonerLLM
        
        class MockReasonerLLM(ReasonerLLM):
            def _initialize_backend(self):
                self.llm = 'mock'
                self.available = True
        
        reasoner = MockReasonerLLM(backend='ollama', model_name='mistral')
        
        assert reasoner.model_name == "mistral"
    
    def test_mock_backend_no_default_model(self):
        """Test mock backend doesn't set default model"""
        from janus.ai.reasoning.reasoner_llm import ReasonerLLM
        
        reasoner = ReasonerLLM(backend='mock')
        
        # Mock backend without explicit model should be None
        assert reasoner.model_name is None


class TestConfigChanges:
    """Test configuration changes for TICKET-MIG-002"""
    
    def test_config_llm_model_is_llama(self):
        """Test config.ini has llama3.2 as default LLM model"""
        import configparser
        
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        assert config.get('llm', 'model') == 'llama3.2'
    
    def test_config_vision_engine_is_florence(self):
        """Test config.ini has florence2 as default vision engine"""
        import configparser
        
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        assert config.get('vision', 'vision_engine') == 'florence2'
    
    def test_config_florence_only(self):
        """Test config.ini has no legacy enable_blip/enable_clip settings"""
        import configparser
        
        config = configparser.ConfigParser()
        config.read('config.ini')
        
        # TICKET-302: No legacy settings - only florence2
        assert not config.has_option('vision', 'enable_florence')
        assert not config.has_option('vision', 'enable_blip')
        assert not config.has_option('vision', 'enable_clip')


class TestSettingsChanges:
    """Test settings changes for TICKET-302"""
    
    def test_vision_settings_florence_only(self):
        """Test VisionSettings dataclass has only Florence-2 field"""
        from janus.runtime.core.settings import VisionSettings
        
        # Check default values
        vs = VisionSettings()
        
        assert hasattr(vs, 'vision_engine')
        assert vs.vision_engine == "florence2"
        # TICKET-302: No legacy fields
        assert not hasattr(vs, 'enable_florence')
        assert not hasattr(vs, 'enable_blip')
        assert not hasattr(vs, 'enable_clip')
    
    def test_settings_loads_florence_config(self):
        """Test Settings class loads Florence-2 configuration"""
        from janus.runtime.core.settings import Settings
        
        settings = Settings()
        
        assert settings.vision.vision_engine == "florence2"
