"""
Pipeline Implementation Module (Internal)

⚠️ INTERNAL MODULE - DO NOT IMPORT DIRECTLY

This module contains the implementation details of JanusPipeline that were
extracted during refactoring (). It exists to reduce
the size of pipeline.py .

For new code, the recommended approach is to use ActionCoordinator directly
or use the JanusAgent public API when it's available.

SYNC/ASYNC PATTERN ():
------------------------------------------
This module uses a consistent sync/async pattern where:
- Async methods (*_async) contain the actual implementation
- Sync methods are thin wrappers using asyncio.run() 

This pattern was evaluated in and decided to be kept as-is because:
1. The wrappers are simple and maintainable (just asyncio.run calls)
2. They provide value for synchronous callers 
3. Removing them would break existing code
4. The duplication is minimal compared to the implementation logic

If you need to add a new pipeline method, follow this pattern:
- Implement the async version with full logic
- Add a sync wrapper that calls asyncio.run(async_version(...))
"""

# Import everything needed by the extracted methods
import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from janus.i18n import t
from janus.ai.reasoning.reasoner_llm import LLMBackend
from janus.ai.reasoning.ambiguity_detector import AmbiguityDetector
from janus.logging.trace_recorder import TraceRecorderManager
from .contracts import (
    ActionPlan,
    ActionResult,
    CommandError,
    ErrorType,
    ExecutionContext,
    ExecutionResult,
    Intent,
)
from .conversation_manager import ConversationState

logger = logging.getLogger(__name__)

# Constants from pipeline.py
SYSTEM_CONTEXT_LOG_TRUNCATE_LENGTH = 30  # Truncate window title for logging

class PipelineImplementationMixin:
    """
    Mixin containing JanusPipeline implementation methods.
    
    This mixin is used by JanusPipeline to provide backward compatibility
    while keeping the main pipeline.py file small.
    
    
    
    
    All methods have access to self.memory, self.settings, self.session_id, etc.
    """
    def process_command(
        self, raw_command: str, mock_execution: bool = False, request_id: Optional[str] = None,
        conversation_mode: bool = False, extra_context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Process a command through the complete pipeline.

        Pipeline flow: NLU → Reasoning → Plan → Execute → Vision → Learn

        Args:
            raw_command: Raw text command from user
            mock_execution: If True, skip actual execution (for testing)
            request_id: Optional request ID for tracking
            conversation_mode: If True, enable conversation mode (unused, )
            extra_context: Optional additional context to merge with generated context
                          (Used for conversation_history in single-shot mode)

        Returns:
            ExecutionResult with all action results and logs
        """
        # Run async version using asyncio.run
        return asyncio.run(self.process_command_async(raw_command, mock_execution, request_id, conversation_mode, extra_context))

    async def process_command_async(
        self, raw_command: str, mock_execution: bool = False, request_id: Optional[str] = None,
        conversation_mode: bool = False, extra_context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Process a command through the complete pipeline asynchronously.

        Pipeline flow: NLU → Reasoning → Plan → Execute → Vision → Learn

        This is the async version that prevents UI blocking during command processing.
        Now supports compound commands with multiple intents.

        Args:
            raw_command: Raw text command from user
            mock_execution: If True, skip actual execution (for testing)
            request_id: Optional request ID for tracking
            conversation_mode: If True, enable conversation mode (unused, )
            extra_context: Optional additional context to merge with generated context
                          (Used for conversation_history in single-shot mode)

        Returns:
            ExecutionResult with all action results and logs
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(f"Processing command async: '{raw_command}' (request_id={request_id})")
        self.memory.log_structured(
            level="INFO",
            logger="JanusPipeline",
            message=f"Processing command async: {raw_command}",
            session_id=self.session_id,
            request_id=request_id,
            module=__name__,
            function="process_command_async",
        )

        # TICKET-DEV-001: Get trace recorder if enabled
        trace_recorder = TraceRecorderManager.get_recorder(self.session_id)

        try:
            # TICKET-DEV-001: Record initial state if trace recording enabled
            # PERF-FOUNDATION-001: Only record screenshots if trace_screenshots_enabled
            if trace_recorder and self.enable_vision and self.settings.features.trace_screenshots_enabled:
                try:
                    screenshot = self.vision_service.capture_screen()
                    trace_recorder.record_step(
                        step_name="initial_state",
                        screenshot=screenshot,
                        metadata={
                            "raw_command": raw_command,
                            "request_id": request_id,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to record initial state for trace: {e}")
            # Step 0 - Semantic Gatekeeper (filter input BEFORE expensive reasoning)
            logger.info("Step 0: Semantic Gatekeeper - classifying input intent")
            intent_type = self.semantic_router.classify_intent(raw_command)
            
            logger.info(f"Semantic classification: '{raw_command}' → {intent_type}")
            self.memory.log_structured(
                level="INFO",
                logger="JanusPipeline.SemanticRouter",
                message=f"Input classified as {intent_type}",
                session_id=self.session_id,
                request_id=request_id,
                module=__name__,
                function="process_command_async",
                extra_data={"raw_command": raw_command, "classification": intent_type},
            )
            
            # Handle NOISE: ignore and return immediately
            if intent_type == "NOISE":
                logger.info("NOISE detected - ignoring input (no Reasoner call)")
                intent = Intent(
                    action="noise_ignored",
                    confidence=1.0,
                    raw_command=raw_command,
                )
                result = ExecutionResult(
                    intent=intent,
                    success=True,
                    message="Ignored (Noise)",
                    session_id=self.session_id,
                    request_id=request_id,
                )
                result.total_duration_ms = int((time.time() - start_time) * 1000)
                return result
            
            # Handle CHAT: not implemented yet
            if intent_type == "CHAT":
                logger.info("CHAT detected - not implemented yet")
                intent = Intent(
                    action="chat_detected",
                    confidence=1.0,
                    raw_command=raw_command,
                )
                result = ExecutionResult(
                    intent=intent,
                    success=True,
                    message="Chat detected (Not implemented)",
                    session_id=self.session_id,
                    request_id=request_id,
                )
                result.total_duration_ms = int((time.time() - start_time) * 1000)
                return result
            
            # ACTION: continue to Reasoner V3
            logger.info("ACTION detected - continuing to Reasoner V3")
            
            # TICKET-REFACTOR-002: Migrated to ActionCoordinator (ReAct OODA loop)
            # Old static planning (generate_structured_plan) removed
            # New architecture: Dynamic execution with ActionCoordinator
            
            # Use configured language from settings (default: "fr")
            language = self.settings.language.default
            
            self.memory.log_structured(
                level="INFO",
                logger="JanusPipeline.OODA",
                message="Using ActionCoordinator for dynamic goal execution",
                session_id=self.session_id,
                request_id=request_id,
                module=__name__,
                function="process_command_async",
            )
            
            # Create intent from raw command
            intent = Intent(
                action="dynamic_goal",
                confidence=1.0,
                raw_command=raw_command,
            )
            
            # Store command
            self.memory_service_wrapper.store_command(
                raw_command=raw_command,
                intent=intent,
                request_id=request_id,
                session_id=self.session_id,
            )
            
            # Notify that execution phase is starting
            if self._on_execution_start_callback:
                try:
                    self._on_execution_start_callback()
                except Exception as e:
                    logger.warning(f"Error in on_execution_start callback: {e}")
            
            # Execute with ActionCoordinator (OODA loop)
            result = await self.action_coordinator.execute_goal(
                user_goal=raw_command,
                intent=intent,
                session_id=self.session_id,
                request_id=request_id,
                language=language,
            )
            
            logger.info(f"ActionCoordinator completed with success={result.success}")
            self.memory.log_structured(
                level="INFO",
                logger="JanusPipeline.OODA",
                message="ActionCoordinator completed",
                session_id=self.session_id,
                request_id=request_id,
                module=__name__,
                function="process_command_async",
                extra_data={
                    "success": result.success,
                    "num_results": len(result.action_results),
                },
            )
            
            # TICKET-DEV-001: Record final state after execution
            # PERF-FOUNDATION-001: Only record screenshots if trace_screenshots_enabled
            if trace_recorder and self.enable_vision and self.settings.features.trace_screenshots_enabled:
                try:
                    screenshot = self.vision_service.capture_screen()
                    trace_recorder.record_step(
                        step_name="final_state",
                        screenshot=screenshot,
                        metadata={
                            "success": result.success,
                            "num_actions": len(result.action_results),
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to record final state for trace: {e}")
            
            # TICKET-REFACTOR-002: Migration complete
            # All commands now execute via ActionCoordinator (OODA loop)
            # No more static planning - dynamic execution only
            
            # Step 4: Vision verification if enabled
            # PERF-FOUNDATION-001: Only verify if vision_verification_enabled
            if self.enable_vision and not mock_execution and self.settings.features.vision_verification_enabled:
                self.vision_service.verify_with_vision(result, request_id, self.memory)

            # Step 5: Learn from execution if enabled
            if self.enable_learning and not mock_execution and self.learning_manager:
                logger.debug("Learning from execution")
                self.memory.log_structured(
                    level="DEBUG",
                    logger="JanusPipeline",
                    message="Learning from execution",
                    session_id=self.session_id,
                    request_id=request_id,
                    module=__name__,
                    function="process_command_async",
                )

                try:
                    # Record feedback automatically based on execution result
                    feedback_type = "POSITIVE" if result.success else "NEGATIVE"
                    raw_command = result.intent.raw_command if hasattr(result.intent, "raw_command") else ""

                    self.learning_manager.record_feedback(
                        text=raw_command, intent=result.intent, feedback_type=feedback_type
                    )

                    # Also record individual action executions for detailed learning
                    for action_result in result.action_results:
                        self.learning_manager.record_action_execution(
                            action_type=action_result.action_type,
                            action_parameters={},
                            success=action_result.success,
                            duration_ms=action_result.duration_ms,
                            error_type=(
                                str(action_result.error_type)
                                if hasattr(action_result, "error_type") and action_result.error_type
                                else None
                            ),
                            error_message=action_result.error if hasattr(action_result, "error") else None,
                        )
                except Exception as e:
                    logger.warning(f"Learning error: {e}")

            # Step 6: Update state
            logger.debug("Updating session state")
            self.memory.log_structured(
                level="DEBUG",
                logger="JanusPipeline",
                message="Updating session state",
                session_id=self.session_id,
                request_id=request_id,
                module=__name__,
                function="process_command_async",
            )

            # Store execution result in context
            self.memory.store_context(
                session_id=self.session_id,
                context_type="execution_result",
                data={
                    "action": result.intent.action,
                    "success": result.success,
                    "action_count": len(result.action_results),
                    "duration_ms": result.total_duration_ms,
                },
            )

            # Calculate total duration
            result.total_duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Command processed successfully in {result.total_duration_ms}ms "
                f"(request_id={request_id})"
            )
            self.memory.log_structured(
                level="INFO",
                logger="JanusPipeline",
                message=f"Command processed successfully",
                session_id=self.session_id,
                request_id=request_id,
                module=__name__,
                function="process_command",
                extra_data={"duration_ms": result.total_duration_ms},
            )

            return result

        except Exception as e:
            logger.error(f"Error processing command: {e}", exc_info=True)
            self.memory.log_structured(
                level="ERROR",
                logger="JanusPipeline",
                message=f"Error processing command: {e}",
                session_id=self.session_id,
                request_id=request_id,
                module=__name__,
                function="process_command_async",
            )

            # Return error result
            error = CommandError(
                error_type=ErrorType.SYSTEM_ERROR,
                message=str(e),
                details={"raw_command": raw_command},
            )

            # Create a minimal intent for error case
            intent = Intent(action="unknown", confidence=0.0, raw_command=raw_command)

            result = ExecutionResult(
                intent=intent,
                success=False,
                error=error,
                session_id=self.session_id,
                request_id=request_id,
            )

            return result

    def process_command_with_conversation(
        self, raw_command: str, mock_execution: bool = False, request_id: Optional[str] = None
    ) -> tuple[ExecutionResult, Optional[str]]:
        """
        Process a command with conversation mode support.

        This method enables multi-turn conversation with:
        - Context carryover from previous turns
        - Clarification questions for ambiguous commands
        - Implicit reference resolution ("it", "that", etc.)

        Args:
            raw_command: Raw text command from user
            mock_execution: If True, skip actual execution (for testing)
            request_id: Optional request ID for tracking

        Returns:
            Tuple of (ExecutionResult, clarification_question or None)
        """
        if request_id is None:
            request_id = str(uuid.uuid4())

        logger.info(
            f"Processing command with conversation: '{raw_command}' (request_id={request_id})"
        )

        # Get or start conversation
        conversation = self.conversation_manager.get_active_conversation(self.session_id)
        if not conversation:
            conversation = self.conversation_manager.start_conversation(self.session_id)
            logger.info(f"Started new conversation for session {self.session_id}")

        # Check if this is a clarification response
        if conversation.state == ConversationState.NEEDS_CLARIFICATION:
            success, context = self.conversation_manager.resolve_clarification(
                conversation.conversation_id, raw_command
            )
            
            if success:
                # Use resolved context to retry original command
                original_command = context.get("original_command", raw_command)
                selected_option = context.get("selected_option")
                
                logger.info(f"Clarification resolved: {selected_option}")
                
                # Process the original command with resolved context
                result = self.process_command(
                    original_command,
                    mock_execution=mock_execution,
                    request_id=request_id,
                    extra_context={"selected_option": selected_option, **context}
                )
                
                # Add turn to conversation
                self.conversation_manager.add_turn(
                    conversation.conversation_id,
                    original_command,
                    intent=result.intent,
                    result=str(result.success),
                )
                
                return result, None
            else:
                # Clarification failed, ask again
                logger.warning("Failed to resolve clarification, asking again")
                last_turn = conversation.turns[-1] if conversation.turns else None
                if last_turn and last_turn.clarification:
                    return self._create_clarification_result(
                        last_turn.clarification.question,
                        last_turn.clarification.options,
                        raw_command,
                        request_id,
                    ), last_turn.clarification.question
                # Fallback to normal processing if no clarification found
        
        # Resolve implicit references using conversation context
        resolved_command = self.conversation_manager.resolve_implicit_references(
            raw_command, conversation.conversation_id
        )
        
        if resolved_command != raw_command:
            logger.info(f"Resolved implicit reference: '{raw_command}' -> '{resolved_command}'")
            raw_command = resolved_command

        # Get conversation context
        context_summary = self.conversation_manager.get_context_for_command(
            conversation.conversation_id
        )
        
        # Build extra context from conversation history
        extra_context = {
            "conversation_history": context_summary.get("last_commands", []),
            "recent_entities": context_summary.get("recent_entities", {}),
        }

        # Process command with conversation context
        result = self.process_command(
            raw_command,
            mock_execution=mock_execution,
            request_id=request_id,
            extra_context=extra_context,
        )

        # Check if clarification is needed
        clarification_question = None
        
        # Use ambiguity detector to check for ambiguities
        if result.intent:
            detector = AmbiguityDetector()
            ambiguity_info = detector.analyze_command(
                raw_command,
                result.intent.action,
                result.intent.parameters
            )
            
            # If ambiguity detected, override intent parameters
            if ambiguity_info["needs_clarification"]:
                result.intent.parameters["needs_clarification"] = True
                result.intent.parameters["ambiguity_type"] = ambiguity_info["ambiguity_type"]
                result.intent.parameters["options"] = ambiguity_info["options"]
        
        # Generate clarification if needed
        if result.intent and result.intent.parameters.get("needs_clarification"):
            ambiguity_type = result.intent.parameters.get("ambiguity_type", "unknown")
            options = result.intent.parameters.get("options", [])
            
            if options:
                clarification = self.conversation_manager.generate_clarification(
                    raw_command, ambiguity_type, options
                )
                
                # Add turn with clarification
                self.conversation_manager.add_turn(
                    conversation.conversation_id,
                    raw_command,
                    intent=result.intent,
                    clarification=clarification,
                    state=ConversationState.NEEDS_CLARIFICATION,
                )
                
                clarification_question = clarification.question
                
                # Format question with options
                formatted_question = f"{clarification.question}\n"
                for i, option in enumerate(clarification.options, 1):
                    formatted_question += f"{i}. {option}\n"
                
                return result, formatted_question.strip()
        
        # Add successful turn to conversation
        self.conversation_manager.add_turn(
            conversation.conversation_id,
            raw_command,
            intent=result.intent,
            result=str(result.success),
        )

        return result, None

    def _create_clarification_result(
        self, question: str, options: List[str], raw_command: str, request_id: str
    ) -> ExecutionResult:
        """Create an execution result for a clarification question"""
        intent = Intent(
            action="clarification_needed",
            confidence=1.0,
            parameters={"question": question, "options": options, "original_command": raw_command},
            raw_command=raw_command,
        )

        result = ExecutionResult(
            intent=intent,
            success=False,
            session_id=self.session_id,
            request_id=request_id,
            action_results=[
                ActionResult(
                    action_type="clarification",
                    success=True,
                    message=question,
                    data={"options": options},
                )
            ],
        )

        return result

    def _build_pruned_context(
        self, 
        required_keys: List[str], 
        request_id: str,
        current_command: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build pruned context containing only required modules (, ).
        Delegates to Memory service wrapper.
        
        Args:
            required_keys: List of required context keys from ContextRouter.
            request_id: Request ID for logging.
            current_command: The current user command (for TF-IDF similarity ranking).
        
        Returns:
            Dict with only the required context data.
        """
        return self.memory_service_wrapper.build_pruned_context(
            required_keys=required_keys,
            request_id=request_id,
            current_command=current_command,
            vision_service=self.vision_service,
        )
    
    # Context loading methods - delegates to Memory service wrapper ()
    
    def get_related_sessions(self, min_similarity: float = 0.3) -> list:
        """Find sessions with similar command patterns - delegates to Memory service wrapper"""
        return self.memory_service_wrapper.get_related_sessions(min_similarity)

    def get_session_summary(self) -> dict:
        """Get summary of current session - delegates to Memory service wrapper"""
        return self.memory_service_wrapper.get_session_summary()

    def cleanup(self):
        """
        Cleanup pipeline resources - delegates to Lifecycle service ()

        This method can be called to clean up any resources held by the pipeline.
        """
        self.lifecycle_service.cleanup()

    def start_monitor(self):
        """
        Start async vision monitor - delegates to Lifecycle service ()
        
        This starts background screen monitoring for popups, errors, and expected elements.
        The monitor runs in a daemon thread and will automatically stop when the program exits.
        """
        self.lifecycle_service.start_vision_monitor()

    def stop_monitor(self):
        """Stop async vision monitor - delegates to Lifecycle service ()"""
        self.lifecycle_service.stop_vision_monitor()

    async def preload_vision_models_async(self):
        """
        Asynchronously preload vision models - delegates to Lifecycle service ()
        
        This prevents the first vision-dependent command from blocking while
        models are loaded. Models are loaded in a background task so the
        application can continue initialization and be ready for user commands.
        
        This method should be called during application startup after pipeline
        initialization but before accepting user commands.
        
        Returns:
            bool: True if preloading was initiated successfully, False otherwise
        """
        return await self.lifecycle_service.preload_vision_models()

    async def preload_llm_model_async(self):
        """
        Asynchronously preload the LLM model - delegates to Lifecycle service ()
        
        This prevents the first LLM-dependent command from experiencing
        cold start delays while the model loads into memory (especially
        for Ollama which can take 60+ seconds on first request).
        
        This method should be called during application startup after pipeline
        initialization but before accepting user commands.
        
        Returns:
            bool: True if preloading was successful, False otherwise
        """
        return await self.lifecycle_service.preload_llm_model()

    async def warmup_systems(self):
        """
        FORCE MODEL LOADING INTO VRAM AT STARTUP - delegates to Lifecycle service ()
        
        This method is critical to avoid timeout on the first command.
        It forces the LLM model to load into memory by sending a dummy inference request.
        
        Must be called BEFORE launching the user interface.
        
        This warmup must complete BEFORE the UI is shown to avoid
        1-minute delays during user interaction.
        """
        return await self.lifecycle_service.warmup_all_systems()

    def _handle_popup_event(self, event):
        """
        Handle popup detection event - delegates to Lifecycle service ()
        
        Default behavior: log the event.
        Future: could pause execution, notify user, attempt to close popup, etc.
        """
        self.lifecycle_service.handle_popup_event(event)

    def _handle_error_event(self, event):
        """
        Handle error detection event - delegates to Lifecycle service ()
        
        Default behavior: log the event.
        Future: could pause execution, attempt recovery, notify user, etc.
        """
        self.lifecycle_service.handle_error_event(event)

