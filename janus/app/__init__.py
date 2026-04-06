"""Main Janus application orchestrator"""
import asyncio
import logging
import sys

from janus import __version__
from janus.cli.commands import (
    run_llm_wizard,
    run_vision_wizard,
    show_history_viewer,
    show_logs_viewer,
)
from janus.runtime.core import MemoryEngine, Settings, JanusPipeline
from janus.i18n import t, tts_welcome, tts_loading_init, tts_loading_systems
from janus.logging.colored_console import (
    Colors,
    print_banner,
    print_config_item,
    print_info,
    print_section,
    print_success,
    setup_colored_logging,
)

from .initialization import (
    cleanup_pipeline,
    initialize_i18n,
    initialize_stt,
    initialize_tts,
    speak_feedback,
    initialize_crash_reporting,
    check_optional_dependencies,
    display_dependency_warnings,
    run_startup_cleanup,
)

logger = logging.getLogger(__name__)


class JanusApplication:
    """Main Janus application orchestrator"""

    def __init__(self, args):
        """Initialize application with parsed arguments"""
        self.args = args
        self.settings = None
        self.memory = None
        self.pipeline = None
        self.stt = None
        self.tts = None

    def run(self):
        """Main entry point - route to appropriate mode"""
        # Handle wizards and viewers first
        if self.args.setup_vision:
            return run_vision_wizard()
        if self.args.setup_llm:
            return run_llm_wizard()
        if self.args.logs:
            return show_logs_viewer()
        if self.args.history:
            return show_history_viewer()
        # TICKET-P1-04: Handle workflow recovery
        if self.args.recover:
            print("❌ Workflow recovery is no longer supported in this version.")
            print("   Please restart the workflow manually.")
            return 1

        # Run main pipeline
        if self.args.no_ui:
            return asyncio.run(self._run_async())
        else:
            return self._run_with_qt()

    def _run_with_qt(self):
        """Run with Qt event loop (for UI mode)"""
        # Setup colored logging AVANT Qt pour voir les logs de démarrage
        setup_colored_logging(logging.DEBUG if self.args.debug else logging.INFO)
        
        try:
            from PySide6.QtWidgets import QApplication
            import qasync

            app = QApplication(sys.argv)
            loop = qasync.QEventLoop(app)
            asyncio.set_event_loop(loop)

            with loop:
                return loop.run_until_complete(self._run_async())
        except ImportError as e:
            logger.warning(f"UI dependencies missing ({e}), falling back to terminal mode")
            print(f"\n{Colors.BRIGHT_YELLOW}⚠️  UI dependencies missing: {e}{Colors.RESET}")
            print(f"{Colors.DIM}   Running in terminal mode. Install 'qasync' and 'PySide6'.{Colors.RESET}\n")
            self.args.no_ui = True
            return asyncio.run(self._run_async())

    async def _run_async(self):
        """Main async pipeline"""
        # Setup colored logging (déjà fait en mode UI, refait si no-ui)
        if self.args.no_ui:
            setup_colored_logging(logging.DEBUG if self.args.debug else logging.INFO)
        
        # Set debug level if requested
        if self.args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.setLevel(logging.DEBUG)

        logger.info(f"Initializing Janus v{__version__}...")

        # Check optional dependencies and display warnings
        dependency_status = check_optional_dependencies()
        display_dependency_warnings(dependency_status)

        # Initialize settings
        cli_overrides = self._build_cli_overrides()
        config_path = getattr(self.args, "config", None)
        self.settings = Settings(config_path=config_path, **cli_overrides)
        self.memory = MemoryEngine(self.settings.database)

        # TICKET-OPS-002: Initialize crash reporting early (after settings but before other components)
        initialize_crash_reporting(config_path)

        # Initialize i18n with language from settings
        initialize_i18n(self.settings)
        
        # TICKET-DATA-001: Run startup data cleanup
        run_startup_cleanup(self.settings)

        # Handle get session
        if self.args.get_session:
            return self._handle_get_session()

        # Self-test mode: validate service wiring and exit
        if getattr(self.args, "self_test", False):
            return await self._run_self_test()

        # Create pipeline
        self.pipeline = JanusPipeline(
            self.settings,
            self.memory,
            session_id=self.args.session_id,
            enable_llm_reasoning=self.settings.features.enable_llm_reasoning,
            enable_vision=self.settings.features.enable_vision,
            enable_learning=self.settings.features.enable_learning,
            enable_tts=self.settings.tts.enable_tts,
        )

        try:
            self.pipeline.start_monitor()
        except Exception as e:
            logger.warning(f"Failed to start async vision monitor: {e}")

        self._log_configuration()

        # Initialize STT/TTS early for loading message
        llm_client = self._get_llm_client() if self.settings.features.enable_semantic_correction else None
        self.stt = initialize_stt(self.settings, llm_client)
        self.tts = initialize_tts(self.settings)

        # Route to appropriate mode with loading flow
        if self.args.once:
            from janus.modes.once_mode import run_once_mode
            return await run_once_mode(self.pipeline, self.args.once)
        elif self.args.no_ui:
            from janus.modes.terminal_mode import run_terminal_mode
            # For terminal mode, preload models then run
            await self._preload_all_models()
            # Welcome message after loading (i18n) - non-bloquant
            if self.tts:
                speak_feedback(self.tts, tts_welcome())  # Fire-and-forget, pas de await
            return await run_terminal_mode(self.pipeline, self.settings, self.stt, self.tts)
        else:
            from janus.modes.ui_mode import run_ui_mode
            # For UI mode, pass control to ui_mode which will handle loading flow
            return await run_ui_mode(self.pipeline, self.settings, self.stt, self.tts, self._preload_all_models)

    async def _run_self_test(self) -> int:
        """Run basic service wiring checks and exit."""
        strict = bool(getattr(self.args, "self_test_strict", False))

        dependency_status = check_optional_dependencies()
        display_dependency_warnings(dependency_status)

        if self.settings is None:
            cli_overrides = self._build_cli_overrides()
            config_path = getattr(self.args, "config", None)
            self.settings = Settings(config_path=config_path, **cli_overrides)
            initialize_i18n(self.settings)

        if self.memory is None:
            self.memory = MemoryEngine(self.settings.database)

        failures = []

        # Pipeline + core services
        try:
            self.pipeline = JanusPipeline(
                self.settings,
                self.memory,
                session_id=self.args.session_id,
                enable_llm_reasoning=self.settings.features.enable_llm_reasoning,
                enable_vision=self.settings.features.enable_vision,
                enable_learning=self.settings.features.enable_learning,
                enable_tts=self.settings.tts.enable_tts,
            )
        except Exception as e:
            failures.append(f"Pipeline init failed: {e}")
            self.pipeline = None

        # Memory sanity
        try:
            session_id = (self.pipeline.session_id if self.pipeline else None) or self.args.session_id or self.memory.create_session()
            _ = self.memory.get_command_history(session_id, limit=1)
        except Exception as e:
            failures.append(f"MemoryEngine check failed: {e}")

        # Clipboard wiring (optional)
        if self.pipeline:
            try:
                clipboard = getattr(self.pipeline, "clipboard_manager", None)
                if clipboard is None:
                    raise RuntimeError("clipboard_manager is None")
                # ClipboardManager API: paste() (sync) or get_text() (async)
                if hasattr(clipboard, "paste"):
                    _ = clipboard.paste()
                elif hasattr(clipboard, "get_text"):
                    _ = await clipboard.get_text()
                else:
                    raise RuntimeError("ClipboardManager has no paste()/get_text()")
            except Exception as e:
                msg = f"Clipboard check failed: {e}"
                if strict:
                    failures.append(msg)
                else:
                    logger.warning(msg)

        # LLM warmup (optional but recommended if enabled)
        if self.pipeline and self.settings.features.enable_llm_reasoning:
            try:
                await self.pipeline.warmup_systems()
            except Exception as e:
                msg = f"LLM warmup failed: {e}"
                if strict:
                    failures.append(msg)
                else:
                    logger.warning(msg)

        # Vision capture (optional)
        if self.pipeline and self.settings.features.enable_vision:
            try:
                vs = getattr(self.pipeline, "vision_service", None)
                runner = getattr(vs, "vision_runner", None) if vs else None
                screenshot_engine = getattr(runner, "screenshot_engine", None) if runner else None
                if screenshot_engine and hasattr(screenshot_engine, "capture_screen"):
                    _ = screenshot_engine.capture_screen()
                else:
                    raise RuntimeError("Vision runner screenshot engine unavailable")
            except Exception as e:
                msg = f"Vision capture failed: {e}"
                if strict:
                    failures.append(msg)
                else:
                    logger.warning(msg)

        # TTS init (optional)
        try:
            self.tts = initialize_tts(self.settings)
        except Exception as e:
            msg = f"TTS init failed: {e}"
            if strict:
                failures.append(msg)
            else:
                logger.warning(msg)

        if failures:
            print("\nSELF-TEST FAILURES:")
            for f in failures:
                print(f"- {f}")
            return 1

        print("\nSELF-TEST OK")
        return 0

    def _build_cli_overrides(self):
        """Build CLI overrides dict"""
        cli_overrides = {}
        if self.args.model is not None:
            cli_overrides["model_size"] = self.args.model
        if self.args.lang is not None:
            cli_overrides["language"] = self.args.lang
        if self.args.enable_tts:
            cli_overrides["tts_override"] = True
        elif self.args.disable_tts:
            cli_overrides["tts_override"] = False
        return cli_overrides

    def _handle_get_session(self):
        """Handle --get-session command"""
        import json

        session_id = self.args.session_id or self.memory.create_session()
        session_data = self.memory.get_session(session_id)
        history = self.memory.get_command_history(session_id, limit=10)

        print_section("Session Information")
        print_config_item("Session ID", session_id)
        if session_data:
            print(f"\n{Colors.DIM}{json.dumps(session_data, indent=2, default=str)}{Colors.RESET}")
        
        print_section("Recent Commands")
        for cmd in history:
            print(f"{Colors.DIM}  • {cmd.get('raw_command')} ({cmd.get('timestamp')}){Colors.RESET}")
        return 0

    async def _preload_all_models(self, progress_callback=None):
        """
        Preload all models synchronously during app initialization.
        
        Args:
            progress_callback: Optional async function(message) to report progress (non-blocking)
        """
        logger.info("Starting synchronous model preloading...")
        
        # Message 1: Initialisation (non-bloquant)
        if progress_callback:
            progress_callback(tts_loading_init())  # Fire-and-forget (pas de await)
        
        # Message 2: Modules cognitifs (non-bloquant, pendant le chargement)
        if progress_callback:
            progress_callback(tts_loading_systems())  # Fire-and-forget (pas de await)
        
        # LLM model preloading - USE warmup_systems() to FORCE model into VRAM
        if self.settings.features.enable_llm_reasoning:
            try:
                logger.info("Loading LLM model into memory (this may take a few seconds)...")
                # This forces the model into VRAM by sending a dummy inference request
                await self.pipeline.warmup_systems()
                logger.info("✓ LLM model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to preload LLM model: {e}")
                logger.info("LLM model will load on-demand when first needed")
        
        # Vision models (le plus long - ~40-50 secondes)
        if self.settings.features.enable_vision:
            try:
                logger.info("Loading vision models...")
                success = await self.pipeline.preload_vision_models_async()
                if success:
                    logger.info("✓ Vision models loaded successfully")
                else:
                    logger.info("Vision models will load on-demand when first needed")
            except Exception as e:
                logger.warning(f"Failed to preload vision models: {e}")
                logger.info("Vision models will load on-demand when first needed")
        
        logger.info("Model preloading complete")

    def _log_configuration(self):
        """Log application configuration"""
        logger.info(f"Unified pipeline ready (session_id={self.pipeline.session_id})")
        logger.info(f"  - LLM reasoning: {'enabled' if self.settings.features.enable_llm_reasoning else 'disabled'}")
        logger.info(f"  - Vision features: {'enabled' if self.settings.features.enable_vision else 'disabled'}")
        logger.info(f"  - Learning: {'enabled' if self.settings.features.enable_learning else 'disabled'}")
        logger.info(f"  - TTS: {'enabled' if self.settings.tts.enable_tts else 'disabled'}")
        logger.info(f"LLM: {self.settings.llm.provider}/{self.settings.llm.model}")

        print_success(f"Janus ready! (session: {self.pipeline.session_id[:8]}...)")
        
        print_section(t("config.llm_reasoning"), Colors.BRIGHT_GREEN)
        enabled_text = t("config.enabled") if self.settings.features.enable_llm_reasoning else t("config.disabled")
        print_config_item(t("config.llm_reasoning"), self.settings.llm.provider + "/" + self.settings.llm.model, self.settings.features.enable_llm_reasoning)
        print_config_item(t("config.vision_features"), enabled_text, self.settings.features.enable_vision)
        print_config_item(t("config.learning"), enabled_text, self.settings.features.enable_learning)
        print_config_item(t("config.tts"), enabled_text, self.settings.tts.enable_tts)

    def _get_llm_client(self):
        """Get LLM client for semantic correction"""
        try:
            from janus.ai.llm.unified_client import create_unified_client_from_settings
            
            llm_client = create_unified_client_from_settings(self.settings)
            if (llm_client.available):
                logger.info(f"LLM client initialized: {self.settings.llm.provider}/{self.settings.llm.model}")
                return llm_client
        except Exception as e:
            logger.warning(f"Failed to initialize LLM client: {e}")
        return None
