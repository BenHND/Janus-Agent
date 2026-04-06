"""
Action history management for multi-step workflows
Records all actions and results for reuse and analysis
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from janus.logging import get_logger


class ActionHistory:
    """
    Records and manages history of all actions and their results
    Enables action replay, analysis, and workflow resumption
    """

    def __init__(self, db_path: str = "janus_data.db"):
        """
        Initialize action history manager

        Args:
            db_path: Path to SQLite database file
        """
        self.logger = get_logger("action_history")
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
        """Create action history tables if they don't exist"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Action history table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS action_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    action_data TEXT NOT NULL,
                    result TEXT,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    duration_ms INTEGER,
                    module TEXT,
                    workflow_id TEXT,
                    step_id TEXT,
                    metadata TEXT,
                    error TEXT
                )
            """
            )

            # Create indexes
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_action_timestamp
                ON action_history(timestamp DESC)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_action_workflow
                ON action_history(workflow_id)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_action_type
                ON action_history(action_type)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_action_status
                ON action_history(status)
            """
            )

    def record_action(
        self,
        action_type: str,
        action_data: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
        status: str = "success",
        duration_ms: Optional[int] = None,
        module: Optional[str] = None,
        workflow_id: Optional[str] = None,
        step_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> int:
        """
        Record an action execution

        Args:
            action_type: Type of action (click, copy, open_app, etc.)
            action_data: Action parameters and details
            result: Action execution result
            status: Execution status (success, failed, pending)
            duration_ms: Execution duration in milliseconds
            module: Module that executed the action
            workflow_id: Associated workflow ID (if part of workflow)
            step_id: Associated step ID (if part of workflow)
            metadata: Additional metadata
            error: Error message if failed

        Returns:
            ID of recorded action
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO action_history (
                    action_type, action_data, result, status, timestamp,
                    duration_ms, module, workflow_id, step_id, metadata, error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    action_type,
                    json.dumps(action_data),
                    json.dumps(result) if result else None,
                    status,
                    datetime.now().isoformat(),
                    duration_ms,
                    module,
                    workflow_id,
                    step_id,
                    json.dumps(metadata) if metadata else None,
                    error,
                ),
            )
            return cursor.lastrowid

    def get_history(
        self,
        limit: int = 100,
        action_type: Optional[str] = None,
        status: Optional[str] = None,
        module: Optional[str] = None,
        workflow_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get action history with optional filters

        Args:
            limit: Maximum number of entries
            action_type: Filter by action type
            status: Filter by status
            module: Filter by module
            workflow_id: Filter by workflow ID
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)

        Returns:
            List of action history entries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM action_history WHERE 1=1"
            params = []

            if action_type:
                query += " AND action_type = ?"
                params.append(action_type)

            if status:
                query += " AND status = ?"
                params.append(status)

            if module:
                query += " AND module = ?"
                params.append(module)

            if workflow_id:
                query += " AND workflow_id = ?"
                params.append(workflow_id)

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)

            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_action_by_id(self, action_id: int) -> Optional[Dict[str, Any]]:
        """
        Get specific action by ID

        Args:
            action_id: Action ID

        Returns:
            Action details or None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM action_history WHERE id = ?", (action_id,))
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    def get_workflow_actions(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Get all actions for a specific workflow

        Args:
            workflow_id: Workflow ID

        Returns:
            List of actions in chronological order
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM action_history
                WHERE workflow_id = ?
                ORDER BY timestamp ASC
            """,
                (workflow_id,),
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def search_actions(
        self, query: str, search_fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search actions by content

        Args:
            query: Search query
            search_fields: Fields to search in (action_type, action_data, result)

        Returns:
            List of matching actions
        """
        if search_fields is None:
            search_fields = ["action_type", "action_data", "result"]

        with self._get_connection() as conn:
            cursor = conn.cursor()

            conditions = []
            params = []

            for field in search_fields:
                if field in ["action_type", "action_data", "result", "error"]:
                    conditions.append(f"{field} LIKE ? COLLATE NOCASE")
                    params.append(f"%{query}%")

            query_sql = "SELECT * FROM action_history WHERE " + " OR ".join(conditions)
            query_sql += " ORDER BY timestamp DESC"

            cursor.execute(query_sql, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_statistics(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get action statistics

        Args:
            start_date: Start date for analysis (ISO format)
            end_date: End date for analysis (ISO format)

        Returns:
            Dictionary with statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            date_filter = ""
            params = []

            if start_date:
                date_filter += " AND timestamp >= ?"
                params.append(start_date)

            if end_date:
                date_filter += " AND timestamp <= ?"
                params.append(end_date)

            stats = {}

            # Total actions
            cursor.execute(f"SELECT COUNT(*) FROM action_history WHERE 1=1{date_filter}", params)
            stats["total_actions"] = cursor.fetchone()[0]

            # Actions by status
            cursor.execute(
                f"""
                SELECT status, COUNT(*)
                FROM action_history
                WHERE 1=1{date_filter}
                GROUP BY status
            """,
                params,
            )
            stats["by_status"] = dict(cursor.fetchall())

            # Actions by type
            cursor.execute(
                f"""
                SELECT action_type, COUNT(*)
                FROM action_history
                WHERE 1=1{date_filter}
                GROUP BY action_type
                ORDER BY COUNT(*) DESC
            """,
                params,
            )
            stats["by_type"] = dict(cursor.fetchall())

            # Actions by module
            cursor.execute(
                f"""
                SELECT module, COUNT(*)
                FROM action_history
                WHERE module IS NOT NULL{date_filter}
                GROUP BY module
                ORDER BY COUNT(*) DESC
            """,
                params,
            )
            stats["by_module"] = dict(cursor.fetchall())

            # Average duration
            cursor.execute(
                f"""
                SELECT AVG(duration_ms)
                FROM action_history
                WHERE duration_ms IS NOT NULL{date_filter}
            """,
                params,
            )
            avg_duration = cursor.fetchone()[0]
            stats["avg_duration_ms"] = int(avg_duration) if avg_duration else 0

            return stats

    def get_recent_failures(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent failed actions

        Args:
            limit: Maximum number of failures to return

        Returns:
            List of failed actions
        """
        return self.get_history(limit=limit, status="failed")

    def clear_history(self, before_date: Optional[str] = None, workflow_id: Optional[str] = None):
        """
        Clear action history

        Args:
            before_date: Clear actions before this date (ISO format)
            workflow_id: Clear actions for specific workflow
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if workflow_id:
                cursor.execute("DELETE FROM action_history WHERE workflow_id = ?", (workflow_id,))
            elif before_date:
                cursor.execute("DELETE FROM action_history WHERE timestamp < ?", (before_date,))
            else:
                cursor.execute("DELETE FROM action_history")

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to dictionary"""
        result = dict(row)

        # Parse JSON fields
        if "action_data" in result and result["action_data"]:
            result["action_data"] = json.loads(result["action_data"])
        if "result" in result and result["result"]:
            result["result"] = json.loads(result["result"])
        if "metadata" in result and result["metadata"]:
            result["metadata"] = json.loads(result["metadata"])

        return result

    def check_for_action_loop(
        self,
        workflow_id: Optional[str] = None,
        max_duplicates: int = 2,
        recency_window: int = 10,
    ) -> Dict[str, Any]:
        """
        Check if the agent is looping (repeating the same action).
        
        QA VIGILANCE POINT #3: This detects when the agent performs the same
        action repeatedly without progress, indicating a loop that should
        trigger a replan or stop.
        
        Args:
            workflow_id: Optional workflow to check (None = check all recent)
            max_duplicates: Maximum allowed consecutive duplicates before flagging
            recency_window: Only check this many recent actions
        
        Returns:
            Dict with:
            - is_looping: bool - True if loop detected
            - duplicate_count: int - Number of consecutive duplicates
            - duplicate_action: dict - The repeating action (if looping)
            - recommendation: str - "replan" or "stop"
        """
        # Get recent actions efficiently - most recent first
        actions = self.get_history(limit=recency_window, workflow_id=workflow_id)
        
        if len(actions) < 2:
            return {
                "is_looping": False,
                "duplicate_count": 0,
                "duplicate_action": None,
                "recommendation": None,
            }
        
        # Check for consecutive duplicates
        latest = actions[0]
        latest_type = latest.get("action_type")
        latest_data = latest.get("action_data", {})
        latest_status = latest.get("status")
        
        duplicate_count = 1
        failed_count = 0 if latest_status != "failed" else 1
        
        for action in actions[1:]:
            # Stop counting if action type or data differs
            if action.get("action_type") != latest_type:
                break
            if action.get("action_data", {}) != latest_data:
                break
            
            duplicate_count += 1
            if action.get("status") == "failed":
                failed_count += 1
        
        is_looping = duplicate_count > max_duplicates
        
        # Determine recommendation
        recommendation = None
        if is_looping:
            if failed_count > max_duplicates:
                # All duplicates failed - likely unrecoverable, should stop
                recommendation = "stop"
            else:
                # Some succeeded but keep repeating - should replan
                recommendation = "replan"
        
        result = {
            "is_looping": is_looping,
            "duplicate_count": duplicate_count,
            "duplicate_action": latest if is_looping else None,
            "recommendation": recommendation,
            "failed_count": failed_count,
        }
        
        if is_looping:
            self.logger.warning(
                f"Loop detected: {duplicate_count} consecutive '{latest_type}' actions. "
                f"Recommendation: {recommendation}"
            )
        
        return result

    def export_history(
        self,
        output_file: str,
        format: str = "json",
        workflow_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> bool:
        """
        Export action history to file

        Args:
            output_file: Output file path
            format: Export format ("json" or "csv")
            workflow_id: Optional filter by workflow
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            True if successful
        """
        try:
            history = self.get_history(
                limit=10000, workflow_id=workflow_id, start_date=start_date, end_date=end_date
            )

            if format.lower() == "csv":
                import csv

                with open(output_file, "w", newline="", encoding="utf-8") as f:
                    if not history:
                        return True

                    # Get all keys from first entry
                    fieldnames = list(history[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)

                    writer.writeheader()
                    for entry in history:
                        # Convert complex fields to JSON strings for CSV
                        row = entry.copy()
                        for key, value in row.items():
                            if isinstance(value, (dict, list)):
                                row[key] = json.dumps(value)
                        writer.writerow(row)
            else:
                # Default to JSON
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(history, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            self.logger.error(f"Error exporting history: {e}", exc_info=True)
            return False
