"""
Unified execution pipeline for Janus.

 DEPRECATION NOTICE ():
This module is now INTERNAL implementation detail.

For external use, import JanusAgent instead:
    from janus.runtime.core import JanusAgent
    
    agent = JanusAgent()
    result = await agent.execute("open Calculator")

JanusPipeline is still used internally by JanusAgent but should NOT be
used directly in new code. See docs/architecture/15-janus-agent-api.md

---

This module provides a single, clean pipeline that:
1. Processes voice or text input (STT for voice)
2. Parses commands into intents (NLU + reasoning)
3. Creates action plans (Planner)
4. Executes actions (ActionCoordinator)
5. Verifies results (Vision)
6. Updates state and logs (Memory)
7. Provides feedback (TTS)

Features:
- Lazy component loading
- Voice and text input support
- Deterministic NLU with optional LLM reasoning
- Vision integration for verification
- Learning integration for continuous improvement
- Structured logging at each step
- Session state management
- Request ID tracking

Unified flow: speech -> reasoning -> action -> vision
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from janus.i18n import t
from janus.ai.reasoning.reasoner_llm import ReasonerLLM, LLMBackend
from janus.services import STTService, VisionService, MemoryServiceWrapper, TTSService

# Import implementation mixin (extracted to reduce file size)
from ._pipeline_impl import PipelineImplementationMixin
from ._pipeline_properties import PipelinePropertiesMixin

from .contracts import (
    ActionPlan,
    ActionResult,
    CommandError,
    ErrorType,
    ExecutionContext,
    ExecutionResult,
    Intent,
)
from .settings import Settings

logger = logging.getLogger(__name__)

# System context logging constants
SYSTEM_CONTEXT_LOG_TRUNCATE_LENGTH = 30  # Truncate window title to this length for logging

class JanusPipeline(PipelinePropertiesMixin, PipelineImplementationMixin):
    """
    Unified execution pipeline for Janus.

    Single, clean pipeline: speech -> reasoning -> action -> vision

    Supports both voice and text input, with optional components:
    - STT (Speech-to-Text) for voice input
    - NLU (Natural Language Understanding) for deterministic intent parsing
    - LLM reasoning for complex command disambiguation
    - Vision for action verification
    - Learning for continuous improvement
    - TTS (Text-to-Speech) for user feedback
    
     REFACTORING NOTE ():
    This class now inherits from PipelineImplementationMixin which contains
    ~2300 lines of implementation. Extracted to reduce
    file size. Phase 2 will extract these into proper service modules.
    """

    def __init__(
        self,
        settings: Settings,
        memory,  # MemoryEngine
        session_id: Optional[str] = None,
        enable_voice: bool = False,
        enable_llm_reasoning: bool = True,
        enable_vision: bool = True,
        enable_learning: bool = True,
        enable_tts: bool = False,
        load_context_from_recent: bool = True,
    ):
        """
        Initialize unified pipeline with settings and memory.

        Args:
            settings: Unified settings
            memory: MemoryEngine for persistence
            session_id: Optional session ID (uses memory's session if not provided)
            enable_voice: Enable voice input (STT)
            enable_llm_reasoning: Enable LLM for command disambiguation
            enable_vision: Enable vision for action verification
            enable_learning: Enable learning from user corrections
            enable_tts: Enable TTS feedback
            load_context_from_recent: Load context from recent sessions (multi-session memory)
        """
        self.settings = settings
        self.memory = memory
        
        # Use session ID from MemoryEngine or provided session_id
        self.session_id = session_id or memory.session_id
        if session_id and session_id != memory.session_id and hasattr(memory, 'switch_session'):
            memory.switch_session(session_id)

        # Feature flags
        self.enable_voice = enable_voice
        self.enable_llm_reasoning = enable_llm_reasoning
        self.enable_vision = enable_vision
        self.enable_learning = enable_learning
        self.enable_tts = enable_tts
        self.load_context_from_recent = load_context_from_recent

        # Callback for status updates (called when execution phase starts)
        self._on_execution_start_callback = None

        # Lazy-loaded components
        self._learning_manager = None
        self._conversation_manager = None  # ConversationManager for multi-turn dialogue
        self._reasoner_llm = None  # ReasonerLLM (the Ferrari)
        self._unified_llm_client = None  # UnifiedLLMClient for semantic correction and other LLM tasks
        self._agent_registry = None  # AgentRegistry for module -> agent mapping 
        self._context_router = None  # ContextRouter for smart context pruning
        self._context_ranker = None  # ContextRanker for smart file history ranking
        self._clipboard_manager = None  # ClipboardManager for robust clipboard access
        self._semantic_router = None  # SemanticRouter for ultra-fast input filtering
        self._action_coordinator = None  # ActionCoordinator for OODA loop
        # Removed _parser_agent - LLM now handles raw text directly
        
        # Service modules ()
        self._stt_service: Optional[STTService] = None
        self._vision_service: Optional[VisionService] = None
        self._memory_service_wrapper: Optional[MemoryServiceWrapper] = None
        self._tts_service: Optional[TTSService] = None
        self._lifecycle_service = None  # LifecycleService for init/cleanup/warmup

        logger.info(
            f"JanusPipeline initialized for session {self.session_id} "
            f"(voice={enable_voice}, llm={enable_llm_reasoning}, "
            f"vision={enable_vision}, learning={enable_learning}, tts={enable_tts}, "
            f"multi_session={load_context_from_recent})"
        )
        memory.log_structured(
            level="INFO",
            logger="JanusPipeline",
            message=f"Pipeline initialized",
            session_id=self.session_id,
            module=__name__,
            function="__init__",
        )

        # Load context from recent sessions if enabled
        if load_context_from_recent:
            self.memory_service_wrapper.load_recent_session_context()
        
        # Start battery monitor for eco mode (TICKET-PERF-002)
        if enable_vision:
            self.lifecycle_service.start_battery_monitor()
        
        # Start task scheduler for delayed actions (TICKET-FEAT-002)
        self.lifecycle_service.start_task_scheduler()

    def set_on_execution_start_callback(self, callback):
        """
        Set a callback to be called when the execution phase starts.
        
        This is called after reasoning/planning is complete but before
        the actual actions are executed.
        
        Args:
            callback: A callable with no arguments, or None to clear
        """
        self._on_execution_start_callback = callback

    def process_voice_command(self, mock_execution: bool = False) -> ExecutionResult:
        """
        Process a voice command through the complete pipeline.

        Pipeline flow: Listen -> STT -> NLU -> Reasoning -> Plan -> Execute -> Vision -> Learn -> TTS

        Args:
            mock_execution: If True, skip actual execution (for testing)

        Returns:
            ExecutionResult with all action results and logs
        """
        # Run async version using asyncio.run
        return asyncio.run(self.process_voice_command_async(mock_execution))

    async def process_voice_command_async(self, mock_execution: bool = False) -> ExecutionResult:
        """
        Process a voice command through the complete pipeline asynchronously.

        Pipeline flow: Listen -> STT -> NLU -> Reasoning -> Plan -> Execute -> Vision -> Learn -> TTS

        This is the async version that prevents UI blocking during voice processing.

        Args:
            mock_execution: If True, skip actual execution (for testing)

        Returns:
            ExecutionResult with all action results and logs
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(f"Processing voice command async (request_id={request_id})")
        self.memory.log_structured(
            level="INFO",
            logger="JanusPipeline",
            message="Processing voice command async",
            session_id=self.session_id,
            request_id=request_id,
            module=__name__,
            function="process_voice_command_async",
        )

        try:
            # Step 0: Stop TTS if speaking to avoid feedback loop
            if self.tts_service.is_speaking():
                logger.debug("Stopping TTS before STT to avoid feedback loop")
                self.tts_service.stop()

            # Step 1: Listen and transcribe (STT) - Use async version
            if not self.stt_service.is_available():
                raise ValueError("Voice input not enabled. Set enable_voice=True")

            transcription = await self.stt_service.listen_and_transcribe_async()

            if not transcription:
                raise ValueError("No transcription from STT")

            logger.info(f"Transcribed: '{transcription}'")

            # Process the transcribed text through the main pipeline
            result = await self.process_command_async(
                transcription, mock_execution=mock_execution, request_id=request_id
            )

            # Provide TTS feedback if enabled
            if result.success:
                self.tts_service.speak("Commande exécutée avec succès")

            return result

        except Exception as e:
            logger.error(f"Error processing voice command: {e}", exc_info=True)
            self.memory.log_structured(
                level="ERROR",
                logger="JanusPipeline",
                message=f"Error processing voice command: {e}",
                session_id=self.session_id,
                request_id=request_id,
                module=__name__,
                function="process_voice_command_async",
            )

            # Return error result
            error = CommandError(error_type=ErrorType.SYSTEM_ERROR, message=str(e), details={})

            intent = Intent(action="error", confidence=0.0, raw_command="")

            result = ExecutionResult(
                intent=intent,
                success=False,
                error=error,
                session_id=self.session_id,
                request_id=request_id,
            )

            return result
