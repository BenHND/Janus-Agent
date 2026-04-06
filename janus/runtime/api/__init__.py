"""
Pipeline Entry Point - Full integration of STT → Reasoner → Executor
Context API - Context & Memory Engine
"""

import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

# Export context API functions
from .context_api import (
    ContextEngine,
    clear_context,
    get_context,
    get_context_statistics,
    resolve_reference,
    update_context,
)

logger = logging.getLogger(__name__)


class PipelineEntry:
    """
    Full pipeline integration

    Flow: STT → VoiceReasoner → Executor
    Provides: listen_and_execute() complete voice automation
    """

    def __init__(
        self,
        stt_engine=None,
        voice_reasoner=None,
        executor=None,
    ):
        """
        Initialize pipeline

        Args:
            stt_engine: STT engine instance
            voice_reasoner: VoiceReasoner instance
            executor: Executor instance
        """
        self.stt_engine = stt_engine
        self.voice_reasoner = voice_reasoner
        self.executor = executor

        logger.info("PipelineEntry initialized")

    def listen_and_execute(
        self,
        duration: Optional[float] = None,
        auto_execute: bool = True,
    ) -> Dict[str, Any]:
        """
        Listen for voice command and execute

        Args:
            duration: Recording duration (None for auto-detect)
            auto_execute: Whether to execute automatically

        Returns:
            Complete result dictionary
        """
        try:
            # Step 1: STT - Listen and transcribe
            logger.info("Step 1: Listening for voice command...")

            if not self.stt_engine:
                return {
                    "status": "error",
                    "error": "STT engine not available",
                }

            transcription = self._listen(duration)

            if not transcription:
                return {
                    "status": "error",
                    "error": "No transcription received",
                }

            logger.info(f"Transcription: {transcription}")

            # Step 2: Reasoning - Parse and normalize intents
            logger.info("Step 2: Reasoning about command...")

            if not self.voice_reasoner:
                return {
                    "status": "error",
                    "error": "Voice reasoner not available",
                    "transcription": transcription,
                }

            intents = self.voice_reasoner.reason(transcription)

            if not intents:
                return {
                    "status": "no_intent",
                    "transcription": transcription,
                    "message": "Could not understand command",
                }

            logger.info(f"Identified {len(intents)} intents")

            # Step 3: Execution - Execute intents
            if auto_execute:
                logger.info("Step 3: Executing intents...")

                if not self.executor:
                    return {
                        "status": "error",
                        "error": "Executor not available",
                        "transcription": transcription,
                        "intents": [asdict(i) for i in intents],
                    }

                # Convert intents to executor format
                intent_dicts = [
                    {
                        "intent": intent.intent,
                        "parameters": intent.parameters,
                        "confidence": intent.confidence,
                        "context": intent.context,
                    }
                    for intent in intents
                ]

                execution_report = self.executor.execute_intents(intent_dicts)

                return {
                    "status": "executed",
                    "transcription": transcription,
                    "intents": [asdict(i) for i in intents],
                    "execution_report": execution_report.to_dict(),
                }
            else:
                # Return intents without executing
                return {
                    "status": "parsed",
                    "transcription": transcription,
                    "intents": [asdict(i) for i in intents],
                }

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    def process_text(
        self,
        text: str,
        auto_execute: bool = True,
    ) -> Dict[str, Any]:
        """
        Process text command (without STT)

        Args:
            text: Command text
            auto_execute: Whether to execute automatically

        Returns:
            Complete result dictionary
        """
        try:
            logger.info(f"Processing text command: {text}")

            # Step 1: Reasoning - Parse and normalize intents
            if not self.voice_reasoner:
                return {
                    "status": "error",
                    "error": "Voice reasoner not available",
                    "text": text,
                }

            intents = self.voice_reasoner.reason(text)

            if not intents:
                return {
                    "status": "no_intent",
                    "text": text,
                    "message": "Could not understand command",
                }

            logger.info(f"Identified {len(intents)} intents")

            # Step 2: Execution - Execute intents
            if auto_execute:
                if not self.executor:
                    return {
                        "status": "error",
                        "error": "Executor not available",
                        "text": text,
                        "intents": [asdict(i) for i in intents],
                    }

                # Convert intents to executor format
                intent_dicts = [
                    {
                        "intent": intent.intent,
                        "parameters": intent.parameters,
                        "confidence": intent.confidence,
                        "context": intent.context,
                    }
                    for intent in intents
                ]

                execution_report = self.executor.execute_intents(intent_dicts)

                return {
                    "status": "executed",
                    "text": text,
                    "intents": [asdict(i) for i in intents],
                    "execution_report": execution_report.to_dict(),
                }
            else:
                # Return intents without executing
                return {
                    "status": "parsed",
                    "text": text,
                    "intents": [asdict(i) for i in intents],
                }

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    def _listen(self, duration: Optional[float] = None) -> Optional[str]:
        """
        Listen and transcribe using STT engine

        Args:
            duration: Recording duration

        Returns:
            Transcription text or None
        """
        try:
            if hasattr(self.stt_engine, "listen_and_transcribe"):
                return self.stt_engine.listen_and_transcribe(duration=duration)
            elif hasattr(self.stt_engine, "transcribe"):
                # Record audio first
                if hasattr(self.stt_engine, "record_audio"):
                    audio = self.stt_engine.record_audio(duration=duration)
                    return self.stt_engine.transcribe(audio)

            logger.error("STT engine does not have expected methods")
            return None

        except Exception as e:
            logger.error(f"Error during listening: {e}")
            return None
