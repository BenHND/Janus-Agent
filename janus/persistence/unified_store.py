"""
Unified Persistent Storage for Janus

This module consolidates persistence_manager.py and persistent_store.py
into a single, comprehensive storage backend supporting:
- Context snapshots and history
- Session data and elements
- Clipboard history
- File operations
- Browser tabs
- Generic object storage
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class UnifiedStore:
    """
    Unified persistent storage using SQLite

    Consolidates all persistence functionality:
    - Context snapshots (from PersistenceManager)
    - Sessions and command history (integrates with MemoryEngine)
    - Clipboard, files, tabs, objects (from PersistentStore)
    """

    def __init__(self, db_path: str = "janus_unified.db", auto_cleanup_days: int = 30):
        """
        Initialize unified persistent store

        Args:
            db_path: Path to SQLite database file
            auto_cleanup_days: Days to keep context history (0 to disable)
        """
        self.db_path = Path(db_path)
        self.auto_cleanup_days = auto_cleanup_days
        self._initialize_database()

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

    def _initialize_database(self):
        """Create all database tables and indexes"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")

            # Context snapshots table (from persistence_manager)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS context_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    snapshot_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    data TEXT NOT NULL,
                    performance_ms REAL,
                    created_at TEXT NOT NULL
                )
            """
            )

            # Context elements table (from persistence_manager)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS context_elements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL,
                    element_type TEXT NOT NULL,
                    element_data TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (snapshot_id) REFERENCES context_snapshots(id) ON DELETE CASCADE
                )
            """
            )

            # Session history table (from persistence_manager)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS session_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_start TEXT NOT NULL,
                    session_end TEXT,
                    total_actions INTEGER DEFAULT 0,
                    summary TEXT
                )
            """
            )

            # Clipboard history table (from persistent_store)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS clipboard_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    source TEXT
                )
            """
            )

            # File operations history (from persistent_store)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS file_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    status TEXT NOT NULL
                )
            """
            )

            # Browser tabs history (from persistent_store)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS browser_tabs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    title TEXT,
                    timestamp TEXT NOT NULL,
                    browser TEXT,
                    metadata TEXT,
                    is_active INTEGER DEFAULT 0
                )
            """
            )

            # Generic copied objects (from persistent_store)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS copied_objects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    object_type TEXT NOT NULL,
                    object_data TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    tags TEXT
                )
            """
            )

            # Create all indexes
            self._create_indexes(cursor)

    def _create_indexes(self, cursor):
        """Create database indexes for performance"""
        # Context indexes
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_context_timestamp
            ON context_snapshots(timestamp DESC)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_context_type
            ON context_snapshots(snapshot_type)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_elements_snapshot
            ON context_elements(snapshot_id)
        """
        )

        # Clipboard indexes
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_clipboard_timestamp
            ON clipboard_history(timestamp DESC)
        """
        )

        # File operations indexes
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_file_ops_timestamp
            ON file_operations(timestamp DESC)
        """
        )

        # Browser tabs indexes
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tabs_timestamp
            ON browser_tabs(timestamp DESC)
        """
        )

        # Copied objects indexes
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_objects_timestamp
            ON copied_objects(timestamp DESC)
        """
        )

    # ========== Context Snapshot Methods (from persistence_manager) ==========

    def save_context_snapshot(
        self, snapshot: Dict[str, Any], snapshot_type: str = "full", source: str = "system"
    ) -> int:
        """
        Save a context snapshot to the database

        Args:
            snapshot: Context snapshot dictionary
            snapshot_type: Type of snapshot ('full', 'quick', 'minimal')
            source: Source of snapshot ('system', 'user', 'automated')

        Returns:
            Snapshot ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO context_snapshots
                (timestamp, snapshot_type, source, data, performance_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    snapshot.get("timestamp", datetime.now().isoformat()),
                    snapshot_type,
                    source,
                    json.dumps(snapshot, ensure_ascii=False),
                    snapshot.get("performance_ms", 0),
                    datetime.now().isoformat(),
                ),
            )

            snapshot_id = cursor.lastrowid

            # Save detailed elements if present
            self._save_context_elements(cursor, snapshot_id, snapshot)

            # Perform auto-cleanup if enabled
            if self.auto_cleanup_days > 0:
                self._auto_cleanup(cursor)

            return snapshot_id

    def _save_context_elements(self, cursor, snapshot_id: int, snapshot: Dict[str, Any]):
        """Save detailed context elements"""
        # Save active window
        if "active_window" in snapshot and snapshot["active_window"]:
            cursor.execute(
                """
                INSERT INTO context_elements
                (snapshot_id, element_type, element_data, metadata)
                VALUES (?, ?, ?, ?)
            """,
                (
                    snapshot_id,
                    "active_window",
                    json.dumps(snapshot["active_window"]),
                    None,
                ),
            )

        # Save applications
        if "open_applications" in snapshot:
            for app in snapshot["open_applications"]:
                cursor.execute(
                    """
                    INSERT INTO context_elements
                    (snapshot_id, element_type, element_data, metadata)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        snapshot_id,
                        "application",
                        json.dumps(app),
                        None,
                    ),
                )

        # Save URLs
        if "urls" in snapshot:
            for url_data in snapshot["urls"]:
                cursor.execute(
                    """
                    INSERT INTO context_elements
                    (snapshot_id, element_type, element_data, metadata)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        snapshot_id,
                        "url",
                        json.dumps(url_data),
                        None,
                    ),
                )

        # Save visible texts (sample only)
        if "visible_text" in snapshot:
            for text in snapshot["visible_text"][:20]:
                cursor.execute(
                    """
                    INSERT INTO context_elements
                    (snapshot_id, element_type, element_data, metadata)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        snapshot_id,
                        "visible_text",
                        json.dumps({"text": text}),
                        None,
                    ),
                )

    def get_latest_snapshot(self, snapshot_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the most recent context snapshot"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if snapshot_type:
                cursor.execute(
                    """
                    SELECT data FROM context_snapshots
                    WHERE snapshot_type = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """,
                    (snapshot_type,),
                )
            else:
                cursor.execute(
                    """
                    SELECT data FROM context_snapshots
                    ORDER BY timestamp DESC
                    LIMIT 1
                """
                )

            row = cursor.fetchone()
            return json.loads(row["data"]) if row else None

    def get_snapshots_in_range(
        self, start_time: datetime, end_time: datetime, snapshot_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get snapshots within a time range"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if snapshot_type:
                cursor.execute(
                    """
                    SELECT data FROM context_snapshots
                    WHERE timestamp >= ? AND timestamp <= ? AND snapshot_type = ?
                    ORDER BY timestamp ASC
                """,
                    (start_time.isoformat(), end_time.isoformat(), snapshot_type),
                )
            else:
                cursor.execute(
                    """
                    SELECT data FROM context_snapshots
                    WHERE timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp ASC
                """,
                    (start_time.isoformat(), end_time.isoformat()),
                )

            return [json.loads(row["data"]) for row in cursor.fetchall()]

    def query_context_elements(self, element_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Query context elements by type"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT ce.element_data, cs.timestamp
                FROM context_elements ce
                JOIN context_snapshots cs ON ce.snapshot_id = cs.id
                WHERE ce.element_type = ?
                ORDER BY cs.timestamp DESC
                LIMIT ?
            """,
                (element_type, limit),
            )

            elements = []
            for row in cursor.fetchall():
                element = json.loads(row["element_data"])
                element["timestamp"] = row["timestamp"]
                elements.append(element)

            return elements

    def save_session(self, session_start: datetime, session_data: Dict[str, Any]) -> int:
        """Save session summary"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO session_history
                (session_start, session_end, total_actions, summary)
                VALUES (?, ?, ?, ?)
            """,
                (
                    session_start.isoformat(),
                    datetime.now().isoformat(),
                    session_data.get("total_actions", 0),
                    json.dumps(session_data, ensure_ascii=False),
                ),
            )

            return cursor.lastrowid

    def _auto_cleanup(self, cursor):
        """Automatically clean up old context data"""
        if self.auto_cleanup_days <= 0:
            return

        cutoff_date = datetime.now() - timedelta(days=self.auto_cleanup_days)

        # Delete old elements first (foreign key constraint)
        cursor.execute(
            """
            DELETE FROM context_elements
            WHERE snapshot_id IN (
                SELECT id FROM context_snapshots
                WHERE timestamp < ?
            )
        """,
            (cutoff_date.isoformat(),),
        )

        # Delete old snapshots
        cursor.execute(
            """
            DELETE FROM context_snapshots
            WHERE timestamp < ?
        """,
            (cutoff_date.isoformat(),),
        )

    # ========== Clipboard Methods (from persistent_store) ==========

    def add_clipboard_entry(
        self,
        content: str,
        content_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> int:
        """Add entry to clipboard history"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO clipboard_history (content, content_type, timestamp, metadata, source)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    content,
                    content_type,
                    datetime.now().isoformat(),
                    json.dumps(metadata) if metadata else None,
                    source,
                ),
            )
            return cursor.lastrowid

    def get_clipboard_history(
        self, limit: int = 50, content_type: Optional[str] = None, source: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get clipboard history"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM clipboard_history WHERE 1=1"
            params = []

            if content_type:
                query += " AND content_type = ?"
                params.append(content_type)

            if source:
                query += " AND source = ?"
                params.append(source)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def search_clipboard(self, query: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """Search clipboard history"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if case_sensitive:
                cursor.execute(
                    """
                    SELECT * FROM clipboard_history
                    WHERE content GLOB ?
                    ORDER BY timestamp DESC
                """,
                    (f"*{query}*",),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM clipboard_history
                    WHERE content LIKE ? COLLATE NOCASE
                    ORDER BY timestamp DESC
                """,
                    (f"%{query}%",),
                )

            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def clear_clipboard_history(self):
        """Clear all clipboard history"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM clipboard_history")

    # ========== File Operations Methods (from persistent_store) ==========

    def add_file_operation(
        self,
        operation_type: str,
        file_path: str,
        status: str = "success",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Record a file operation"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO file_operations (operation_type, file_path, timestamp, metadata, status)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    operation_type,
                    file_path,
                    datetime.now().isoformat(),
                    json.dumps(metadata) if metadata else None,
                    status,
                ),
            )
            return cursor.lastrowid

    def get_file_operations(
        self, limit: int = 50, operation_type: Optional[str] = None, file_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get file operation history"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM file_operations WHERE 1=1"
            params = []

            if operation_type:
                query += " AND operation_type = ?"
                params.append(operation_type)

            if file_path:
                query += " AND file_path LIKE ?"
                params.append(f"%{file_path}%")

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    # ========== Browser Tabs Methods (from persistent_store) ==========

    def add_browser_tab(
        self,
        url: str,
        title: Optional[str] = None,
        browser: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        is_active: bool = False,
    ) -> int:
        """Record a browser tab"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO browser_tabs (url, title, timestamp, browser, metadata, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    url,
                    title,
                    datetime.now().isoformat(),
                    browser,
                    json.dumps(metadata) if metadata else None,
                    1 if is_active else 0,
                ),
            )
            return cursor.lastrowid

    def get_browser_tabs(
        self, limit: int = 50, browser: Optional[str] = None, active_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get browser tab history"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM browser_tabs WHERE 1=1"
            params = []

            if browser:
                query += " AND browser = ?"
                params.append(browser)

            if active_only:
                query += " AND is_active = 1"

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def set_tab_active(self, tab_id: int, is_active: bool = True):
        """Set tab active status"""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE browser_tabs
                SET is_active = ?
                WHERE id = ?
            """,
                (1 if is_active else 0, tab_id),
            )

    # ========== Generic Object Storage Methods (from persistent_store) ==========

    def add_copied_object(
        self,
        object_type: str,
        object_data: Any,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> int:
        """Store a generic copied object"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO copied_objects (object_type, object_data, timestamp, metadata, tags)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    object_type,
                    json.dumps(object_data),
                    datetime.now().isoformat(),
                    json.dumps(metadata) if metadata else None,
                    json.dumps(tags) if tags else None,
                ),
            )
            return cursor.lastrowid

    def get_copied_objects(
        self, limit: int = 50, object_type: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get copied objects"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM copied_objects WHERE 1=1"
            params = []

            if object_type:
                query += " AND object_type = ?"
                params.append(object_type)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            results = [self._row_to_dict(row) for row in cursor.fetchall()]

            # Filter by tags if specified
            if tags:
                results = [
                    r for r in results if r.get("tags") and any(tag in r["tags"] for tag in tags)
                ]

            return results

    # ========== Utility Methods ==========

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to dictionary"""
        result = dict(row)

        # Parse JSON fields
        if "metadata" in result and result["metadata"]:
            result["metadata"] = json.loads(result["metadata"])
        if "tags" in result and result["tags"]:
            result["tags"] = json.loads(result["tags"])
        if "object_data" in result and result["object_data"]:
            result["object_data"] = json.loads(result["object_data"])

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Count context snapshots
            cursor.execute("SELECT COUNT(*) FROM context_snapshots")
            stats["context_snapshots"] = cursor.fetchone()[0]

            # Count context elements
            cursor.execute("SELECT COUNT(*) FROM context_elements")
            stats["context_elements"] = cursor.fetchone()[0]

            # Count clipboard entries
            cursor.execute("SELECT COUNT(*) FROM clipboard_history")
            stats["clipboard_entries"] = cursor.fetchone()[0]

            # Count file operations
            cursor.execute("SELECT COUNT(*) FROM file_operations")
            stats["file_operations"] = cursor.fetchone()[0]

            # Count browser tabs
            cursor.execute("SELECT COUNT(*) FROM browser_tabs")
            stats["browser_tabs"] = cursor.fetchone()[0]

            # Count copied objects
            cursor.execute("SELECT COUNT(*) FROM copied_objects")
            stats["copied_objects"] = cursor.fetchone()[0]

            # Count session history
            cursor.execute("SELECT COUNT(*) FROM session_history")
            stats["session_count"] = cursor.fetchone()[0]

            # Database size
            db_size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0
            stats["db_size_mb"] = round(db_size_bytes / (1024 * 1024), 2)

            return stats

    def clear_all(self):
        """Clear all data from database (use with caution)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM context_elements")
            cursor.execute("DELETE FROM context_snapshots")
            cursor.execute("DELETE FROM session_history")
            cursor.execute("DELETE FROM clipboard_history")
            cursor.execute("DELETE FROM file_operations")
            cursor.execute("DELETE FROM browser_tabs")
            cursor.execute("DELETE FROM copied_objects")
