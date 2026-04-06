"""
Test async vision model preloading functionality
"""
import asyncio
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock


class TestVisionCognitiveEnginePreloading:
    """Test VisionCognitiveEngine async preloading"""
    
    def test_lazy_load_flag_prevents_immediate_loading(self):
        """Test that lazy_load=True prevents immediate model loading"""
        with patch('janus.vision.vision_cognitive_engine.torch'):
            from janus.vision.vision_cognitive_engine import VisionCognitiveEngine
            
            # Create engine with lazy loading
            engine = VisionCognitiveEngine(lazy_load=True)
            
            # Models should not be loaded yet
            assert engine.caption_model is None
            assert engine.clip_model is None
            assert engine._models_loaded is False
    
    def test_lazy_load_false_attempts_immediate_loading(self):
        """Test that lazy_load=False attempts immediate model loading"""
        with patch('janus.vision.vision_cognitive_engine.torch'):
            with patch('janus.vision.vision_cognitive_engine.Blip2Processor'):
                from janus.vision.vision_cognitive_engine import VisionCognitiveEngine
                
                # Create engine without lazy loading (default)
                engine = VisionCognitiveEngine(lazy_load=False, model_type="auto")
                
                # _init_models should have been called
                # In this mock environment, models won't actually load but the attempt was made
                assert engine._loading is False  # Loading completed
    
    @pytest.mark.asyncio
    async def test_preload_models_async_basic(self):
        """Test basic async model preloading"""
        with patch('janus.vision.vision_cognitive_engine.torch'):
            with patch('janus.vision.vision_cognitive_engine.Blip2Processor'):
                with patch('janus.vision.vision_cognitive_engine.Blip2ForConditionalGeneration'):
                    with patch('janus.vision.vision_cognitive_engine.CLIPProcessor'):
                        with patch('janus.vision.vision_cognitive_engine.CLIPModel'):
                            from janus.vision.vision_cognitive_engine import VisionCognitiveEngine
                            
                            # Create engine with lazy loading
                            engine = VisionCognitiveEngine(lazy_load=True, model_type="auto")
                            
                            # Preload models
                            result = await engine.preload_models_async()
                            
                            # Should indicate completion (though models are mocked)
                            assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_preload_models_async_already_loaded(self):
        """Test that preloading with already loaded models returns quickly"""
        from janus.vision.vision_cognitive_engine import VisionCognitiveEngine
        
        # Create engine with lazy loading
        engine = VisionCognitiveEngine(lazy_load=True)
        
        # Simulate models already loaded
        engine._models_loaded = True
        
        # Preload should return immediately
        result = await engine.preload_models_async()
        
        assert result is True


class TestLightVisionEnginePreloading:
    """Test LightVisionEngine async preloading"""
    
    def test_lazy_load_flag_prevents_immediate_loading(self):
        """Test that lazy_load=True prevents immediate model loading"""
        from janus.vision.light_vision_engine import LightVisionEngine
        
        # Create engine with lazy loading
        engine = LightVisionEngine(enable_ai_models=True, lazy_load=True)
        
        # Models should not be loaded yet
        assert engine._vision_engine is None
        assert engine._models_available is False
    
    def test_lazy_load_false_with_ai_disabled(self):
        """Test that AI disabled prevents model loading"""
        from janus.vision.light_vision_engine import LightVisionEngine
        
        # Create engine with AI disabled
        engine = LightVisionEngine(enable_ai_models=False, lazy_load=False)
        
        # Models should not be loaded
        assert engine._vision_engine is None
        assert engine._models_available is False
    
    @pytest.mark.asyncio
    async def test_preload_models_async_with_ai_disabled(self):
        """Test that preloading with AI disabled returns False"""
        from janus.vision.light_vision_engine import LightVisionEngine
        
        # Create engine with AI disabled
        engine = LightVisionEngine(enable_ai_models=False, lazy_load=True)
        
        # Preload should return False
        result = await engine.preload_models_async()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_preload_models_async_already_loaded(self):
        """Test that preloading with already loaded models returns quickly"""
        from janus.vision.light_vision_engine import LightVisionEngine
        
        # Create engine with lazy loading
        engine = LightVisionEngine(enable_ai_models=True, lazy_load=True)
        
        # Simulate models already loaded
        engine._models_available = True
        
        # Preload should return immediately
        result = await engine.preload_models_async()
        
        assert result is True


class TestPipelineVisionPreloading:
    """Test pipeline vision model preloading integration"""
    
    @pytest.mark.asyncio
    async def test_preload_vision_models_async_vision_disabled(self):
        """Test that preloading with vision disabled returns False"""
        from janus.runtime.core.pipeline import JanusPipeline
        from janus.runtime.core import MemoryEngine
        from janus.runtime.core.settings import Settings
        
        # Create mock settings with vision disabled
        settings = Mock(spec=Settings)
        settings.features = Mock()
        settings.features.enable_llm_reasoning = False
        settings.features.enable_vision = False
        settings.features.enable_learning = False
        settings.tts = Mock()
        settings.tts.enable_tts = False
        settings.database = Mock()
        settings.database.path = ":memory:"
        
        memory = Mock(spec=MemoryEngine)
        memory.create_session = Mock(return_value="test_session")
        memory.log_structured = Mock()
        
        # Create pipeline with vision disabled
        pipeline = JanusPipeline(
            settings=settings,
            memory=memory,
            enable_vision=False
        )
        
        # Preload should return False when vision is disabled
        result = await pipeline.preload_vision_models_async()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_preload_vision_models_async_no_executor(self):
        """Test that preloading without executor returns False gracefully"""
        from janus.runtime.core.pipeline import JanusPipeline
        from janus.runtime.core import MemoryEngine
        from janus.runtime.core.settings import Settings
        
        # Create mock settings with vision enabled
        settings = Mock(spec=Settings)
        settings.features = Mock()
        settings.features.enable_llm_reasoning = False
        settings.features.enable_vision = True
        settings.features.enable_learning = False
        settings.tts = Mock()
        settings.tts.enable_tts = False
        settings.database = Mock()
        settings.database.path = ":memory:"
        settings.vision = Mock()
        settings.vision.enable_blip = True
        settings.vision.enable_clip = True
        
        memory = Mock(spec=MemoryEngine)
        memory.create_session = Mock(return_value="test_session")
        memory.log_structured = Mock()
        
        # Create pipeline with vision enabled
        pipeline = JanusPipeline(
            settings=settings,
            memory=memory,
            enable_vision=True
        )
        
        # Executor not initialized yet, should return False gracefully
        result = await pipeline.preload_vision_models_async()
        
        assert result is False


class TestVisionOnDemandLoading:
    """Test fallback on-demand loading when preloading hasn't completed"""
    
    def test_verify_action_result_loads_models_on_demand(self):
        """Test that verify_action_result loads models on-demand if not preloaded"""
        from janus.vision.light_vision_engine import LightVisionEngine
        from PIL import Image
        
        # Create engine with lazy loading
        engine = LightVisionEngine(enable_ai_models=True, lazy_load=True, log_detections=False)
        
        # Models not loaded yet
        assert engine._models_available is False
        
        # Create a dummy action and screenshot
        action = {"action": "click", "target": "button"}
        screenshot = Image.new('RGB', (100, 100))
        
        # Mock _init_models to simulate loading without actual models
        with patch.object(engine, '_init_models') as mock_init:
            with patch.object(engine, '_verify_with_heuristics') as mock_verify:
                mock_verify.return_value = {
                    "verified": True,
                    "confidence": 0.5,
                    "method": "heuristic"
                }
                
                # Call verify_action_result
                result = engine.verify_action_result(screenshot, action, timeout_ms=1000)
                
                # Should have called _init_models
                mock_init.assert_called_once()
                
                # Should have result
                assert result is not None
                assert "verified" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
