"""
TTSAdapter - Base interface for Text-to-Speech adapters
Ticket ADD-VOX: Voice Response / TTS Integration
Ticket TICKET-MAC-03: Enhanced TTS controls
Ticket TICKET-04: Non-blocking async TTS operations
"""

from abc import ABC, abstractmethod
from typing import Optional


class TTSAdapter(ABC):
    """
    Base adapter interface for Text-to-Speech engines

    This interface defines the contract for all TTS implementations,
    allowing for local TTS (macOS, Windows, Linux) or cloud-based solutions.
    """

    @abstractmethod
    async def speak(self, text: str, lang: str = "fr", priority: int = 0) -> bool:
        """
        Speak the given text (async version - TICKET-04)

        This method is now async to avoid blocking the event loop.
        Blocking I/O operations (audio generation, playback) should be
        wrapped in asyncio.to_thread() or loop.run_in_executor().

        Args:
            text: The text to speak
            lang: Language code (e.g., "fr-FR", "en-US")
            priority: Priority level (0 = normal, higher = more important)

        Returns:
            True if speech was queued/started successfully, False otherwise
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop current speech immediately"""
        pass

    @abstractmethod
    def is_speaking(self) -> bool:
        """
        Check if TTS is currently speaking

        Returns:
            True if speech is in progress, False otherwise
        """
        pass

    @abstractmethod
    def set_voice(self, voice: Optional[str]) -> None:
        """
        Set the voice to use for speech

        Args:
            voice: Voice name/identifier (platform-specific)
        """
        pass

    @abstractmethod
    def set_rate(self, rate: int) -> None:
        """
        Set speech rate

        Args:
            rate: Words per minute (typically 100-300)
        """
        pass

    @abstractmethod
    def set_volume(self, volume: float) -> None:
        """
        Set speech volume

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        pass

    @abstractmethod
    def get_volume(self) -> float:
        """
        Get current volume level

        Returns:
            Volume level (0.0 to 1.0)
        """
        pass

    @abstractmethod
    def mute(self) -> None:
        """Mute TTS output"""
        pass

    @abstractmethod
    def unmute(self) -> None:
        """Unmute TTS output"""
        pass

    @abstractmethod
    def is_muted(self) -> bool:
        """
        Check if TTS is muted

        Returns:
            True if muted, False otherwise
        """
        pass

    @abstractmethod
    def get_available_voices(self) -> list:
        """
        Get list of available voices

        Returns:
            List of voice names/identifiers
        """
        pass
