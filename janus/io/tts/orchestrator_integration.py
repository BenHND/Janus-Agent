"""
TTS Orchestrator Integration
Ticket ADD-VOX: Voice Response / TTS Integration
TICKET A6: Enhanced with microphone re-enable after TTS

Integrates TTS with the orchestrator to provide voice feedback during action execution.
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from janus.constants import HIGH_PRIORITY, MEDIUM_PRIORITY
from ..orchestrator.action_plan import ActionIntent, ActionPlan, ExecutionState
from .adapter import TTSAdapter


class TTSOrchestratorIntegration:
    """
    Integrates TTS with the orchestrator to provide voice feedback

    Features:
    - Voice confirmations for action start/completion
    - Error announcements
    - Plan progress updates
    - Configurable verbosity (compact/verbose)
    - Microphone re-enable after TTS (TICKET A6)
    """

    def __init__(
        self,
        tts_adapter: TTSAdapter,
        enable_tts: bool = False,
        auto_confirmations: bool = True,
        verbosity: str = "compact",
        lang: str = "fr-FR",
        stt_enable_callback: Optional[Callable[[], Awaitable[None]]] = None,
    ):
        """
        Initialize TTS orchestrator integration

        Args:
            tts_adapter: TTS adapter instance
            enable_tts: Enable TTS responses
            auto_confirmations: Enable automatic voice confirmations
            verbosity: Verbosity level ("compact" or "verbose")
            lang: Default language for TTS
            stt_enable_callback: Callback to re-enable STT after TTS (TICKET A6)
        """
        self.tts = tts_adapter
        self.enable_tts = enable_tts
        self.auto_confirmations = auto_confirmations
        self.verbosity = verbosity
        self.lang = lang
        self.stt_enable_callback = stt_enable_callback  # TICKET A6
        self.logger = logging.getLogger(self.__class__.__name__)

        # Message templates
        self._init_message_templates()

    def _init_message_templates(self):
        """Initialize message templates for different languages"""
        self.templates = {
            "fr-FR": {
                "compact": {
                    "plan_started": "Ok",
                    "intent_started": "Ok",
                    "intent_complete": "C'est fait",
                    "intent_failed": "Erreur",
                    "plan_complete": "Terminé",
                    "plan_failed": "Échec",
                },
                "verbose": {
                    "plan_started": "D'accord, je commence",
                    "intent_started": "J'exécute {action}",
                    "intent_complete": "J'ai terminé {action}",
                    "intent_failed": "Erreur lors de {action}",
                    "plan_complete": "Toutes les actions sont terminées",
                    "plan_failed": "Le plan a échoué",
                },
            },
            "en-US": {
                "compact": {
                    "plan_started": "Ok",
                    "intent_started": "Ok",
                    "intent_complete": "Done",
                    "intent_failed": "Error",
                    "plan_complete": "Complete",
                    "plan_failed": "Failed",
                },
                "verbose": {
                    "plan_started": "Alright, starting now",
                    "intent_started": "Executing {action}",
                    "intent_complete": "Completed {action}",
                    "intent_failed": "Error during {action}",
                    "plan_complete": "All actions completed",
                    "plan_failed": "Plan failed",
                },
            },
        }

    def _get_message(self, message_type: str, **kwargs) -> str:
        """
        Get message from templates

        Args:
            message_type: Type of message (e.g., "plan_started", "intent_complete")
            **kwargs: Template variables

        Returns:
            Formatted message string
        """
        # Get language templates
        lang = self.lang if self.lang in self.templates else "en-US"
        lang_templates = self.templates[lang]

        # Get verbosity templates
        verbosity = self.verbosity if self.verbosity in ["compact", "verbose"] else "compact"
        messages = lang_templates[verbosity]

        # Get message template
        template = messages.get(message_type, "")

        # Format with kwargs
        try:
            return template.format(**kwargs)
        except KeyError:
            return template

    def on_plan_started(self, plan: ActionPlan) -> None:
        """
        Called when plan execution starts

        Args:
            plan: The action plan that is starting
        """
        if not self.enable_tts or not self.auto_confirmations:
            return

        message = self._get_message("plan_started")
        if message:
            # Schedule async TTS call without blocking (TICKET-04)
            asyncio.create_task(self.tts.speak(message, lang=self.lang, priority=MEDIUM_PRIORITY))
            self.logger.debug(f"TTS: Plan started - '{message}'")

    def on_intent_started(self, intent: ActionIntent) -> None:
        """
        Called when an intent execution starts

        Args:
            intent: The action intent that is starting
        """
        if not self.enable_tts or not self.auto_confirmations:
            return

        # Extract action description
        action_desc = self._get_action_description(intent)

        message = self._get_message("intent_started", action=action_desc)
        if message and self.verbosity == "verbose":
            # Schedule async TTS call without blocking (TICKET-04)
            asyncio.create_task(self.tts.speak(message, lang=self.lang, priority=HIGH_PRIORITY))
            self.logger.debug(f"TTS: Intent started - '{message}'")

    def on_intent_complete(self, intent: ActionIntent) -> None:
        """
        Called when an intent execution completes successfully

        Args:
            intent: The completed action intent
        """
        if not self.enable_tts or not self.auto_confirmations:
            return

        # Extract action description
        action_desc = self._get_action_description(intent)

        message = self._get_message("intent_complete", action=action_desc)
        if message:
            # Schedule async TTS call without blocking (TICKET-04)
            asyncio.create_task(self.tts.speak(message, lang=self.lang, priority=HIGH_PRIORITY))
            self.logger.debug(f"TTS: Intent complete - '{message}'")

    def on_intent_failed(self, intent: ActionIntent) -> None:
        """
        Called when an intent execution fails

        Args:
            intent: The failed action intent
        """
        if not self.enable_tts:
            return

        # Always announce errors, even if auto_confirmations is off
        action_desc = self._get_action_description(intent)

        message = self._get_message("intent_failed", action=action_desc)
        if message:
            # High priority for errors - Schedule async TTS call (TICKET-04)
            asyncio.create_task(self.tts.speak(message, lang=self.lang, priority=7))
            self.logger.debug(f"TTS: Intent failed - '{message}'")

    def on_plan_complete(self, plan: ActionPlan) -> None:
        """
        Called when plan execution completes

        Args:
            plan: The completed action plan
        """
        if not self.enable_tts or not self.auto_confirmations:
            return

        if plan.state == ExecutionState.SUCCESS:
            message = self._get_message("plan_complete")
        else:
            message = self._get_message("plan_failed")

        if message:
            # Schedule async TTS call without blocking (TICKET-04)
            asyncio.create_task(self.tts.speak(message, lang=self.lang, priority=5))
            self.logger.debug(f"TTS: Plan complete - '{message}'")

    def on_ask_confirmation(self, question: str, priority: int = 8) -> None:
        """
        Called when user confirmation is needed

        Args:
            question: The confirmation question
            priority: Message priority (default: 8 for high priority)
        """
        if not self.enable_tts:
            return

        # Always speak confirmation requests - Schedule async TTS call (TICKET-04)
        asyncio.create_task(self.tts.speak(question, lang=self.lang, priority=priority))
        self.logger.debug(f"TTS: Confirmation request - '{question}'")

    def _get_action_description(self, intent: ActionIntent) -> str:
        """
        Extract action description from intent

        Args:
            intent: Action intent

        Returns:
            Human-readable action description
        """
        # Try to get a human-readable description
        if hasattr(intent, "description") and intent.description:
            return intent.description

        # Fall back to action type
        action_type = intent.action_type if hasattr(intent, "action_type") else intent.id

        # Clean up action type for speaking
        action_type = action_type.replace("_", " ")

        return action_type

    async def speak_custom(self, text: str, priority: int = 5) -> bool:
        """
        Speak custom text (async - TICKET-04)

        Args:
            text: Text to speak
            priority: Message priority

        Returns:
            True if speech was queued successfully
        """
        if not self.enable_tts:
            return False

        return await self.tts.speak(text, lang=self.lang, priority=priority)

    def set_enabled(self, enabled: bool) -> None:
        """
        Enable or disable TTS

        Args:
            enabled: True to enable, False to disable
        """
        self.enable_tts = enabled
        self.logger.info(f"TTS {'enabled' if enabled else 'disabled'}")

    def set_auto_confirmations(self, enabled: bool) -> None:
        """
        Enable or disable automatic confirmations

        Args:
            enabled: True to enable, False to disable
        """
        self.auto_confirmations = enabled
        self.logger.info(f"Auto confirmations {'enabled' if enabled else 'disabled'}")

    def set_verbosity(self, verbosity: str) -> None:
        """
        Set verbosity level

        Args:
            verbosity: "compact" or "verbose"
        """
        if verbosity in ["compact", "verbose"]:
            self.verbosity = verbosity
            self.logger.info(f"TTS verbosity set to: {verbosity}")

    def set_stt_enable_callback(self, callback: Optional[Callable[[], Awaitable[None]]]) -> None:
        """
        Set callback to re-enable STT after TTS (TICKET A6)

        Args:
            callback: Async callback to re-enable STT/microphone
        """
        self.stt_enable_callback = callback
        self.logger.info(f"STT enable callback {'set' if callback else 'cleared'}")

    async def ask_clarification(
        self, question: str, priority: int = 8, auto_enable_mic: bool = True
    ) -> bool:
        """
        Ask a clarification question via TTS and optionally re-enable microphone (TICKET A6).

        Args:
            question: The question to ask
            priority: Message priority (default: 8 for high priority)
            auto_enable_mic: Whether to automatically re-enable microphone after speaking

        Returns:
            True if question was spoken successfully
        """
        if not self.enable_tts:
            return False

        # Speak the question
        success = self.tts.speak(question, lang=self.lang, priority=priority)

        if success:
            self.logger.debug(f"TTS: Asked clarification - '{question}'")

            # Re-enable microphone automatically after TTS completes
            if auto_enable_mic and self.stt_enable_callback:
                try:
                    # Wait a brief moment for TTS to start
                    await asyncio.sleep(0.1)

                    # Call the callback to re-enable STT
                    await self.stt_enable_callback()
                    self.logger.debug("Microphone re-enabled after TTS")
                except Exception as e:
                    self.logger.error(f"Failed to re-enable microphone: {e}")

        return success
