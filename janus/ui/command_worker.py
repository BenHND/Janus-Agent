"""
Command Worker - QThread-based worker for non-blocking command processing.

TICKET-P3-01: UI Asynchronous Non-Blocking

This module provides a QThread-based worker that processes commands
in a separate thread, emitting signals to update the UI without
blocking the main Qt event loop. This allows the UI to remain
responsive during LLM network calls.

Key features:
- Runs JanusPipeline.process_command in a worker thread
- Emits status signals (thinking, acting, done, error) for UI updates
- Supports cancellation via stop() method
- Thread-safe communication with the main UI thread
"""

import asyncio
import logging
import time
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QThread, Signal

logger = logging.getLogger(__name__)

# TICKET-AUDIT-TODO-001: Vision processing visibility delay
# This delay ensures the "looking" state is visible to users before switching to "acting"
# Ideally this would be event-driven with a callback from vision processing completion,
# but that would require significant pipeline refactoring. This constant provides a
# reasonable UX tradeoff while keeping the code simple.
VISION_VISIBILITY_DELAY_MS = 500  # 500ms for users to see vision processing state


class CommandWorkerSignals(QObject):
    """
    Signals emitted by the CommandWorker.
    
    These signals are thread-safe and can be connected to slots
    in the main UI thread without causing blocking.
    """
    # Emitted when command processing starts (before LLM call)
    started = Signal()
    
    # Emitted when vision/OCR is processing (TICKET-UX-001)
    looking = Signal()
    
    # Emitted when the LLM is processing (thinking state)
    thinking = Signal()
    
    # Emitted when actions are being executed (acting state)
    acting = Signal()
    
    # Emitted when processing is complete
    # Args: (result, clarification)
    finished = Signal(object, object)
    
    # Emitted on error
    # Args: error_message (str)
    error = Signal(str)
    
    # Emitted to update transcript text
    transcript = Signal(str)


class CommandWorker(QThread):
    """
    Worker thread for processing voice commands without blocking the UI.
    
    This worker runs JanusPipeline.process_command_with_conversation
    in a separate QThread, emitting signals to keep the UI updated
    on the current processing state.
    
    Usage:
        worker = CommandWorker(pipeline, "open Safari")
        worker.signals.thinking.connect(lambda: update_status("Thinking..."))
        worker.signals.acting.connect(lambda: update_status("Acting..."))
        worker.signals.finished.connect(on_command_complete)
        worker.start()
    """
    
    def __init__(
        self,
        pipeline: Any,
        command: str,
        mock_execution: bool = False,
        parent: Optional[QObject] = None
    ):
        """
        Initialize the command worker.
        
        Args:
            pipeline: JanusPipeline instance
            command: The command text to process
            mock_execution: If True, skip actual execution (for testing)
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self.pipeline = pipeline
        self.command = command
        self.mock_execution = mock_execution
        self.signals = CommandWorkerSignals()
        self._stopped = False
        
    def stop(self):
        """
        Request the worker to stop.
        
        Note: This sets a flag but cannot immediately cancel an ongoing
        LLM request. The worker will check this flag at safe points.
        """
        self._stopped = True
        logger.debug("CommandWorker stop requested")
        
    def is_stopped(self) -> bool:
        """Check if stop was requested."""
        return self._stopped
    
    def run(self):
        """
        Execute the command processing in the worker thread.
        
        This method runs in a separate thread and emits signals
        to communicate with the main UI thread.
        """
        try:
            logger.info(f"CommandWorker starting: '{self.command}'")
            self.signals.started.emit()
            
            # Check for stop before processing
            if self._stopped:
                logger.debug("CommandWorker stopped before processing")
                return
            
            # Emit thinking signal - LLM is about to process
            self.signals.thinking.emit()
            
            # Set up callback to emit looking/acting signals when execution phase starts
            # TICKET-UX-001: Improved timing for LOOKING state visibility
            def on_execution_start():
                logger.debug("CommandWorker: Execution phase starting")
                # Emit looking signal (vision/OCR processing)
                logger.debug("CommandWorker: Emitting looking signal (vision/OCR)")
                self.signals.looking.emit()
                
                # TICKET-AUDIT-TODO-001: Brief delay for vision processing visibility
                # This ensures users see the "looking" state before it switches to "acting".
                # The delay is configurable via VISION_VISIBILITY_DELAY_MS constant.
                # Future improvement: Replace with event-driven callback from vision completion.
                time.sleep(VISION_VISIBILITY_DELAY_MS / 1000.0)
                
                logger.debug("CommandWorker: Emitting acting signal")
                self.signals.acting.emit()
            
            self.pipeline.set_on_execution_start_callback(on_execution_start)
            
            try:
                # Process the command in this worker thread.
                # The pipeline's process_command_with_conversation handles
                # async operations internally and returns synchronously.
                result, clarification = self.pipeline.process_command_with_conversation(
                    self.command,
                    mock_execution=self.mock_execution
                )
            finally:
                # Always clear the callback after processing
                self.pipeline.set_on_execution_start_callback(None)
            
            # Check for stop after processing
            if self._stopped:
                logger.debug("CommandWorker stopped after processing")
                return
            
            # Emit finished signal with result
            logger.info(f"CommandWorker finished: success={result.success if result else False}")
            self.signals.finished.emit(result, clarification)
            
        except Exception as e:
            logger.error(f"CommandWorker error: {e}", exc_info=True)
            self.signals.error.emit(str(e))


class RecordingWorker(QThread):
    """
    Worker thread for recording and transcribing audio.
    
    This worker handles the audio recording and transcription process
    in a separate thread, emitting signals when transcription is complete.
    """
    
    # Signals
    started = Signal()
    recording_stopped = Signal()
    transcription_complete = Signal(str)  # transcribed text
    error = Signal(str)
    
    def __init__(
        self,
        stt: Any,
        language: str = "fr",
        max_duration: float = 15.0,
        parent: Optional[QObject] = None
    ):
        """
        Initialize the recording worker.
        
        Args:
            stt: Speech-to-text engine instance
            language: Language code for transcription
            max_duration: Maximum recording duration in seconds
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self.stt = stt
        self.language = language
        self.max_duration = max_duration
        self._stopped = False
        
    def stop(self):
        """Request the worker to stop recording."""
        self._stopped = True
        if self.stt:
            self.stt.stop_listening()
        
    def run(self):
        """Execute the recording and transcription in the worker thread."""
        import os
        
        try:
            logger.debug("RecordingWorker starting")
            self.started.emit()
            
            if self._stopped:
                return
            
            # Create a new event loop for this thread (QThread context)
            # This is more efficient than asyncio.run() which creates/destroys a loop each time
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Start listening
                self.stt.start_listening()
                
                # Record audio using the loop
                audio_path, error = loop.run_until_complete(
                    self.stt.record_audio_async(max_duration=self.max_duration)
                )
                
                # Recording stopped (silence detected or max duration)
                self.recording_stopped.emit()
                
                # Transcribe if we got audio (even if stop was requested, complete the transcription)
                text = None
                if audio_path and not error:
                    result = loop.run_until_complete(
                        self.stt.transcribe_async(audio_path, self.language)
                    )
                    text = result.get("final") if result.get("success") else None
                    
                    # Cleanup temp audio file
                    if audio_path:
                        try:
                            os.remove(audio_path)
                        except (OSError, FileNotFoundError) as e:
                            logger.debug(f"Could not delete temp file {audio_path}: {e}")
                else:
                    logger.debug(f"Recording failed: {error}")
                
                if text:
                    self.transcription_complete.emit(text)
                else:
                    # No valid transcription
                    self.transcription_complete.emit("")
            
            finally:
                # Clean up the event loop properly
                try:
                    # Only process tasks if the loop is still running or has pending tasks
                    if not loop.is_closed():
                        # Cancel any pending tasks
                        pending = asyncio.all_tasks(loop)
                        if pending:
                            logger.debug(f"Cancelling {len(pending)} pending tasks")
                            for task in pending:
                                task.cancel()
                            # Give tasks a chance to finish cancellation
                            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        
                        # Shutdown async generators
                        loop.run_until_complete(loop.shutdown_asyncgens())
                        
                        # Close the loop
                        loop.close()
                except Exception as e:
                    logger.debug(f"Error closing event loop: {e}")
                    
        except Exception as e:
            logger.error(f"RecordingWorker error: {e}", exc_info=True)
            self.error.emit(str(e))
