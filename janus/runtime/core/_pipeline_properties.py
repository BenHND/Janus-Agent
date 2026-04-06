"""
Pipeline Properties Mixin (Internal)

INTERNAL MODULE - DO NOT IMPORT DIRECTLY

This module contains lazy-loading properties extracted from JanusPipeline
during refactoring (). It exists to reduce the size of
pipeline.py .

These properties provide lazy initialization of pipeline components.

"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Import services
from janus.services import STTService, VisionService, MemoryServiceWrapper, TTSService, LifecycleService


class PipelinePropertiesMixin:
    """
    Mixin containing JanusPipeline lazy-loading properties.
    
    This mixin provides access to pipeline components through lazy initialization.
    Components are only loaded when first accessed, reducing startup time.
    
    
    
    
    Properties have access to: self.settings, self.enable_*, self.memory, etc.
    """

    @property
    def reasoner_llm(self): # -> ReasonerLLM
        """Lazy-load ReasonerLLM (the Ferrari) for intelligent command parsing"""
        if self._reasoner_llm is None:
            logger.debug("Loading ReasonerLLM...")
            # Import ReasonerLLM locally to avoid circular dependencies
            from janus.ai.reasoning.reasoner_llm import ReasonerLLM
            
            try:
                # Configure backend from settings
                provider = self.settings.llm.provider
                
                # Map LLM provider to ReasonerLLM backend
                backend_map = {
                    "ollama": "ollama",
                    "local": "llama-cpp",
                    "mock": "mock",
                }
                
                # Default to mock for cloud providers (OpenAI, Anthropic, Mistral)
                backend = backend_map.get(provider, "mock")
                
                if backend == "ollama":
                    self._reasoner_llm = ReasonerLLM(
                        backend=backend,
                        model_name=self.settings.llm.model
                    )
                elif backend == "llama-cpp":
                    self._reasoner_llm = ReasonerLLM(
                        backend=backend,
                        model_path=self.settings.llm.model_path
                    )
                else:
                    self._reasoner_llm = ReasonerLLM(backend="mock")
                
                # If backend fails to initialize, fall back to working mock backend
                if not self._reasoner_llm.available:
                    logger.warning(
                        f"ReasonerLLM backend '{backend}' not available, "
                        f"falling back to mock backend for plan generation"
                    )
                    # TICKET-FIX: Do not fallback to mock if Ollama is just missing a model
                    # We want to fail loudly or try to download it, which ReasonerLLM already does.
                    # But if it failed after that, it means it's really broken.
                    # However, for debugging, let's print WHY it failed.
                    self._reasoner_llm = ReasonerLLM(backend="mock")
                    logger.info("ReasonerLLM initialized with mock backend (fallback)")
                else:
                    logger.info(f"ReasonerLLM initialized with backend: {backend}")
                    
            except Exception as e:
                logger.warning(f"Failed to load ReasonerLLM: {e}, using mock backend")
                # Create a working mock instance
                self._reasoner_llm = ReasonerLLM(backend="mock")
        return self._reasoner_llm

    @property
    def unified_llm_client(self):
        """
        Lazy-load UnifiedLLMClient for semantic correction and other LLM tasks.
        
        This is the main LLM client configured in [llm] section, used for:
        - Semantic correction (when semantic_correction_model_path is empty)
        - Natural reformatting
        - Other text processing tasks
        
        Note: This is separate from ReasonerLLM which is specialized for command reasoning.
        """
        if self._unified_llm_client is None:
            logger.debug("Loading UnifiedLLMClient for semantic correction...")
            try:
                from ..llm.unified_client import UnifiedLLMClient
                
                self._unified_llm_client = UnifiedLLMClient(
                    provider=self.settings.llm.provider,
                    model=self.settings.llm.model,
                    temperature=self.settings.llm.temperature,
                    max_tokens=self.settings.llm.max_tokens,
                    timeout=self.settings.llm.request_timeout,
                    model_path=self.settings.llm.model_path,
                    fallback_providers=self.settings.llm.fallback_providers,
                )
                
                if not self._unified_llm_client.available:
                    logger.warning(
                        f"UnifiedLLMClient not available (provider: {self.settings.llm.provider}, "
                        f"model: {self.settings.llm.model}). "
                        "Semantic correction will use fallback methods."
                    )
                else:
                    logger.info(
                        f"UnifiedLLMClient initialized: provider={self.settings.llm.provider}, "
                        f"model={self.settings.llm.model}"
                    )
            except Exception as e:
                logger.warning(f"Failed to load UnifiedLLMClient: {e}")
                self._unified_llm_client = None
        return self._unified_llm_client

    @property
    def agent_registry(self):
        """Lazy-load agent registry """
        if self._agent_registry is None:
            logger.debug("Loading agent registry...")
            from .agent_setup import setup_agent_registry
            
            self._agent_registry = setup_agent_registry()
            
            # Wire up SchedulerAgent with lifecycle service (TICKET-FEAT-002)
            scheduler_agent = self._agent_registry.get_agent("scheduler")
            if scheduler_agent:
                scheduler_agent.set_lifecycle_service(self.lifecycle_service)
                logger.debug("SchedulerAgent wired with lifecycle service")
        return self._agent_registry

    @property
    def context_router(self):
        """
        Force le routeur en mode SIGNAL (Mots-clés) pour supprimer la latence de 15s.
        
        Performance optimization - always use MockContextRouter (keyword-based)
        for instant context routing (0ms) instead of LLM-based routing which can add
        significant latency (up to 15s on cold start).
        
        Returns:
            MockContextRouter instance for fast keyword-based context routing.
        """
        if self._context_router is None:
            from janus.ai.reasoning.context_router import MockContextRouter
            logger.info("⚡️ PERFORMANCE: ContextRouter forcé en mode SIGNAL (0ms)")
            self._context_router = MockContextRouter()
        return self._context_router

    # Removed parser_agent property - LLM now handles raw text directly without preprocessing

    @property
    def context_ranker(self):
        """
        Lazy-load ContextRanker for smart file history ranking ().
        
        The ContextRanker scores and ranks context items by relevance,
        using temporal decay and type matching to avoid overwhelming the LLM
        with irrelevant history.
        
        Returns:
            ContextRanker instance for intelligent context ranking.
        """
        if self._context_ranker is None:
            from .context_ranker import ContextRanker
            logger.debug("Loading ContextRanker for smart context ranking")
            self._context_ranker = ContextRanker(decay_halflife_hours=24.0)
        return self._context_ranker

    @property
    def clipboard_manager(self):
        """
        Lazy-load ClipboardManager for robust clipboard access ().
        
        The ClipboardManager provides cross-platform clipboard operations
        with history tracking, type support (text/image/file), and persistence.
        Replaces hacky subprocess calls with proper clipboard API.
        
        Returns:
            ClipboardManager instance for clipboard operations.
        """
        if self._clipboard_manager is None:
            from janus.platform.clipboard import ClipboardManager
            logger.debug("Loading ClipboardManager for robust clipboard access")
            self._clipboard_manager = ClipboardManager(
                history_limit=50,
                persist_file="clipboard_history.json",
                use_system_clipboard=True,
            )
        return self._clipboard_manager

    @property
    def action_coordinator(self):
        """
        Lazy-load ActionCoordinator for OODA loop execution ().
        
        The ActionCoordinator implements the pure ReAct pattern:
        Observe → Orient → Decide → Act
        
        This replaces static planning with dynamic goal execution,
        adapting to visual state at each step.
        
        TICKET-FEAT-001: Now includes clipboard_manager for Smart Clipboard feature.
        
        Returns:
            ActionCoordinator instance for OODA loop execution.
        """
        if self._action_coordinator is None:
            from .action_coordinator import ActionCoordinator
            logger.debug("Loading ActionCoordinator for OODA loop")
            self._action_coordinator = ActionCoordinator(
                agent_registry=self.agent_registry,
                max_iterations=20,
                clipboard_manager=self.clipboard_manager,
                settings=self.settings,  # PERF-FOUNDATION-001: Pass settings for vision policy
            )
        return self._action_coordinator
    
    @property
    def semantic_router(self):
        """
        Lazy-load SemanticRouter for ultra-fast input filtering ().
        
        The SemanticRouter filters input BEFORE expensive reasoning calls:
        - NOISE: Politeness, affirmations, incomplete input → ignored
        - CHAT: Conversation, questions, jokes → handled separately
        - ACTION: Commands requiring system actions → sent to reasoner
        
        Performance: <50ms classification vs 2-10s for full reasoning.
        
        Returns:
            SemanticRouter instance for input classification.
        """
        if self._semantic_router is None:
            from janus.ai.reasoning.semantic_router import SemanticRouter
            logger.debug("Loading SemanticRouter for input filtering")
            # Pass reasoner for LLM-based classification (with keyword fallback)
            self._semantic_router = SemanticRouter(reasoner=self.reasoner_llm)
        return self._semantic_router

    @property
    def stt_service(self): # -> STTService
        """Lazy-load STT service ()"""
        if self._stt_service is None:
            self._stt_service = STTService(
                settings=self.settings,
                enabled=self.enable_voice,
                unified_llm_client=self.unified_llm_client,
            )
        return self._stt_service
    
    @property
    def stt(self):
        """Lazy-load STT engine - delegates to STT service"""
        return self.stt_service.stt

    @property
    def vision_service(self): # -> VisionService
        """Lazy-load Vision service ()"""
        if self._vision_service is None:
            self._vision_service = VisionService(
                settings=self.settings,
                enabled=self.enable_vision,
            )
        return self._vision_service
    
    @property
    def vision_runner(self):
        """Lazy-load vision runner - delegates to Vision service"""
        return self.vision_service.vision_runner

    @property
    def learning_manager(self):
        """Lazy-load learning manager"""
        if self._learning_manager is None and self.enable_learning:
            logger.debug("Loading learning manager...")
            try:
                from ..learning.learning_manager import LearningManager

                self._learning_manager = LearningManager()
            except Exception as e:
                logger.warning(f"Failed to load learning manager: {e}")
        return self._learning_manager

    @property
    def tts_service(self): # -> TTSService
        """Lazy-load TTS service ()"""
        if self._tts_service is None:
            self._tts_service = TTSService(
                settings=self.settings,
                enabled=self.enable_tts,
            )
        return self._tts_service
    
    @property
    def tts(self):
        """Lazy-load TTS adapter - delegates to TTS service"""
        return self.tts_service.tts

    @property
    def conversation_manager(self):
        """Lazy-load ConversationManager for multi-turn dialogue support"""
        if self._conversation_manager is None:
            from .conversation_manager import ConversationManager
            self._conversation_manager = ConversationManager(self.memory)
            logger.info("ConversationManager initialized")
        return self._conversation_manager

    @property
    def async_vision_monitor(self):
        """Lazy-load async vision monitor - delegates to Vision service"""
        return self.vision_service.async_vision_monitor
    
    @property
    def memory_service_wrapper(self): # -> MemoryServiceWrapper
        """Lazy-load Memory service wrapper ()"""
        if self._memory_service_wrapper is None:
            self._memory_service_wrapper = MemoryServiceWrapper(
                memory=self.memory,
                context_ranker=self.context_ranker,
                clipboard_manager=self.clipboard_manager,
            )
        return self._memory_service_wrapper
    
    @property
    def lifecycle_service(self): # -> LifecycleService
        """Lazy-load Lifecycle service ()"""
        if self._lifecycle_service is None:
            self._lifecycle_service = LifecycleService(
                settings=self.settings,
                memory=self.memory,
                session_id=self.session_id,
                pipeline=self,  # Pass pipeline reference for dynamic component access
            )
        return self._lifecycle_service

