"""
Tests for TICKET-305: Context Router Pipeline Integration

Tests the integration of ContextRouter into JanusPipeline to ensure
smart context pruning works correctly.
"""
import unittest
from unittest.mock import MagicMock, patch

from janus.runtime.core.pipeline import JanusPipeline
from janus.runtime.core import MemoryEngine
from janus.runtime.core.settings import Settings


class TestContextRouterPipelineIntegration(unittest.TestCase):
    """Test ContextRouter integration in JanusPipeline"""

    def setUp(self):
        """Set up test pipeline with mocked components"""
        self.settings = Settings()
        self.memory = MagicMock(spec=MemoryEngine)
        self.memory.create_session.return_value = "test-session-id"
        self.memory.list_all_sessions.return_value = []
        
    def test_pipeline_has_context_router_property(self):
        """Test that JanusPipeline has context_router property"""
        with patch.object(JanusPipeline, '_load_recent_session_context'):
            pipeline = JanusPipeline(
                settings=self.settings,
                memory=self.memory,
                enable_llm_reasoning=False,  # Disable to avoid LLM init
            )
            
            # Should have context_router property
            self.assertTrue(hasattr(pipeline, 'context_router'))
            self.assertTrue(hasattr(pipeline, '_context_router'))
    
    def test_pipeline_context_router_lazy_loading(self):
        """Test that context_router is lazy-loaded"""
        with patch.object(JanusPipeline, '_load_recent_session_context'):
            pipeline = JanusPipeline(
                settings=self.settings,
                memory=self.memory,
                enable_llm_reasoning=False,
            )
            
            # Initially None
            self.assertIsNone(pipeline._context_router)
            
            # Access property triggers loading
            router = pipeline.context_router
            self.assertIsNotNone(router)
            self.assertIsNotNone(pipeline._context_router)
    
    def test_pipeline_has_build_pruned_context_method(self):
        """Test that pipeline has _build_pruned_context method"""
        with patch.object(JanusPipeline, '_load_recent_session_context'):
            pipeline = JanusPipeline(
                settings=self.settings,
                memory=self.memory,
                enable_llm_reasoning=False,
            )
            
            self.assertTrue(hasattr(pipeline, '_build_pruned_context'))
            self.assertTrue(callable(pipeline._build_pruned_context))
    
    def test_build_pruned_context_empty_keys(self):
        """Test _build_pruned_context returns empty dict for empty keys"""
        with patch.object(JanusPipeline, '_load_recent_session_context'):
            pipeline = JanusPipeline(
                settings=self.settings,
                memory=self.memory,
                enable_llm_reasoning=False,
            )
            
            # Empty keys should return empty context
            context = pipeline._build_pruned_context([], "test-request-id")
            self.assertEqual(context, {})
    
    def test_build_pruned_context_with_clipboard(self):
        """Test _build_pruned_context loads clipboard when requested"""
        with patch.object(JanusPipeline, '_load_recent_session_context'):
            pipeline = JanusPipeline(
                settings=self.settings,
                memory=self.memory,
                enable_llm_reasoning=False,
            )
            
            # Mock clipboard loading
            with patch.object(pipeline, '_load_clipboard_context', return_value="test clipboard"):
                context = pipeline._build_pruned_context(["clipboard"], "test-request-id")
                self.assertIn("clipboard", context)
                self.assertEqual(context["clipboard"], "test clipboard")
    
    def test_build_pruned_context_with_file_history(self):
        """Test _build_pruned_context loads file history when requested"""
        with patch.object(JanusPipeline, '_load_recent_session_context'):
            pipeline = JanusPipeline(
                settings=self.settings,
                memory=self.memory,
                enable_llm_reasoning=False,
            )
            
            # Mock file history loading
            file_data = [{"command": "open file.txt", "intent": "open_file"}]
            with patch.object(pipeline, '_load_file_history_context', return_value=file_data):
                context = pipeline._build_pruned_context(["file_history"], "test-request-id")
                self.assertIn("file_history", context)
                self.assertEqual(context["file_history"], file_data)
    
    def test_build_pruned_context_multiple_keys(self):
        """Test _build_pruned_context handles multiple keys"""
        with patch.object(JanusPipeline, '_load_recent_session_context'):
            pipeline = JanusPipeline(
                settings=self.settings,
                memory=self.memory,
                enable_llm_reasoning=False,
            )
            
            # Mock multiple context loaders
            with patch.object(pipeline, '_load_clipboard_context', return_value="clipboard text"):
                with patch.object(pipeline, '_load_file_history_context', return_value=[{"file": "test"}]):
                    context = pipeline._build_pruned_context(
                        ["clipboard", "file_history"], 
                        "test-request-id"
                    )
                    
                    self.assertIn("clipboard", context)
                    self.assertIn("file_history", context)
                    self.assertEqual(len(context), 2)


class TestContextRouterDoD(unittest.TestCase):
    """
    Test Definition of Done criteria from TICKET-305 at pipeline level.
    
    DoD:
    [ ] A command "Ouvre Safari" does NOT inject OCR or Clipboard into Reasoner prompt
    [ ] A command "Résume cette page" DOES inject browser_content or clipboard
    """

    def setUp(self):
        """Set up test pipeline"""
        self.settings = Settings()
        self.memory = MagicMock(spec=MemoryEngine)
        self.memory.create_session.return_value = "test-session-id"
        self.memory.list_all_sessions.return_value = []
        self.memory.get_command_history.return_value = []

    def test_dod_simple_command_no_context_injection(self):
        """
        DoD: "Ouvre Safari" should NOT inject OCR or Clipboard.
        This verifies that simple commands get empty context.
        """
        with patch.object(JanusPipeline, '_load_recent_session_context'):
            pipeline = JanusPipeline(
                settings=self.settings,
                memory=self.memory,
                enable_llm_reasoning=False,
            )
            
            # Get context requirements for simple command
            router = pipeline.context_router
            requirements = router.get_requirements("Ouvre Safari")
            
            # Should NOT require vision (OCR) or clipboard
            self.assertNotIn("vision", requirements)
            self.assertNotIn("clipboard", requirements)
            
            # Build context should return empty dict
            context = pipeline._build_pruned_context(requirements, "test-id")
            self.assertEqual(context, {})

    def test_dod_summarize_requires_browser_content(self):
        """
        DoD: "Résume cette page" SHOULD inject browser_content.
        """
        with patch.object(JanusPipeline, '_load_recent_session_context'):
            pipeline = JanusPipeline(
                settings=self.settings,
                memory=self.memory,
                enable_llm_reasoning=False,
            )
            
            # Get context requirements for summarize command
            router = pipeline.context_router
            requirements = router.get_requirements("Résume cette page")
            
            # Should require browser_content
            self.assertIn("browser_content", requirements)


if __name__ == "__main__":
    unittest.main()
