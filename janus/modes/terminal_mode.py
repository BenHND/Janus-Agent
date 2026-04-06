"""Terminal mode - Interactive command-line interface"""
import asyncio
import logging
import threading

from janus.i18n import t, tts_done, tts_error
from janus.logging.colored_console import (
    Colors,
    print_action,
    print_banner,
    print_command,
    print_error,
    print_listening,
    print_section,
    print_separator,
    print_success,
    print_thinking,
    print_warning,
    setup_colored_logging,
)

logger = logging.getLogger(__name__)


async def run_terminal_mode(pipeline, settings, stt, tts):
    """Run in terminal mode (no GUI)"""
    from janus.app.initialization import speak_feedback
    
    # Setup colored logging
    setup_colored_logging(logging.INFO)
    
    logger.info("Starting terminal mode...")
    
    print_banner(
        t("terminal.banner_title"),
        t("terminal.banner_subtitle", session_id=pipeline.session_id[:8]),
        Colors.BRIGHT_MAGENTA
    )
    
    print_section(t("terminal.commands_section"), Colors.BRIGHT_BLUE)
    commands_list = t("terminal.commands_list")
    for cmd in commands_list:
        print(f"{Colors.DIM}  • {cmd}{Colors.RESET}")
    
    print_separator()
    
    # TICKET-P3-02: Wake word detection support
    wake_word_detector = None
    wake_word_event = None
    
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
                wake_word_event = threading.Event()
                
                def on_wake_word_detected():
                    """Callback when wake word is detected"""
                    logger.info("Wake word detected!")
                    wake_word_event.set()
                
                wake_word_detector.start(on_wake_word_detected)
                print(f"\n{Colors.BRIGHT_GREEN}🎤 Wake word detection enabled{Colors.RESET}")
                print(f"{Colors.DIM}   Say 'Hey Janus' to activate voice command{Colors.RESET}\n")
                logger.info("Wake word detector started")
        except Exception as e:
            logger.warning(f"Failed to initialize wake word detector: {e}")
            print(f"\n{Colors.BRIGHT_YELLOW}⚠️  Wake word detection disabled: {e}{Colors.RESET}\n")
    
    try:
        while True:
            # TICKET-P3-02: Wait for wake word if enabled
            if wake_word_detector and wake_word_event:
                print(f"{Colors.DIM}💤 Listening for wake word...{Colors.RESET}")
                
                # Wait for wake word detection
                while not wake_word_event.is_set():
                    await asyncio.sleep(0.1)
                
                # Wake word detected - clear event for next iteration
                wake_word_event.clear()
                
                # Visual/audio feedback
                print(f"\n{Colors.BRIGHT_GREEN}✓ Wake word detected!{Colors.RESET}")
                if tts:
                    await speak_feedback(tts, "Oui?")  # "Yes?" in French
            
            print_listening()
            
            # Record and transcribe
            text = await stt.listen_and_transcribe_async(
                language=settings.language.default,
                max_duration=15,
            )
            
            if not text or not text.strip():
                print_warning(t("ui.no_speech"))
                continue
            
            print_command(text)
            print_thinking()
            
            # Process command
            result = await pipeline.process_command_async(text, conversation_mode=False)
            
            if result.success:
                print_success(t("ui.command_success"))
                if result.action_results:
                    for action_result in result.action_results:
                        msg = action_result.message or action_result.action_type
                        print_action(msg)
                if tts:
                    await speak_feedback(tts, tts_done())
            else:
                error_msg = result.error_message or "Unknown error"
                print_error(f"{t('ui.command_failed')}: {error_msg}")
                if tts:
                    await speak_feedback(tts, tts_error())
            
            print_separator()
                    
    except KeyboardInterrupt:
        print(f"\n\n{Colors.BRIGHT_YELLOW}👋 {t('ui.shutting_down')}{Colors.RESET}")
        logger.info("Terminal mode interrupted by user")
        return 0
    except Exception as e:
        logger.exception(f"Terminal mode error: {e}")
        print_error(t("errors.fatal_error", error=str(e)))
        return 1
    finally:
        # Cleanup wake word detector
        if wake_word_detector:
            try:
                wake_word_detector.stop()
                logger.info("Wake word detector stopped")
            except Exception as e:
                logger.debug(f"Error stopping wake word detector: {e}")

