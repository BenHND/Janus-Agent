"""
Enhanced Multi-Session Memory with MemoryEngine Integration

This module provides multi-session, multi-window memory management
with persistent storage via MemoryEngine backend.

Replaces deprecated JSON persistence with proper database backend.
"""

import logging
import threading
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional


class SessionMemory:
    """
    Represents memory for a single session
    In-memory cache with optional persistence via MemoryEngine
    """

    def __init__(self, session_id: str):
        """
        Initialize session memory

        Args:
            session_id: Unique session identifier
        """
        self.session_id = session_id
        self.data: Dict[str, Any] = {}
        self.windows: Dict[str, Dict[str, Any]] = {}
        self.created_at = datetime.now().isoformat()
        self.last_accessed = datetime.now().isoformat()
        self._lock = threading.Lock()

    def set(self, key: str, value: Any, window_id: Optional[str] = None):
        """Set a value in session memory"""
        with self._lock:
            self.last_accessed = datetime.now().isoformat()

            if window_id:
                if window_id not in self.windows:
                    self.windows[window_id] = {}
                self.windows[window_id][key] = value
            else:
                self.data[key] = value

    def get(self, key: str, window_id: Optional[str] = None, default=None) -> Any:
        """Get a value from session memory"""
        with self._lock:
            self.last_accessed = datetime.now().isoformat()

            if window_id:
                return self.windows.get(window_id, {}).get(key, default)
            else:
                return self.data.get(key, default)

    def delete(self, key: str, window_id: Optional[str] = None) -> bool:
        """Delete a value from session memory"""
        with self._lock:
            if window_id:
                if window_id in self.windows and key in self.windows[window_id]:
                    del self.windows[window_id][key]
                    return True
            else:
                if key in self.data:
                    del self.data[key]
                    return True
            return False

    def get_all_windows(self) -> List[str]:
        """Get all window IDs in this session"""
        with self._lock:
            return list(self.windows.keys())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session to dictionary"""
        with self._lock:
            return {
                "session_id": self.session_id,
                "data": self.data.copy(),
                "windows": {wid: data.copy() for wid, data in self.windows.items()},
                "created_at": self.created_at,
                "last_accessed": self.last_accessed,
            }


class GlobalClipboard:
    """
    Global clipboard shared across all modules and sessions
    """

    def __init__(self, max_history: int = 100):
        """
        Initialize global clipboard

        Args:
            max_history: Maximum number of clipboard entries to keep
        """
        self.max_history = max_history
        self.history: List[Dict[str, Any]] = []
        self.current: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()
        self.logger = logging.getLogger("global_clipboard")

        # Module-specific clipboard namespaces
        self.module_clipboards: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def copy(
        self,
        content: Any,
        content_type: str = "text",
        module: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Copy content to clipboard"""
        with self._lock:
            entry_id = f"clip_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

            entry = {
                "id": entry_id,
                "content": content,
                "content_type": content_type,
                "module": module,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat(),
            }

            self.current = entry
            self.history.insert(0, entry)

            # Trim history
            if len(self.history) > self.max_history:
                self.history = self.history[: self.max_history]

            # Store in module-specific clipboard
            if module:
                self.module_clipboards[module].insert(0, entry)
                if len(self.module_clipboards[module]) > self.max_history:
                    self.module_clipboards[module] = self.module_clipboards[module][
                        : self.max_history
                    ]

            self.logger.info(
                f"Copied to clipboard: {entry_id} (type={content_type}, module={module})"
            )
            return entry_id

    def paste(self) -> Optional[Any]:
        """Get current clipboard content"""
        with self._lock:
            if self.current:
                return self.current["content"]
            return None

    def get_current(self) -> Optional[Dict[str, Any]]:
        """Get current clipboard entry with metadata"""
        with self._lock:
            return self.current.copy() if self.current else None

    def get_history(
        self, limit: int = 10, module: Optional[str] = None, content_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get clipboard history"""
        with self._lock:
            # Get base history
            if module:
                history = self.module_clipboards.get(module, [])
            else:
                history = self.history

            # Filter by content type
            if content_type:
                history = [e for e in history if e["content_type"] == content_type]

            return [e.copy() for e in history[:limit]]

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search clipboard history"""
        with self._lock:
            results = []
            query_lower = query.lower()

            for entry in self.history:
                content = str(entry["content"]).lower()
                if query_lower in content:
                    results.append(entry.copy())
                    if len(results) >= limit:
                        break

            return results

    def clear(self, module: Optional[str] = None):
        """Clear clipboard history"""
        with self._lock:
            if module:
                if module in self.module_clipboards:
                    self.module_clipboards[module].clear()
            else:
                self.history.clear()
                self.current = None
                self.module_clipboards.clear()

            self.logger.info(f"Cleared clipboard{' for ' + module if module else ''}")


class EnhancedMultiSessionMemory:
    """
    Enhanced multi-session memory with MemoryEngine integration

    Provides in-memory caching with optional persistence to database.
    Replaces deprecated JSON file persistence.
    """

    def __init__(self, memory_service=None):
        """
        Initialize multi-session memory

        Args:
            memory_service: Optional MemoryEngine instance for persistence
        """
        self.memory_service = memory_service
        self.sessions: Dict[str, SessionMemory] = {}
        self.global_clipboard = GlobalClipboard()
        self._lock = threading.Lock()
        self.logger = logging.getLogger("multi_session_memory")

        # Cross-session shared data
        self.shared_data: Dict[str, Any] = {}

    def create_session(self, session_id: str) -> SessionMemory:
        """
        Create a new session

        Args:
            session_id: Unique session identifier

        Returns:
            Created session
        """
        with self._lock:
            if session_id in self.sessions:
                return self.sessions[session_id]

            session = SessionMemory(session_id)
            self.sessions[session_id] = session
            self.logger.info(f"Created session: {session_id}")

            # Persist to MemoryEngine if available
            if self.memory_service:
                self.memory_service.create_session(session_id)

            return session

    def get_session(self, session_id: str) -> Optional[SessionMemory]:
        """
        Get an existing session

        Args:
            session_id: Session identifier

        Returns:
            Session or None
        """
        with self._lock:
            session = self.sessions.get(session_id)

            # Try loading from MemoryEngine if not in cache
            if session is None and self.memory_service:
                session_data = self.memory_service.get_session(session_id)
                if session_data is not None:
                    session = SessionMemory(session_id)
                    session.data = session_data
                    self.sessions[session_id] = session

            return session

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session

        Args:
            session_id: Session to delete

        Returns:
            True if deleted
        """
        with self._lock:
            deleted = False

            # Remove from in-memory cache
            if session_id in self.sessions:
                del self.sessions[session_id]
                deleted = True
                self.logger.info(f"Deleted session: {session_id}")

            # Delete from MemoryEngine if available
            if self.memory_service:
                self.memory_service.delete_session(session_id)
                deleted = True

            return deleted

    def list_sessions(self) -> List[str]:
        """
        List all session IDs

        Returns:
            List of session IDs
        """
        with self._lock:
            session_ids = set(self.sessions.keys())

            # Add sessions from MemoryEngine
            if self.memory_service:
                db_sessions = self.memory_service.list_all_sessions()
                session_ids.update(s["session_id"] for s in db_sessions)

            return list(session_ids)

    def set_shared(self, key: str, value: Any):
        """
        Set a value in shared cross-session data

        Args:
            key: Key to store
            value: Value to store
        """
        with self._lock:
            self.shared_data[key] = value

    def get_shared(self, key: str, default=None) -> Any:
        """
        Get a value from shared cross-session data

        Args:
            key: Key to retrieve
            default: Default value

        Returns:
            Stored value or default
        """
        with self._lock:
            return self.shared_data.get(key, default)

    def get_all_windows(self, session_id: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Get all windows across sessions

        Args:
            session_id: If specified, only get windows for this session

        Returns:
            Dict mapping session_id to list of window_ids
        """
        with self._lock:
            if session_id:
                session = self.sessions.get(session_id)
                return {session_id: session.get_all_windows()} if session else {}
            else:
                return {sid: session.get_all_windows() for sid, session in self.sessions.items()}

    def persist_session(self, session_id: str) -> bool:
        """
        Explicitly persist session to database

        Args:
            session_id: Session to persist

        Returns:
            True if successful
        """
        if not self.memory_service:
            return False

        session = self.sessions.get(session_id)
        if not session:
            return False

        try:
            self.memory_service.update_session(session_id, session.data)
            return True
        except Exception as e:
            self.logger.error(f"Failed to persist session {session_id}: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get memory statistics

        Returns:
            Statistics dictionary
        """
        with self._lock:
            total_windows = sum(
                len(session.get_all_windows()) for session in self.sessions.values()
            )

            stats = {
                "total_sessions": len(self.sessions),
                "total_windows": total_windows,
                "clipboard_entries": len(self.global_clipboard.history),
                "shared_data_keys": len(self.shared_data),
                "sessions": {
                    sid: {
                        "windows": len(session.get_all_windows()),
                        "data_keys": len(session.data),
                        "last_accessed": session.last_accessed,
                    }
                    for sid, session in self.sessions.items()
                },
            }

            # Add database stats if available
            if self.memory_service:
                stats["persistent_sessions"] = len(self.memory_service.list_all_sessions())

            return stats
