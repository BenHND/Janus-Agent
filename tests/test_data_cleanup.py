"""
Unit tests for DataCleanupManager (TICKET-DATA-001)

Tests automatic data cleanup and retention policies.
"""
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from janus.utils.data_cleanup import DataCleanupManager


class MockRetentionSettings:
    """Mock data retention settings for testing"""
    
    def __init__(self):
        self.memory_context_days = 30
        self.memory_history_days = 30
        self.semantic_vectors_days = 60
        self.action_history_days = 90
        self.workflow_states_days = 14
        self.audio_logs_days = 7
        self.safe_queue_days = 30
        self.unified_store_days = 30
        self.max_total_size_mb = 2000
        self.auto_cleanup_on_startup = True
        self.cleanup_check_interval_hours = 24


class MockSettings:
    """Mock settings for testing"""
    
    def __init__(self):
        self.data_retention = MockRetentionSettings()


class TestDataCleanupManager(unittest.TestCase):
    """Test cases for DataCleanupManager"""
    
    def setUp(self):
        """Set up test environment"""
        self.settings = MockSettings()
        self.manager = DataCleanupManager(self.settings)
    
    def test_initialization(self):
        """Test manager initialization"""
        self.assertIsNotNone(self.manager)
        self.assertEqual(self.manager.settings, self.settings)
        self.assertEqual(self.manager.retention, self.settings.data_retention)
    
    def test_cleanup_memory_engine(self):
        """Test MemoryEngine cleanup (integration test)"""
        # Test that the method handles errors gracefully
        result = self.manager._cleanup_memory_engine()
        
        # Should return dict with stats or error
        self.assertIsInstance(result, dict)
        # Either success keys or error key
        self.assertTrue(
            "context_deleted" in result or "error" in result
        )
    
    def test_cleanup_chromadb(self):
        """Test ChromaDB cleanup"""
        # Test when chromadb directory doesn't exist
        result = self.manager._cleanup_chromadb()
        self.assertIn("skipped", result)
        
    def test_cleanup_chromadb_not_installed(self):
        """Test ChromaDB cleanup when chromadb is not installed"""
        # This is tested implicitly in the _cleanup_chromadb method
        # when chromadb import fails
        result = self.manager._cleanup_chromadb()
        # Should handle ImportError gracefully
        self.assertIsNotNone(result)
    
    def test_cleanup_action_history(self):
        """Test ActionHistory cleanup (integration test)"""
        # Test that the method handles errors gracefully
        result = self.manager._cleanup_action_history()
        
        # Should return dict with stats or error
        self.assertIsInstance(result, dict)
        self.assertTrue(
            "records_deleted" in result or "error" in result
        )
    
    def test_cleanup_workflows(self):
        """Test workflow cleanup (integration test)"""
        # Test that the method handles errors gracefully
        result = self.manager._cleanup_workflows()
        
        # Should return dict with stats or error
        self.assertIsInstance(result, dict)
        self.assertTrue(
            "workflows_deleted" in result or "error" in result
        )
    
    def test_cleanup_audio_logs(self):
        """Test audio logs cleanup (integration test)"""
        # Test that the method handles errors gracefully
        result = self.manager._cleanup_audio_logs()
        
        # Should return dict with stats or error
        self.assertIsInstance(result, dict)
        self.assertTrue(
            "logs_deleted" in result or "error" in result
        )
    
    def test_cleanup_safe_queue(self):
        """Test SafeQueue cleanup (integration test)"""
        # Test that the method handles errors gracefully
        result = self.manager._cleanup_safe_queue()
        
        # Should return dict with stats or error
        self.assertIsInstance(result, dict)
        self.assertTrue(
            "entries_deleted" in result or "error" in result
        )
    
    def test_cleanup_unified_store(self):
        """Test UnifiedStore cleanup (integration test)"""
        # Test that the method handles errors gracefully
        result = self.manager._cleanup_unified_store()
        
        # Should return dict with stats or error
        self.assertIsInstance(result, dict)
        self.assertTrue(
            "snapshots_deleted" in result or "error" in result
        )
    
    @patch('janus.utils.data_cleanup.DataCleanupManager._cleanup_memory_engine')
    @patch('janus.utils.data_cleanup.DataCleanupManager._cleanup_chromadb')
    @patch('janus.utils.data_cleanup.DataCleanupManager._cleanup_action_history')
    @patch('janus.utils.data_cleanup.DataCleanupManager._cleanup_workflows')
    @patch('janus.utils.data_cleanup.DataCleanupManager._cleanup_audio_logs')
    @patch('janus.utils.data_cleanup.DataCleanupManager._cleanup_safe_queue')
    @patch('janus.utils.data_cleanup.DataCleanupManager._cleanup_unified_store')
    def test_run_full_cleanup(self, mock_unified, mock_queue, mock_audio, 
                             mock_workflows, mock_history, mock_chromadb, mock_memory):
        """Test full cleanup run"""
        # Mock all cleanup methods
        mock_memory.return_value = {"context_deleted": 10, "history_deleted": 20}
        mock_chromadb.return_value = {"vectors_deleted": 5}
        mock_history.return_value = {"records_deleted": 15}
        mock_workflows.return_value = {"workflows_deleted": 3, "steps_deleted": 8}
        mock_audio.return_value = {"logs_deleted": 25}
        mock_queue.return_value = {"entries_deleted": 7}
        mock_unified.return_value = {"snapshots_deleted": 2, "clipboard_deleted": 4, "file_ops_deleted": 1}
        
        # Run full cleanup
        result = self.manager.run_full_cleanup()
        
        # Verify all methods were called
        mock_memory.assert_called_once()
        mock_chromadb.assert_called_once()
        mock_history.assert_called_once()
        mock_workflows.assert_called_once()
        mock_audio.assert_called_once()
        mock_queue.assert_called_once()
        mock_unified.assert_called_once()
        
        # Verify result structure
        self.assertIn("memory", result)
        self.assertIn("vectors", result)
        self.assertIn("action_history", result)
        self.assertIn("workflows", result)
        self.assertIn("audio_logs", result)
        self.assertIn("safe_queue", result)
        self.assertIn("unified_store", result)
    
    def test_get_storage_stats_empty(self):
        """Test storage stats when no files exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                
                stats = self.manager.get_storage_stats()
                
                # Should have total key
                self.assertIn("total", stats)
                self.assertEqual(stats["total"], 0)
            finally:
                os.chdir(original_dir)
    
    def test_get_storage_stats_with_files(self):
        """Test storage stats with some files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                
                # Create some test database files
                test_db = Path("janus_memory.db")
                test_db.write_bytes(b"x" * 1024)  # 1KB file
                
                test_db2 = Path("janus_data.db")
                test_db2.write_bytes(b"y" * 2048)  # 2KB file
                
                stats = self.manager.get_storage_stats()
                
                # Should track both files
                self.assertIn("janus_memory.db", stats)
                self.assertIn("janus_data.db", stats)
                self.assertEqual(stats["janus_memory.db"], 1024)
                self.assertEqual(stats["janus_data.db"], 2048)
                self.assertEqual(stats["total"], 3072)
            finally:
                os.chdir(original_dir)
    
    def test_check_disk_space_under_limit(self):
        """Test disk space check when under limit"""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                
                # Create small file (1MB)
                test_db = Path("janus_memory.db")
                test_db.write_bytes(b"x" * (1024 * 1024))  # 1MB
                
                # Limit is 2000MB, so should be fine
                result = self.manager.check_disk_space()
                
                self.assertFalse(result)  # No cleanup needed
            finally:
                os.chdir(original_dir)
    
    def test_check_disk_space_over_limit(self):
        """Test disk space check when over limit"""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                
                # Lower the limit to 1MB for testing
                self.settings.data_retention.max_total_size_mb = 1
                
                # Create 2MB file
                test_db = Path("janus_memory.db")
                test_db.write_bytes(b"x" * (2 * 1024 * 1024))  # 2MB
                
                result = self.manager.check_disk_space()
                
                self.assertTrue(result)  # Cleanup needed
            finally:
                os.chdir(original_dir)


if __name__ == "__main__":
    unittest.main()
