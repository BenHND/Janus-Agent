"""UI mode - Interactive overlay interface

TICKET-P3-01: UI Asynchronous Non-Blocking
This module uses QThread-based workers to process commands without blocking
the Qt event loop. This allows the UI to remain responsive during LLM calls.
"""
import asyncio
import logging
import os
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def run_ui_mode(pipeline, settings, stt, tts, preload_models_func=None):
    """
    Run Janus with PySide6 overlay UI (default mode)
    
    TICKET-P3-01: Uses QThread workers for non-blocking command processing.
    The UI remains responsive during LLM network calls - users can move
    the window or click Stop while waiting for LLM responses.
    
    Args:
        pipeline: JanusPipeline instance
        settings: Settings instance
        stt: Speech-to-text engine
        tts: Text-to-speech engine
        preload_models_func: Optional async function to preload models before starting
    """
    from PySide6.QtWidgets import QApplication
    from janus.app.initialization import speak_feedback
    from janus.i18n import (
        t, tts_done, tts_error, tts_redo, tts_undo, tts_welcome,
        tts_loading_init, tts_loading_systems, tts_executing,
        status_listening, status_idle, status_looking, status_thinking, status_acting, status_loading
    )
    from janus.ui.keyboard_shortcuts import KeyboardShortcutHandler
    from janus.ui.overlay_ui import OverlayUI, StatusState
    from janus.ui.command_worker import CommandWorker, RecordingWorker

    logger.info("Starting UI mode with PySide6 overlay (TICKET-P3-01: non-blocking)")

    class ListeningState:
        """Track listening state and worker threads."""
        def __init__(self):
            self.active = False
            self.recording_worker: Optional[RecordingWorker] = None
            self.command_worker: Optional[CommandWorker] = None
            self.stop_event = threading.Event()
            self.event_loop = None  # Store reference to main event loop
            self.toggle_lock = threading.Lock()  # Prevent race conditions on mic toggle

    listening_state = ListeningState()
    
    # Initialize chat_window reference (will be created after overlay)
    chat_window = None

    def handle_undo_sync():
        logger.info("Keyboard shortcut: Undo")
        result = asyncio.run(pipeline.process_command_async("undo", mock_execution=False))
        if result.success:
            asyncio.run(speak_feedback(tts, tts_undo()))

    def handle_redo_sync():
        logger.info("Keyboard shortcut: Redo")
        result = asyncio.run(pipeline.process_command_async("redo", mock_execution=False))
        if result.success:
            asyncio.run(speak_feedback(tts, tts_redo()))

    shortcuts = KeyboardShortcutHandler(on_undo=handle_undo_sync, on_redo=handle_redo_sync)
    shortcuts.start()

    # --- Recording Worker Callbacks ---
    def on_recording_started():
        """Called when recording starts."""
        logger.debug("Recording started")

    def on_recording_stopped():
        """Called when recording stops (silence detected or max duration)."""
        logger.debug("Recording stopped, setting status to IDLE")
        overlay.signals.set_status_signal.emit((StatusState.IDLE, status_idle()))

    def on_transcription_complete(text: str):
        """Called when transcription is complete."""
        if not text:
            # No valid transcription - restart listening only if still active and not stopped
            logger.info("Recording completed with no valid transcription")
            if listening_state.active and not listening_state.stop_event.is_set():
                start_recording_worker()
            else:
                logger.debug("Not restarting recording: listening is inactive or stopped")
            return

        logger.info(f"Transcribed: {text}")
        listening_state.active = False
        overlay.mic_enabled = False
        overlay.signals.append_transcript_signal.emit(text)

        # Start command processing in a separate worker (non-blocking)
        start_command_worker(text)

    def on_recording_error(error_msg: str):
        """Called on recording error."""
        logger.error(f"Recording error: {error_msg}")
        overlay.signals.set_status_signal.emit((StatusState.IDLE, status_idle()))
        overlay.signals.append_transcript_signal.emit(f"Error: {error_msg}")
        listening_state.active = False
        overlay.mic_enabled = False

    # --- Command Worker Callbacks ---
    def on_command_started():
        """Called when command processing starts."""
        logger.debug("Command processing started")

    def on_command_looking():
        """Called when vision/OCR is processing (TICKET-UX-001: optimistic UI feedback)."""
        logger.debug("Command worker: Looking state (vision/OCR)")
        overlay.signals.set_status_signal.emit((StatusState.LOOKING, status_looking()))
        # Update chat window if it's visible
        if chat_window and chat_window.isVisible():
            chat_window.update_last_status("looking", "Analyse visuelle...")

    def on_command_thinking():
        """Called when LLM is thinking (TICKET-P3-01: non-blocking state update)."""
        logger.debug("Command worker: Thinking state")
        overlay.signals.set_status_signal.emit((StatusState.THINKING, status_thinking()))
        # Update chat window if it's visible
        if chat_window and chat_window.isVisible():
            chat_window.update_last_status("thinking", "Analyse de la commande...")

    def on_command_acting():
        """Called when actions are being executed."""
        logger.debug("Command worker: Acting state")
        overlay.signals.set_status_signal.emit((StatusState.ACTING, status_acting()))
        # Update chat window if it's visible
        if chat_window and chat_window.isVisible():
            chat_window.update_last_status("acting", "Exécution en cours...")
        # Speak "Très bien" when transitioning from thinking to execution
        if listening_state.event_loop:
            asyncio.run_coroutine_threadsafe(
                speak_feedback(tts, tts_executing()), listening_state.event_loop
            )

    def on_command_finished(result: Any, clarification: Optional[str]):
        """Called when command processing is complete."""
        import time
        
        if clarification:
            overlay.signals.set_status_signal.emit((StatusState.IDLE, status_idle()))
            overlay.signals.append_transcript_signal.emit(f"❓ {clarification}")
            # Update chat window if it's visible
            if chat_window and chat_window.isVisible():
                chat_window.set_processing(False)
                chat_window.add_assistant_message(f"❓ {clarification}")
            # Schedule TTS in the main event loop (thread-safe)
            if listening_state.event_loop:
                asyncio.run_coroutine_threadsafe(
                    speak_feedback(tts, clarification), listening_state.event_loop
                )
            # Re-enable listening for clarification response
            listening_state.active = True
            overlay.mic_enabled = True
            start_recording_worker()
            return

        if result and result.success:
            # Show results
            for action_result in result.action_results:
                msg = action_result.message or action_result.action_type
                overlay.signals.append_transcript_signal.emit(msg)
                # Update chat window if it's visible
                if chat_window and chat_window.isVisible():
                    chat_window.add_assistant_message(msg)
            
            # Update chat window with success status
            if chat_window and chat_window.isVisible():
                chat_window.set_processing(False)
                chat_window.add_status_indicator("done", "✅ Action terminée avec succès")
            
            # Brief delay then reset to idle
            # Use QTimer for non-blocking delay instead of time.sleep
            from PySide6.QtCore import QTimer
            def set_idle():
                overlay.signals.set_status_signal.emit((StatusState.IDLE, status_idle()))
            QTimer.singleShot(1000, set_idle)
            
            # Speak success feedback
            if listening_state.event_loop:
                asyncio.run_coroutine_threadsafe(
                    speak_feedback(tts, tts_done()), listening_state.event_loop
                )
        else:
            overlay.signals.set_status_signal.emit((StatusState.IDLE, status_idle()))
            error_msg = ""
            if result and result.error:
                error_msg = (
                    result.error.message
                    if hasattr(result.error, "message")
                    else str(result.error)
                )
                overlay.signals.append_transcript_signal.emit(f"Error: {error_msg}")
            # Update chat window with error
            if chat_window and chat_window.isVisible():
                chat_window.set_processing(False)
                chat_window.add_status_indicator("error", error_msg or "Erreur inconnue")
            # Speak error feedback
            if listening_state.event_loop:
                asyncio.run_coroutine_threadsafe(
                    speak_feedback(tts, tts_error()), listening_state.event_loop
                )

        listening_state.command_worker = None

    def on_command_error(error_msg: str):
        """Called on command processing error."""
        logger.error(f"Command error: {error_msg}")
        overlay.signals.set_status_signal.emit((StatusState.ERROR, error_msg))
        overlay.signals.append_transcript_signal.emit(f"Error: {error_msg}")
        listening_state.active = False
        overlay.mic_enabled = False
        listening_state.command_worker = None
        
        # Reset to idle after error display
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: overlay.signals.set_status_signal.emit(
            (StatusState.IDLE, status_idle())
        ))

    # --- Worker Management ---
    def start_recording_worker():
        """Start the recording worker thread."""
        # Clean up any existing worker
        if listening_state.recording_worker and listening_state.recording_worker.isRunning():
            listening_state.recording_worker.stop()
            listening_state.recording_worker.wait()

        worker = RecordingWorker(
            stt=stt,
            language=settings.language.default,
            max_duration=15.0
        )
        
        # Connect signals
        worker.started.connect(on_recording_started)
        worker.recording_stopped.connect(on_recording_stopped)
        worker.transcription_complete.connect(on_transcription_complete)
        worker.error.connect(on_recording_error)
        
        listening_state.recording_worker = worker
        worker.start()

    def start_command_worker(command: str):
        """Start the command processing worker thread (TICKET-P3-01)."""
        # Clean up any existing worker
        if listening_state.command_worker and listening_state.command_worker.isRunning():
            listening_state.command_worker.stop()
            listening_state.command_worker.wait()

        worker = CommandWorker(
            pipeline=pipeline,
            command=command,
            mock_execution=False
        )
        
        # Connect signals (TICKET-P3-01: non-blocking UI updates, TICKET-UX-001: looking state)
        worker.signals.started.connect(on_command_started)
        worker.signals.looking.connect(on_command_looking)
        worker.signals.thinking.connect(on_command_thinking)
        worker.signals.acting.connect(on_command_acting)
        worker.signals.finished.connect(on_command_finished)
        worker.signals.error.connect(on_command_error)
        
        listening_state.command_worker = worker
        worker.start()

    def stop_all_workers():
        """Stop all running workers and wait for them to complete."""
        # Reduced timeout from 5s to 2s for better responsiveness
        if listening_state.recording_worker and listening_state.recording_worker.isRunning():
            listening_state.recording_worker.stop()
            listening_state.recording_worker.wait(2000)  # Wait up to 2 seconds
        if listening_state.command_worker and listening_state.command_worker.isRunning():
            listening_state.command_worker.stop()
            listening_state.command_worker.wait(2000)  # Wait up to 2 seconds

    def on_mic_toggle(enabled: bool):
        """Handle mic button toggle with mutex to prevent race conditions."""
        with listening_state.toggle_lock:
            listening_state.active = enabled
            if enabled:
                logger.info("UI: Listening started")
                overlay.signals.set_status_signal.emit((StatusState.LISTENING, status_listening()))
                if tts and tts.is_speaking():
                    tts.stop()
                stt.start_listening()
                listening_state.stop_event.clear()
                start_recording_worker()
            else:
                logger.info("UI: Listening stopped")
                stt.stop_listening()
                listening_state.stop_event.set()
                stop_all_workers()
                overlay.signals.set_status_signal.emit((StatusState.IDLE, status_idle()))

    def on_config():
        logger.info("UI: Config button clicked")
    
    def on_text_submit(text: str):
        """Handle text input submission (same as voice transcription)"""
        logger.info(f"UI: Text submitted: {text}")
        # Process the text command the same way as voice transcription
        # Disable mic mode and start command processing
        listening_state.active = False
        overlay.mic_enabled = False
        start_command_worker(text)

    app = QApplication.instance()
    # Prevent app from quitting when window is closed (for debugging/persistence)
    # app.setQuitOnLastWindowClosed(False) 
    
    overlay = OverlayUI(
        on_mic_toggle=on_mic_toggle,
        on_config=on_config,
        on_text_submit=on_text_submit,
        config_path="janus_overlay_position.json",
    )
    logger.info("OverlayUI created successfully")

    # Create the chat window (initially hidden)
    from janus.ui.chat_overlay_window import ChatOverlayWindow
    chat_window = ChatOverlayWindow(dark_mode=overlay._dark_mode)
    overlay.chat_window = chat_window  # Connect chat window to overlay
    
    def on_chat_text_submitted(text: str):
        """Called when user sends a message via chat"""
        logger.info(f"Chat: Text submitted: {text}")
        chat_window.set_processing(True)
        chat_window.add_status_indicator("thinking", "Réflexion en cours...")
        start_command_worker(text)
    
    def on_chat_stop_requested():
        """Called when user clicks Stop in chat"""
        logger.info("Chat: Stop requested")
        stop_all_workers()
        chat_window.set_processing(False)
        chat_window.add_status_indicator("error", "Interrompu par l'utilisateur")
    
    def on_chat_mic_toggle(enabled: bool):
        """Called when user toggles mic in chat"""
        logger.info(f"Chat: Mic toggle requested: {enabled}")
        # Delegate to main overlay mic toggle
        overlay.mic_enabled = enabled
        on_mic_toggle(enabled)
        # Update chat mic button state
        chat_window.mic_btn.setChecked(enabled)
    
    # Connect chat window signals
    chat_window.text_submitted.connect(on_chat_text_submitted)
    chat_window.stop_requested.connect(on_chat_stop_requested)
    chat_window.mic_toggle_requested.connect(on_chat_mic_toggle)
    
    logger.info("Chat window created and connected successfully")

    overlay.show()
    overlay.raise_()
    overlay.activateWindow()

    # Set loading state and disable mic button
    overlay.set_loading(status_loading())
    logger.info("Overlay set to loading state")
    
    # Get the current event loop and store it for the listening thread
    loop = asyncio.get_running_loop()
    listening_state.event_loop = loop
    
    # Define progress callback that speaks each step via TTS
    def on_progress_sync(message: str):
        """Speak progress message via TTS (non-blocking sync wrapper)"""
        logger.info(f"Loading progress: {message}")
        if tts:
            # Schedule the async task in the event loop
            asyncio.run_coroutine_threadsafe(speak_feedback(tts, message), loop)
    
    # Preload models with progressive feedback
    if preload_models_func:
        logger.info("Preloading models with progressive feedback...")
        await preload_models_func(progress_callback=on_progress_sync)
        logger.info("Models preloaded successfully")
    
    # Speak welcome message after loading
    if tts:
        asyncio.create_task(speak_feedback(tts, tts_welcome()))  # Execute async task
    
    # Enable mic button and set status to idle
    overlay.enable_mic_button()
    overlay.set_status(StatusState.IDLE, status_idle())
    logger.info("Overlay ready for user interaction")
    
    # TICKET-P3-02: Wake word detection support
    wake_word_detector = None
    if settings.wakeword.enabled:
        try:
            from janus.io.stt.wake_word_detector import create_wake_word_detector
            
            wake_word_detector = create_wake_word_detector(
                recorder=stt.recorder,
                enable_wake_word=True,
                model=settings.wakeword.model,
                threshold=settings.wakeword.threshold,
                cooldown_ms=settings.wakeword.cooldown_ms,
            )
            
            if wake_word_detector:
                def activate_listening():
                    if not listening_state.active:
                        overlay.mic_enabled = True
                        on_mic_toggle(True)
                        # Visual feedback
                        overlay.signals.append_transcript_signal.emit("✓ Wake word detected")
                        # Audio feedback
                        if tts and listening_state.event_loop:
                            asyncio.run_coroutine_threadsafe(
                                speak_feedback(tts, "Oui?"), listening_state.event_loop
                            )

                def on_wake_word_detected():
                    """Callback when wake word is detected"""
                    logger.info("Wake word detected! Activating voice command...")
                    # Emit signal to trigger UI update on main thread
                    overlay.signals.wake_word_detected_signal.emit()

                # Connect the signal to the slot
                overlay.signals.wake_word_detected_signal.connect(activate_listening)
                
                wake_word_detector.start(on_wake_word_detected)
                logger.info("✓ Wake word detector started")
                overlay.signals.append_transcript_signal.emit("🎤 Wake word detection enabled - say 'Hey Janus'")
        except Exception as e:
            logger.warning(f"Failed to initialize wake word detector: {e}")
            overlay.signals.append_transcript_signal.emit(f"⚠️ Wake word detection disabled: {e}")

    # TICKET-PERF-002: Connect battery monitor to overlay eco mode indicator
    if hasattr(pipeline, 'lifecycle_service'):
        try:
            battery_monitor = pipeline.lifecycle_service._battery_monitor
            if battery_monitor:
                def on_battery_mode_enabled():
                    """Called when system switches to battery - show eco mode indicator"""
                    logger.info("Battery mode enabled - showing eco mode indicator in overlay")
                    overlay.signals.show_eco_mode_signal.emit()
                
                def on_battery_mode_disabled():
                    """Called when system switches to AC - hide eco mode indicator"""
                    logger.info("AC power detected - hiding eco mode indicator in overlay")
                    overlay.signals.hide_eco_mode_signal.emit()
                
                # Register callbacks with battery monitor
                battery_monitor.add_on_battery_callback(on_battery_mode_enabled)
                battery_monitor.add_on_ac_callback(on_battery_mode_disabled)
                logger.info("✓ Battery monitor connected to overlay eco mode indicator")
                
                # Show eco mode indicator if currently on battery
                if battery_monitor.is_on_battery():
                    overlay.signals.show_eco_mode_signal.emit()
        except Exception as e:
            logger.warning(f"Failed to connect battery monitor to overlay: {e}")

    # Wait for app closure using qasync
    close_future = asyncio.Future()

    async def _shutdown_async():
        """
        Best-effort shutdown to avoid QThread aborts.
        TICKET 1 (P0): Request global shutdown before cleanup.
        """
        logger.info("UI shutdown: stopping workers and background services...")
        
        # TICKET 1 (P0): Request global shutdown FIRST to prevent any new OS actions
        from janus.runtime.shutdown import request_shutdown
        request_shutdown("UI window closed")

        # 0) Ensure we don't restart recording during shutdown
        try:
            listening_state.stop_event.set()
            listening_state.active = False
            overlay.mic_enabled = False
        except Exception as e:
            logger.debug(f"UI shutdown: listening state set error: {e}")

        # 1) Stop UI workers (QThreads)
        try:
            stop_all_workers()
        except Exception as e:
            logger.debug(f"UI shutdown: stop_all_workers error: {e}")

        # 2) Stop STT listening (may have background threads)
        try:
            stt.stop_listening()
        except Exception as e:
            logger.debug(f"UI shutdown: stt.stop_listening error: {e}")
        
        # Close the recorder stream properly
        try:
            if hasattr(stt, 'recorder') and stt.recorder:
                stt.recorder.close()
                logger.debug("UI shutdown: recorder closed")
        except Exception as e:
            logger.debug(f"UI shutdown: recorder.close error: {e}")

        # 3) Stop wake word detector if running
        nonlocal wake_word_detector
        if wake_word_detector:
            try:
                wake_word_detector.stop()
            except Exception as e:
                logger.debug(f"UI shutdown: wake_word_detector.stop error: {e}")
            wake_word_detector = None

        # 4) Stop pipeline monitors/schedulers
        try:
            from janus.app.initialization import cleanup_pipeline
            cleanup_pipeline(pipeline)
        except Exception as e:
            logger.debug(f"UI shutdown: cleanup_pipeline error: {e}")

        # 5) Stop keyboard shortcuts hook
        try:
            shortcuts.stop()
        except Exception as e:
            logger.debug(f"UI shutdown: shortcuts.stop error: {e}")

        # 6) Final assurance: log any QThreads still running
        try:
            from PySide6.QtCore import QThread

            app_threads = [t for t in QThread.currentThread().children() if isinstance(t, QThread)]
            if app_threads:
                logger.debug(f"UI shutdown: QThread children still present: {len(app_threads)}")
            if listening_state.recording_worker:
                logger.debug(
                    f"UI shutdown: recording_worker running={listening_state.recording_worker.isRunning()}"
                )
            if listening_state.command_worker:
                logger.debug(
                    f"UI shutdown: command_worker running={listening_state.command_worker.isRunning()}"
                )
        except Exception as e:
            logger.debug(f"UI shutdown: thread introspection error: {e}")

        logger.info("UI shutdown: complete")

    def on_about_to_quit():
        logger.info("Application is about to quit...")
        # Run shutdown synchronously *now* to ensure threads are joined
        # before Qt starts destroying QObjects.
        try:
            if listening_state.event_loop:
                fut = asyncio.run_coroutine_threadsafe(_shutdown_async(), listening_state.event_loop)
                fut.result(timeout=10)
            else:
                asyncio.run(_shutdown_async())
        except Exception as e:
            logger.debug(f"UI shutdown: error: {e}")

        if not close_future.done():
            close_future.set_result(0)

    app.aboutToQuit.connect(on_about_to_quit)

    print("✓ Overlay window created and displayed")

    # Wait indefinitely for app to close
    await close_future
    
    # Cleanup is handled by aboutToQuit shutdown hook
    return 0
