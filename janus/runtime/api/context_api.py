"""
Context API - Public API for Context & Memory Engine
Part of PHASE-19: Context & Memory Engine

Provides high-level API functions:
- get_context(): Get current context snapshot
- update_context(): Update context with new data
- clear_context(): Clear all context data

ARCH-004: Migrated to use ActionCoordinator for canonical SystemState observation.
ContextAnalyzer has been removed.
"""

import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from janus.runtime.core.memory_engine import MemoryEngine
from janus.memory.calendar_provider import CalendarProvider

# ARCH-004: Import ActionCoordinator for canonical SystemState observation
from janus.runtime.core.action_coordinator import ActionCoordinator
from janus.memory.email_provider import EmailProvider
from janus.memory.session_context import SessionContext
from janus.persistence.unified_store import UnifiedStore

from janus.constants import CONTEXT_MEMORY_LIMIT


class ContextEngine:
    """
    Unified Context & Memory Engine

    Combines:
    - ActionCoordinator: System state capture via canonical SystemState (ARCH-004)
    - SessionContext: Short-term session memory
    - MemoryEngine: Unified memory system
    - UnifiedStore: Long-term storage
    """

    def __init__(
        self,
        enable_ocr: bool = False,  # OCR is slow, disabled by default
        enable_persistence: bool = True,
        db_path: str = "context_memory.db",
        enable_calendar: bool = False,  # Calendar provider disabled by default
        enable_email: bool = False,  # Email provider disabled by default
    ):
        """
        Initialize context engine

        Args:
            enable_ocr: Enable OCR for visible text capture (slower) - DEPRECATED
            enable_persistence: Enable persistent storage
            db_path: Path to persistence database
            enable_calendar: Enable calendar context provider
            enable_email: Enable email context provider
        """
        # ARCH-004: Use ActionCoordinator for system state observation
        # OCR is handled separately via vision system, not through state observation
        self.coordinator = ActionCoordinator(max_iterations=1)
        
        self.session = SessionContext()
        self.memory = MemoryEngine(db_path=db_path)

        # Initialize persistence if enabled
        self.persistence = None
        if enable_persistence:
            self.persistence = UnifiedStore(db_path=db_path)

        self.enable_persistence = enable_persistence

        # Initialize context providers
        self.calendar_provider = CalendarProvider()
        self.email_provider = EmailProvider()

        if enable_calendar:
            self.calendar_provider.enable()

        if enable_email:
            self.email_provider.enable()

    async def get_context(self, include_ocr: bool = False, include_apps: bool = True) -> Dict[str, Any]:
        """
        Get complete context snapshot

        ARCH-004: Uses ActionCoordinator for canonical SystemState observation.
        OCR parameter is deprecated - vision is handled separately.

        Args:
            include_ocr: DEPRECATED - OCR handled via vision system
            include_apps: DEPRECATED - apps always included in SystemState

        Returns:
            Complete context dictionary with:
            - system_state: Current system state (canonical SystemState as dict)
            - session: Current session context
            - memory: Conversational context
            - performance_ms: Total time taken
        """
        start_time = time.time()

        # ARCH-004: Get system state via ActionCoordinator (canonical SystemState)
        import asyncio
        system_state_obj = await self.coordinator._observe_system_state()
        system_state = system_state_obj.to_dict()

        # Get session context
        session_context = self.session.get_context_for_chaining()

        # Get memory context
        memory_context = {
            "last_app": self.memory.retrieve("last_app"),
            "last_file": self.memory.retrieve("last_file"),
            "last_url": self.memory.retrieve("last_url"),
            "last_commands": self.memory.get_command_history(
                session_id=self.memory.session_id, 
                limit=CONTEXT_MEMORY_LIMIT
            ),
        }

        # Get provider contexts
        calendar_context = self.calendar_provider.get_context()
        email_context = self.email_provider.get_context()

        # Calculate total performance
        elapsed_ms = (time.time() - start_time) * 1000

        context = {
            "timestamp": datetime.now().isoformat(),
            "system_state": system_state,
            "session": session_context,
            "memory": memory_context,
            "calendar": calendar_context,
            "email": email_context,
            "performance_ms": round(elapsed_ms, 2),
        }

        # Save to persistence if enabled
        if self.persistence:
            snapshot_type = "canonical_state"  # ARCH-004: Always canonical now
            self.persistence.save_context_snapshot(context, snapshot_type=snapshot_type)

        return context

    def update_context(
        self,
        command_text: Optional[str] = None,
        intent: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        action_type: Optional[str] = None,
        action_details: Optional[Dict[str, Any]] = None,
    ):
        """
        Update context with new information

        Args:
            command_text: Command text (for commands)
            intent: Command intent
            parameters: Command parameters
            result: Execution result
            action_type: Action type (click, copy, paste)
            action_details: Action details
        """
        # Update session context
        if command_text and intent and parameters is not None:
            self.session.record_command(command_text, intent, parameters, result)
            # Store command in memory
            request_id = str(uuid.uuid4())
            self.memory.store_command(
                session_id=self.memory.session_id,
                raw_command=command_text,
                intent=intent,
                request_id=request_id,
                parameters=parameters
            )
            # Update quick references
            if parameters.get("app_name"):
                self.memory.store("last_app", parameters["app_name"])
            if parameters.get("file_path"):
                self.memory.store("last_file", parameters["file_path"])
            if parameters.get("url"):
                self.memory.store("last_url", parameters["url"])

        elif action_type == "click" and action_details:
            self.session.record_click(
                action_details.get("x", 0),
                action_details.get("y", 0),
                action_details.get("target"),
            )

        elif action_type == "copy" and action_details:
            self.session.record_copy(
                action_details.get("content", ""),
                action_details.get("source"),
            )

        elif action_type == "paste" and action_details:
            self.session.record_paste(
                action_details.get("content", ""),
                action_details.get("destination"),
            )

    def clear_context(
        self, clear_memory: bool = True, clear_session: bool = True, clear_persistence: bool = False
    ):
        """
        Clear context data

        Args:
            clear_memory: Clear conversational memory
            clear_session: Clear session context
            clear_persistence: Clear persistent storage (destructive!)
        """
        if clear_session:
            self.session.clear()

        if clear_memory:
            # Clear current session's memory
            self.memory.cleanup(days_old=0)

        if clear_persistence and self.persistence:
            self.persistence.clear_all()

    def resolve_reference(
        self, reference: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Resolve contextual reference like "it", "that", "here"

        Args:
            reference: Reference text
            context: Optional context hint

        Returns:
            Resolved value or None
        """
        # Try session context first (most recent)
        result = self.session.resolve_reference(reference)

        if result is not None:
            return result

        # Try memory context
        ref_lower = reference.lower().strip()

        if "app" in ref_lower:
            return self.memory.retrieve("last_app")

        if "file" in ref_lower:
            return self.memory.retrieve("last_file")

        if "url" in ref_lower or "site" in ref_lower:
            return self.memory.retrieve("last_url")

        # Use MemoryEngine's reference resolution
        return self.memory.resolve_reference(reference)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get context engine statistics

        Returns:
            Dictionary with statistics from all components
        """
        stats = {
            "session": self.session.get_statistics(),
            "memory": self.memory.get_statistics(),
        }

        # UnifiedStore doesn't have get_statistics, so we skip it
        # if self.persistence:
        #     stats["persistence"] = self.persistence.get_statistics()

        return stats


# Global context engine instance (lazy initialization)
_context_engine: Optional[ContextEngine] = None


def get_context_engine(enable_ocr: bool = False, enable_persistence: bool = True) -> ContextEngine:
    """
    Get or create global context engine instance

    Args:
        enable_ocr: Enable OCR for text capture
        enable_persistence: Enable persistent storage

    Returns:
        ContextEngine instance
    """
    global _context_engine

    if _context_engine is None:
        _context_engine = ContextEngine(
            enable_ocr=enable_ocr,
            enable_persistence=enable_persistence,
        )

    return _context_engine


# Public API Functions


def get_context(include_ocr: bool = False, include_apps: bool = True) -> Dict[str, Any]:
    """
    Get current context snapshot
    
    ARCH-004: Now uses canonical SystemState via ActionCoordinator.
    OCR parameter is deprecated.

    Args:
        include_ocr: DEPRECATED - OCR handled via vision system
        include_apps: DEPRECATED - apps always included in SystemState

    Returns:
        Context dictionary with system state, session, and memory

    Example:
        >>> context = get_context()
        >>> print(f"Last app: {context['memory']['last_app']}")
        >>> print(f"Performance: {context['performance_ms']}ms")
    """
    import asyncio
    engine = get_context_engine()
    
    # Run async method in sync context
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, engine.get_context(include_ocr=include_ocr, include_apps=include_apps))
                return future.result()
        else:
            return loop.run_until_complete(engine.get_context(include_ocr=include_ocr, include_apps=include_apps))
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(engine.get_context(include_ocr=include_ocr, include_apps=include_apps))


def update_context(
    command_text: Optional[str] = None,
    intent: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
    action_type: Optional[str] = None,
    action_details: Optional[Dict[str, Any]] = None,
):
    """
    Update context with new command or action

    Args:
        command_text: Command text
        intent: Command intent
        parameters: Command parameters
        result: Execution result
        action_type: Action type (click, copy, paste)
        action_details: Action details

    Example:
        >>> update_context(
        ...     command_text="open Chrome",
        ...     intent="open_app",
        ...     parameters={"app_name": "Chrome"},
        ... )
    """
    engine = get_context_engine()
    engine.update_context(
        command_text=command_text,
        intent=intent,
        parameters=parameters,
        result=result,
        action_type=action_type,
        action_details=action_details,
    )


def clear_context(
    clear_memory: bool = True, clear_session: bool = True, clear_persistence: bool = False
):
    """
    Clear context data

    Args:
        clear_memory: Clear conversational memory
        clear_session: Clear session context
        clear_persistence: Clear persistent storage (destructive!)

    Example:
        >>> clear_context(clear_session=True)  # Clear session only
        >>> clear_context()  # Clear session and memory
    """
    engine = get_context_engine()
    engine.clear_context(
        clear_memory=clear_memory,
        clear_session=clear_session,
        clear_persistence=clear_persistence,
    )


def resolve_reference(reference: str) -> Optional[Any]:
    """
    Resolve contextual reference

    Args:
        reference: Reference text (e.g., "it", "that", "here")

    Returns:
        Resolved value or None

    Example:
        >>> update_context(action_type="copy", action_details={"content": "Hello"})
        >>> resolve_reference("it")  # Returns "Hello"
    """
    engine = get_context_engine()
    return engine.resolve_reference(reference)


def get_context_statistics() -> Dict[str, Any]:
    """
    Get context engine statistics

    Returns:
        Dictionary with statistics

    Example:
        >>> stats = get_context_statistics()
        >>> print(f"Total actions: {stats['session']['total_actions']}")
    """
    engine = get_context_engine()
    return engine.get_statistics()
