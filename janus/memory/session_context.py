"""
SessionContext - Short-term session memory
Part of PHASE-19: Context & Memory Engine

Maintains memory for the current session:
- Last command executed
- Last click/copy/paste action
- Temporary references for command chaining
"""

import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ActionRecord:
    """Record of a single action in the session"""

    timestamp: float
    action_type: str  # 'command', 'click', 'copy', 'paste', etc.
    details: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None


class SessionContext:
    """
    Short-term memory for current session

    Features:
    - Last action tracking
    - Reference resolution ("it", "that", "here")
    - Command chaining context
    - Lightweight in-memory storage
    """

    def __init__(self, max_actions: int = 50):
        """
        Initialize session context

        Args:
            max_actions: Maximum number of actions to keep in memory
        """
        self.max_actions = max_actions
        self.actions: List[ActionRecord] = []

        # Quick reference tracking
        self.last_command = None
        self.last_click_position = None
        self.last_copied_content = None
        self.last_opened_app = None
        self.last_opened_file = None
        self.last_url = None

        # TICKET-ARCH-005: Dynamic memory for variable passing
        # Stores extracted data as key-value pairs (e.g., {"CEO_name": "John Smith"})
        self.dynamic_memory: Dict[str, Any] = {}

        # Session start time
        self.session_start = time.time()

    def record_command(
        self,
        command_text: str,
        intent: str,
        parameters: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
    ):
        """
        Record a command execution

        Args:
            command_text: Original command text
            intent: Parsed intent
            parameters: Command parameters
            result: Execution result
        """
        record = ActionRecord(
            timestamp=time.time(),
            action_type="command",
            details={
                "command_text": command_text,
                "intent": intent,
                "parameters": parameters,
            },
            result=result,
        )

        self._add_action(record)
        self.last_command = command_text

        # Update quick references based on intent
        self._update_references(intent, parameters, result)

    def record_click(self, x: int, y: int, target: Optional[str] = None):
        """
        Record a click action

        Args:
            x: X coordinate
            y: Y coordinate
            target: Optional description of click target
        """
        record = ActionRecord(
            timestamp=time.time(),
            action_type="click",
            details={"x": x, "y": y, "target": target},
        )

        self._add_action(record)
        self.last_click_position = (x, y)

    def record_copy(self, content: str, source: Optional[str] = None):
        """
        Record a copy action

        Args:
            content: Copied content
            source: Optional source description
        """
        record = ActionRecord(
            timestamp=time.time(),
            action_type="copy",
            details={"content": content, "source": source},
        )

        self._add_action(record)
        self.last_copied_content = content

    def record_paste(self, content: str, destination: Optional[str] = None):
        """
        Record a paste action

        Args:
            content: Pasted content
            destination: Optional destination description
        """
        record = ActionRecord(
            timestamp=time.time(),
            action_type="paste",
            details={"content": content, "destination": destination},
        )

        self._add_action(record)

    def _add_action(self, record: ActionRecord):
        """
        Add action to history

        Args:
            record: Action record to add
        """
        self.actions.append(record)

        # Trim if exceeding max
        if len(self.actions) > self.max_actions:
            self.actions = self.actions[-self.max_actions :]

    def _update_references(
        self, intent: str, parameters: Dict[str, Any], result: Optional[Dict[str, Any]]
    ):
        """
        Update quick references based on intent

        Args:
            intent: Command intent
            parameters: Command parameters
            result: Execution result
        """
        # Update last app
        if intent == "open_app" and "app_name" in parameters:
            self.last_opened_app = parameters["app_name"]

        # Update last file
        if intent in ["open_file", "create_file"] and "file_path" in parameters:
            self.last_opened_file = parameters["file_path"]
        elif intent == "create_file" and "filename" in parameters:
            self.last_opened_file = parameters["filename"]

        # Update last URL
        if intent in ["navigate_url", "open_url"] and "url" in parameters:
            self.last_url = parameters["url"]

    def resolve_reference(self, reference: str) -> Optional[Any]:
        """
        Resolve a contextual reference like "it", "that", "here"

        Args:
            reference: Reference text (e.g., "it", "that", "here")

        Returns:
            Resolved value or None
        """
        ref_lower = reference.lower().strip()

        # "it" or "that" typically refers to last copied content
        if ref_lower in ["it", "that", "le", "la", "ça"]:
            return self.last_copied_content

        # "here" refers to last click position
        if ref_lower in ["here", "ici"]:
            return self.last_click_position

        # "this file" refers to last opened file
        if "file" in ref_lower or "fichier" in ref_lower:
            return self.last_opened_file

        # "this app" refers to last opened app
        if "app" in ref_lower or "application" in ref_lower:
            return self.last_opened_app

        return None

    def get_last_action(self, action_type: Optional[str] = None) -> Optional[ActionRecord]:
        """
        Get last action of a specific type

        Args:
            action_type: Filter by action type (None for any action)

        Returns:
            Last action record or None
        """
        if not self.actions:
            return None

        if action_type is None:
            return self.actions[-1]

        # Find last action of specific type
        for action in reversed(self.actions):
            if action.action_type == action_type:
                return action

        return None

    def get_last_n_actions(self, n: int = 5) -> List[ActionRecord]:
        """
        Get last N actions

        Args:
            n: Number of actions to retrieve

        Returns:
            List of action records
        """
        return self.actions[-n:]

    def get_context_for_chaining(self) -> Dict[str, Any]:
        """
        Get context information for command chaining

        Returns:
            Dictionary with context for resolving implicit references
        """
        return {
            "last_command": self.last_command,
            "last_click_position": self.last_click_position,
            "last_copied_content": self.last_copied_content,
            "last_opened_app": self.last_opened_app,
            "last_opened_file": self.last_opened_file,
            "last_url": self.last_url,
            "session_duration_seconds": round(time.time() - self.session_start, 2),
            "total_actions": len(self.actions),
            "memory": self.dynamic_memory.copy(),  # TICKET-ARCH-005: Include dynamic memory
        }

    def clear(self):
        """Clear all session context"""
        self.actions = []
        self.last_command = None
        self.last_click_position = None
        self.last_copied_content = None
        self.last_opened_app = None
        self.last_opened_file = None
        self.last_url = None
        self.dynamic_memory = {}
    
    def save_to_memory(self, key: str, value: Any):
        """
        Save data to dynamic memory (TICKET-ARCH-005)
        
        This allows the agent to extract information and reuse it later.
        Example: save_to_memory("CEO_name", "John Smith")
        
        Args:
            key: Memory key (e.g., "CEO_name", "linkedin_profile_url")
            value: Value to store (any JSON-serializable type)
        """
        self.dynamic_memory[key] = value
    
    def get_from_memory(self, key: str) -> Optional[Any]:
        """
        Retrieve data from dynamic memory (TICKET-ARCH-005)
        
        Args:
            key: Memory key to retrieve
            
        Returns:
            Stored value or None if not found
        """
        return self.dynamic_memory.get(key)
    
    def get_all_memory(self) -> Dict[str, Any]:
        """
        Get all dynamic memory (TICKET-ARCH-005)
        
        Returns:
            Dictionary with all stored key-value pairs
        """
        return self.dynamic_memory.copy()
    
    def clear_memory(self):
        """Clear dynamic memory (TICKET-ARCH-005)"""
        self.dynamic_memory = {}

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get session statistics

        Returns:
            Dictionary with session stats
        """
        action_counts = {}
        for action in self.actions:
            action_type = action.action_type
            action_counts[action_type] = action_counts.get(action_type, 0) + 1

        return {
            "session_start": datetime.fromtimestamp(self.session_start).isoformat(),
            "session_duration_seconds": round(time.time() - self.session_start, 2),
            "total_actions": len(self.actions),
            "action_counts": action_counts,
            "has_copied_content": self.last_copied_content is not None,
            "has_click_position": self.last_click_position is not None,
            "dynamic_memory_items": len(self.dynamic_memory),
        }
