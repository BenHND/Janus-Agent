"""
Unified typed settings system for Janus.

This module provides a single source of truth for all configuration,
with support for:
- Environment variables (.env file)
- Config file loading (config.ini)
- CLI overrides
- Type safety via dataclasses
- Grouped settings by component

Configuration priority: env > config.ini > defaults
"""

import configparser
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from janus.exceptions import ConfigError

# Load environment variables from .env file if present
try:
    from dotenv import load_dotenv

    load_dotenv()  # Load .env file from current directory
except ImportError:
    pass  # dotenv not installed, will only use existing environment variables

logger = logging.getLogger(__name__)


@dataclass
class WhisperSettings:
    """Whisper STT settings"""

    model_size: str = "base"
    use_faster_whisper: bool = True  # Use faster-whisper or standard Whisper
    enable_context_buffer: bool = True
    enable_corrections: bool = True
    models_dir: str = "models/whisper"  # Local models directory
    # Optional override paths for semantic correction/reformatting
    # When empty, uses the main LLM from [llm] section
    semantic_correction_model_path: str = ""
    natural_reformatter_model_path: str = ""


@dataclass
class AudioSettings:
    """Audio recording settings"""

    sample_rate: int = 16000
    chunk_duration_ms: int = 20  # Optimized for responsiveness
    silence_threshold: int = 60  # ~1.2s of silence to stop recording (at 20ms chunks)
    
    # Deprecated: vad_aggressiveness kept for backward compatibility with config files
    # but is no longer used - recording uses energy-based silence detection only
    vad_aggressiveness: int = 3
    
    # faster-whisper VAD settings
    enable_vad_filter: bool = False  # Enable/disable VAD in faster-whisper
    vad_min_silence_duration_ms: int = 500  # Min silence to split segments
    vad_speech_pad_ms: int = 200  # Padding around speech segments


@dataclass
class WakeWordSettings:
    """
    Wake Word Detection Settings (TICKET-P3-02)
    
    Professional wake word configuration for "Hey Janus"
    """
    enabled: bool = False  # Enable wake word detection
    engine: str = "openwakeword"  # Wake word engine (only openwakeword supported)
    model: str = "hey_janus"  # Model name or path to custom .onnx/.tflite file
    threshold: float = 0.5  # Detection threshold (0.0-1.0, higher = fewer false positives)
    cooldown_ms: int = 1000  # Cooldown after detection (milliseconds)


@dataclass
class SpeakerVerificationSettings:
    """
    Speaker Verification Settings (TICKET-STT-002)
    
    Voice fingerprinting to prevent unauthorized voices from triggering commands
    """
    enabled: bool = False  # Enable speaker verification
    embedding_path: str = "user_data/user_voice.npy"  # Path to user voice embedding
    similarity_threshold: float = 0.75  # Minimum cosine similarity (-1.0 to 1.0, where 1.0 = identical)


@dataclass
class LanguageSettings:
    """Language settings"""

    default: str = "fr"


@dataclass
class AutomationSettings:
    """
    Automation execution settings
    
    Note: ui_enable_vision should be kept synchronized with FeaturesSettings.enable_vision.
    It's a separate flag for backward compatibility with UIExecutor.
    """

    safety_delay: float = 0.5
    pyautogui_pause: float = 0.1
    # UIExecutor settings (Code improvement - 06)
    ui_default_timeout: float = 10.0
    ui_max_retries: int = 2
    ui_retry_delay: float = 0.5
    ui_action_delay: float = 0.3
    ui_wait_poll_interval: float = 0.5
    ui_applescript_timeout: float = 10.0
    ui_enable_vision: bool = True  # Should match features.enable_vision


@dataclass
class CalibrationSettings:
    """Calibration profile settings"""

    profile_dir: str = "calibration_profiles"


@dataclass
class ExecutionSettings:
    """
    Execution engine settings (TICKET-111, TICKET-P1-03, TICKET-AUDIT-001, ARCH-001)
    
    These settings control the behavior of the ActionCoordinator (OODA loop):
    - max_retries: Number of retries per step
    - enable_replanning: Enable LLM-based replanning on failures
    - enable_vision_recovery: Enable vision-based error recovery (TICKET-P1-03: enabled by default)
    - continue_on_validation_error: Continue executing even if validation fails
    - attempt_context_recovery: Attempt to recover context automatically
    - context_recovery_timeout: Timeout for context recovery in seconds
    
    ARCH-001 Phase 2: V3 engines removed, only ActionCoordinator (OODA) remains
    """

    max_retries: int = 1
    enable_replanning: bool = False
    enable_vision_recovery: bool = True  # TICKET-P1-03: Enabled by default with fast heuristics
    continue_on_validation_error: bool = False
    attempt_context_recovery: bool = True
    context_recovery_timeout: float = 2.0


@dataclass
class VisionSettings:
    """
    Vision AI settings
    
    Note: The main vision enable/disable is controlled by FeaturesSettings.enable_vision.
    These sub-flags control which specific vision models are loaded when vision is enabled.
    
    TICKET-302: Florence-2 only (no legacy BLIP-2/CLIP code).
    """

    models_dir: str = "models/vision"  # Local vision models directory
    # TICKET-302: Florence-2 is the only vision engine (no legacy code)
    vision_engine: str = "florence2"


@dataclass
class AsyncVisionMonitorSettings:
    """
    Async Vision Monitor settings
    
    Background screen monitoring for popups, errors, and expected elements.
    Only active when FeaturesSettings.enable_vision is True.
    """

    enable_monitor: bool = False  # Enable background monitoring
    check_interval_ms: int = 1000  # Interval between screen checks
    enable_popup_detection: bool = True  # Detect popup dialogs
    enable_error_detection: bool = True  # Detect error messages


@dataclass
class SessionSettings:
    """Session management settings"""

    state_file: str = "session_state.json"
    max_history: int = 50


@dataclass
class LLMSettings:
    """LLM provider settings"""

    provider: str = "mock"
    model: str = "gpt-4"
    fallback_providers: List[str] = field(default_factory=list)
    model_path: str = ""
    temperature: float = 0.7
    max_tokens: int = 2000
    request_timeout: int = 120  # Timeout for LLM requests (seconds) - higher for cold starts
    retry_timeout: int = 60  # Timeout for retry attempts (seconds)
    enable_cache: bool = True
    cache_ttl: int = 300
    auto_confirm_safe: bool = True
    ollama_endpoint: str = "http://localhost:11434"


@dataclass
class TTSSettings:
    """Text-to-Speech settings"""

    enable_tts: bool = True
    engine: str = "piper"
    piper_model_path: str = ""
    voice: str = ""
    rate: int = 180
    volume: float = 0.7
    lang: str = "fr-FR"
    auto_confirmations: bool = True
    verbosity: str = "compact"
    avoid_feedback_loop: bool = True


@dataclass
class DatabaseSettings:
    """Database storage settings"""

    path: str = "data/janus.db"
    enable_wal: bool = True
    journal_mode: str = "WAL"
    synchronous: str = "NORMAL"
    cache_size: int = -2000  # 2MB cache


@dataclass
class LoggingSettings:
    """Structured logging settings"""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_structured: bool = True
    log_to_database: bool = True
    log_to_console: bool = True
    log_to_file: bool = False
    log_file: str = "janus.log"


@dataclass
class RateLimitSettings:
    """
    Rate limiting settings (P2 Feature)
    
    Controls rate limits for global, per-agent, and per-provider scopes
    to prevent overload and denial of service on external providers.
    """
    
    enabled: bool = True  # Enable rate limiting
    
    # Global rate limit (applies to all actions)
    global_max_requests: int = 100  # Max requests per time window
    global_time_window_seconds: float = 60.0  # Time window in seconds
    global_burst_allowance: int = 20  # Additional burst capacity
    
    # Per-agent rate limits (can be overridden per agent)
    agent_max_requests: int = 30
    agent_time_window_seconds: float = 60.0
    agent_burst_allowance: int = 5
    
    # Provider-specific limits (email, slack, teams, crm)
    email_max_requests: int = 10
    email_time_window_seconds: float = 60.0
    slack_max_requests: int = 20
    slack_time_window_seconds: float = 60.0
    teams_max_requests: int = 20
    teams_time_window_seconds: float = 60.0
    crm_max_requests: int = 15
    crm_time_window_seconds: float = 60.0


@dataclass
class OfflineSettings:
    """
    Offline mode and queue settings (P2 Feature)
    
    Controls behavior when services are unavailable and queue management.
    """
    
    enabled: bool = True  # Enable offline mode and queueing
    queue_enabled: bool = True  # Enable action queue
    auto_process_queue: bool = True  # Auto-process queue when services are online
    max_queue_size: int = 1000  # Maximum queued actions
    default_max_retries: int = 3  # Default retry attempts
    default_expiration_hours: int = 24  # Default expiration time
    purge_completed_hours: int = 168  # Purge completed after 1 week
    check_interval_seconds: int = 60  # Check for service availability every 60s


@dataclass
class DataRetentionSettings:
    """
    Data retention and cleanup settings (TICKET-DATA-001)
    
    Controls automatic cleanup of old data to prevent disk saturation.
    All retention periods are in days (0 = unlimited, not recommended).
    """
    
    # Retention periods (days)
    memory_context_days: int = 30  # MemoryEngine context data
    memory_history_days: int = 30  # MemoryEngine history data
    semantic_vectors_days: int = 60  # ChromaDB vector store
    action_history_days: int = 90  # Action history for analytics
    workflow_states_days: int = 14  # Completed/failed workflows
    audio_logs_days: int = 7  # Audio recordings for debugging
    safe_queue_days: int = 30  # Completed queue entries
    unified_store_days: int = 30  # UnifiedStore snapshots/clipboard
    
    # Storage limits
    max_total_size_mb: int = 2000  # Max total data size (triggers emergency cleanup)
    
    # Cleanup behavior
    auto_cleanup_on_startup: bool = True  # Run cleanup at application start
    cleanup_check_interval_hours: int = 24  # Periodic cleanup interval


@dataclass
class FeaturesSettings:
    """
    Feature activation settings - single source of truth for all feature flags
    
    All features are enabled by default for production.
    Sub-features (like automation.ui_enable_vision) are controlled
    by these master flags and provide fine-grained control only when the master flag is enabled.
    
    PERF-FOUNDATION-001: Vision policy granular control
    - vision_decision_enabled: Use vision for decision-making (SOM in OODA)
    - vision_verification_enabled: Use vision for post-action verification
    - trace_screenshots_enabled: Enable screenshot tracing for debug/audit
    """

    enable_llm_reasoning: bool = True
    enable_vision: bool = True
    enable_learning: bool = True
    enable_semantic_correction: bool = True
    
    # PERF-FOUNDATION-001: Granular vision control
    vision_decision_enabled: bool = True  # Vision for decision (SOM)
    vision_verification_enabled: bool = True  # Vision for verification
    trace_screenshots_enabled: bool = False  # Debug/audit only
    
    # P2 Features
    enable_dry_run: bool = True  # Enable dry-run mode support
    enable_rollback: bool = True  # Enable rollback/compensation support
    enable_rate_limiting: bool = True  # Enable rate limiting
    enable_offline_mode: bool = True  # Enable offline mode and queueing


class Settings:
    """
    Unified settings manager for Janus.

    Loads configuration from config.ini and provides typed access
    to all settings via component-specific groups.
    """

    def __init__(self, config_path: Optional[str] = None, **cli_overrides):
        """
        Initialize settings from config file and CLI overrides.

        Args:
            config_path: Path to config.ini file (default: ./config.ini)
            **cli_overrides: CLI arguments that override config values
        """
        self.config_path = config_path or "config.ini"
        self._config = (
            configparser.RawConfigParser()
        )  # Use RawConfigParser to avoid interpolation issues

        # Load config file if it exists
        if os.path.exists(self.config_path):
            self._config.read(self.config_path)

        # Initialize settings groups
        self.whisper = self._load_whisper_settings(**cli_overrides)
        self.audio = self._load_audio_settings(**cli_overrides)
        self.wakeword = self._load_wakeword_settings(**cli_overrides)  # TICKET-P3-02
        self.speaker_verification = self._load_speaker_verification_settings(**cli_overrides)  # TICKET-STT-002
        self.language = self._load_language_settings(**cli_overrides)
        self.automation = self._load_automation_settings(**cli_overrides)
        self.calibration = self._load_calibration_settings(**cli_overrides)
        self.execution = self._load_execution_settings(**cli_overrides)  # TICKET-111: Load execution settings
        self.vision = self._load_vision_settings(**cli_overrides)
        self.async_vision_monitor = self._load_async_vision_monitor_settings(**cli_overrides)
        self.session = self._load_session_settings(**cli_overrides)
        self.llm = self._load_llm_settings(**cli_overrides)
        self.tts = self._load_tts_settings(**cli_overrides)
        self.database = self._load_database_settings(**cli_overrides)
        self.logging = self._load_logging_settings(**cli_overrides)
        self.features = self._load_features_settings(**cli_overrides)
        self.rate_limit = self._load_rate_limit_settings(**cli_overrides)  # P2: Rate limiting
        self.offline = self._load_offline_settings(**cli_overrides)  # P2: Offline mode
        self.data_retention = self._load_data_retention_settings(**cli_overrides)  # TICKET-DATA-001: Data retention

    def _get(
        self, section: str, key: str, default: any, type_cast=str, env_key: Optional[str] = None
    ):
        """
        Get config value with type casting.

        Priority: environment variable (only for whitelisted vars) > config.ini > default
        
        Environment variables are ONLY read for:
        - SPECTRA_MODELS_DIR (Whisper models directory)
        - SPECTRA_VISION_MODELS_DIR (Vision models directory)
        - OLLAMA_ENDPOINT (Ollama API endpoint)
        
        All other configuration MUST come from config.ini.

        Args:
            section: Config file section name
            key: Config file key name
            default: Default value if not found
            type_cast: Type to cast the value to (str, int, float, bool)
            env_key: Environment variable name (must be in whitelist)

        Returns:
            Configuration value with proper type
        """
        # Whitelist of environment variables that can override config.ini
        # These are allowed for deployment/packaging flexibility:
        # - SPECTRA_MODELS_DIR: Location for Whisper models (for macOS app bundles)
        # - SPECTRA_VISION_MODELS_DIR: Location for Vision AI models (for macOS app bundles)
        # - OLLAMA_ENDPOINT: Ollama server URL (for Docker/remote deployments)
        ALLOWED_ENV_VARS = {
            "SPECTRA_MODELS_DIR",
            "SPECTRA_VISION_MODELS_DIR", 
            "OLLAMA_ENDPOINT",
        }
        
        try:
            # Only check environment variables if explicitly whitelisted
            env_value = None
            if env_key and env_key in ALLOWED_ENV_VARS:
                env_value = os.environ.get(env_key)

            if env_value is not None:
                # Cast environment variable to proper type
                if type_cast == bool:
                    return env_value.lower() in ("true", "1", "yes", "on")
                elif type_cast == int:
                    return int(env_value)
                elif type_cast == float:
                    return float(env_value)
                return env_value

            # Fall back to config.ini
            if not self._config.has_section(section):
                return default
            value = self._config.get(section, key, fallback=default)

            # If value is already the correct type, return it
            if isinstance(value, type_cast):
                return value

            if type_cast == bool:
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ("true", "1", "yes", "on")
            elif type_cast == int:
                return int(value)
            elif type_cast == float:
                return float(value)
            return value
        except (ValueError, AttributeError, TypeError) as e:
            logger.warning(
                f"Failed to parse config value [{section}].{key}: {e}. Using default: {default}"
            )
            return default

    def _load_whisper_settings(self, **overrides) -> WhisperSettings:
        """Load Whisper settings"""
        return WhisperSettings(
            model_size=overrides.get("model_size") or self._get("whisper", "model_size", "base"),
            use_faster_whisper=self._get("whisper", "use_faster_whisper", True, bool),
            enable_context_buffer=self._get("whisper", "enable_context_buffer", True, bool),
            enable_corrections=self._get("whisper", "enable_corrections", True, bool),
            models_dir=overrides.get("models_dir")
            or self._get("whisper", "models_dir", "models/whisper", env_key="SPECTRA_MODELS_DIR"),
            semantic_correction_model_path=self._get("whisper", "semantic_correction_model_path", ""),
            natural_reformatter_model_path=self._get("whisper", "natural_reformatter_model_path", ""),
        )

    def _load_audio_settings(self, **overrides) -> AudioSettings:
        """Load audio settings"""
        return AudioSettings(
            sample_rate=self._get("audio", "sample_rate", 16000, int),
            chunk_duration_ms=self._get("audio", "chunk_duration_ms", 20, int),
            vad_aggressiveness=self._get("audio", "vad_aggressiveness", 3, int),
            silence_threshold=self._get("audio", "silence_threshold", 12, int),
            enable_vad_filter=self._get("audio", "enable_vad_filter", False, bool),
            vad_min_silence_duration_ms=self._get("audio", "vad_min_silence_duration_ms", 500, int),
            vad_speech_pad_ms=self._get("audio", "vad_speech_pad_ms", 200, int),
        )

    def _load_wakeword_settings(self, **overrides) -> WakeWordSettings:
        """Load wake word settings (TICKET-P3-02)"""
        return WakeWordSettings(
            enabled=self._get("wakeword", "enabled", False, bool),
            engine=self._get("wakeword", "engine", "openwakeword"),
            model=self._get("wakeword", "model", "hey_janus"),
            threshold=self._get("wakeword", "threshold", 0.5, float),
            cooldown_ms=self._get("wakeword", "cooldown_ms", 1000, int),
        )
    
    def _load_speaker_verification_settings(self, **overrides) -> SpeakerVerificationSettings:
        """Load speaker verification settings (TICKET-STT-002)"""
        return SpeakerVerificationSettings(
            enabled=self._get("speaker_verification", "enabled", False, bool),
            embedding_path=self._get("speaker_verification", "embedding_path", "user_data/user_voice.npy"),
            similarity_threshold=self._get("speaker_verification", "similarity_threshold", 0.75, float),
        )

    def _load_language_settings(self, **overrides) -> LanguageSettings:
        """Load language settings with fr/en validation"""
        # Get raw language value
        raw_lang = overrides.get("language") or self._get("language", "default", "fr")

        # Normalize and validate: only fr or en allowed, fallback to fr
        lang = (raw_lang or "fr").lower().strip()
        if lang not in ("fr", "en"):
            logger.warning(
                f"Invalid language '{raw_lang}', falling back to 'fr'. Only 'fr' and 'en' are supported."
            )
            lang = "fr"

        return LanguageSettings(default=lang)

    def _load_automation_settings(self, **overrides) -> AutomationSettings:
        """
        Load automation settings
        
        Note: ui_enable_vision is loaded from config but should ideally match features.enable_vision.
        We don't enforce this here to maintain flexibility, but it's recommended to keep them synchronized.
        """
        return AutomationSettings(
            safety_delay=self._get("automation", "safety_delay", 0.5, float),
            pyautogui_pause=self._get("automation", "pyautogui_pause", 0.1, float),
            ui_default_timeout=self._get("automation", "ui_default_timeout", 10.0, float),
            ui_max_retries=self._get("automation", "ui_max_retries", 2, int),
            ui_retry_delay=self._get("automation", "ui_retry_delay", 0.5, float),
            ui_action_delay=self._get("automation", "ui_action_delay", 0.3, float),
            ui_wait_poll_interval=self._get("automation", "ui_wait_poll_interval", 0.5, float),
            ui_applescript_timeout=self._get("automation", "ui_applescript_timeout", 10.0, float),
            ui_enable_vision=self._get("automation", "ui_enable_vision", True, bool),
        )

    def _load_calibration_settings(self, **overrides) -> CalibrationSettings:
        """Load calibration settings"""
        return CalibrationSettings(
            profile_dir=self._get("calibration", "profile_dir", "calibration_profiles"),
        )

    def _load_execution_settings(self, **overrides) -> ExecutionSettings:
        """Load execution engine settings (TICKET-111, ARCH-001 Phase 2)"""
        return ExecutionSettings(
            max_retries=self._get("execution", "max_retries", 1, int),
            enable_replanning=self._get("execution", "enable_replanning", False, bool),
            enable_vision_recovery=self._get("execution", "enable_vision_recovery", False, bool),
            continue_on_validation_error=self._get(
                "execution", "continue_on_validation_error", False, bool
            ),
            attempt_context_recovery=self._get("execution", "attempt_context_recovery", True, bool),
            context_recovery_timeout=self._get("execution", "context_recovery_timeout", 2.0, float),
        )

    def _load_vision_settings(self, **overrides) -> VisionSettings:
        """Load vision AI settings (TICKET-302: Added Florence-2 support)"""
        return VisionSettings(
            models_dir=overrides.get("vision_models_dir")
            or self._get(
                "vision", "models_dir", "models/vision", env_key="SPECTRA_VISION_MODELS_DIR"
            ),
            # TICKET-302: Florence-2 only (no legacy options)
            vision_engine=self._get("vision", "vision_engine", "florence2", str),
        )

    def _load_async_vision_monitor_settings(self, **overrides) -> AsyncVisionMonitorSettings:
        """Load async vision monitor settings"""
        return AsyncVisionMonitorSettings(
            enable_monitor=self._get("async_vision_monitor", "enable_monitor", False, bool),
            check_interval_ms=self._get("async_vision_monitor", "check_interval_ms", 1000, int),
            enable_popup_detection=self._get("async_vision_monitor", "enable_popup_detection", True, bool),
            enable_error_detection=self._get("async_vision_monitor", "enable_error_detection", True, bool),
        )

    def _load_session_settings(self, **overrides) -> SessionSettings:
        """Load session settings"""
        return SessionSettings(
            state_file=self._get("session", "state_file", "session_state.json"),
            max_history=self._get("session", "max_history", 50, int),
        )

    def _load_llm_settings(self, **overrides) -> LLMSettings:
        """Load LLM settings"""
        fallback_str = self._get("llm", "fallback_providers", "")
        fallback_providers = [p.strip() for p in fallback_str.split(",") if p.strip()]
        
        # OLLAMA_ENDPOINT can be overridden by environment variable (for Docker/deployment)
        ollama_endpoint = os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434")

        return LLMSettings(
            provider=self._get("llm", "provider", "mock"),
            model=self._get("llm", "model", "gpt-4"),
            fallback_providers=fallback_providers,
            model_path=self._get("llm", "model_path", ""),
            temperature=self._get("llm", "temperature", 0.7, float),
            max_tokens=self._get("llm", "max_tokens", 2000, int),
            request_timeout=self._get("llm", "request_timeout", 120, int),
            retry_timeout=self._get("llm", "retry_timeout", 60, int),
            enable_cache=self._get("llm", "enable_cache", True, bool),
            cache_ttl=self._get("llm", "cache_ttl", 300, int),
            auto_confirm_safe=self._get("llm", "auto_confirm_safe", True, bool),
            ollama_endpoint=ollama_endpoint,
        )

    def _load_tts_settings(self, **overrides) -> TTSSettings:
        """Load TTS settings"""
        enable_tts = overrides.get("tts_override")
        if enable_tts is None:
            enable_tts = self._get("tts", "enable_tts", True, bool)

        return TTSSettings(
            enable_tts=enable_tts,
            engine=self._get("tts", "engine", "piper"),
            piper_model_path=self._get("tts", "piper_model_path", ""),
            voice=self._get("tts", "voice", ""),
            rate=self._get("tts", "rate", 180, int),
            volume=self._get("tts", "volume", 0.7, float),
            lang=self._get("tts", "lang", "fr-FR"),
            auto_confirmations=self._get("tts", "auto_confirmations", True, bool),
            verbosity=self._get("tts", "verbosity", "compact"),
            avoid_feedback_loop=self._get("tts", "avoid_feedback_loop", True, bool),
        )

    def _load_database_settings(self, **overrides) -> DatabaseSettings:
        """Load database settings"""
        db_path = self._get("database", "path", "data/janus.db")

        # Ensure data directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        return DatabaseSettings(
            path=db_path,
            enable_wal=self._get("database", "enable_wal", True, bool),
            journal_mode=self._get("database", "journal_mode", "WAL"),
            synchronous=self._get("database", "synchronous", "NORMAL"),
            cache_size=self._get("database", "cache_size", -2000, int),
        )

    def _load_logging_settings(self, **overrides) -> LoggingSettings:
        """Load logging settings"""
        return LoggingSettings(
            level=self._get("logging", "level", "INFO"),
            format=self._get(
                "logging", "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ),
            enable_structured=self._get("logging", "enable_structured", True, bool),
            log_to_database=self._get("logging", "log_to_database", True, bool),
            log_to_console=self._get("logging", "log_to_console", True, bool),
            log_to_file=self._get("logging", "log_to_file", False, bool),
            log_file=self._get("logging", "log_file", "janus.log"),
        )

    def _load_features_settings(self, **overrides) -> FeaturesSettings:
        """
        Load feature activation settings from config.ini only.
        
        Configuration is now exclusively read from config.ini.
        No auto-detection, no environment variables for config.
        Values must be 'true' or 'false' - stability over magic.
        
        PERF-FOUNDATION-001: Added granular vision control flags
        P2: Added dry-run, rollback, rate limiting, offline mode flags
        """
        # Read values directly from config.ini - no env vars, no auto-detection
        enable_llm = self._get("features", "enable_llm_reasoning", "true", bool)
        enable_vision = self._get("features", "enable_vision", "true", bool)
        enable_learning = self._get("features", "enable_learning", "true", bool)
        enable_semantic = self._get("features", "enable_semantic_correction", "true", bool)
        
        # PERF-FOUNDATION-001: Granular vision control flags
        vision_decision_enabled = self._get("features", "vision_decision_enabled", "true", bool)
        vision_verification_enabled = self._get("features", "vision_verification_enabled", "true", bool)
        trace_screenshots_enabled = self._get("features", "trace_screenshots_enabled", "false", bool)
        
        # P2 Features
        enable_dry_run = self._get("features", "enable_dry_run", "true", bool)
        enable_rollback = self._get("features", "enable_rollback", "true", bool)
        enable_rate_limiting = self._get("features", "enable_rate_limiting", "true", bool)
        enable_offline_mode = self._get("features", "enable_offline_mode", "true", bool)
        
        return FeaturesSettings(
            enable_llm_reasoning=enable_llm,
            enable_vision=enable_vision,
            enable_learning=enable_learning,
            enable_semantic_correction=enable_semantic,
            vision_decision_enabled=vision_decision_enabled,
            vision_verification_enabled=vision_verification_enabled,
            trace_screenshots_enabled=trace_screenshots_enabled,
            enable_dry_run=enable_dry_run,
            enable_rollback=enable_rollback,
            enable_rate_limiting=enable_rate_limiting,
            enable_offline_mode=enable_offline_mode,
        )
    
    def _load_rate_limit_settings(self, **overrides) -> RateLimitSettings:
        """Load rate limiting settings from config.ini (P2 Feature)"""
        return RateLimitSettings(
            enabled=self._get("rate_limit", "enabled", "true", bool),
            global_max_requests=self._get("rate_limit", "global_max_requests", "100", int),
            global_time_window_seconds=self._get("rate_limit", "global_time_window_seconds", "60.0", float),
            global_burst_allowance=self._get("rate_limit", "global_burst_allowance", "20", int),
            agent_max_requests=self._get("rate_limit", "agent_max_requests", "30", int),
            agent_time_window_seconds=self._get("rate_limit", "agent_time_window_seconds", "60.0", float),
            agent_burst_allowance=self._get("rate_limit", "agent_burst_allowance", "5", int),
            email_max_requests=self._get("rate_limit", "email_max_requests", "10", int),
            email_time_window_seconds=self._get("rate_limit", "email_time_window_seconds", "60.0", float),
            slack_max_requests=self._get("rate_limit", "slack_max_requests", "20", int),
            slack_time_window_seconds=self._get("rate_limit", "slack_time_window_seconds", "60.0", float),
            teams_max_requests=self._get("rate_limit", "teams_max_requests", "20", int),
            teams_time_window_seconds=self._get("rate_limit", "teams_time_window_seconds", "60.0", float),
            crm_max_requests=self._get("rate_limit", "crm_max_requests", "15", int),
            crm_time_window_seconds=self._get("rate_limit", "crm_time_window_seconds", "60.0", float),
        )
    
    def _load_offline_settings(self, **overrides) -> OfflineSettings:
        """Load offline mode and queue settings from config.ini (P2 Feature)"""
        return OfflineSettings(
            enabled=self._get("offline", "enabled", "true", bool),
            queue_enabled=self._get("offline", "queue_enabled", "true", bool),
            auto_process_queue=self._get("offline", "auto_process_queue", "true", bool),
            max_queue_size=self._get("offline", "max_queue_size", "1000", int),
            default_max_retries=self._get("offline", "default_max_retries", "3", int),
            default_expiration_hours=self._get("offline", "default_expiration_hours", "24", int),
            purge_completed_hours=self._get("offline", "purge_completed_hours", "168", int),
            check_interval_seconds=self._get("offline", "check_interval_seconds", "60", int),
        )
    
    def _load_data_retention_settings(self, **overrides) -> DataRetentionSettings:
        """Load data retention and cleanup settings from config.ini (TICKET-DATA-001)"""
        return DataRetentionSettings(
            memory_context_days=self._get("data_retention", "memory_context_days", "30", int),
            memory_history_days=self._get("data_retention", "memory_history_days", "30", int),
            semantic_vectors_days=self._get("data_retention", "semantic_vectors_days", "60", int),
            action_history_days=self._get("data_retention", "action_history_days", "90", int),
            workflow_states_days=self._get("data_retention", "workflow_states_days", "14", int),
            audio_logs_days=self._get("data_retention", "audio_logs_days", "7", int),
            safe_queue_days=self._get("data_retention", "safe_queue_days", "30", int),
            unified_store_days=self._get("data_retention", "unified_store_days", "30", int),
            max_total_size_mb=self._get("data_retention", "max_total_size_mb", "2000", int),
            auto_cleanup_on_startup=self._get("data_retention", "auto_cleanup_on_startup", "true", bool),
            cleanup_check_interval_hours=self._get("data_retention", "cleanup_check_interval_hours", "24", int),
        )
