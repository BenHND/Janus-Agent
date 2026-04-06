"""Application initialization and setup"""
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


def check_database_migrations(db_path: str) -> bool:
    """
    Check database migration status and apply if needed.
    
    TICKET-DB-001: Ensures database schema is up-to-date before app starts.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        True if migrations are successful or not needed, False if migration failed
    """
    try:
        from janus.runtime.core.db_migrations import MigrationManager
        
        # Get migration info
        manager = MigrationManager(db_path)
        info = manager.get_migration_info()
        
        if info["up_to_date"]:
            logger.info(f"✓ Database schema is up-to-date (v{info['current_version']})")
            return True
        
        if info["migrations_needed"] > 0:
            logger.info(
                f"Database migration required: v{info['current_version']} -> v{info['latest_version']}"
            )
            logger.info(f"Pending migrations: {info['pending_migrations']}")
            
            # Apply migrations
            success = manager.apply_migrations()
            
            if success:
                logger.info("✓ Database migrations completed successfully")
                return True
            else:
                logger.error("✗ Database migration failed")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Database migration check failed: {e}")
        return False


def run_startup_cleanup(settings) -> bool:
    """
    Run data cleanup at application startup (TICKET-DATA-001).
    
    Automatically purges old data to prevent disk saturation.
    Cleanup is run if auto_cleanup_on_startup is enabled in settings.
    
    Args:
        settings: Application settings with data_retention configuration
        
    Returns:
        True if cleanup succeeded or was skipped, False if it failed
    """
    try:
        # Check if auto cleanup is enabled
        if not settings.data_retention.auto_cleanup_on_startup:
            logger.info("Automatic cleanup is disabled in config")
            return True
        
        from janus.utils.data_cleanup import DataCleanupManager
        
        cleanup_manager = DataCleanupManager(settings)
        
        # Check if urgent cleanup needed
        if cleanup_manager.check_disk_space():
            logger.warning("⚠️  Disk space critical - running emergency cleanup")
        
        # Run cleanup
        logger.info("Running startup data cleanup...")
        stats = cleanup_manager.run_full_cleanup()
        
        # Log results with summary
        total_deleted = 0
        for component, component_stats in stats.items():
            if isinstance(component_stats, dict):
                for value in component_stats.values():
                    if isinstance(value, int):
                        total_deleted += value
        
        logger.info(f"✓ Startup cleanup completed: {total_deleted} items deleted")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Startup cleanup failed: {e}")
        logger.warning(
            "Data cleanup failure - disk space may not be managed properly. "
            "Manual cleanup may be required to prevent disk saturation."
        )
        # Don't fail application startup if cleanup fails, but make it very visible
        return False


def check_optional_dependencies() -> Dict[str, Dict[str, Any]]:
    """
    Check for optional dependencies and report their status at startup.
    
    This function centralizes the verification of optional dependencies that
    enable specific features. When a dependency is missing, it provides clear
    warnings to the user about which features will be disabled.
    
    Returns:
        Dict mapping feature names to their status information:
        - 'available': bool - whether the dependency is available
        - 'dependencies': List[str] - list of missing dependencies
        - 'impact': str - description of what's disabled without this dependency
        - 'install_command': str - command to install missing dependencies
    """
    status = {}
    
    # Check sentence-transformers and numpy for embedding-based features
    embeddings_available = True
    missing_embeddings = []
    try:
        import sentence_transformers
    except ImportError:
        embeddings_available = False
        missing_embeddings.append("sentence-transformers")
    
    try:
        import numpy
    except ImportError:
        embeddings_available = False
        missing_embeddings.append("numpy")
    
    status["embeddings"] = {
        "available": embeddings_available,
        "dependencies": missing_embeddings,
        "impact": "Semantic Router will use keyword-based fallback instead of embeddings",
        "install_command": "pip install sentence-transformers numpy"
    }
    
    # Check chromadb for semantic memory
    chromadb_available = True
    missing_chromadb = []
    try:
        import chromadb
    except ImportError:
        chromadb_available = False
        missing_chromadb.append("chromadb")
    
    # ChromaDB also requires embeddings dependencies
    if not embeddings_available:
        chromadb_available = False
        missing_chromadb.extend(missing_embeddings)
    
    status["semantic_memory"] = {
        "available": chromadb_available,
        "dependencies": list(set(missing_chromadb)),  # Remove duplicates
        "impact": "Long-term semantic memory and RAG features are DISABLED",
        "install_command": "pip install chromadb sentence-transformers"
    }
    
    # Check resemblyzer for speaker verification
    speaker_verification_available = True
    missing_speaker = []
    try:
        import resemblyzer
    except ImportError:
        speaker_verification_available = False
        missing_speaker.append("resemblyzer")
    
    status["speaker_verification"] = {
        "available": speaker_verification_available,
        "dependencies": missing_speaker,
        "impact": "Voice fingerprinting/speaker verification is DISABLED",
        "install_command": "pip install resemblyzer"
    }
    
    # Check torch for AI/Vision features
    torch_available = True
    missing_torch = []
    try:
        import torch
    except ImportError:
        torch_available = False
        missing_torch.append("torch")
    
    status["pytorch"] = {
        "available": torch_available,
        "dependencies": missing_torch,
        "impact": "AI Vision features (BLIP-2, CLIP, Florence-2) may be limited or disabled",
        "install_command": "pip install torch"
    }
    
    # Check transformers for Vision AI
    transformers_available = True
    missing_transformers = []
    try:
        import transformers
    except ImportError:
        transformers_available = False
        missing_transformers.append("transformers")
    
    status["transformers"] = {
        "available": transformers_available,
        "dependencies": missing_transformers,
        "impact": "Vision AI models (Florence-2 in OmniParser) are DISABLED",
        "install_command": "pip install transformers"
    }
    
    # Check native OCR availability (TICKET-CLEANUP-VISION: Removed pytesseract/easyocr)
    # Native OCR is built-in for all platforms (Apple Vision, Windows OCR, RapidOCR)
    ocr_available = True  # Native OCR is always available
    
    status["ocr"] = {
        "available": True,
        "dependencies": [],
        "impact": "",
        "install_command": ""
    }
    
    # Check faster-whisper for optimized STT
    faster_whisper_available = True
    missing_faster_whisper = []
    try:
        import faster_whisper
    except ImportError:
        faster_whisper_available = False
        missing_faster_whisper.append("faster-whisper")
    
    status["faster_whisper"] = {
        "available": faster_whisper_available,
        "dependencies": missing_faster_whisper,
        "impact": "Optimized Whisper (4x faster) is not available, using standard Whisper",
        "install_command": "pip install faster-whisper"
    }
    
    # Check openwakeword for wake word detection
    wakeword_available = True
    missing_wakeword = []
    try:
        import openwakeword
    except ImportError:
        wakeword_available = False
        missing_wakeword.append("openwakeword")
    
    status["wake_word"] = {
        "available": wakeword_available,
        "dependencies": missing_wakeword,
        "impact": "Wake word detection ('Hey Janus') is DISABLED",
        "install_command": "pip install openwakeword"
    }
    
    return status


def display_dependency_warnings(dependency_status: Dict[str, Dict[str, Any]]) -> None:
    """
    Display clear warnings for missing optional dependencies.
    
    This provides user-friendly feedback about which features are disabled
    and how to enable them.
    
    Args:
        dependency_status: Status dict from check_optional_dependencies()
    """
    missing_features = []
    
    for feature_name, status_info in dependency_status.items():
        if not status_info["available"] and status_info["dependencies"]:
            missing_features.append((feature_name, status_info))
    
    if missing_features:
        print("\n" + "=" * 70)
        print("⚠️  OPTIONAL DEPENDENCIES MISSING")
        print("=" * 70)
        print("\nSome features are running in degraded mode due to missing dependencies:\n")
        
        for feature_name, status_info in missing_features:
            print(f"❌ {feature_name.upper().replace('_', ' ')}")
            print(f"   Missing: {', '.join(status_info['dependencies'])}")
            print(f"   Impact: {status_info['impact']}")
            if status_info['install_command']:
                print(f"   Install: {status_info['install_command']}")
            print()
        
        print("=" * 70)
        print("ℹ️  To install ALL optional dependencies, run:")
        print("   ./install.sh")
        print("   OR")
        print("   pip install -r requirements.txt -r requirements-llm.txt -r requirements-vision.txt")
        print("=" * 70 + "\n")
        
        # Log warnings
        logger.warning(f"Running with {len(missing_features)} missing optional dependencies")
        for feature_name, status_info in missing_features:
            logger.warning(
                f"{feature_name}: Missing {status_info['dependencies']} - {status_info['impact']}"
            )
    else:
        logger.info("✓ All optional dependencies are available")


def initialize_stt(settings, llm_client=None):
    """Initialize Speech-to-Text engine"""
    from janus.io.stt.whisper_stt import WhisperSTT

    logger.info("Loading Speech-to-Text engine...")

    enable_logging = getattr(settings, "audio_logging", {}).get("enable_logging", False)
    log_dir = getattr(settings, "audio_logging", {}).get("log_dir", "audio_logs")

    return WhisperSTT(
        model_size=settings.whisper.model_size,
        language=settings.language.default,
        enable_context_buffer=settings.whisper.enable_context_buffer,
        enable_semantic_correction=settings.features.enable_semantic_correction,
        semantic_correction_model_path=settings.whisper.semantic_correction_model_path,
        natural_reformatter_model_path=settings.whisper.natural_reformatter_model_path,
        enable_corrections=settings.whisper.enable_corrections,
        enable_normalization=True,
        enable_logging=enable_logging,
        log_dir=log_dir,
        llm_service=llm_client,
        use_faster_whisper=settings.whisper.use_faster_whisper,
        enable_vad_filter=settings.audio.enable_vad_filter,
        vad_min_silence_duration_ms=settings.audio.vad_min_silence_duration_ms,
        vad_speech_pad_ms=settings.audio.vad_speech_pad_ms,
        enable_speaker_verification=settings.speaker_verification.enabled,
        speaker_embedding_path=settings.speaker_verification.embedding_path,
        speaker_similarity_threshold=settings.speaker_verification.similarity_threshold,
    )


def initialize_tts(settings):
    """Initialize Text-to-Speech engine if enabled"""
    if not settings.tts.enable_tts:
        logger.info("Text-to-Speech is disabled in settings")
        print("ℹ Text-to-Speech is disabled")
        return None

    try:
        from janus.io.tts import PiperNeuralTTSAdapter

        tts = PiperNeuralTTSAdapter(
            model_path=settings.tts.piper_model_path or None,
            rate=settings.tts.rate,
            volume=settings.tts.volume,
            lang=settings.tts.lang,
        )
        logger.info("✓ Text-to-Speech enabled (Piper)")
        print("✓ Text-to-Speech enabled")
        return tts
    except Exception as e:
        logger.warning(f"Failed to initialize TTS: {e}")
        print(f"✗ Text-to-Speech initialization failed: {e}")
        return None


async def speak_feedback(tts, message: str):
    """Speak a feedback message if TTS is enabled"""
    if tts:
        try:
            await tts.speak(message)
        except Exception as e:
            logger.warning(f"TTS error: {e}")


def initialize_i18n(settings):
    """Initialize i18n with language from settings"""
    from janus.i18n import set_language
    
    language = settings.language.default
    logger.info(f"Setting UI language to: {language}")
    set_language(language)


def cleanup_pipeline(pipeline):
    """
    Cleanup pipeline resources - TICKET 1 (P0)
    
    Stops all background threads and services to ensure clean shutdown:
    - Task scheduler thread
    - Battery monitor thread
    - Vision monitor thread
    - STT listening/recording threads
    - Wake word detector
    - Command worker loops
    
    Args:
        pipeline: JanusPipeline instance to cleanup
    """
    logger.info("Cleaning up pipeline resources...")
    
    # 1. Stop vision monitor
    try:
        pipeline.stop_monitor()
    except Exception as e:
        logger.debug(f"Error stopping vision monitor: {e}")
    
    # 2. Stop lifecycle services (scheduler, battery monitor)
    try:
        if hasattr(pipeline, 'lifecycle_service'):
            # Stop task scheduler
            try:
                pipeline.lifecycle_service.stop_task_scheduler()
            except Exception as e:
                logger.debug(f"Error stopping task scheduler: {e}")
            
            # Stop battery monitor
            try:
                pipeline.lifecycle_service.stop_battery_monitor()
            except Exception as e:
                logger.debug(f"Error stopping battery monitor: {e}")
    except Exception as e:
        logger.debug(f"Error accessing lifecycle service: {e}")
    
    # 3. Stop STT service (listening threads, mic threads)
    try:
        if hasattr(pipeline, 'stt_service') and pipeline.stt_service:
            if hasattr(pipeline.stt_service, 'stop_listening'):
                pipeline.stt_service.stop_listening()
            if hasattr(pipeline.stt_service, 'cleanup'):
                pipeline.stt_service.cleanup()
    except Exception as e:
        logger.debug(f"Error stopping STT service: {e}")
    
    # 4. General pipeline cleanup (delegates to lifecycle service)
    try:
        if hasattr(pipeline, 'cleanup'):
            pipeline.cleanup()
    except Exception as e:
        logger.debug(f"Error in pipeline.cleanup(): {e}")

    # 5. Cleanup multiprocessing children (if any)
    try:
        import multiprocessing
        multiprocessing.active_children()
    except Exception as e:
        logger.debug(f"Multiprocessing cleanup error: {e}")

    logger.info("Cleanup complete")


async def warmup_agents() -> Dict[str, bool]:
    """
    Eagerly initialize all agents at application startup.
    
    TICKET-336: Pre-load agents to reduce latency during command execution.
    This should be called early in the application startup sequence.
    
    Returns:
        Dict mapping module names to initialization success status
    """
    from janus.runtime.core.agent_registry import get_global_agent_registry
    from janus.runtime.core.agent_setup import setup_agent_registry
    
    logger.info("🚀 Starting agent warmup (TICKET-336 optimization)...")
    
    # Ensure registry is set up with V3 agents
    registry = setup_agent_registry(use_v3_agents=True)
    
    # Warm up all registered agents
    results = await registry.warmup()
    
    return results


def initialize_crash_reporting(config_path: Optional[str] = None) -> bool:
    """
    Initialize crash reporting and error telemetry
    
    TICKET-OPS-002: Sets up Sentry crash reporting with opt-in consent
    - Prompts user for consent on first launch
    - Initializes Sentry SDK if consent is granted
    - Installs global exception handlers
    - Sanitizes all crash reports to remove sensitive data
    
    Args:
        config_path: Path to config.ini file
        
    Returns:
        True if crash reporting is enabled, False otherwise
    """
    try:
        from janus.telemetry import (
            ConsentManager,
            prompt_for_consent,
            initialize_crash_reporting as init_sentry,
            sanitize_event,
        )
        
        # Check if user has consented
        consent_manager = ConsentManager(config_path)
        
        if not consent_manager.has_answered():
            # First launch - prompt for consent
            logger.info("First launch detected - prompting for crash reporting consent")
            consent = prompt_for_consent(config_path)
        else:
            consent = consent_manager.get_consent()
        
        if not consent:
            logger.info("Crash reporting disabled by user preference")
            return False
        
        # Get Sentry DSN from environment variable
        # Users should set SENTRY_DSN in their environment or .env file
        sentry_dsn = os.environ.get("SENTRY_DSN")
        
        if not sentry_dsn:
            logger.info(
                "SENTRY_DSN environment variable not set. "
                "Crash reporting is enabled but will not send reports. "
                "To enable remote crash reporting, set SENTRY_DSN in your .env file. "
                "See docs/developer/TICKET-OPS-002-CRASH-REPORTING.md for details."
            )
            # Return True because consent is granted, even though no DSN is configured
            # This allows local logging and potential future configuration without re-prompting
            return True
        
        # Determine environment
        environment = os.environ.get("SENTRY_ENVIRONMENT", "production")
        
        # Initialize crash reporting with sanitization
        reporter = init_sentry(
            enabled=True,
            dsn=sentry_dsn,
            environment=environment,
            sanitize_callback=sanitize_event,
        )
        
        if reporter:
            logger.info("✓ Crash reporting initialized successfully")
            return True
        else:
            logger.warning("✗ Failed to initialize crash reporting")
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize crash reporting: {e}")
        return False


def initialize_voice_enrollment(settings, recorder) -> bool:
    """
    Initialize voice enrollment if speaker verification is enabled.
    
    TICKET-STT-002: Enroll user voice for speaker verification if not already enrolled.
    
    Args:
        settings: Application settings
        recorder: WhisperRecorder instance for recording audio samples
        
    Returns:
        True if enrollment is completed or not needed, False if enrollment failed
    """
    if not settings.speaker_verification.enabled:
        logger.info("Speaker verification is disabled - skipping enrollment")
        return True
    
    try:
        from janus.io.stt.speaker_verifier import SpeakerVerifier
        from janus.io.stt.voice_enrollment import VoiceEnrollmentManager
        
        # Check if user is already enrolled
        embedding_path = settings.speaker_verification.embedding_path
        if Path(embedding_path).exists():
            logger.info(f"✓ User voice profile already exists at {embedding_path}")
            return True
        
        # Initialize verifier
        verifier = SpeakerVerifier(
            embedding_path=embedding_path,
            similarity_threshold=settings.speaker_verification.similarity_threshold,
            sample_rate=settings.audio.sample_rate,
        )
        
        if not verifier.is_available():
            logger.warning("Speaker verification not available - resemblyzer not installed")
            return False
        
        # Initialize enrollment manager
        enrollment_manager = VoiceEnrollmentManager(
            verifier=verifier,
            recorder=recorder,
            embedding_path=embedding_path,
        )
        
        # Prompt user for enrollment
        print("\n" + "="*60)
        print("🎤 VOICE ENROLLMENT REQUIRED (TICKET-STT-002)")
        print("="*60)
        print("Speaker verification is enabled to prevent unauthorized access.")
        print("Please record 3 voice samples to create your voice profile.")
        print()
        print("You will be asked to read the following phrases:")
        for i, prompt in enumerate(enrollment_manager.get_enrollment_prompts(), 1):
            print(f"  {i}. {prompt}")
        print()
        
        response = input("Press Enter to start enrollment or 'skip' to continue without enrollment: ")
        if response.lower() == 'skip':
            logger.info("User skipped voice enrollment")
            return True
        
        # Run enrollment
        def progress_callback(step, total, message):
            print(f"[{step}/{total}] {message}")
        
        success, message = enrollment_manager.enroll_user_interactive(
            on_progress=progress_callback
        )
        
        if success:
            print(f"\n✓ {message}")
            print(f"Voice profile saved to: {embedding_path}")
            return True
        else:
            print(f"\n✗ {message}")
            logger.error(f"Voice enrollment failed: {message}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize voice enrollment: {e}")
        return False
