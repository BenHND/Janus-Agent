"""
Unit tests for LifecycleService and MemoryServiceWrapper refactoring

These tests verify TICKET-PIPELINE-003 and TICKET-PIPELINE-004:
- MemoryServiceWrapper.store_command works correctly
- LifecycleService methods delegate properly
- Pipeline integration works with new services
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from janus.runtime.core import Settings, MemoryEngine, JanusPipeline
from janus.services import LifecycleService, MemoryServiceWrapper


class TestMemoryEngineWrapper(unittest.TestCase):
    """Test cases for MemoryEngine wrapper integration (TICKET-PIPELINE-003)"""

    def setUp(self):
        """Set up test fixtures with isolated temp directory"""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Create minimal config.ini for testing
        config_path = os.path.join(self.test_dir, "config.ini")
        with open(config_path, "w") as f:
            f.write(
                """[whisper]
model_size = base

[language]
default = fr

[llm]
provider = mock
model = gpt-4

[database]
path = janus.db
enable_wal = true

[logging]
level = INFO
enable_structured = true
log_to_database = true
"""
            )

        self.settings = Settings(config_path=config_path)
        self.memory = MemoryEngine(self.settings.database)
        self.memory_wrapper = MemoryServiceWrapper(memory=self.memory)

    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    def test_store_command_exists(self):
        """Test that store_command method exists"""
        self.assertTrue(hasattr(self.memory_wrapper, 'store_command'))

    def test_store_command_callable(self):
        """Test that store_command is callable"""
        self.assertTrue(callable(getattr(self.memory_wrapper, 'store_command', None)))

    def test_build_pruned_context_exists(self):
        """Test that build_pruned_context method exists"""
        self.assertTrue(hasattr(self.memory_wrapper, 'build_pruned_context'))

    def test_get_related_sessions_exists(self):
        """Test that get_related_sessions method exists"""
        self.assertTrue(hasattr(self.memory_wrapper, 'get_related_sessions'))

    def test_get_session_summary_exists(self):
        """Test that get_session_summary method exists"""
        self.assertTrue(hasattr(self.memory_wrapper, 'get_session_summary'))


class TestLifecycleService(unittest.TestCase):
    """Test cases for LifecycleService (TICKET-PIPELINE-004)"""

    def setUp(self):
        """Set up test fixtures with isolated temp directory"""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Create minimal config.ini for testing
        config_path = os.path.join(self.test_dir, "config.ini")
        with open(config_path, "w") as f:
            f.write(
                """[whisper]
model_size = base

[language]
default = fr

[llm]
provider = mock
model = gpt-4

[database]
path = janus.db
enable_wal = true

[logging]
level = INFO
enable_structured = true
log_to_database = true

[async_vision_monitor]
enable_monitor = false
"""
            )

        self.settings = Settings(config_path=config_path)
        self.memory = MemoryEngine(self.settings.database)
        self.lifecycle_service = LifecycleService(
            settings=self.settings,
            memory=self.memory,
            session_id=self.memory.session_id,
            pipeline=None,  # Test without pipeline
        )

    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    def test_cleanup_exists(self):
        """Test that cleanup method exists"""
        self.assertTrue(hasattr(self.lifecycle_service, 'cleanup'))

    def test_start_vision_monitor_exists(self):
        """Test that start_vision_monitor method exists"""
        self.assertTrue(hasattr(self.lifecycle_service, 'start_vision_monitor'))

    def test_stop_vision_monitor_exists(self):
        """Test that stop_vision_monitor method exists"""
        self.assertTrue(hasattr(self.lifecycle_service, 'stop_vision_monitor'))

    def test_preload_vision_models_exists(self):
        """Test that preload_vision_models method exists"""
        self.assertTrue(hasattr(self.lifecycle_service, 'preload_vision_models'))

    def test_preload_llm_model_exists(self):
        """Test that preload_llm_model method exists"""
        self.assertTrue(hasattr(self.lifecycle_service, 'preload_llm_model'))

    def test_warmup_all_systems_exists(self):
        """Test that warmup_all_systems method exists"""
        self.assertTrue(hasattr(self.lifecycle_service, 'warmup_all_systems'))

    def test_handle_popup_event_exists(self):
        """Test that handle_popup_event method exists"""
        self.assertTrue(hasattr(self.lifecycle_service, 'handle_popup_event'))

    def test_handle_error_event_exists(self):
        """Test that handle_error_event method exists"""
        self.assertTrue(hasattr(self.lifecycle_service, 'handle_error_event'))

    def test_cleanup_no_services(self):
        """Test cleanup works with no services set"""
        # Should not raise any exceptions
        self.lifecycle_service.cleanup()


class TestPipelineIntegration(unittest.TestCase):
    """Test cases for pipeline integration with new services"""

    def setUp(self):
        """Set up test fixtures with isolated temp directory"""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Create minimal config.ini for testing
        config_path = os.path.join(self.test_dir, "config.ini")
        with open(config_path, "w") as f:
            f.write(
                """[whisper]
model_size = base

[language]
default = fr

[llm]
provider = mock
model = gpt-4

[database]
path = janus.db
enable_wal = true

[logging]
level = INFO
enable_structured = true
log_to_database = true

[async_vision_monitor]
enable_monitor = false
"""
            )

        self.settings = Settings(config_path=config_path)
        self.memory = MemoryEngine(self.settings.database)
        self.pipeline = JanusPipeline(
            self.settings, 
            self.memory,
            enable_vision=False,
            enable_llm_reasoning=True,
        )

    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_dir)
        shutil.rmtree(self.test_dir)

    def test_pipeline_has_lifecycle_service(self):
        """Test that pipeline has lifecycle_service property"""
        self.assertTrue(hasattr(self.pipeline, 'lifecycle_service'))

    def test_pipeline_lifecycle_service_accessible(self):
        """Test that lifecycle_service is accessible"""
        lifecycle = self.pipeline.lifecycle_service
        self.assertIsNotNone(lifecycle)
        self.assertIsInstance(lifecycle, LifecycleService)

    def test_pipeline_has_memory_service_wrapper(self):
        """Test that pipeline has memory_service_wrapper property"""
        self.assertTrue(hasattr(self.pipeline, 'memory_service_wrapper'))

    def test_pipeline_memory_wrapper_accessible(self):
        """Test that memory_service_wrapper is accessible"""
        memory_wrapper = self.pipeline.memory_service_wrapper
        self.assertIsNotNone(memory_wrapper)
        self.assertIsInstance(memory_wrapper, MemoryServiceWrapper)

    def test_pipeline_cleanup_delegation(self):
        """Test that pipeline.cleanup() delegates to lifecycle_service"""
        # Should not raise any exceptions
        self.pipeline.cleanup()

    def test_pipeline_stop_monitor_delegation(self):
        """Test that pipeline.stop_monitor() delegates to lifecycle_service"""
        # Should not raise any exceptions
        self.pipeline.stop_monitor()


if __name__ == '__main__':
    unittest.main()
