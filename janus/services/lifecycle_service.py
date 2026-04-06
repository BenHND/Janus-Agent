"""
LifecycleService: Lifecycle Management Service for Pipeline

Handles all lifecycle-related operations for the Janus pipeline including:
- Resource cleanup and initialization
- Vision monitor start/stop
- Model preloading (vision and LLM)
- System warmup
- Event handling for popups and errors

This service extracts lifecycle functionality from JanusPipeline to improve
modularity and testability (TICKET-PIPELINE-004).
"""

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from janus.runtime.core.memory_engine import MemoryEngine
    from janus.runtime.core.settings import Settings
    from janus.ai.reasoning.reasoner_llm import LLMBackend

logger = logging.getLogger(__name__)


class LifecycleService:
    """
    Service for lifecycle management operations.
    
    Provides initialization, cleanup, warmup, and monitoring capabilities
    for the Janus pipeline.
    """
    
    def __init__(
        self,
        settings: "Settings",
        memory: "MemoryEngine",
        session_id: str,
        pipeline=None,
    ):
        """
        Initialize Lifecycle Service.
        
        Args:
            settings: Unified settings object
            memory: Memory engine for structured logging
            session_id: Current session ID
            pipeline: Optional pipeline reference for accessing components dynamically
        """
        self.settings = settings
        self.memory = memory
        self.session_id = session_id
        self._pipeline = pipeline
        self._battery_monitor = None  # TICKET-PERF-002: Battery monitor for eco mode
        self._task_scheduler = None  # TICKET-FEAT-002: Task scheduler for delayed actions
    
    # Properties to access pipeline components dynamically (lazy loading support)
    
    @property
    def _stt_service(self):
        """Get STT service from pipeline if available"""
        return getattr(self._pipeline, 'stt_service', None) if self._pipeline else None
    
    @property
    def _vision_service(self):
        """Get vision service from pipeline if available"""
        return getattr(self._pipeline, 'vision_service', None) if self._pipeline else None
    
    @property
    def _tts_service(self):
        """Get TTS service from pipeline if available"""
        return getattr(self._pipeline, 'tts_service', None) if self._pipeline else None
    
    @property
    def _async_vision_monitor(self):
        """Get async vision monitor from pipeline if available"""
        return getattr(self._pipeline, 'async_vision_monitor', None) if self._pipeline else None
    
    @property
    def _executor(self):
        """Get executor from pipeline if available"""
        return getattr(self._pipeline, 'executor', None) if self._pipeline else None
    
    @property
    def _reasoner_llm(self):
        """Get reasoner LLM from pipeline if available"""
        return getattr(self._pipeline, 'reasoner_llm', None) if self._pipeline else None
    
    @property
    def _context_router(self):
        """Get context router from pipeline if available"""
        return getattr(self._pipeline, 'context_router', None) if self._pipeline else None
    
    @property
    def _enable_vision(self):
        """Get vision enable flag from pipeline if available"""
        return getattr(self._pipeline, 'enable_vision', False) if self._pipeline else False
    
    @property
    def _enable_llm_reasoning(self):
        """Get LLM reasoning enable flag from pipeline if available"""
        return getattr(self._pipeline, 'enable_llm_reasoning', False) if self._pipeline else False
    
    def cleanup(self):
        """
        Cleanup pipeline resources.

        This method can be called to clean up any resources held by the pipeline.
        """
        logger.debug("Cleaning up pipeline resources")
        
        # Stop task scheduler if running (TICKET-FEAT-002)
        self.stop_task_scheduler()
        
        # Stop battery monitor if running (TICKET-PERF-002)
        self.stop_battery_monitor()
        
        # Stop async vision monitor if running
        self.stop_vision_monitor()
        
        # Cleanup service modules
        if self._stt_service:
            self._stt_service.cleanup()
        if self._vision_service:
            self._vision_service.cleanup()
        if self._tts_service:
            self._tts_service.cleanup()

    def start_vision_monitor(self):
        """
        Start async vision monitor if enabled in settings.
        
        This starts background screen monitoring for popups, errors, and expected elements.
        The monitor runs in a daemon thread and will automatically stop when the program exits.
        """
        # Check if monitor is enabled in settings
        if not self.settings.async_vision_monitor.enable_monitor:
            logger.debug("Async vision monitor disabled in settings")
            return
        
        # Check if vision is enabled globally
        if not self._enable_vision:
            logger.warning("Cannot start async vision monitor: vision features are disabled")
            return
        
        # Get or create monitor instance
        monitor = self._async_vision_monitor
        if monitor is None:
            logger.warning("Failed to create async vision monitor")
            return
        
        # Import MonitorEventType for event registration
        from janus.vision.async_vision_monitor import MonitorEventType
        
        # Register default event handlers
        monitor.add_callback(
            MonitorEventType.POPUP_DETECTED,
            self.handle_popup_event
        )
        monitor.add_callback(
            MonitorEventType.ERROR_DETECTED,
            self.handle_error_event
        )
        
        # Start monitoring
        monitor.start()
        logger.info(
            f"Async vision monitor started (interval={monitor.check_interval_ms}ms, "
            f"popup_detection={monitor.enable_popup_detection}, "
            f"error_detection={monitor.enable_error_detection})"
        )

    def stop_vision_monitor(self):
        """Stop async vision monitor if running."""
        if self._async_vision_monitor and self._async_vision_monitor.is_running():
            logger.info("Stopping async vision monitor...")
            self._async_vision_monitor.stop()
            logger.info("Async vision monitor stopped")

    async def preload_vision_models(self):
        """
        Asynchronously preload vision models in the background at startup.
        
        This prevents the first vision-dependent command from blocking while
        models are loaded. Models are loaded in a background task so the
        application can continue initialization and be ready for user commands.
        
        This method should be called during application startup after pipeline
        initialization but before accepting user commands.
        
        Returns:
            bool: True if preloading was initiated successfully, False otherwise
        """
        if not self._enable_vision:
            logger.debug("Vision features disabled, skipping model preload")
            return False
        
        # Check if vision settings are enabled
        vision_settings = getattr(self.settings, 'vision', None)
        if vision_settings:
            enable_blip = getattr(vision_settings, 'enable_blip', True)
            enable_clip = getattr(vision_settings, 'enable_clip', True)
            if not enable_blip and not enable_clip:
                logger.debug("Vision AI models disabled in settings, skipping preload")
                return False
        
        logger.info("Starting background preload of vision models...")
        
        try:
            # Get the executor which has the LightVisionEngine
            executor = self._executor
            if executor and hasattr(executor, '_light_vision') and executor._light_vision:
                # Preload models in the LightVisionEngine
                success = await executor._light_vision.preload_models_async()
                if success:
                    logger.info("✓ Vision models preloaded and ready for use")
                    return True
                else:
                    logger.info("Vision models preload initiated but models may not be available")
                    return False
            else:
                logger.debug("LightVisionEngine not initialized, models will load on-demand")
                return False
                
        except Exception as e:
            logger.warning(f"Failed to initiate vision model preload: {e}")
            logger.info("Models will load on-demand when first needed")
            return False

    async def preload_llm_model(self):
        """
        Asynchronously preload the LLM model into memory at startup.
        
        This prevents the first LLM-dependent command from experiencing
        cold start delays while the model loads into memory (especially
        for Ollama which can take 60+ seconds on first request).
        
        This method should be called during application startup after pipeline
        initialization but before accepting user commands.
        
        Returns:
            bool: True if preloading was successful, False otherwise
        """
        if not self._enable_llm_reasoning:
            logger.debug("LLM reasoning disabled, skipping model preload")
            return False
        
        logger.info("Starting background preload of LLM model...")
        
        try:
            # Get the reasoner which manages the LLM
            reasoner = self._reasoner_llm
            
            if reasoner is None:
                logger.warning("ReasonerLLM not initialized, cannot preload model")
                return False
            
            # Import LLMBackend for checking backend type
            from janus.ai.reasoning.reasoner_llm import LLMBackend
            
            # Log backend info for debugging
            logger.info(f"ReasonerLLM backend: {reasoner.backend.value}, available: {reasoner.available}")
            
            # Only do actual warmup for Ollama backend - mock doesn't need it
            if reasoner.backend == LLMBackend.MOCK:
                logger.info("Using mock backend - no real LLM model to preload")
                return True  # Mock is always "ready"
            
            if not reasoner.available:
                logger.warning(f"LLM backend '{reasoner.backend.value}' not available for warmup")
                return False
            
            if hasattr(reasoner, 'warmup_model_async'):
                logger.info(f"Warming up LLM model '{reasoner.model_name}'...")
                success = await reasoner.warmup_model_async()
                if success:
                    logger.info(f"✓ LLM model '{reasoner.model_name}' preloaded and ready for use")
                    return True
                else:
                    logger.warning(f"LLM model warmup failed for '{reasoner.model_name}'")
                    return False
            else:
                logger.warning("Reasoner doesn't support warmup_model_async method")
                return False
                
        except Exception as e:
            logger.warning(f"Failed to initiate LLM model preload: {e}")
            logger.info("Model will load on-demand when first needed")
            return False

    async def warmup_all_systems(self):
        """
        FORCE MODEL LOADING INTO VRAM AT STARTUP.
        
        This method is critical to avoid timeout on the first command.
        It forces the LLM model to load into memory by sending a dummy inference request.
        
        Must be called BEFORE launching the user interface.
        
        TICKET-315: This warmup must complete BEFORE the UI is shown to avoid
        1-minute delays during user interaction.
        """
        warmup_start = time.time()
        logger.info("🔥 WARMUP: Starting LLM model warmup (this is normal at startup)...")
        
        if not self._enable_llm_reasoning:
            logger.info("LLM reasoning disabled, skipping warmup")
            return
        
        # 1. Initialize the Reasoner (exit lazy loading)
        llm = self._reasoner_llm
        
        if llm is None:
            logger.error("❌ Reasoner not initialized for warmup")
            return
        
        if not llm.available:
            logger.error(f"❌ Reasoner not available for warmup (backend: {llm.backend.value})")
            return
        
        # Import LLMBackend for checking backend type
        from janus.ai.reasoning.reasoner_llm import LLMBackend
        
        # Skip warmup for mock backend
        if llm.backend == LLMBackend.MOCK:
            logger.info("Using mock backend - no warmup needed")
            return
        
        # 2. Initialize ContextRouter early (exit lazy loading)
        # This is critical because ContextRouter also uses the LLM and lazy-loads at first command
        logger.info("Initializing ContextRouter...")
        context_router = self._context_router
        if context_router:
            logger.info("✓ ContextRouter initialized")
        else:
            logger.warning("ContextRouter not available")
        
        # 3. Send a 'dummy' request to force the model into memory/VRAM
        # Prefer the public warmup API when available; avoid calling private methods.
        try:
            logger.info(f"Pinging Ollama to load {llm.model_name} into memory...")

            if hasattr(llm, "warmup_model_async"):
                ok = await llm.warmup_model_async()
                warmup_duration = time.time() - warmup_start
                if ok:
                    logger.info(
                        f"✅ WARMUP COMPLETE: LLM model is hot and ready! (took {warmup_duration:.1f}s)"
                    )
                else:
                    logger.warning(
                        f"⚠️ LLM warmup reported failure after {warmup_duration:.1f}s (continuing anyway)"
                    )
                return

            # Fallback: use a minimal plan generation in an executor.
            # This stays within the public surface of ReasonerLLM.
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: llm.generate_structured_plan(
                    command="warmup",
                    language="en",
                    system_context={},
                    max_steps=1,
                    json_mode=False,
                ),
            )

            warmup_duration = time.time() - warmup_start
            logger.info(f"✅ WARMUP COMPLETE: LLM model is hot and ready! (took {warmup_duration:.1f}s)")
        except Exception as e:
            warmup_duration = time.time() - warmup_start
            logger.warning(f"⚠️ Non-blocking error during warmup after {warmup_duration:.1f}s: {e}")

        # 4. Warm up embeddings and vision models (heavy-but-one-time cost)
        # This is intentionally synchronous-ish at startup to make later runs "fuse".
        try:
            # Force MemoryEngine semantic embeddings to load (SentenceTransformer + Chroma)
            if getattr(self.memory, "_embedding_model", None) is None:
                if hasattr(self.memory, "_init_semantic_memory"):
                    logger.info("🔥 WARMUP: Loading semantic memory embeddings...")
                    self.memory._init_semantic_memory()
        except Exception as e:
            logger.warning(f"⚠️ Warmup: semantic memory init failed: {e}")

        try:
            # Force SemanticRouter embedding classifier to load (centroids)
            sr = getattr(self, "_semantic_router", None)
            if sr is None and getattr(self, "_pipeline", None) is not None:
                sr = getattr(self._pipeline, "semantic_router", None)
            if sr is not None and hasattr(sr, "_init_embedding_classifier"):
                logger.info("🔥 WARMUP: Loading SemanticRouter embeddings...")
                sr._init_embedding_classifier()
        except Exception as e:
            logger.warning(f"⚠️ Warmup: semantic router embeddings failed: {e}")

        try:
            # Force tool retrieval embeddings if present on pipeline
            trs = getattr(self._pipeline, "tool_retrieval_service", None) if self._pipeline else None
            if trs is not None and hasattr(trs, "_init_embedding_model"):
                logger.info("🔥 WARMUP: Loading tool retrieval embeddings...")
                trs._init_embedding_model()
        except Exception as e:
            logger.warning(f"⚠️ Warmup: tool retrieval embeddings failed: {e}")

        try:
            # Force vision models to preload (OCR / vision engine)
            vision_service = getattr(self, "_vision_service", None)
            if vision_service is not None and hasattr(vision_service, "warmup"):
                logger.info("🔥 WARMUP: Preloading vision models...")
                await vision_service.warmup()
        except Exception as e:
            logger.warning(f"⚠️ Warmup: vision preload failed: {e}")

    def handle_popup_event(self, event):
        """
        Handle popup detection event.
        
        Default behavior: log the event.
        Future: could pause execution, notify user, attempt to close popup, etc.
        
        Args:
            event: Popup detection event from async vision monitor
        """
        logger.warning(
            f"Popup detected: {event.details.get('keywords_found', [])} "
            f"(priority={event.priority})"
        )
        self.memory.log_structured(
            level="WARNING",
            logger="AsyncVisionMonitor",
            message=f"Popup detected: {event.details}",
            session_id=self.session_id,
            module=__name__,
            function="handle_popup_event",
            extra_data=event.to_dict(),
        )

    def handle_error_event(self, event):
        """
        Handle error detection event.
        
        Default behavior: log the event.
        Future: could pause execution, attempt recovery, notify user, etc.
        
        Args:
            event: Error detection event from async vision monitor
        """
        logger.error(
            f"Error detected: {event.details.get('error_type', 'unknown')} - "
            f"{event.details.get('message', 'N/A')} (priority={event.priority})"
        )
        self.memory.log_structured(
            level="ERROR",
            logger="AsyncVisionMonitor",
            message=f"Error detected: {event.details}",
            session_id=self.session_id,
            module=__name__,
            function="handle_error_event",
            extra_data=event.to_dict(),
        )
    
    def start_battery_monitor(self):
        """
        Start battery monitor for eco mode.
        TICKET-PERF-002: Mode Économie d'Énergie (Laptop Mode)
        
        Monitors power state and enables power-saving features when on battery.
        """
        try:
            from ..utils.battery_monitor import BatteryMonitor
            
            if self._battery_monitor is None:
                self._battery_monitor = BatteryMonitor(check_interval_seconds=10)
                
                # Register callbacks for power state changes
                self._battery_monitor.add_on_battery_callback(self._on_battery_power)
                self._battery_monitor.add_on_ac_callback(self._on_ac_power)
                
                logger.info("Battery monitor initialized")
            
            # Start monitoring
            self._battery_monitor.start()
            
            # Apply initial state based on current power status
            if self._battery_monitor.is_on_battery():
                logger.info("System is on battery - enabling eco mode")
                self._on_battery_power()
            else:
                logger.info("System is on AC power - eco mode disabled")
            
        except Exception as e:
            logger.warning(f"Failed to start battery monitor: {e}")
    
    def stop_battery_monitor(self):
        """Stop battery monitor if running."""
        if self._battery_monitor and self._battery_monitor.is_running():
            logger.info("Stopping battery monitor...")
            self._battery_monitor.stop()
            self._battery_monitor = None
            logger.info("Battery monitor stopped")
    
    def _on_battery_power(self):
        """
        Callback when system switches to battery power.
        TICKET-PERF-002: Enables eco mode features
        """
        logger.info("⚡ Switching to battery power - enabling eco mode")
        
        # Enable eco mode in vision service
        if self._vision_service:
            self._vision_service.enable_eco_mode()
        
        # Log the change
        self.memory.log_structured(
            level="INFO",
            logger="LifecycleService",
            message="Eco mode enabled - system on battery power",
            session_id=self.session_id,
            module=__name__,
            function="_on_battery_power",
        )
    
    def _on_ac_power(self):
        """
        Callback when system switches to AC power.
        TICKET-PERF-002: Disables eco mode features
        """
        logger.info("🔌 Switching to AC power - disabling eco mode")
        
        # Disable eco mode in vision service
        if self._vision_service:
            self._vision_service.disable_eco_mode()
        
        # Log the change
        self.memory.log_structured(
            level="INFO",
            logger="LifecycleService",
            message="Eco mode disabled - system on AC power",
            session_id=self.session_id,
            module=__name__,
            function="_on_ac_power",
        )
    
    def start_task_scheduler(self):
        """
        Start task scheduler for delayed and recurring actions.
        TICKET-FEAT-002: Scheduler & Actions Différées (Cron)
        
        Initializes and starts the task scheduler that manages
        delayed and recurring task execution.
        """
        try:
            from janus.runtime.core.scheduler import TaskScheduler
            
            if self._task_scheduler is None:
                # Get database connection from memory engine
                db_connection = None
                if hasattr(self.memory, 'db') and self.memory.db:
                    db_connection = self.memory.db.db  # Access the SQLite connection
                
                # Initialize scheduler with database and services
                self._task_scheduler = TaskScheduler(
                    db_connection=db_connection,
                    tts_service=self._tts_service,
                    pipeline=self._pipeline,
                )
                
                logger.info("Task scheduler initialized")
            
            # Start scheduler
            self._task_scheduler.start()
            logger.info("Task scheduler started")
            
        except Exception as e:
            logger.warning(f"Failed to start task scheduler: {e}")
    
    def stop_task_scheduler(self):
        """Stop task scheduler if running."""
        if self._task_scheduler:
            logger.info("Stopping task scheduler...")
            self._task_scheduler.stop()
            self._task_scheduler = None
            logger.info("Task scheduler stopped")
    
    def get_task_scheduler(self):
        """Get task scheduler instance (for use by other components)"""
        return self._task_scheduler
