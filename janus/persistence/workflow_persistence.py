"""
Workflow persistence and resumption for complex multi-step workflows
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class WorkflowPersistence:
    """
    Manages persistence and resumption of multi-step workflows
    Enables workflow checkpointing and recovery after failures
    """

    def __init__(self, db_path: str = "janus_data.db"):
        """
        Initialize workflow persistence

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._initialize_tables()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _initialize_tables(self):
        """Create workflow persistence tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Workflows table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    paused_at TEXT,
                    metadata TEXT,
                    error TEXT
                )
            """
            )

            # Workflow steps table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    step_data TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
                )
            """
            )

            # Create indexes
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_workflow_status
                ON workflows(status)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_step_workflow
                ON workflow_steps(workflow_id)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_step_status
                ON workflow_steps(status)
            """
            )

    def save_workflow(
        self,
        workflow_id: str,
        name: Optional[str] = None,
        status: str = "pending",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Save or update a workflow

        Args:
            workflow_id: Unique workflow identifier
            name: Optional workflow name
            status: Workflow status (pending, in_progress, completed, failed, paused)
            metadata: Optional metadata

        Returns:
            True if successful
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if workflow exists
            cursor.execute("SELECT id FROM workflows WHERE id = ?", (workflow_id,))
            exists = cursor.fetchone() is not None

            if exists:
                # Update existing workflow
                cursor.execute(
                    """
                    UPDATE workflows
                    SET name = ?, status = ?, metadata = ?
                    WHERE id = ?
                """,
                    (name, status, json.dumps(metadata) if metadata else None, workflow_id),
                )
            else:
                # Insert new workflow
                cursor.execute(
                    """
                    INSERT INTO workflows (id, name, status, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        workflow_id,
                        name,
                        status,
                        datetime.now().isoformat(),
                        json.dumps(metadata) if metadata else None,
                    ),
                )

            return True

    def save_workflow_step(
        self,
        workflow_id: str,
        step_id: str,
        step_data: Dict[str, Any],
        status: str = "pending",
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        retry_count: int = 0,
    ) -> int:
        """
        Save or update a workflow step

        Args:
            workflow_id: Parent workflow ID
            step_id: Step identifier
            step_data: Step configuration and data
            status: Step status (pending, in_progress, completed, failed, skipped)
            result: Step execution result
            error: Error message if failed
            retry_count: Number of retries attempted

        Returns:
            Step database ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if step exists
            cursor.execute(
                """
                SELECT id FROM workflow_steps
                WHERE workflow_id = ? AND step_id = ?
            """,
                (workflow_id, step_id),
            )

            row = cursor.fetchone()

            if row:
                # Update existing step
                step_db_id = row[0]
                cursor.execute(
                    """
                    UPDATE workflow_steps
                    SET step_data = ?, status = ?, result = ?, error = ?, retry_count = ?
                    WHERE id = ?
                """,
                    (
                        json.dumps(step_data),
                        status,
                        json.dumps(result) if result else None,
                        error,
                        retry_count,
                        step_db_id,
                    ),
                )
            else:
                # Insert new step
                cursor.execute(
                    """
                    INSERT INTO workflow_steps
                    (workflow_id, step_id, step_data, status, result, error, retry_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        workflow_id,
                        step_id,
                        json.dumps(step_data),
                        status,
                        json.dumps(result) if result else None,
                        error,
                        retry_count,
                    ),
                )
                step_db_id = cursor.lastrowid

            return step_db_id

    def update_workflow_status(
        self, workflow_id: str, status: str, error: Optional[str] = None
    ) -> bool:
        """
        Update workflow status

        Args:
            workflow_id: Workflow ID
            status: New status
            error: Optional error message

        Returns:
            True if successful
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            timestamp_field = None
            if status == "in_progress":
                timestamp_field = "started_at"
            elif status in ["completed", "failed"]:
                timestamp_field = "completed_at"
            elif status == "paused":
                timestamp_field = "paused_at"

            if timestamp_field:
                cursor.execute(
                    f"""
                    UPDATE workflows
                    SET status = ?, {timestamp_field} = ?, error = ?
                    WHERE id = ?
                """,
                    (status, datetime.now().isoformat(), error, workflow_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE workflows
                    SET status = ?, error = ?
                    WHERE id = ?
                """,
                    (status, error, workflow_id),
                )

            return cursor.rowcount > 0

    def update_step_status(
        self,
        workflow_id: str,
        step_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        Update step status

        Args:
            workflow_id: Workflow ID
            step_id: Step ID
            status: New status
            result: Optional result data
            error: Optional error message

        Returns:
            True if successful
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            timestamp_field = None
            if status == "in_progress":
                timestamp_field = "started_at"
            elif status in ["completed", "failed", "skipped"]:
                timestamp_field = "completed_at"

            if timestamp_field:
                cursor.execute(
                    f"""
                    UPDATE workflow_steps
                    SET status = ?, result = ?, error = ?, {timestamp_field} = ?
                    WHERE workflow_id = ? AND step_id = ?
                """,
                    (
                        status,
                        json.dumps(result) if result else None,
                        error,
                        datetime.now().isoformat(),
                        workflow_id,
                        step_id,
                    ),
                )
            else:
                cursor.execute(
                    """
                    UPDATE workflow_steps
                    SET status = ?, result = ?, error = ?
                    WHERE workflow_id = ? AND step_id = ?
                """,
                    (status, json.dumps(result) if result else None, error, workflow_id, step_id),
                )

            return cursor.rowcount > 0

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow by ID

        Args:
            workflow_id: Workflow ID

        Returns:
            Workflow data or None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    def get_workflow_steps(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Get all steps for a workflow

        Args:
            workflow_id: Workflow ID

        Returns:
            List of workflow steps
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM workflow_steps
                WHERE workflow_id = ?
                ORDER BY id ASC
            """,
                (workflow_id,),
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_resumable_workflows(self) -> List[Dict[str, Any]]:
        """
        Get workflows that can be resumed (paused or failed)

        Returns:
            List of resumable workflows
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM workflows
                WHERE status IN ('paused', 'failed', 'in_progress')
                ORDER BY paused_at DESC, created_at DESC
            """
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_pending_steps(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Get pending steps for a workflow

        Args:
            workflow_id: Workflow ID

        Returns:
            List of pending steps
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM workflow_steps
                WHERE workflow_id = ? AND status = 'pending'
                ORDER BY id ASC
            """,
                (workflow_id,),
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_workflow_progress(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get workflow execution progress

        Args:
            workflow_id: Workflow ID

        Returns:
            Progress information
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Count steps by status
            cursor.execute(
                """
                SELECT status, COUNT(*)
                FROM workflow_steps
                WHERE workflow_id = ?
                GROUP BY status
            """,
                (workflow_id,),
            )

            status_counts = dict(cursor.fetchall())

            total = sum(status_counts.values())
            completed = status_counts.get("completed", 0)
            failed = status_counts.get("failed", 0)
            pending = status_counts.get("pending", 0)
            in_progress = status_counts.get("in_progress", 0)

            progress = (completed / total * 100) if total > 0 else 0

            return {
                "total_steps": total,
                "completed": completed,
                "failed": failed,
                "pending": pending,
                "in_progress": in_progress,
                "progress_percent": round(progress, 2),
            }

    def checkpoint_workflow(self, workflow_id: str) -> bool:
        """
        Create a checkpoint for workflow (pause it)

        Args:
            workflow_id: Workflow ID

        Returns:
            True if successful
        """
        return self.update_workflow_status(workflow_id, "paused")

    def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete a workflow and its steps

        Args:
            workflow_id: Workflow ID

        Returns:
            True if successful
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Delete steps first (foreign key constraint)
            cursor.execute("DELETE FROM workflow_steps WHERE workflow_id = ?", (workflow_id,))

            # Delete workflow
            cursor.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))

            return cursor.rowcount > 0

    def cleanup_old_workflows(self, days: int = 30) -> int:
        """
        Clean up old completed workflows

        Args:
            days: Delete workflows older than this many days

        Returns:
            Number of workflows deleted
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            # Get workflow IDs to delete
            cursor.execute(
                """
                SELECT id FROM workflows
                WHERE status = 'completed' AND completed_at < ?
            """,
                (cutoff_date,),
            )

            workflow_ids = [row[0] for row in cursor.fetchall()]

            # Delete steps
            for wf_id in workflow_ids:
                cursor.execute("DELETE FROM workflow_steps WHERE workflow_id = ?", (wf_id,))

            # Delete workflows
            cursor.execute(
                """
                DELETE FROM workflows
                WHERE status = 'completed' AND completed_at < ?
            """,
                (cutoff_date,),
            )

            return len(workflow_ids)

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to dictionary"""
        result = dict(row)

        # Parse JSON fields
        if "metadata" in result and result["metadata"]:
            result["metadata"] = json.loads(result["metadata"])
        if "step_data" in result and result["step_data"]:
            result["step_data"] = json.loads(result["step_data"])
        if "result" in result and result["result"]:
            result["result"] = json.loads(result["result"])

        return result


# Import timedelta for cleanup_old_workflows
from datetime import timedelta
