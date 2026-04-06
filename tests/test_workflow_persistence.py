"""
Unit tests for WorkflowPersistence
"""
import os
import tempfile
import unittest
from datetime import datetime, timedelta

from janus.persistence.workflow_persistence import WorkflowPersistence


class TestWorkflowPersistence(unittest.TestCase):
    """Test cases for WorkflowPersistence"""

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.persistence = WorkflowPersistence(self.temp_db.name)

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_save_workflow(self):
        """Test saving a workflow"""
        success = self.persistence.save_workflow(
            workflow_id="wf_001",
            name="Test Workflow",
            status="pending",
            metadata={"priority": "high"},
        )
        self.assertTrue(success)

    def test_save_workflow_update(self):
        """Test updating an existing workflow"""
        # Create workflow
        self.persistence.save_workflow("wf_001", name="Original", status="pending")

        # Update workflow
        self.persistence.save_workflow("wf_001", name="Updated", status="in_progress")

        # Verify update
        workflow = self.persistence.get_workflow("wf_001")
        self.assertEqual(workflow["name"], "Updated")
        self.assertEqual(workflow["status"], "in_progress")

    def test_save_workflow_step(self):
        """Test saving a workflow step"""
        # Create workflow first
        self.persistence.save_workflow("wf_001")

        step_id = self.persistence.save_workflow_step(
            workflow_id="wf_001",
            step_id="step1",
            step_data={"action": "click", "target": "button"},
            status="pending",
        )
        self.assertIsInstance(step_id, int)
        self.assertGreater(step_id, 0)

    def test_update_workflow_status(self):
        """Test updating workflow status"""
        self.persistence.save_workflow("wf_001", status="pending")

        success = self.persistence.update_workflow_status("wf_001", "in_progress")
        self.assertTrue(success)

        workflow = self.persistence.get_workflow("wf_001")
        self.assertEqual(workflow["status"], "in_progress")
        self.assertIsNotNone(workflow["started_at"])

    def test_update_step_status(self):
        """Test updating step status"""
        self.persistence.save_workflow("wf_001")
        self.persistence.save_workflow_step("wf_001", "step1", {"action": "test"}, "pending")

        success = self.persistence.update_step_status(
            "wf_001", "step1", "completed", result={"output": "success"}
        )
        self.assertTrue(success)

        steps = self.persistence.get_workflow_steps("wf_001")
        self.assertEqual(steps[0]["status"], "completed")
        self.assertIsNotNone(steps[0]["result"])

    def test_get_workflow(self):
        """Test getting workflow by ID"""
        self.persistence.save_workflow("wf_001", name="Test Workflow", metadata={"key": "value"})

        workflow = self.persistence.get_workflow("wf_001")
        self.assertIsNotNone(workflow)
        self.assertEqual(workflow["id"], "wf_001")
        self.assertEqual(workflow["name"], "Test Workflow")
        self.assertEqual(workflow["metadata"]["key"], "value")

    def test_get_workflow_not_found(self):
        """Test getting non-existent workflow"""
        workflow = self.persistence.get_workflow("nonexistent")
        self.assertIsNone(workflow)

    def test_get_workflow_steps(self):
        """Test getting all steps for a workflow"""
        self.persistence.save_workflow("wf_001")
        self.persistence.save_workflow_step("wf_001", "step1", {"action": "1"})
        self.persistence.save_workflow_step("wf_001", "step2", {"action": "2"})
        self.persistence.save_workflow_step("wf_001", "step3", {"action": "3"})

        steps = self.persistence.get_workflow_steps("wf_001")
        self.assertEqual(len(steps), 3)

        # Steps should be in order
        self.assertEqual(steps[0]["step_id"], "step1")
        self.assertEqual(steps[1]["step_id"], "step2")
        self.assertEqual(steps[2]["step_id"], "step3")

    def test_get_resumable_workflows(self):
        """Test getting resumable workflows"""
        self.persistence.save_workflow("wf_001", status="completed")
        self.persistence.save_workflow("wf_002", status="paused")
        self.persistence.save_workflow("wf_003", status="failed")
        self.persistence.save_workflow("wf_004", status="in_progress")

        resumable = self.persistence.get_resumable_workflows()

        # Should return paused, failed, and in_progress
        self.assertEqual(len(resumable), 3)
        statuses = {wf["status"] for wf in resumable}
        self.assertIn("paused", statuses)
        self.assertIn("failed", statuses)
        self.assertIn("in_progress", statuses)

    def test_get_pending_steps(self):
        """Test getting pending steps"""
        self.persistence.save_workflow("wf_001")
        self.persistence.save_workflow_step("wf_001", "step1", {}, status="completed")
        self.persistence.save_workflow_step("wf_001", "step2", {}, status="pending")
        self.persistence.save_workflow_step("wf_001", "step3", {}, status="pending")

        pending = self.persistence.get_pending_steps("wf_001")
        self.assertEqual(len(pending), 2)

    def test_get_workflow_progress(self):
        """Test getting workflow progress"""
        self.persistence.save_workflow("wf_001")
        self.persistence.save_workflow_step("wf_001", "step1", {}, status="completed")
        self.persistence.save_workflow_step("wf_001", "step2", {}, status="completed")
        self.persistence.save_workflow_step("wf_001", "step3", {}, status="pending")
        self.persistence.save_workflow_step("wf_001", "step4", {}, status="failed")

        progress = self.persistence.get_workflow_progress("wf_001")

        self.assertEqual(progress["total_steps"], 4)
        self.assertEqual(progress["completed"], 2)
        self.assertEqual(progress["pending"], 1)
        self.assertEqual(progress["failed"], 1)
        self.assertEqual(progress["progress_percent"], 50.0)

    def test_checkpoint_workflow(self):
        """Test creating workflow checkpoint"""
        self.persistence.save_workflow("wf_001", status="in_progress")

        success = self.persistence.checkpoint_workflow("wf_001")
        self.assertTrue(success)

        workflow = self.persistence.get_workflow("wf_001")
        self.assertEqual(workflow["status"], "paused")
        self.assertIsNotNone(workflow["paused_at"])

    def test_delete_workflow(self):
        """Test deleting a workflow"""
        self.persistence.save_workflow("wf_001")
        self.persistence.save_workflow_step("wf_001", "step1", {})

        success = self.persistence.delete_workflow("wf_001")
        self.assertTrue(success)

        # Verify deletion
        workflow = self.persistence.get_workflow("wf_001")
        self.assertIsNone(workflow)

        steps = self.persistence.get_workflow_steps("wf_001")
        self.assertEqual(len(steps), 0)

    def test_workflow_with_error(self):
        """Test recording workflow with error"""
        self.persistence.save_workflow("wf_001")
        self.persistence.update_workflow_status("wf_001", "failed", error="Connection timeout")

        workflow = self.persistence.get_workflow("wf_001")
        self.assertEqual(workflow["status"], "failed")
        self.assertEqual(workflow["error"], "Connection timeout")

    def test_step_retry_count(self):
        """Test step retry count tracking"""
        self.persistence.save_workflow("wf_001")
        self.persistence.save_workflow_step(
            "wf_001", "step1", {"action": "test"}, status="failed", retry_count=3
        )

        steps = self.persistence.get_workflow_steps("wf_001")
        self.assertEqual(steps[0]["retry_count"], 3)


if __name__ == "__main__":
    unittest.main()
