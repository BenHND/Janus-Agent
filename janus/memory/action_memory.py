"""
Action Memory System for Janus

Feature 6: Action Memory
Issue: FONCTIONNALITÉS MANQUANTES - #6

The agent must remember:
- Last click location and target
- Last scroll position and direction
- What it was searching for
- Recent UI elements interacted with
- Context of current task

This provides:
- Short-term action memory for immediate context
- Pattern detection for repetitive actions
- Recovery from failures using recent context
- Better chaining by understanding recent actions
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ActionMemoryType(Enum):
    """Types of actions to remember"""

    CLICK = "click"
    SCROLL = "scroll"
    TYPE = "type"
    SEARCH = "search"
    NAVIGATION = "navigation"
    VERIFICATION = "verification"


@dataclass
class ActionMemoryEntry:
    """Single entry in action memory"""

    action_type: ActionMemoryType
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    target_description: Optional[str] = None
    coordinates: Optional[Tuple[int, int]] = None
    context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "action_type": self.action_type.value,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "success": self.success,
            "target_description": self.target_description,
            "coordinates": self.coordinates,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionMemoryEntry":
        """Create from dictionary"""
        return cls(
            action_type=ActionMemoryType(data["action_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            details=data.get("details", {}),
            success=data.get("success", True),
            target_description=data.get("target_description"),
            coordinates=tuple(data["coordinates"]) if data.get("coordinates") else None,
            context=data.get("context"),
        )


class ActionMemory:
    """
    Short-term memory for agent actions

    Remembers recent actions to provide context for:
    - Retry logic (what was just attempted?)
    - Chaining (what did I just do?)
    - Recovery (where was I before the error?)
    - Pattern detection (am I doing the same thing repeatedly?)
    """

    def __init__(self, max_size: int = 100):
        """
        Initialize action memory

        Args:
            max_size: Maximum number of actions to remember
        """
        self.max_size = max_size
        self.memory: List[ActionMemoryEntry] = []

        # Quick access to recent specific actions
        self._last_click: Optional[ActionMemoryEntry] = None
        self._last_scroll: Optional[ActionMemoryEntry] = None
        self._last_search: Optional[ActionMemoryEntry] = None
        self._search_target: Optional[str] = None

        # Pattern detection
        self._action_counts: Dict[str, int] = {}

    def record_click(
        self,
        target: str,
        coordinates: Tuple[int, int],
        success: bool = True,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Record a click action

        Args:
            target: Description of what was clicked
            coordinates: (x, y) coordinates of click
            success: Whether click succeeded
            context: Additional context
        """
        entry = ActionMemoryEntry(
            action_type=ActionMemoryType.CLICK,
            timestamp=datetime.now(),
            target_description=target,
            coordinates=coordinates,
            success=success,
            details={"x": coordinates[0], "y": coordinates[1]},
            context=context,
        )

        self._add_entry(entry)
        self._last_click = entry
        self._increment_count("click")

    def record_scroll(
        self,
        direction: str,
        amount: int,
        position: Optional[Tuple[int, int]] = None,
        success: bool = True,
    ):
        """
        Record a scroll action

        Args:
            direction: "up" or "down"
            amount: Scroll amount
            position: Optional position where scroll occurred
            success: Whether scroll succeeded
        """
        entry = ActionMemoryEntry(
            action_type=ActionMemoryType.SCROLL,
            timestamp=datetime.now(),
            coordinates=position,
            success=success,
            details={"direction": direction, "amount": amount},
        )

        self._add_entry(entry)
        self._last_scroll = entry
        self._increment_count("scroll")

    def record_search(
        self,
        search_target: str,
        found: bool = False,
        location: Optional[Tuple[int, int]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Record a search action (looking for an element)

        Args:
            search_target: What was being searched for
            found: Whether it was found
            location: Location where found (if found)
            context: Additional context
        """
        entry = ActionMemoryEntry(
            action_type=ActionMemoryType.SEARCH,
            timestamp=datetime.now(),
            target_description=search_target,
            coordinates=location,
            success=found,
            details={"search_query": search_target, "found": found},
            context=context,
        )

        self._add_entry(entry)
        self._last_search = entry
        self._search_target = search_target if not found else None
        self._increment_count("search")

    def record_navigation(self, from_location: str, to_location: str, success: bool = True):
        """
        Record a navigation action

        Args:
            from_location: Where navigation started
            to_location: Where navigation went
            success: Whether navigation succeeded
        """
        entry = ActionMemoryEntry(
            action_type=ActionMemoryType.NAVIGATION,
            timestamp=datetime.now(),
            target_description=to_location,
            success=success,
            details={"from": from_location, "to": to_location},
        )

        self._add_entry(entry)
        self._increment_count("navigation")

    def record_verification(
        self, what_verified: str, result: bool, details: Optional[Dict[str, Any]] = None
    ):
        """
        Record a verification action

        Args:
            what_verified: What was being verified
            result: Verification result
            details: Additional details
        """
        entry = ActionMemoryEntry(
            action_type=ActionMemoryType.VERIFICATION,
            timestamp=datetime.now(),
            target_description=what_verified,
            success=result,
            details=details or {},
        )

        self._add_entry(entry)
        self._increment_count("verification")

    def get_last_click(self) -> Optional[ActionMemoryEntry]:
        """Get last click action"""
        return self._last_click

    def get_last_scroll(self) -> Optional[ActionMemoryEntry]:
        """Get last scroll action"""
        return self._last_scroll

    def get_last_search(self) -> Optional[ActionMemoryEntry]:
        """Get last search action"""
        return self._last_search

    def get_current_search_target(self) -> Optional[str]:
        """Get what is currently being searched for"""
        return self._search_target

    def get_recent_actions(self, count: int = 10) -> List[ActionMemoryEntry]:
        """
        Get N most recent actions

        Args:
            count: Number of actions to retrieve

        Returns:
            List of recent actions (newest first)
        """
        return self.memory[-count:][::-1]

    def get_actions_by_type(
        self, action_type: ActionMemoryType, count: int = 10
    ) -> List[ActionMemoryEntry]:
        """
        Get recent actions of specific type

        Args:
            action_type: Type of actions to retrieve
            count: Maximum number to retrieve

        Returns:
            List of matching actions (newest first)
        """
        matching = [e for e in self.memory if e.action_type == action_type]
        return matching[-count:][::-1]

    def get_failed_actions(self, count: int = 10) -> List[ActionMemoryEntry]:
        """
        Get recent failed actions

        Args:
            count: Maximum number to retrieve

        Returns:
            List of failed actions (newest first)
        """
        failed = [e for e in self.memory if not e.success]
        return failed[-count:][::-1]

    def is_repeating_pattern(self, action_type: str, threshold: int = 3) -> bool:
        """
        Detect if action is being repeated excessively

        Args:
            action_type: Type of action to check
            threshold: Number of repetitions to consider a pattern

        Returns:
            True if pattern detected
        """
        return self._action_counts.get(action_type, 0) >= threshold

    def get_context_summary(self) -> Dict[str, Any]:
        """
        Get summary of current action context

        Returns:
            Dictionary with context summary including:
            - Last actions of each type
            - Current search target
            - Recent failures
            - Pattern warnings
        """
        summary = {
            "last_click": self._last_click.to_dict() if self._last_click else None,
            "last_scroll": self._last_scroll.to_dict() if self._last_scroll else None,
            "last_search": self._last_search.to_dict() if self._last_search else None,
            "current_search_target": self._search_target,
            "recent_actions_count": len(self.memory),
            "failed_actions_count": len([e for e in self.memory if not e.success]),
            "action_counts": self._action_counts.copy(),
            "potential_patterns": [
                action_type for action_type, count in self._action_counts.items() if count >= 3
            ],
        }

        # Add recent failures
        recent_failures = self.get_failed_actions(5)
        summary["recent_failures"] = [f.to_dict() for f in recent_failures]

        return summary

    def clear(self):
        """Clear all memory"""
        self.memory.clear()
        self._last_click = None
        self._last_scroll = None
        self._last_search = None
        self._search_target = None
        self._action_counts.clear()

    def clear_search_target(self):
        """Clear current search target (e.g., after found)"""
        self._search_target = None

    def _add_entry(self, entry: ActionMemoryEntry):
        """Add entry to memory"""
        self.memory.append(entry)

        # Trim if exceeds max size
        if len(self.memory) > self.max_size:
            self.memory = self.memory[-self.max_size :]

    def _increment_count(self, action_type: str):
        """Increment action count for pattern detection"""
        self._action_counts[action_type] = self._action_counts.get(action_type, 0) + 1

        # Reset counts periodically to avoid false positives
        if sum(self._action_counts.values()) > 50:
            self._action_counts = {k: v // 2 for k, v in self._action_counts.items()}

    def save_to_file(self, filepath: str):
        """Save memory to JSON file"""
        data = {
            "memory": [entry.to_dict() for entry in self.memory],
            "search_target": self._search_target,
            "action_counts": self._action_counts,
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def load_from_file(self, filepath: str):
        """Load memory from JSON file"""
        with open(filepath, "r") as f:
            data = json.load(f)

        self.memory = [ActionMemoryEntry.from_dict(e) for e in data.get("memory", [])]
        self._search_target = data.get("search_target")
        self._action_counts = data.get("action_counts", {})

        # Reconstruct quick access references
        for entry in reversed(self.memory):
            if entry.action_type == ActionMemoryType.CLICK and self._last_click is None:
                self._last_click = entry
            elif entry.action_type == ActionMemoryType.SCROLL and self._last_scroll is None:
                self._last_scroll = entry
            elif entry.action_type == ActionMemoryType.SEARCH and self._last_search is None:
                self._last_search = entry


class ActionMemoryManager:
    """
    Manager for action memory across sessions

    Provides:
    - Per-session action memory
    - Cross-session pattern detection
    - Memory persistence
    """

    def __init__(self):
        """Initialize action memory manager"""
        self.sessions: Dict[str, ActionMemory] = {}
        self.current_session_id: Optional[str] = None

    def create_session(self, session_id: str) -> ActionMemory:
        """
        Create new action memory session

        Args:
            session_id: Session identifier

        Returns:
            ActionMemory instance for session
        """
        memory = ActionMemory()
        self.sessions[session_id] = memory
        self.current_session_id = session_id
        return memory

    def get_session(self, session_id: str) -> Optional[ActionMemory]:
        """Get action memory for session"""
        return self.sessions.get(session_id)

    def get_current_session(self) -> Optional[ActionMemory]:
        """Get current session memory"""
        if self.current_session_id:
            return self.sessions.get(self.current_session_id)
        return None

    def switch_session(self, session_id: str) -> bool:
        """
        Switch to different session

        Args:
            session_id: Session to switch to

        Returns:
            True if successful
        """
        if session_id in self.sessions:
            self.current_session_id = session_id
            return True
        return False

    def get_cross_session_patterns(self) -> Dict[str, Any]:
        """
        Analyze patterns across all sessions

        Returns:
            Dictionary with cross-session insights
        """
        total_actions = 0
        total_failures = 0
        action_type_counts = {}

        for memory in self.sessions.values():
            total_actions += len(memory.memory)
            total_failures += len([e for e in memory.memory if not e.success])

            for action_type, count in memory._action_counts.items():
                action_type_counts[action_type] = action_type_counts.get(action_type, 0) + count

        return {
            "total_sessions": len(self.sessions),
            "total_actions": total_actions,
            "total_failures": total_failures,
            "failure_rate": total_failures / total_actions if total_actions > 0 else 0,
            "action_type_counts": action_type_counts,
            "most_common_action": (
                max(action_type_counts.items(), key=lambda x: x[1])[0]
                if action_type_counts
                else None
            ),
        }
