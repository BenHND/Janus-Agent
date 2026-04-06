"""
Global clipboard manager for centralized clipboard operations across all modules
"""

import json
import os
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from janus.logging import get_logger

# Try to import pyperclip, but allow it to fail for testing
try:
    import pyperclip

    PYPERCLIP_AVAILABLE = True
except Exception:
    PYPERCLIP_AVAILABLE = False


class ClipboardType(Enum):
    """Types of clipboard content"""

    TEXT = "text"
    FILE_PATH = "file_path"
    IMAGE = "image"
    JSON = "json"


class ClipboardEntry:
    """Represents a clipboard entry with metadata"""

    def __init__(
        self,
        content: str,
        content_type: ClipboardType = ClipboardType.TEXT,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.content = content
        self.content_type = content_type
        # Use timezone-aware timestamp for proper time comparison
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "content": self.content,
            "content_type": self.content_type.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClipboardEntry":
        """Create from dictionary"""
        entry = cls(
            content=data["content"],
            content_type=ClipboardType(data["content_type"]),
            metadata=data.get("metadata", {}),
        )
        entry.timestamp = data["timestamp"]
        return entry


class ClipboardManager:
    """
    Centralized clipboard manager accessible by all modules and orchestrator.
    Provides clipboard operations with history tracking and type support.
    """

    def __init__(
        self,
        history_limit: int = 50,
        persist_file: str = "clipboard_history.json",
        use_system_clipboard: bool = True,
    ):
        """
        Initialize clipboard manager

        Args:
            history_limit: Maximum number of entries to keep in history
            persist_file: File to persist clipboard history
            use_system_clipboard: Whether to use system clipboard (set to False for testing)
        """
        self.logger = get_logger("clipboard_manager")
        self.history_limit = history_limit
        self.persist_file = persist_file
        self.use_system_clipboard = use_system_clipboard and PYPERCLIP_AVAILABLE
        self._internal_clipboard = ""  # Internal clipboard for when system clipboard is unavailable
        self.history: List[ClipboardEntry] = []
        self._load_history()

    def _load_history(self):
        """Load clipboard history from disk"""
        if os.path.exists(self.persist_file):
            try:
                with open(self.persist_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.history = [ClipboardEntry.from_dict(entry) for entry in data]
            except Exception as e:
                self.logger.warning(f"Could not load clipboard history: {e}")
                self.history = []

    def _save_history(self):
        """Save clipboard history to disk"""
        try:
            with open(self.persist_file, "w", encoding="utf-8") as f:
                data = [entry.to_dict() for entry in self.history]
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.warning(f"Could not save clipboard history: {e}")

    def copy(
        self,
        content: str,
        content_type: ClipboardType = ClipboardType.TEXT,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Copy content to clipboard and add to history

        Args:
            content: Content to copy
            content_type: Type of content
            metadata: Optional metadata about the content

        Returns:
            True if successful, False otherwise
        """
        try:
            # Copy to system clipboard if available
            if self.use_system_clipboard:
                pyperclip.copy(content)
            else:
                self._internal_clipboard = content

            # Add to history
            entry = ClipboardEntry(content, content_type, metadata)
            self.history.insert(0, entry)

            # Limit history size
            if len(self.history) > self.history_limit:
                self.history = self.history[: self.history_limit]

            # Persist history
            self._save_history()

            return True
        except Exception as e:
            self.logger.error(f"Error copying to clipboard: {e}", exc_info=True)
            return False

    def paste(self) -> Optional[str]:
        """
        Get content from system clipboard

        Returns:
            Clipboard content or None if empty/error
        """
        try:
            if self.use_system_clipboard:
                content = pyperclip.paste()
            else:
                content = self._internal_clipboard
            return content if content else None
        except Exception as e:
            self.logger.error(f"Error pasting from clipboard: {e}", exc_info=True)
            return None

    # --- FIX CRITIQUE: Méthode requise par ActionCoordinator ---
    async def get_text(self) -> str:
        """
        Get text from clipboard (async alias for paste).
        Used by ActionCoordinator to observe system state.
        Returns empty string if None to avoid crashes.
        """
        content = self.paste()
        return content if content else ""
    # -----------------------------------------------------------

    def get_last(self, count: int = 1) -> List[ClipboardEntry]:
        """
        Get last N entries from clipboard history

        Args:
            count: Number of entries to retrieve

        Returns:
            List of clipboard entries
        """
        return self.history[:count]

    def get_history(self, content_type: Optional[ClipboardType] = None) -> List[ClipboardEntry]:
        """
        Get clipboard history, optionally filtered by type

        Args:
            content_type: Optional filter by content type

        Returns:
            List of clipboard entries
        """
        if content_type:
            return [entry for entry in self.history if entry.content_type == content_type]
        return self.history.copy()

    def search(self, query: str, case_sensitive: bool = False) -> List[ClipboardEntry]:
        """
        Search clipboard history for entries containing query

        Args:
            query: Search query
            case_sensitive: Whether to perform case-sensitive search

        Returns:
            List of matching clipboard entries
        """
        results = []
        for entry in self.history:
            content = entry.content if case_sensitive else entry.content.lower()
            search_query = query if case_sensitive else query.lower()
            if search_query in content:
                results.append(entry)
        return results

    def clear_history(self):
        """Clear clipboard history"""
        self.history = []
        self._save_history()

    def get_current(self) -> Optional[ClipboardEntry]:
        """
        Get the most recent clipboard entry

        Returns:
            Most recent clipboard entry or None
        """
        return self.history[0] if self.history else None

    def copy_text(self, text: str, source: Optional[str] = None) -> bool:
        """
        Convenience method to copy text

        Args:
            text: Text to copy
            source: Optional source description

        Returns:
            True if successful
        """
        metadata = {"source": source} if source else {}
        return self.copy(text, ClipboardType.TEXT, metadata)

    def copy_file_path(self, path: str) -> bool:
        """
        Copy file path to clipboard

        Args:
            path: File path to copy

        Returns:
            True if successful
        """
        metadata = {"type": "file_path", "path": path}
        return self.copy(path, ClipboardType.FILE_PATH, metadata)

    def copy_json(self, data: Any, pretty: bool = True) -> bool:
        """
        Copy JSON data to clipboard

        Args:
            data: Data to serialize as JSON
            pretty: Whether to pretty-print JSON

        Returns:
            True if successful
        """
        try:
            json_str = json.dumps(data, indent=2 if pretty else None, ensure_ascii=False)
            metadata = {"type": "json", "original_type": type(data).__name__}
            return self.copy(json_str, ClipboardType.JSON, metadata)
        except Exception as e:
            self.logger.error(f"Error serializing to JSON: {e}", exc_info=True)
            return False

    def capture_current_clipboard(self) -> Optional[ClipboardEntry]:
        """
        Capture the current system clipboard content and add it to history if new.
        
        This is called at "wake word" time to capture what the user has selected.
        If the clipboard content is different from the most recent entry, it creates
        a new entry in history.
        
        Returns:
            ClipboardEntry for the current clipboard content, or None if empty
        """
        try:
            # Get current clipboard content from system
            current_content = self.paste()
            
            if not current_content:
                return None
            
            # Check if this is different from the most recent history entry
            last_entry = self.get_current()
            if last_entry and last_entry.content == current_content:
                # Content unchanged, return existing entry
                return last_entry
            
            # New content - add to history
            self.copy_text(current_content, source="wake_word_capture")
            return self.get_current()
            
        except Exception as e:
            self.logger.error(f"Error capturing clipboard: {e}", exc_info=True)
            return None

    def get_recent_clipboard(self, max_age_seconds: float = 10.0) -> Optional[str]:
        """
        Get clipboard content if it was copied recently (within max_age_seconds).
        
        This implements the "Smart Clipboard" feature - if the user copied something
        recently and then gives a voice command, we assume they want to reference it.
        
        Args:
            max_age_seconds: Maximum age in seconds for clipboard to be considered "recent"
        
        Returns:
            Clipboard text content if recent, None otherwise
        """
        try:
            # First, capture current clipboard to ensure we have the latest
            entry = self.capture_current_clipboard()
            
            if not entry:
                return None
            
            # Parse timestamp and check age
            entry_time = datetime.fromisoformat(entry.timestamp)
            
            # Make timezone-aware if not already
            if entry_time.tzinfo is None:
                entry_time = entry_time.replace(tzinfo=timezone.utc)
            
            current_time = datetime.now(timezone.utc)
            age_seconds = (current_time - entry_time).total_seconds()
            
            if age_seconds <= max_age_seconds:
                self.logger.debug(f"Clipboard is recent ({age_seconds:.1f}s old), including in context")
                return entry.content
            else:
                self.logger.debug(f"Clipboard is old ({age_seconds:.1f}s), not including")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting recent clipboard: {e}", exc_info=True)
            return None