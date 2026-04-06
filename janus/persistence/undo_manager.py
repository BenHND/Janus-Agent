"""
Undo/Redo manager for reversible actions
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from janus.logging import get_logger


class UndoableActionType(Enum):
    """Types of actions that can be undone"""

    CLIPBOARD = "clipboard"
    FILE_OPERATION = "file_operation"
    TEXT_EDIT = "text_edit"
    CONFIGURATION = "configuration"
    CUSTOM = "custom"


class UndoManager:
    """
    Manages undo/redo functionality for reversible actions
    Maintains action stacks and provides undo/redo operations
    """

    def __init__(self, db_path: str = "janus_data.db", max_undo_stack: int = 100):
        """
        Initialize undo manager

        Args:
            db_path: Path to SQLite database file
            max_undo_stack: Maximum size of undo stack
        """
        self.logger = get_logger("undo_manager")
        self.db_path = Path(db_path)
        self.max_undo_stack = max_undo_stack
        self._undo_handlers: Dict[str, Callable] = {}
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
        """Create undo/redo tables if they don't exist"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Undo stack table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS undo_stack (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    action_data TEXT NOT NULL,
                    undo_data TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    description TEXT,
                    is_undone INTEGER DEFAULT 0,
                    undone_at TEXT
                )
            """
            )

            # Create index
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_undo_timestamp
                ON undo_stack(timestamp DESC)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_undo_status
                ON undo_stack(is_undone)
            """
            )

    def register_undo_handler(self, action_type: str, handler: Callable):
        """
        Register a handler function for undoing specific action types

        Args:
            action_type: Type of action
            handler: Function that performs the undo (takes undo_data as parameter)
        """
        self._undo_handlers[action_type] = handler

    def record_undoable_action(
        self,
        action_type: str,
        action_data: Dict[str, Any],
        undo_data: Dict[str, Any],
        description: Optional[str] = None,
    ) -> int:
        """
        Record an action that can be undone

        Args:
            action_type: Type of action
            action_data: Data about the action that was performed
            undo_data: Data needed to undo the action
            description: Human-readable description of the action

        Returns:
            ID of recorded action
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO undo_stack (action_type, action_data, undo_data, timestamp, description)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    action_type,
                    json.dumps(action_data),
                    json.dumps(undo_data),
                    datetime.now().isoformat(),
                    description,
                ),
            )

            action_id = cursor.lastrowid

            # Limit stack size
            cursor.execute(
                """
                SELECT COUNT(*) FROM undo_stack WHERE is_undone = 0
            """
            )
            count = cursor.fetchone()[0]

            if count > self.max_undo_stack:
                # Remove oldest undoable actions
                cursor.execute(
                    """
                    DELETE FROM undo_stack
                    WHERE id IN (
                        SELECT id FROM undo_stack
                        WHERE is_undone = 0
                        ORDER BY timestamp ASC
                        LIMIT ?
                    )
                """,
                    (count - self.max_undo_stack,),
                )

            return action_id

    def undo(self) -> Optional[Dict[str, Any]]:
        """
        Undo the most recent action

        Returns:
            Information about the undone action, or None if nothing to undo
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get most recent undoable action
            cursor.execute(
                """
                SELECT * FROM undo_stack
                WHERE is_undone = 0
                ORDER BY timestamp DESC
                LIMIT 1
            """
            )

            row = cursor.fetchone()
            if not row:
                return None

            action = self._row_to_dict(row)
            action_type = action["action_type"]
            undo_data = action["undo_data"]

            # Get undo handler
            handler = self._undo_handlers.get(action_type)
            if not handler:
                return {
                    "status": "error",
                    "error": f"No undo handler registered for action type: {action_type}",
                }

            try:
                # Execute undo
                result = handler(undo_data)

                # Mark as undone
                cursor.execute(
                    """
                    UPDATE undo_stack
                    SET is_undone = 1, undone_at = ?
                    WHERE id = ?
                """,
                    (datetime.now().isoformat(), action["id"]),
                )

                return {"status": "success", "action": action, "result": result}
            except Exception as e:
                return {"status": "error", "error": str(e), "action": action}

    def redo(self) -> Optional[Dict[str, Any]]:
        """
        Redo the most recently undone action

        Returns:
            Information about the redone action, or None if nothing to redo
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get most recently undone action
            cursor.execute(
                """
                SELECT * FROM undo_stack
                WHERE is_undone = 1
                ORDER BY undone_at DESC
                LIMIT 1
            """
            )

            row = cursor.fetchone()
            if not row:
                return None

            action = self._row_to_dict(row)
            action_type = action["action_type"]
            action_data = action["action_data"]

            # For redo, we need a redo handler or the original action executor
            # This is a simplified implementation - in practice, you'd need
            # access to the original action executor

            # Mark as redone (no longer undone)
            cursor.execute(
                """
                UPDATE undo_stack
                SET is_undone = 0, undone_at = NULL
                WHERE id = ?
            """,
                (action["id"],),
            )

            return {
                "status": "success",
                "action": action,
                "message": "Action redone - now available for undo again",
            }

    def get_undo_stack(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get current undo stack

        Args:
            limit: Maximum number of entries

        Returns:
            List of undoable actions
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM undo_stack
                WHERE is_undone = 0
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (limit,),
            )

            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_redo_stack(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get current redo stack (undone actions)

        Args:
            limit: Maximum number of entries

        Returns:
            List of redoable actions
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM undo_stack
                WHERE is_undone = 1
                ORDER BY undone_at DESC
                LIMIT ?
            """,
                (limit,),
            )

            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def can_undo(self) -> bool:
        """Check if there are actions that can be undone"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM undo_stack WHERE is_undone = 0")
            count = cursor.fetchone()[0]
            return count > 0

    def can_redo(self) -> bool:
        """Check if there are actions that can be redone"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM undo_stack WHERE is_undone = 1")
            count = cursor.fetchone()[0]
            return count > 0

    def clear_undo_stack(self):
        """Clear the entire undo stack"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM undo_stack")

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to dictionary"""
        result = dict(row)

        # Parse JSON fields
        if "action_data" in result and result["action_data"]:
            result["action_data"] = json.loads(result["action_data"])
        if "undo_data" in result and result["undo_data"]:
            result["undo_data"] = json.loads(result["undo_data"])

        return result


class LogViewer:
    """
    Log viewer for querying and filtering action logs
    """

    def __init__(self, db_path: str = "janus_data.db"):
        """
        Initialize log viewer

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def get_logs(
        self,
        limit: int = 100,
        action_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get action logs with filters

        Args:
            limit: Maximum number of entries
            action_type: Filter by action type
            status: Filter by status
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            List of log entries
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

    def search_logs(self, query: str) -> List[Dict[str, Any]]:
        """
        Search logs by content

        Args:
            query: Search query

        Returns:
            List of matching log entries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM action_history
                WHERE action_type LIKE ?
                   OR action_data LIKE ?
                   OR error LIKE ?
                ORDER BY timestamp DESC
            """,
                (f"%{query}%", f"%{query}%", f"%{query}%"),
            )

            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def export_logs(
        self, output_file: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> bool:
        """
        Export logs to file

        Args:
            output_file: Output file path
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            True if successful
        """
        try:
            logs = self.get_logs(limit=10000, start_date=start_date, end_date=end_date)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            self.logger.error(f"Error exporting logs: {e}", exc_info=True)
            return False

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
