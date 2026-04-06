"""
TTSService: Text-to-Speech Service

Handles all TTS-related operations for the Janus pipeline including:
- Lazy loading and initialization of TTS adapter
- Configuration management (voice, rate, volume, language)
- Voice feedback operations
- Observable speaking state for anti-echo (Neural Gatekeeper)

This service extracts TTS functionality from JanusPipeline to improve
modularity and testability.

TICKET: Zero-Latency Audio Pipeline
- Added observable is_speaking state for microphone gating
- Added stop_speaking_immediately() for barge-in support
"""

import asyncio
import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from janus.runtime.core.settings import Settings

logger = logging.getLogger(__name__)


class TTSService:
    """
    Service for Text-to-Speech operations.
    
    Provides lazy-loaded TTS adapter with proper configuration based on settings.
    Handles voice feedback to users.
    
    TICKET: Zero-Latency Audio Pipeline (Anti-Echo / Neural Gatekeeper)
    - Observable is_speaking state for microphone gating
    - stop_speaking_immediately() for barge-in support
    """
    
    def __init__(
        self,
        settings: "Settings",
        enabled: bool = False,
    ):
        """
        Initialize TTS Service.
        
        Args:
            settings: Unified settings object
            enabled: Whether TTS is enabled
        """
        self.settings = settings
        self.enabled = enabled
        self._tts = None
    
    @property
    def tts(self):
        """
        Lazy-load TTS adapter.
        
        Returns:
            TTSAdapter instance or None if not enabled/failed to load
        """
        if self._tts is None and self.enabled:
            logger.debug("Loading TTS adapter...")
            try:
                from janus.io.tts import DefaultTTSAdapter

                self._tts = DefaultTTSAdapter(
                    voice=self.settings.tts.voice or None,
                    rate=self.settings.tts.rate,
                    volume=self.settings.tts.volume,
                    lang=self.settings.tts.lang,
                    enable_queue=True,
                )
                logger.info("TTS adapter loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load TTS: {e}")
        return self._tts
    
    def speak(self, text: str) -> bool:
        """
        Speak the given text using TTS.
        
        Args:
            text: Text to speak
        
        Returns:
            True if speech was initiated successfully, False otherwise
        """
        if not self.enabled or not self.tts:
            logger.debug("TTS not available, skipping speech")
            return False
        
        try:
            speak_fn = getattr(self.tts, "speak", None)
            if speak_fn is None:
                return False

            result = speak_fn(text)

            # If adapter implements async speak(), schedule it.
            if asyncio.iscoroutine(result):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(result)
                except RuntimeError:
                    # No running loop (sync context): run in place.
                    asyncio.run(result)
            return True
        except Exception as e:
            logger.warning(f"Error speaking text: {e}")
            return False
    
    def stop(self):
        """Stop current TTS playback."""
        if self.tts:
            try:
                self.tts.stop()
            except Exception as e:
                logger.warning(f"Error stopping TTS: {e}")
    
    def stop_speaking_immediately(self):
        """
        Stop TTS playback immediately (barge-in support).
        
        This method is called when user interrupts the agent by speaking
        or clicking a button. It forcefully stops all TTS output.
        """
        if self.tts:
            try:
                logger.debug("Barge-in: Stopping TTS immediately")
                self.tts.stop()
                # Also clear any queued messages if the adapter supports it
                if hasattr(self.tts, 'clear_queue'):
                    self.tts.clear_queue()
            except Exception as e:
                logger.warning(f"Error stopping TTS immediately: {e}")
    
    def is_speaking(self) -> bool:
        """
        Check if TTS is currently speaking (observable state for anti-echo).
        
        This state is used by the microphone recorder to gate audio input
        and prevent the agent from hearing itself (Neural Gatekeeper).
        
        Returns:
            True if TTS is speaking, False otherwise
        """
        if not self.tts:
            return False
        
        try:
            return self.tts.is_speaking()
        except Exception as e:
            logger.warning(f"Error checking TTS speaking status: {e}")
            return False
    
    def is_available(self) -> bool:
        """
        Check if TTS is available.
        
        Returns:
            True if TTS is enabled and adapter loaded successfully
        """
        return self.enabled and self.tts is not None
    
    def cleanup(self):
        """Clean up TTS resources."""
        if self._tts is not None:
            try:
                # Stop any ongoing speech
                self.stop()
                # Cleanup if the adapter has a cleanup method
                if hasattr(self._tts, 'cleanup'):
                    self._tts.cleanup()
                self._tts = None
                logger.debug("TTS adapter cleaned up")
            except Exception as e:
                logger.warning(f"Error cleaning up TTS: {e}")
