"""
VisionService: Vision and Screen Verification Service

Handles all vision-related operations for the Janus pipeline including:
- Lazy loading and initialization of vision runner and async monitor
- Action verification using vision
- Vision context loading for reasoning
- Screen capture and analysis

This service extracts vision functionality from JanusPipeline to improve
modularity and testability.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from janus.runtime.core.settings import Settings
    from janus.runtime.core.contracts import ActionResult, ExecutionResult

logger = logging.getLogger(__name__)


class VisionService:
    """
    Service for Vision and screen verification operations.
    
    Provides lazy-loaded vision components with proper configuration.
    Handles action verification and vision context loading.
    """
    
    def __init__(
        self,
        settings: "Settings",
        enabled: bool = False,
    ):
        """
        Initialize Vision Service.
        
        Args:
            settings: Unified settings object
            enabled: Whether vision is enabled
        """
        self.settings = settings
        self.enabled = enabled
        self._vision_runner = None
        self._async_vision_monitor = None
        self._vision_power_manager = None  # TICKET-PERF-002: Power management
    
    @property
    def vision_runner(self):
        """
        Lazy-load vision runner.
        
        Returns:
            VisionRunner instance or None if not enabled/failed to load
        """
        if self._vision_runner is None and self.enabled:
            logger.debug("Loading vision runner...")
            try:
                from janus.vision.vision_runner import VisionRunner
                
                self._vision_runner = VisionRunner()
                logger.info("Vision runner loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load vision runner: {e}")
        return self._vision_runner
    
    @property
    def async_vision_monitor(self):
        """
        Lazy-load async vision monitor.
        
        Returns:
            AsyncVisionMonitor instance or None if not enabled/failed to load
        """
        if self._async_vision_monitor is None and self.enabled:
            logger.debug("Loading async vision monitor...")
            try:
                from janus.vision.async_vision_monitor import AsyncVisionMonitor
                
                self._async_vision_monitor = AsyncVisionMonitor(
                    check_interval_ms=self.settings.async_vision_monitor.check_interval_ms,
                    enable_popup_detection=self.settings.async_vision_monitor.enable_popup_detection,
                    enable_error_detection=self.settings.async_vision_monitor.enable_error_detection,
                )
                logger.info("Async vision monitor loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load async vision monitor: {e}")
        return self._async_vision_monitor
    
    @property
    def vision_power_manager(self):
        """
        Lazy-load vision power manager.
        TICKET-PERF-002: Power management for eco mode
        
        Returns:
            VisionPowerManager instance or None if not enabled/failed to load
        """
        if self._vision_power_manager is None and self.enabled:
            logger.debug("Loading vision power manager...")
            try:
                from janus.vision.vision_power_manager import VisionPowerManager
                
                self._vision_power_manager = VisionPowerManager(idle_timeout_seconds=30)
                logger.info("Vision power manager loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load vision power manager: {e}")
        return self._vision_power_manager
    
    def verify_with_vision(self, result: "ExecutionResult", request_id: str, memory):
        """
        Verify action execution using vision.
        
        PERF-FOUNDATION-001: Smart verification policy
        - Respects vision_verification_enabled flag
        - FAST mode: Only verify failures, recoverable errors, or risky UI actions
        - Skip verification for successful results by default
        - Risky actions: UI module click/type actions
        
        Args:
            result: Execution result to verify
            request_id: Request ID for tracking
            memory: Memory engine for structured logging
        """
        # PERF-FOUNDATION-001: Check vision_verification_enabled flag
        if not self.settings.features.vision_verification_enabled:
            logger.debug("Vision verification disabled by vision_verification_enabled flag")
            return
        
        if not self.vision_runner:
            return
        
        logger.debug("Verifying with vision")
        if memory:
            memory.log_structured(
                level="DEBUG",
                logger="VisionService",
                message="Verifying with vision",
                session_id=getattr(result, 'session_id', None),
                request_id=request_id,
                module=__name__,
                function="verify_with_vision",
            )
        
        try:
            # Vision verification for each action result
            for action_result in result.action_results:
                # PERF-FOUNDATION-001: Smart verification policy
                should_verify = self._should_verify_action(action_result)
                
                if not should_verify:
                    logger.debug(f"Skipping verification for successful action: {action_result.action_type}")
                    continue
                
                # Use vision to verify the action
                verification_passed = self.vision_runner.verify_action_result(action_result)
                if not verification_passed:
                    logger.warning(
                        f"Vision verification failed for action: {action_result.action_type}"
                    )
                    if action_result.success:
                        action_result.success = False
                        action_result.message += " (vision verification failed)"
        except Exception as e:
            logger.warning(f"Vision verification error: {e}")
    
    def _should_verify_action(self, action_result) -> bool:
        """
        Determine if an action should be verified with vision.
        
        PERF-FOUNDATION-001: Verification policy
        - Always verify if action failed
        - Always verify if recoverable error
        - Always verify risky UI actions (ui module with click/type)
        - Skip verification for successful non-risky actions
        
        Args:
            action_result: Action result to check
            
        Returns:
            True if action should be verified, False otherwise
        """
        # Always verify failures
        if not action_result.success:
            return True
        
        # Always verify recoverable errors
        if hasattr(action_result, 'recoverable') and action_result.recoverable:
            return True
        
        # Check for risky UI actions (ui module with click/type/input/press)
        # Action types follow format: "module.action" (e.g., "ui.click", "ui.type")
        action_type = action_result.action_type.lower()
        
        # Check if this is a UI module action
        if not action_type.startswith('ui.'):
            return False
        
        # Extract the action name (part after "ui.")
        action_name = action_type.split('.', 1)[1] if '.' in action_type else ''
        
        # Check if the action itself is risky (not just contains the keyword)
        risky_actions = {'click', 'type', 'input', 'press', 'send', 'submit'}
        is_risky = action_name in risky_actions
        
        if is_risky:
            logger.debug(f"Risky UI action detected, will verify: {action_result.action_type}")
            return True
        
        # Skip verification for successful, non-risky actions
        return False
    
    def verify_action_with_vision(
        self, action_result: "ActionResult", request_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verify a single action with vision and return verification data.
        
        Args:
            action_result: The action result to verify
            request_id: Request ID for tracking
        
        Returns:
            Dictionary with verification data, or None if vision not available
        """
        if not self.vision_runner:
            return None
        
        try:
            logger.debug(f"Verifying action {action_result.action_type} with vision")
            
            # Perform vision verification
            verification_passed = self.vision_runner.verify_action_result(action_result)
            
            # Collect vision data
            vision_data = {
                "verification": {
                    "passed": verification_passed,
                    "action_type": action_result.action_type,
                    "timestamp": datetime.now().isoformat(),
                },
                "visual_state": {
                    # This would contain actual screenshot analysis in production
                    "verified": verification_passed,
                    "confidence": 0.85 if verification_passed else 0.3,
                },
            }
            
            return vision_data
        
        except Exception as e:
            logger.warning(f"Vision verification error: {e}")
            return None
    
    def load_vision_context(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Load vision/OCR context data.
        
        Args:
            request_id: Request ID for tracking
        
        Returns:
            Vision data dict or None if unavailable
        """
        if not self.enabled or not self.vision_runner:
            return None
        
        try:
            # Get current screen state from vision runner
            # This is a placeholder - actual implementation depends on VisionRunner API
            # For now, return None to indicate no vision data available
            return None
        except Exception as e:
            logger.warning(f"Failed to load vision context: {e}")
            return None
    
    async def preload_vision_models_async(self):
        """
        Preload vision models asynchronously to avoid cold start delays.
        """
        if not self.enabled:
            return
        
        logger.info("Preloading vision models...")
        try:
            if self.vision_runner:
                # VisionRunner might have a preload method
                if hasattr(self.vision_runner, 'preload_models'):
                    await self.vision_runner.preload_models()
                logger.info("Vision models preloaded successfully")
        except Exception as e:
            logger.warning(f"Failed to preload vision models: {e}")
    
    def is_available(self) -> bool:
        """
        Check if vision runner is available.
        
        Returns:
            True if vision is enabled and runner loaded successfully
        """
        return self.enabled and self.vision_runner is not None
    
    def enable_eco_mode(self):
        """
        Enable eco mode for vision components.
        TICKET-PERF-002: Mode Économie d'Énergie
        
        Reduces vision monitoring frequency and enables model unloading.
        """
        if not self.enabled:
            return
        
        logger.info("Enabling vision eco mode")
        
        # Enable eco mode in async vision monitor (reduces polling)
        if self.async_vision_monitor:
            self.async_vision_monitor.enable_eco_mode()
        
        # Enable eco mode in power manager (enables model unloading)
        if self.vision_power_manager:
            self.vision_power_manager.enable_eco_mode()
    
    def disable_eco_mode(self):
        """
        Disable eco mode for vision components.
        TICKET-PERF-002: Mode Économie d'Énergie
        
        Restores normal vision monitoring frequency and reloads models if needed.
        """
        if not self.enabled:
            return
        
        logger.info("Disabling vision eco mode")
        
        # Disable eco mode in async vision monitor (restores polling)
        if self.async_vision_monitor:
            self.async_vision_monitor.disable_eco_mode()
        
        # Disable eco mode in power manager (reloads models)
        if self.vision_power_manager:
            self.vision_power_manager.disable_eco_mode()
    
    def record_vision_activity(self):
        """
        Record vision activity for power management.
        TICKET-PERF-002: Tracks usage to manage model unloading
        
        Call this whenever vision models are actively used.
        """
        if self.vision_power_manager:
            self.vision_power_manager.record_activity()
    
    def cleanup(self):
        """Clean up vision resources."""
        if self._vision_runner is not None:
            try:
                if hasattr(self._vision_runner, 'cleanup'):
                    self._vision_runner.cleanup()
                self._vision_runner = None
                logger.debug("Vision runner cleaned up")
            except Exception as e:
                logger.warning(f"Error cleaning up vision runner: {e}")
        
        if self._async_vision_monitor is not None:
            try:
                if hasattr(self._async_vision_monitor, 'stop'):
                    self._async_vision_monitor.stop()
                self._async_vision_monitor = None
                logger.debug("Async vision monitor cleaned up")
            except Exception as e:
                logger.warning(f"Error cleaning up async vision monitor: {e}")
        
        if self._vision_power_manager is not None:
            try:
                if hasattr(self._vision_power_manager, 'stop'):
                    self._vision_power_manager.stop()
                self._vision_power_manager = None
                logger.debug("Vision power manager cleaned up")
            except Exception as e:
                logger.warning(f"Error cleaning up vision power manager: {e}")
