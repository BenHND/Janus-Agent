"""Tests for CompensationManager (P2 Rollback Feature)"""

import os
import tempfile
import unittest
from pathlib import Path

from janus.safety.compensation_manager import (
    CompensationManager,
    compensate_file_creation,
    compensate_file_deletion,
    compensate_file_move,
    register_builtin_handlers
)


class TestCompensationManager(unittest.TestCase):
    """Test compensation/rollback functionality"""
    
    def setUp(self):
        """Create compensation manager for tests"""
        self.manager = CompensationManager()
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test directory"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_register_handler(self):
        """Test registering compensation handlers"""
        def test_handler(data):
            return True
        
        self.manager.register_handler("test.action", test_handler)
        self.assertIn("test.action", self.manager._compensation_handlers)
    
    def test_record_action(self):
        """Test recording a reversible action"""
        record = self.manager.record_action(
            "action_1",
            "files.create_file",
            {"path": "/tmp/test.txt"}
        )
        
        self.assertEqual(record.action_id, "action_1")
        self.assertEqual(record.status, "pending")
        self.assertEqual(len(self.manager._compensation_history), 1)
    
    def test_compensate_with_handler(self):
        """Test successful compensation with registered handler"""
        # Register a test handler
        executed = []
        def test_handler(data):
            executed.append(data)
            return True
        
        self.manager.register_handler("test.action", test_handler)
        
        # Record and compensate
        self.manager.record_action("action_1", "test.action", {"test": "data"})
        result = self.manager.compensate("action_1")
        
        self.assertTrue(result)
        self.assertEqual(len(executed), 1)
        self.assertEqual(executed[0]["test"], "data")
    
    def test_compensate_without_handler(self):
        """Test compensation fails when no handler registered"""
        self.manager.record_action("action_1", "unknown.action", {"test": "data"})
        result = self.manager.compensate("action_1")
        
        self.assertFalse(result)
    
    def test_compensate_nonexistent_action(self):
        """Test compensation of non-existent action"""
        result = self.manager.compensate("nonexistent")
        self.assertFalse(result)
    
    def test_compensate_already_compensated(self):
        """Test compensating already-compensated action"""
        def test_handler(data):
            return True
        
        self.manager.register_handler("test.action", test_handler)
        self.manager.record_action("action_1", "test.action", {})
        
        # Compensate once
        self.manager.compensate("action_1")
        # Try again
        result = self.manager.compensate("action_1")
        
        self.assertTrue(result)  # Should succeed (already compensated)
    
    def test_get_reversible_actions(self):
        """Test getting reversible actions"""
        self.manager.record_action("action_1", "test.action", {})
        self.manager.record_action("action_2", "test.action", {})
        
        reversible = self.manager.get_reversible_actions()
        self.assertEqual(len(reversible), 2)
    
    def test_get_compensation_stats(self):
        """Test getting compensation statistics"""
        def test_handler(data):
            return True
        
        self.manager.register_handler("test.action", test_handler)
        
        self.manager.record_action("action_1", "test.action", {})
        self.manager.record_action("action_2", "test.action", {})
        self.manager.compensate("action_1")
        
        stats = self.manager.get_compensation_stats()
        self.assertEqual(stats["pending"], 1)
        self.assertEqual(stats["compensated"], 1)


class TestFileCompensationHandlers(unittest.TestCase):
    """Test built-in file compensation handlers"""
    
    def setUp(self):
        """Create test directory"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test directory"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_compensate_file_creation(self):
        """Test compensating file creation by deleting it"""
        test_file = os.path.join(self.test_dir, "test.txt")
        
        # Create file
        Path(test_file).write_text("test content")
        self.assertTrue(os.path.exists(test_file))
        
        # Compensate (delete)
        result = compensate_file_creation({"path": test_file})
        
        self.assertTrue(result)
        self.assertFalse(os.path.exists(test_file))
    
    def test_compensate_file_creation_already_deleted(self):
        """Test compensating file creation when file already deleted"""
        test_file = os.path.join(self.test_dir, "nonexistent.txt")
        
        # Compensate non-existent file (should succeed)
        result = compensate_file_creation({"path": test_file})
        
        self.assertTrue(result)
    
    def test_compensate_file_deletion(self):
        """Test compensating file deletion by restoring it"""
        test_file = os.path.join(self.test_dir, "test.txt")
        original_content = "original content"
        
        # Simulate deleted file with backup
        result = compensate_file_deletion({
            "path": test_file,
            "backup_content": original_content
        })
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(test_file))
        self.assertEqual(Path(test_file).read_text(), original_content)
    
    def test_compensate_file_move(self):
        """Test compensating file move by moving it back"""
        from_file = os.path.join(self.test_dir, "from.txt")
        to_file = os.path.join(self.test_dir, "to.txt")
        
        # Create file and move it
        Path(from_file).write_text("content")
        import shutil
        shutil.move(from_file, to_file)
        
        self.assertFalse(os.path.exists(from_file))
        self.assertTrue(os.path.exists(to_file))
        
        # Compensate (move back)
        result = compensate_file_move({
            "from": from_file,
            "to": to_file
        })
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(from_file))
        self.assertFalse(os.path.exists(to_file))
    
    def test_register_builtin_handlers(self):
        """Test registering built-in handlers"""
        register_builtin_handlers()
        
        from janus.safety.compensation_manager import get_global_compensation_manager
        manager = get_global_compensation_manager()
        
        self.assertIn("files.create_file", manager._compensation_handlers)
        self.assertIn("files.delete_file", manager._compensation_handlers)
        self.assertIn("files.move_file", manager._compensation_handlers)


if __name__ == "__main__":
    unittest.main()
