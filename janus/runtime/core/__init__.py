"""
Janus Core Module

Unified core architecture providing:
- JanusAgent: Single public entry point (TICKET-AUDIT-003)
- Typed contracts (Intent, ActionPlan, ActionResult, etc.)
- Unified action schema (UnifiedAction, ActionTarget, etc.)
- Unified settings system
- SQLite-based memory service
- Unified memory manager (integrates all memory subsystems)
- Single unified execution pipeline (JanusPipeline)
- ActionCoordinator for OODA loop execution (TICKET-AUDIT-001)

Clean, modern architecture with no legacy code.
V3 Pipeline: SemanticRouter → ReasonerLLM → Validator → AgentExecutor
OODA Loop: Observe → Orient → Decide → Act (ActionCoordinator)

Public API:
- JanusAgent: Use this for all external integrations
- Internal: All other classes are implementation details
"""

from .action_coordinator import ActionCoordinator
from .janus_agent import JanusAgent, execute_command
# DEPRECATED: UnifiedAction schema - kept for backward compatibility only
# The SSOT is {module, action, args} from module_action_schema.py
# Do NOT use these in new code - they are not part of the public API
from .action_schema import (
    ActionChain,
    ActionMethod,
    ActionRetryPolicy,
    ActionTarget,
    ActionType,
    ActionVerification,
    UnifiedAction,
    VerificationType,
    click_action,
    open_tab_action,
    scroll_until_action,
    type_action,
    verify_state_action,
    wait_for_action,
)
from .context_ranker import ContextRanker
from .contracts import (
    ActionPlan,
    ActionResult,
    CommandError,
    ErrorType,
    ExecutionContext,
    ExecutionResult,
    Intent,
)
from .conversation_manager import (
    ClarificationQuestion,
    Conversation,
    ConversationManager,
    ConversationState,
    ConversationTurn,
)
from .memory_engine import MemoryEngine
from .pipeline import JanusPipeline
from .settings import Settings

__all__ = [
    # Public API - ONLY JanusAgent should be used externally
    "JanusAgent",
    "execute_command",
    # Contracts - for type hints and integration
    "Intent",
    "ActionPlan",
    "ActionResult",
    "ExecutionResult",
    "ExecutionContext",
    "CommandError",
    "ErrorType",
    # DEPRECATED: UnifiedAction schema - NOT part of public API
    # Use {module, action, args} schema from module_action_schema instead
    # These are kept for backward compatibility only
    # "UnifiedAction",  # Removed from public API
    # "ActionType",
    # "ActionMethod",
    # "ActionTarget",
    # "ActionVerification",
    # "VerificationType",
    # "ActionRetryPolicy",
    # "ActionChain",
    # "click_action",
    # "type_action",
    # "wait_for_action",
    # "verify_state_action",
    # "scroll_until_action",
    # "open_tab_action",
    # Settings & Memory
    "Settings",
    "MemoryEngine",  # TICKET-MIGRATION-001: Unified memory system
    "ContextRanker",
    # Conversation Management
    "ConversationManager",
    "Conversation",
    "ConversationTurn",
    "ConversationState",
    "ClarificationQuestion",
    # Pipeline & Coordination (Internal - should not be used directly)
    "JanusPipeline",
    "ActionCoordinator",
]
