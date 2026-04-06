"""ActionCoordinator - OODA Loop Orchestration with Burst Mode.
Delegates to extracted modules (RecoveryManager, StopConditionEvaluator, etc.)"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional, List, TYPE_CHECKING

from janus.runtime.core.agent_registry import AgentRegistry, get_global_agent_registry
from janus.runtime.core.contracts import (
    ActionResult, ErrorType, ExecutionResult, Intent, BurstDecision, BurstMetrics,
    StopCondition, StopConditionType, SystemState, RecoveryState, SkillHint, SkillMetrics,
    CommandError,
)
from janus.ai.reasoning.prompt_loader import load_prompt
from janus.platform.os import get_system_bridge
from janus.platform.os.system_bridge import SystemBridgeStatus
from janus.runtime.core.module_action_schema import (
    validate_action_step, get_all_module_names, get_all_actions_for_module, get_prompt_schema_section,
)
from janus.utils.retry import RetryConfig, FallbackChain
from janus.constants import DEFAULT_MAX_RETRIES, INITIAL_RETRY_DELAY
from janus.runtime.core.recovery_manager import RecoveryManager
from janus.runtime.core.stop_conditions import StopConditionEvaluator
from janus.runtime.core.visual_observer import VisualObserver
from janus.runtime.core.stagnation_detector import StagnationDetector
from janus.runtime.core.system_state_observer import SystemStateObserver
from janus.runtime.core.skill_hint_checker import SkillHintChecker

if TYPE_CHECKING:
    from janus.runtime.core.settings import Settings

logger = logging.getLogger(__name__)

class ActionCoordinator:
    """OODA Loop orchestrator with Burst Mode. Delegates to extracted modules."""
    def __init__(
        self,
        agent_registry: Optional[AgentRegistry] = None,
        max_iterations: int = 20,
        clipboard_manager = None,
        tool_rag_top_k: int = 5,
        stagnation_threshold: int = 3, 
        settings: Optional['Settings'] = None,
        semantic_router = None,
    ):
        self.agent_registry = agent_registry or get_global_agent_registry()
        self.max_iterations = max_iterations
        self.clipboard_manager = clipboard_manager
        self.tool_rag_top_k = tool_rag_top_k
        self.stagnation_threshold = stagnation_threshold
        
        if settings is None:
            from janus.runtime.core import Settings
            settings = Settings()
        self.settings = settings
        
        self.semantic_router = semantic_router
        
        self._reasoner = None
        self._vision_engine = None
        self._tool_retriever = None
        self._context_router = None
        self._system_bridge = get_system_bridge()
        
        self._current_session_id: Optional[str] = None
        
        self._recovery_manager = RecoveryManager(max_recovery_attempts=3)
        self._stop_condition_evaluator = None
        self._visual_observer = None
        self._async_vision_monitor = None  # PERF-M4-001: Cached monitor instance
        self._stagnation_detector = StagnationDetector(stagnation_threshold=stagnation_threshold)
        self._system_state_observer = SystemStateObserver(
            system_bridge=self._system_bridge,
            clipboard_manager=clipboard_manager
        )
        self._skill_hint_checker = None
        
        from janus.runtime.core.contracts import SkillMetrics
        self.skill_metrics = SkillMetrics()
        
        # P2: Initialize rate limiter if enabled
        self._rate_limiter = None
        if settings.features.enable_rate_limiting and settings.rate_limit.enabled:
            from janus.safety.rate_limiter import RateLimiter
            self._rate_limiter = RateLimiter()
            # Configure global rate limit
            self._rate_limiter.configure(
                "global",
                max_requests=settings.rate_limit.global_max_requests,
                time_window_seconds=settings.rate_limit.global_time_window_seconds,
                burst_allowance=settings.rate_limit.global_burst_allowance
            )
            logger.info(f"Rate limiter enabled: {settings.rate_limit.global_max_requests} req/{settings.rate_limit.global_time_window_seconds}s")
    
    @property
    def reasoner(self):
        if self._reasoner is None:
            from janus.ai.reasoning.reasoner_llm import ReasonerLLM
            provider = self.settings.llm.provider
            
            backend_map = {"ollama": "ollama", "local": "llama-cpp", "mock": "mock"}
            backend = backend_map.get(provider, "mock")
            
            if backend == "ollama":
                self._reasoner = ReasonerLLM(backend=backend, model_name=self.settings.llm.model)
            elif backend == "llama-cpp":
                self._reasoner = ReasonerLLM(backend=backend, model_path=self.settings.llm.model_path)
            else:
                self._reasoner = ReasonerLLM(backend="mock")
            logger.debug(f"Reasoner loaded: {backend}")
        return self._reasoner
    
    @property
    def vision_engine(self):
        if self._vision_engine is None:
            try:
                from janus.vision.set_of_marks import SetOfMarksEngine
                self._vision_engine = SetOfMarksEngine(cache_ttl=2.0, enable_cache=True)
            except Exception as e:
                logger.warning(f"Vision engine load failed: {e}")
        return self._vision_engine
    
    @property
    def tool_retriever(self):
        if self._tool_retriever is None:
            try:
                from janus.services.tool_retrieval_service import ToolRetrievalService
                from janus.config.tools_registry import TOOLS_CATALOG, CATALOG_VERSION_HASH
                
                self._tool_retriever = ToolRetrievalService(
                    enable_session_cache=True,
                    enable_delta_updates=True
                )
                if self._tool_retriever.available:
                    self._tool_retriever.index_tools(TOOLS_CATALOG, catalog_version=CATALOG_VERSION_HASH)
            except Exception:
                pass
        return self._tool_retriever
    
    @property
    def context_router(self):
        """
        Lazy-load ContextRouter for vision gating.
        
        TICKET-5: Uses MockContextRouter for zero-latency keyword-based routing.
        Determines if vision context is needed based on user command.
        """
        if self._context_router is None:
            try:
                from janus.ai.reasoning.context_router import MockContextRouter
                self._context_router = MockContextRouter()
                logger.debug("ContextRouter loaded (MockContextRouter for zero-latency)")
            except Exception as e:
                logger.warning(f"ContextRouter load failed: {e}")
        return self._context_router
    
    @property
    def stop_condition_evaluator(self):
        """Lazy-load StopConditionEvaluator."""
        if self._stop_condition_evaluator is None:
            self._stop_condition_evaluator = StopConditionEvaluator(vision_engine=self.vision_engine)
        return self._stop_condition_evaluator
    
    @property
    def visual_observer(self):
        """Lazy-load VisualObserver."""
        if self._visual_observer is None:
            # PERF-M4-001: Get or create AsyncVisionMonitor (cached to avoid race conditions)
            if self._async_vision_monitor is None:
                try:
                    from janus.vision.async_vision_monitor import get_global_monitor
                    self._async_vision_monitor = get_global_monitor()
                    if not self._async_vision_monitor.is_running():
                        # Start it if not already running
                        self._async_vision_monitor.start()
                        logger.info("Started AsyncVisionMonitor for non-blocking vision")
                except Exception as e:
                    logger.debug(f"AsyncVisionMonitor not available: {e}")
            
            self._visual_observer = VisualObserver(
                vision_engine=self.vision_engine,
                system_bridge=self._system_bridge,
                async_vision_monitor=self._async_vision_monitor  # PERF-M4-001
            )
        return self._visual_observer
    
    @property
    def skill_hint_checker(self):
        """Lazy-load SkillHintChecker."""
        if self._skill_hint_checker is None:
            self._skill_hint_checker = SkillHintChecker(
                semantic_router=self.semantic_router,
                skill_metrics=self.skill_metrics
            )
        return self._skill_hint_checker
    
    async def execute_goal(
        self, user_goal: str, intent: Intent, session_id: str,
        request_id: str, language: str = "fr",
    ) -> ExecutionResult:
        """Execute user goal using OODA loop with Burst Mode."""
        from .execution_metrics import track_execution_engine
        
        logger.info(f"🚀 OODA Loop Start (Burst OODA Mode with Background Vision): '{user_goal}'")
        
        self._current_session_id = session_id
        
        self._recovery_manager.reset_recovery_state()
        
        result = ExecutionResult(intent=intent, success=True, session_id=session_id, request_id=request_id)
        memory: Dict[str, Any] = {}
        force_vision = False
        # Anti-loop guard: track repeated failures of the same action type
        repeated_failures: dict[str, int] = {}
        
        # PERF-M4-001: Start background vision updates if enabled
        background_vision_enabled = (
            self.settings.features.enable_vision and
            self.settings.features.vision_decision_enabled
        )
        
        if background_vision_enabled and self.visual_observer:
            self.visual_observer.start_background_vision(update_interval=0.1)
            logger.info("✓ Background vision started (10 FPS max)")
        
        try:
            iteration = 0
            while iteration < self.max_iterations:
                iteration += 1
                step_start = time.time()
                logger.info(f"\n🔄 Iteration {iteration}/{self.max_iterations}")
                
                observe_start = time.time()
                system_state = await self._system_state_observer.observe_system_state()
                observe_time = (time.time() - observe_start) * 1000
                result.burst_metrics.t_observe_ms += observe_time
                
                # Stagnation detection (ARCH-004: Uses SystemState.__hash__())
                is_stagnant = self._stagnation_detector.detect_stagnation(system_state, result.burst_metrics)
                if is_stagnant:
                    logger.warning("⚠️ Stagnation detected - attempting recovery")
                    recovery_success = await self._recovery_manager.try_recovery(
                        system_state,
                        self.reasoner,
                        "stagnation",
                        result.action_results,
                        user_goal
                    )
                    
                    if recovery_success:
                        force_vision = True
                        result.burst_metrics.recovery_attempts += 1
                        logger.info("✓ Recovery successful - forcing vision for next iteration")
                    else:
                        logger.error("❌ Recovery failed - continuing without vision")
                
                # PERF: Check accessibility first to skip vision when possible
                visual_context = ""
                needs_vision_by_context = False
                
                # Use ContextRouter to determine if vision is needed based on command
                # TICKET-ARCHI: Pass iteration number so vision is enabled by default on first iteration
                if self.context_router and self.context_router.available:
                    context_requirements = self.context_router.get_requirements(
                        user_goal, 
                        is_first_iteration=(iteration == 1)
                    )
                    needs_vision_by_context = "vision" in context_requirements
                    logger.debug(f"ContextRouter: vision_needed={needs_vision_by_context} for '{user_goal[:50]}...'")
                
                should_use_vision = (
                    self.settings.features.enable_vision and 
                    self.settings.features.vision_decision_enabled and
                    (force_vision or needs_vision_by_context)
                )
                
                if should_use_vision:
                    vision_start = time.time()
                    # PERF-M4-001: Use background vision if available, otherwise block
                    # Background vision returns immediately with latest cached state
                    visual_context, context_source = await self.visual_observer.observe_visual_context(
                        force_vision=force_vision,
                        use_background=background_vision_enabled  # Use background if enabled
                    )
                    vision_time = (time.time() - vision_start) * 1000
                    result.burst_metrics.t_vision_ms += vision_time
                    
                    # Track whether we used accessibility instead of vision
                    if "cached" in context_source:
                        # Background vision was used - almost instant
                        logger.debug(f"Used background vision (age: <100ms, latency: {vision_time:.0f}ms)")
                    elif context_source == "accessibility":
                        result.burst_metrics.accessibility_fallback_count += 1
                        logger.debug(f"Used accessibility instead of vision (saved ~{vision_time:.0f}ms)")
                    elif context_source == "vision":
                        result.burst_metrics.vision_calls += 1
                    # If source is "none", we got empty context - still count as vision attempt
                    else:
                        result.burst_metrics.vision_calls += 1
                
                decision = await self._decide_burst(
                    user_goal, 
                    system_state, 
                    visual_context, 
                    result.action_results, 
                    language,
                    force_vision
                )
                
                force_vision = False
                
                if "error" in decision:
                    error_type = decision.get("error_type", "unknown")
                    error_msg = decision.get("error", "Unknown error")
                    
                    logger.warning(f"❌ Decision error ({error_type}): {error_msg}")
                    
                    recovery_success = await self._recovery_manager.try_recovery(
                        system_state,
                        self.reasoner,
                        f"decision_error: {error_type}",
                        result.action_results,
                        user_goal
                    )
                    
                    if recovery_success:
                        result.burst_metrics.recovery_attempts += 1
                        logger.info("✓ Recovery attempted after decision error")
                        continue
                    
                    # Recovery failed or not attempted - log error and continue
                    error_result = ActionResult(
                        action_type=f"decision_error.{error_type}",
                        success=False,
                        message=f"Decision failed: {error_msg}",
                        recoverable=True
                    )
                    result.add_result(error_result)
                    continue
                
                burst_success = await self._execute_burst(decision, memory, result, system_state)
                
                if not burst_success:
                    logger.warning("❌ Burst execution failed")
                    break
                
                if decision.get("stop_when"):
                    post_burst_state = await self._system_state_observer.observe_system_state()
                    if self.stop_condition_evaluator.evaluate_stop_conditions(decision["stop_when"], post_burst_state):
                        logger.info("✓ Stop condition met after burst")
                        continue
                
                if decision.get("needs_vision"):
                    force_vision = True
                    logger.info("🔍 Vision requested for next iteration")
                
                if self._vision_engine:
                    self._vision_engine.invalidate_cache()
        
                # Anti-loop: if we repeatedly fail the same action, stop early.
                # TICKET-ARCHI: Detect failures due to missing vision context and force vision
                for ar in result.action_results:
                    if not getattr(ar, "success", True):
                        key = getattr(ar, "action_type", "unknown")
                        error_msg = getattr(ar, "error", "")
                        repeated_failures[key] = repeated_failures.get(key, 0) + 1
                        
                        # TICKET-ARCHI: If UI click fails due to missing parameters and we don't have vision,
                        # force vision for next iteration instead of failing immediately
                        if (key == "ui.click" and 
                            ("required" in str(error_msg).lower() or "selector" in str(error_msg).lower()) and
                            (not visual_context or visual_context in ("[]", "none")) and 
                            repeated_failures[key] == 1):  # Only on first failure
                            force_vision = True
                            logger.info("🔍 UI click failed due to missing context - forcing vision for next iteration")
                        
                        # If browser.* keeps failing, don't spin another 20 iterations.
                        if key.startswith("browser.") and repeated_failures[key] >= 2:
                            result.success = False
                            result.error = CommandError(
                                error_type=ErrorType.EXECUTION_ERROR,
                                message=(
                                    f"Action répétée en échec: {key}. "
                                    "Je stoppe pour éviter une boucle. "
                                    "Je peux soit ouvrir une URL directe (browser.open_url), "
                                    "soit tu me dis quel navigateur / étape exacte."
                                ),
                            )
                            return result
                        
                        # TICKET-ARCHI: Generic failure detection - stop after 3 identical consecutive failures
                        if repeated_failures[key] >= 3:
                            logger.error(f"❌ Action {key} failed {repeated_failures[key]} times - stopping to prevent infinite loop")
                            result.success = False
                            result.error = CommandError(
                                error_type=ErrorType.EXECUTION_ERROR,
                                message=(
                                    f"Action {key} a échoué {repeated_failures[key]} fois consécutives. "
                                    "Arrêt pour éviter une boucle infinie."
                                ),
                            )
                            return result
        finally:
            # PERF-M4-001: Stop background vision when OODA loop completes
            if background_vision_enabled and self.visual_observer:
                self.visual_observer.stop_background_vision()
                logger.debug("Background vision stopped")
            
            track_execution_engine(
                entry_point="ActionCoordinator.execute_goal",
                success=result.success
            )
        
        logger.info(f"📊 Burst Metrics: {result.burst_metrics.to_dict()}")
        return result
    
    async def _decide_burst(
        self, user_goal: str, system_state: SystemState, visual_context: str,
        action_history: List[ActionResult], language: str, force_vision: bool = False
    ) -> Dict[str, Any]:
        """Generate burst decision (2-6 actions)."""
        if not self.reasoner.available:
            return {"error": "LLM unavailable", "error_type": "llm_unavailable"}
        
        llm_start = time.time()
        
        # PERF-M4-001: Log context pruning - strict limit to last 3 actions
        logger.info(
            f"📝 Context pruning: {len(action_history)} total actions → "
            f"last 3 will be sent to LLM (strict limit enforced by ContextAssembler)"
        )
        
        skill_hint = self.skill_hint_checker.check_skill_hint(user_goal, system_state)
        
        decision = self.reasoner.decide_burst_actions(
            user_goal=user_goal,
            system_state=system_state.to_dict(),
            visual_context=visual_context,
            action_history=action_history,
            language=language,
            force_vision=force_vision,
            skill_hint=skill_hint
        )
        
        llm_time = (time.time() - llm_start) * 1000
        
        # Track metrics (will be added to result.burst_metrics)
        # Note: We can't access result.burst_metrics here, so we log it
        logger.debug(f"🧠 Burst decision took {llm_time:.2f}ms")
        return decision
    
    async def _execute_burst(
        self, decision: Dict[str, Any], memory: Dict[str, Any],
        result: ExecutionResult, system_state: SystemState
    ) -> bool:
        """Execute burst of actions sequentially."""
        actions = decision.get("actions", [])
        
        if not actions:
            logger.warning("Empty burst - no actions to execute")
            return True
        
        logger.info(f"🚀 Executing burst of {len(actions)} actions")
        result.burst_metrics.record_burst(len(actions))
        
        for i, action in enumerate(actions):
            act_start = time.time()
            
            logger.info(f"  [{i+1}/{len(actions)}] {action.get('module')}.{action.get('action')}")
            
            action_result = await self._act_single(
                action,
                memory,
                act_start,
                system_state,
                result.burst_metrics
            )
            
            act_time = (time.time() - act_start) * 1000
            result.burst_metrics.t_act_ms += act_time
            
            result.add_result(action_result)
            
            if action.get("action") == "done":
                logger.info("✓ Burst completed with 'done' action")
                return True
            
            if not action_result.success and not action_result.recoverable:
                logger.error(f"❌ Fatal error in burst action {i+1}: {action_result.error}")
                return False
            
            # Small pause between actions (50ms) to let UI update
            await asyncio.sleep(0.05)
        
        logger.info(f"✓ Burst of {len(actions)} actions completed")
        return True
    
    async def _act_single(
        self,
        action_plan: Dict[str, Any],
        memory: Dict[str, Any],
        start_time: float,
        system_state: SystemState,
        burst_metrics: Optional[BurstMetrics] = None
    ) -> ActionResult:
        """Execute single action with retry logic and rate limiting."""
        module = action_plan.get("module", "unknown")
        action = action_plan.get("action", "unknown")
        action_type = f"{module}.{action}"
        
        # P2: Check rate limits before executing
        if self._rate_limiter:
            # Check global rate limit
            if not self._rate_limiter.check_and_consume("global"):
                logger.warning(f"⚠️ Global rate limit exceeded for {action_type}")
                return ActionResult(
                    action_type=action_type,
                    success=False,
                    error="Global rate limit exceeded",
                    duration_ms=int((time.time() - start_time) * 1000),
                    retry_count=0,
                    recoverable=True  # Can retry later
                )
            
            # Check module-specific rate limit if configured
            module_scope = f"agent:{module}"
            if self._rate_limiter.get_remaining(module_scope) is not None:
                if not self._rate_limiter.check_and_consume(module_scope):
                    logger.warning(f"⚠️ Agent rate limit exceeded for {module}")
                    return ActionResult(
                        action_type=action_type,
                        success=False,
                        error=f"Rate limit exceeded for {module} agent",
                        duration_ms=int((time.time() - start_time) * 1000),
                        retry_count=0,
                        recoverable=True
                    )
        
        # Get retry policy from ActionRetryPolicy if available
        retry_config = RetryConfig(
            max_attempts=DEFAULT_MAX_RETRIES,
            initial_delay=INITIAL_RETRY_DELAY,
            # Only retry on network/transient errors, not programming errors
            retry_on_exceptions=[TimeoutError, ConnectionError, OSError]
        )
        
        retry_count = 0
        last_exception = None
        
        for attempt in range(retry_config.max_attempts):
            try:
                # Injection contextuelle (ARCH-004: Convert SystemState to dict for backward compatibility)
                ctx = {
                    "vision_engine": self._vision_engine,
                    "memory": memory,
                    "app": system_state.active_app,
                    "system_state": system_state.to_dict()
                }
                
                args = action_plan.get("args", {})
                
                # P2: Support dry_run mode if enabled
                dry_run = action_plan.get("dry_run", False)
                
                res = await self.agent_registry.execute_async(
                    module=module,
                    action=action,
                    args=args,
                    context=ctx,
                    dry_run=dry_run  # P2: Pass dry_run to agents
                )
                
                result = ActionResult(
                    action_type=action_type,
                    success=res.get("status") == "success",
                    message=res.get("message"),
                    data=res.get("data"),
                    duration_ms=int((time.time() - start_time) * 1000),
                    retry_count=retry_count,
                    dry_run=res.get("dry_run", False),  # P2: Track dry-run status
                    reversible=res.get("reversible", False),  # P2: Track reversibility
                    compensation_data=res.get("compensation_data")  # P2: Store compensation data
                )
                
                if burst_metrics and retry_count > 0:
                    burst_metrics.total_retries += retry_count
                    burst_metrics.successful_retries += 1
                    logger.info(f"✓ Action succeeded after {retry_count} retries: {action_type}")
                return result
            except Exception as e:
                last_exception = e
                retry_count += 1
                
                if not retry_config.should_retry(e):
                    logger.error(f"❌ Non-retryable error in {action_type}: {e}")
                    break
                
                if attempt < retry_config.max_attempts - 1:
                    delay = retry_config.calculate_delay(attempt)
                    logger.warning(
                        f"⚠️ Action {action_type} failed (attempt {attempt + 1}/{retry_config.max_attempts}): {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ Action {action_type} failed after {retry_config.max_attempts} attempts: {e}")
        
        if burst_metrics and retry_count > 0:
            burst_metrics.total_retries += retry_count
            burst_metrics.failed_retries += 1
        return ActionResult(
            action_type=action_type,
            success=False,
            error=str(last_exception) if last_exception else "Unknown error",
            duration_ms=int((time.time() - start_time) * 1000),
            retry_count=retry_count,
            recoverable=True
        )
