"""
Tests for orphan component integration (TICKET-322, TICKET-323, TICKET-324).

These tests verify that the previously orphan components (ContextRanker, 
ClipboardManager, UndoManager) are properly integrated into the main pipeline.
"""
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from janus.runtime.core.context_ranker import ContextRanker
from janus.runtime.core.contracts import ActionResult, Intent
from janus.runtime.core import MemoryEngine
from janus.runtime.core.settings import DatabaseSettings


def create_mock_settings():
    """Create a properly configured mock Settings object."""
    settings = MagicMock()
    
    # LLM settings
    settings.llm.provider = "mock"
    settings.llm.model = "mock"
    settings.llm.model_path = None
    settings.llm.temperature = 0.7
    settings.llm.max_tokens = 2048
    settings.llm.request_timeout = 30
    settings.llm.fallback_providers = []
    
    # TTS settings
    settings.tts.voice = None
    settings.tts.rate = 1.0
    settings.tts.volume = 1.0
    settings.tts.lang = "en"
    
    # Async vision monitor settings
    settings.async_vision_monitor.enable_monitor = False
    settings.async_vision_monitor.check_interval_ms = 500
    settings.async_vision_monitor.enable_popup_detection = False
    settings.async_vision_monitor.enable_error_detection = False
    
    # Execution settings
    settings.execution.enable_vision_recovery = False
    settings.execution.enable_replanning = False
    settings.execution.max_retries = 1
    
    # Features settings
    settings.features.enable_semantic_correction = False
    
    # Language settings
    settings.language.default = "fr"
    
    # Whisper settings
    settings.whisper.enable_context_buffer = False
    settings.whisper.semantic_correction_model_path = None
    settings.whisper.enable_corrections = False
    settings.whisper.models_dir = None
    
    return settings


class TestContextRankerIntegration(unittest.TestCase):
    """Test ContextRanker integration with pipeline (TICKET-322)."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
        self.temp_db.close()
        
        # Create settings with temp database
        self.db_settings = DatabaseSettings(path=self.temp_db.name)
        self.memory = MemoryEngine(self.db_settings)
        self.session_id = self.memory.create_session()

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass

    def test_context_ranker_lazy_loading(self):
        """Test that ContextRanker is lazy-loaded in pipeline."""
        from janus.runtime.core.pipeline import JanusPipeline
        
        settings = create_mock_settings()
        
        pipeline = JanusPipeline(
            settings=settings,
            memory=self.memory,
            session_id=self.session_id,
            enable_voice=False,
            enable_llm_reasoning=False,
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
        )
        
        # Context ranker should not be loaded yet
        self.assertIsNone(pipeline._context_ranker)
        
        # Access the property to trigger lazy loading
        ranker = pipeline.context_ranker
        
        # Now it should be loaded
        self.assertIsNotNone(pipeline._context_ranker)
        self.assertIsInstance(ranker, ContextRanker)

    def test_context_ranker_ranks_file_history(self):
        """Test that context ranker properly ranks file history."""
        ranker = ContextRanker(decay_halflife_hours=24.0)
        
        # Create context items with different relevance
        context_items = [
            {
                "type": "file",
                "data": {"file_path": "/old/file.txt", "intent": "open_file"},
                "timestamp": datetime.now().isoformat(),
            },
            {
                "type": "file",
                "data": {"file_path": "/project/main.py", "intent": "save_file"},
                "timestamp": datetime.now().isoformat(),
            },
            {
                "type": "app",
                "data": {"app_name": "Chrome"},
                "timestamp": datetime.now().isoformat(),
            },
        ]
        
        # Intent looking for file operations
        intent = Intent(
            action="open_file",
            confidence=0.9,
            parameters={"path": "/project/main.py"}
        )
        
        # Rank items
        ranked = ranker.rank_context_items(context_items, intent, max_items=5)
        
        # Should have ranked items
        self.assertGreater(len(ranked), 0)
        
        # Each item should have a score
        for item, score in ranked:
            self.assertIsInstance(score, float)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)


class TestClipboardManagerIntegration(unittest.TestCase):
    """Test ClipboardManager integration with pipeline (TICKET-323)."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
        self.temp_db.close()
        
        # Create temporary clipboard history file
        self.temp_clipboard = tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json"
        )
        self.temp_clipboard.close()
        
        self.db_settings = DatabaseSettings(path=self.temp_db.name)
        self.memory = MemoryEngine(self.db_settings)
        self.session_id = self.memory.create_session()

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
        try:
            os.unlink(self.temp_clipboard.name)
        except:
            pass

    def test_clipboard_manager_lazy_loading(self):
        """Test that ClipboardManager is lazy-loaded in pipeline."""
        from janus.platform.clipboard.clipboard_manager import ClipboardManager
        from janus.runtime.core.pipeline import JanusPipeline
        
        settings = create_mock_settings()
        
        pipeline = JanusPipeline(
            settings=settings,
            memory=self.memory,
            session_id=self.session_id,
            enable_voice=False,
            enable_llm_reasoning=False,
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
        )
        
        # Clipboard manager should not be loaded yet
        self.assertIsNone(pipeline._clipboard_manager)
        
        # Access the property to trigger lazy loading
        manager = pipeline.clipboard_manager
        
        # Now it should be loaded
        self.assertIsNotNone(pipeline._clipboard_manager)
        self.assertIsInstance(manager, ClipboardManager)

    def test_clipboard_context_loading(self):
        """Test that _load_clipboard_context uses ClipboardManager."""
        from janus.platform.clipboard.clipboard_manager import ClipboardManager
        from janus.runtime.core.pipeline import JanusPipeline
        
        settings = create_mock_settings()
        
        pipeline = JanusPipeline(
            settings=settings,
            memory=self.memory,
            session_id=self.session_id,
            enable_voice=False,
            enable_llm_reasoning=False,
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
        )
        
        # Mock clipboard manager with test content
        mock_manager = MagicMock(spec=ClipboardManager)
        mock_entry = MagicMock()
        mock_entry.content = "Test clipboard content"
        mock_manager.get_current.return_value = mock_entry
        pipeline._clipboard_manager = mock_manager
        
        # Load clipboard context
        content = pipeline._load_clipboard_context("test-request")
        
        # Should have loaded via ClipboardManager
        self.assertEqual(content, "Test clipboard content")
        mock_manager.get_current.assert_called_once()


class TestUndoManagerIntegration(unittest.TestCase):
    """Test UndoManager integration with AgentExecutorV3 (TICKET-324)."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
        self.temp_db.close()

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass

    def test_undo_manager_lazy_loading(self):
        """Test that UndoManager is lazy-loaded in executor."""
        from janus.runtime.core.agent_executor_v3 import AgentExecutorV3
        from janus.persistence.undo_manager import UndoManager
        
        executor = AgentExecutorV3(
            enable_vision_recovery=False,
            enable_replanning=False,
        )
        
        # Undo manager should not be loaded yet
        self.assertIsNone(executor._undo_manager)
        
        # Access the property to trigger lazy loading
        manager = executor.undo_manager
        
        # Now it should be loaded
        self.assertIsNotNone(executor._undo_manager)
        self.assertIsInstance(manager, UndoManager)

    def test_undo_registration_on_success(self):
        """Test that successful actions are registered with UndoManager."""
        from janus.runtime.core.agent_executor_v3 import AgentExecutorV3
        from janus.persistence.undo_manager import UndoManager
        
        executor = AgentExecutorV3(
            enable_vision_recovery=False,
            enable_replanning=False,
        )
        
        # Mock the undo manager
        mock_undo = MagicMock(spec=UndoManager)
        mock_undo.record_undoable_action.return_value = 1
        executor._undo_manager = mock_undo
        
        # Create a successful action result
        result = ActionResult(
            action_type="file.create",
            success=True,
            message="File created",
            data={"path": "/test/file.txt"},
        )
        
        # Register the action
        executor._register_undo_action(
            module="file",
            action="create",
            args={"path": "/test/file.txt"},
            result=result,
            step_id="step_1",
        )
        
        # Verify undo was registered
        mock_undo.record_undoable_action.assert_called_once()
        call_args = mock_undo.record_undoable_action.call_args
        self.assertEqual(call_args.kwargs["action_type"], "file.create")
        self.assertIn("path", call_args.kwargs["undo_data"])

    def test_undo_data_building(self):
        """Test that undo data is correctly built for different actions."""
        from janus.runtime.core.agent_executor_v3 import AgentExecutorV3
        
        executor = AgentExecutorV3(
            enable_vision_recovery=False,
            enable_replanning=False,
        )
        
        # Test file create → undo with delete
        result = ActionResult(
            action_type="file.create",
            success=True,
            data={},
        )
        undo_data = executor._build_undo_data(
            "file", "create", {"path": "/test/file.txt"}, result
        )
        self.assertIsNotNone(undo_data)
        self.assertEqual(undo_data["action"], "delete")
        self.assertEqual(undo_data["path"], "/test/file.txt")
        
        # Test system open_application → undo with close
        result = ActionResult(
            action_type="system.open_application",
            success=True,
            data={},
        )
        undo_data = executor._build_undo_data(
            "system", "open_application", {"app_name": "Chrome"}, result
        )
        self.assertIsNotNone(undo_data)
        self.assertEqual(undo_data["action"], "close_application")
        self.assertEqual(undo_data["app_name"], "Chrome")
        
        # Test non-undoable action
        result = ActionResult(
            action_type="browser.navigate",
            success=True,
            data={},
        )
        undo_data = executor._build_undo_data(
            "browser", "navigate", {"url": "https://example.com"}, result
        )
        self.assertIsNone(undo_data)


class TestPipelineFileHistoryRanking(unittest.TestCase):
    """Test that file history uses ContextRanker in pipeline (TICKET-322)."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
        self.temp_db.close()
        
        self.db_settings = DatabaseSettings(path=self.temp_db.name)
        self.memory = MemoryEngine(self.db_settings)
        self.session_id = self.memory.create_session()

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass

    def test_file_history_context_returns_ranked_items(self):
        """Test that _load_file_history_context returns ranked items."""
        from janus.runtime.core.pipeline import JanusPipeline
        
        settings = create_mock_settings()
        
        pipeline = JanusPipeline(
            settings=settings,
            memory=self.memory,
            session_id=self.session_id,
            enable_voice=False,
            enable_llm_reasoning=False,
            enable_vision=False,
            enable_learning=False,
            enable_tts=False,
        )
        
        # Store some file-related commands
        intent = Intent(action="open_file", confidence=0.9, parameters={"path": "/test.py"})
        self.memory.store_command(
            session_id=self.session_id,
            request_id="req1",
            raw_command="open file test.py",
            intent=intent,
        )
        
        # Load file history
        file_history = pipeline._load_file_history_context("test-request")
        
        # If we have history, it should include relevance scores
        if file_history:
            for item in file_history:
                # Each item should have a relevance_score field from ranking
                self.assertIn("relevance_score", item)
                self.assertIsInstance(item["relevance_score"], float)


if __name__ == "__main__":
    unittest.main()

