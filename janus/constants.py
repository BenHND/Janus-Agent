"""
Shared constants for Janus
TICKET-QUALITY-02: Extract Hard-Coded Values

This module contains all shared constants used throughout the Janus application.
Constants are organized by category for easy maintenance and discovery.
"""

from enum import Enum

# ============================================================================
# TIMING CONSTANTS
# ============================================================================

# Execution timeouts (seconds)
DEFAULT_ACTION_TIMEOUT = 30.0  # Default timeout for action execution
SHORT_TIMEOUT = 10.0  # Timeout for quick operations (UI actions, AppleScript)
LONG_TIMEOUT = 60.0  # Timeout for long operations (terminal commands, builds)
NETWORK_TIMEOUT = 30.0  # Timeout for network/API requests
OLLAMA_HEALTH_CHECK_TIMEOUT = 2.0  # Timeout for Ollama service health check
# LLM request timeout - higher to account for model cold starts (first request)
LLM_REQUEST_TIMEOUT = 120  # Default timeout for LLM API requests (seconds)
LLM_RETRY_TIMEOUT = 60  # Timeout for LLM retry attempts (seconds)
# Max tokens for JSON mode output - reduced to prevent verbose generation
# TICKET 3 (P0): Reduced from 512 to 256 to improve burst decision latency
LLM_JSON_MODE_MAX_TOKENS = 256  # JSON burst responses rarely need more than this

# Async pipeline timeouts (TICKET 4)
ASYNC_ACTION_TIMEOUT = 10.0  # Timeout for async action execution
ASYNC_VISION_TIMEOUT = 4.0  # Timeout for async vision verification
ASYNC_TOTAL_TIMEOUT = 15.0  # Total timeout for parallel action+vision

# Retry configuration
DEFAULT_MAX_RETRIES = 2  # Maximum retry attempts for retryable operations
DEFAULT_RETRY_DELAY = 0.5  # Initial delay between retries (seconds)
MAX_RETRY_ATTEMPTS = 3  # Maximum retry attempts for critical operations
INITIAL_RETRY_DELAY = 1.0  # Initial delay for exponential backoff (seconds)
MAX_RETRY_DELAY = 60.0  # Maximum delay for exponential backoff (seconds)
EXPONENTIAL_BACKOFF_BASE = 2.0  # Base for exponential backoff calculation
JITTER_MULTIPLIER_MIN = 0.5  # Minimum jitter multiplier for retry delays

# Action delays (seconds)
DEFAULT_ACTION_DELAY = 0.3  # Delay after successful UI actions
SAFETY_DELAY = 0.5  # Safety delay between automation actions
PYAUTOGUI_PAUSE = 0.1  # Pause between PyAutoGUI calls
FOCUS_RETRY_DELAY = 0.5  # Delay between window focus retry attempts

# Polling intervals (seconds)
UI_WAIT_POLL_INTERVAL = 0.5  # Polling interval for UI wait operations
QUEUE_POLL_TIMEOUT = 0.1  # Timeout for queue polling operations

# Thread timeouts (seconds)
WORKER_THREAD_JOIN_TIMEOUT = 2.0  # Timeout for joining worker threads
TTS_WORKER_TIMEOUT = 5.0  # Timeout for TTS worker operations

# Window management
MAX_FOCUS_ATTEMPTS = 3  # Maximum attempts to focus a window
FOCUS_TIMEOUT = 5.0  # Timeout for window focus operations


# ============================================================================
# CACHE AND PERFORMANCE CONSTANTS
# ============================================================================

# LLM cache configuration
LLM_CACHE_TTL = 300  # Cache time-to-live in seconds (5 minutes)
LLM_MAX_TOKENS = 2000  # Maximum tokens in LLM response
LLM_DEFAULT_TEMPERATURE = 0.7  # Default temperature for LLM responses

# Context configuration
LLM_CONTEXT_SIZE = 2048  # Context window size for local LLM
LLM_THREAD_COUNT = 4  # Number of threads for local LLM processing

# History limits
MAX_COMMAND_HISTORY = 50  # Maximum commands to keep in history
DEFAULT_HISTORY_LIMIT = 100  # Default history limit for various buffers
CONTEXT_MEMORY_LIMIT = 5  # Number of recent commands to include in context

# Report limits
DEFAULT_REPORT_LIMIT = 10  # Default number of reports to list


# ============================================================================
# THRESHOLD AND LIMIT CONSTANTS
# ============================================================================

# Audio thresholds
DEFAULT_VAD_AGGRESSIVENESS = 3  # VAD aggressiveness level (0-3)
DEFAULT_SILENCE_THRESHOLD = 20  # Consecutive silent chunks before stopping
DEFAULT_ACTIVATION_THRESHOLD = 500.0  # Voice activation energy threshold
DEFAULT_SAMPLE_RATE = 16000  # Audio sample rate in Hz
DEFAULT_CHUNK_DURATION_MS = 30  # Chunk duration for VAD processing

# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.9  # High confidence level
MEDIUM_CONFIDENCE_THRESHOLD = 0.8  # Medium confidence level
LOW_CONFIDENCE_THRESHOLD = 0.5  # Low confidence level
MINIMAL_CONFIDENCE_THRESHOLD = 0.3  # Minimal acceptable confidence
FALLBACK_CONFIDENCE = 0.2  # Confidence for fallback/unknown results

# Memory and performance
MEMORY_LEAK_THRESHOLD_MB = 10.0  # Memory leak detection threshold in MB
MIN_LEAK_DETECTION_ITERATIONS = 3  # Minimum iterations for leak detection
DATABASE_CACHE_SIZE_KB = -2000  # SQLite cache size (-2000 = 2MB)

# Content limits
MAX_CONTENT_SUMMARY_LENGTH = 200  # Maximum length for content summaries
CONTENT_PREVIEW_LENGTH = 100  # Length of content preview in characters


# ============================================================================
# VOLUME AND AUDIO CONSTANTS
# ============================================================================

# Volume levels (0.0 to 1.0)
DEFAULT_TTS_VOLUME = 0.7  # Default TTS volume level
MIN_VOLUME = 0.0  # Minimum volume level
MAX_VOLUME = 1.0  # Maximum volume level

# Speech settings
DEFAULT_TTS_RATE = 180  # Default TTS speech rate (words per minute)
MIN_SPEECH_RATE = 100  # Minimum speech rate
MAX_SPEECH_RATE = 300  # Maximum speech rate


# ============================================================================
# LLM AND AI CONSTANTS
# ============================================================================

# LLM sampling parameters
DEFAULT_TOP_P = 0.95  # Top-p (nucleus) sampling parameter
DEFAULT_REPEAT_PENALTY = 1.1  # Repetition penalty for LLM generation

# Priority levels (for TTS and other queued operations)
HIGH_PRIORITY = 3  # High priority messages
MEDIUM_PRIORITY = 5  # Medium priority messages
LOW_PRIORITY = 7  # Low priority messages


# ============================================================================
# ENUMS FOR STRING CONSTANTS
# ============================================================================


class ExecutionStatus(Enum):
    """Status of action execution"""

    SUCCESS = "success"
    RETRYABLE_FAIL = "retryable_fail"
    FATAL_FAIL = "fatal_fail"
    SKIPPED = "skipped"


class ActionType(Enum):
    """Types of actions that can be executed"""

    OPEN = "open"
    CLOSE = "close"
    CLICK = "click"
    TYPE = "type"
    SEARCH = "search"
    FIND = "find"
    EXECUTE = "execute"
    RUN = "run"
    NAVIGATE = "navigate"
    COPY = "copy"
    PASTE = "paste"
    SCROLL = "scroll"
    WAIT = "wait"


class IntentType(Enum):
    """High-level intent types"""

    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    OPEN_FILE = "open_file"
    NAVIGATE_URL = "navigate_url"
    SEARCH_WEB = "search_web"
    CLICK_ELEMENT = "click"
    CLICK_SELECTOR = "click_selector"
    TYPE_TEXT = "type"
    COPY_TEXT = "copy"
    PASTE_TEXT = "paste"
    EXECUTE_COMMAND = "execute"
    SCHEDULE_TASK = "schedule_task"  # TICKET-FEAT-002: Schedule delayed/recurring tasks
    CANCEL_TASK = "cancel_task"       # TICKET-FEAT-002: Cancel scheduled tasks
    UNKNOWN = "unknown"


class ErrorCategory(Enum):
    """Error categories for standardized error handling"""

    NETWORK = "network"
    PERMISSION = "permission"
    USER_INPUT = "user_input"
    INTERNAL = "internal"


class ActionStatus(Enum):
    """Status of action execution results"""

    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"


class LLMProvider(Enum):
    """Supported LLM providers"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    OLLAMA = "ollama"
    MISTRAL = "mistral"
    MOCK = "mock"


class LanguageCode(Enum):
    """Supported language codes"""

    FRENCH = "fr"
    FRENCH_FR = "fr-FR"
    ENGLISH = "en"
    ENGLISH_US = "en-US"
    SPANISH = "es"
    SPANISH_ES = "es-ES"
    GERMAN = "de"
    GERMAN_DE = "de-DE"
    ITALIAN = "it"
    ITALIAN_IT = "it-IT"


class TTSVerbosity(Enum):
    """TTS verbosity levels"""

    COMPACT = "compact"
    VERBOSE = "verbose"


class LogLevel(Enum):
    """Logging levels"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseJournalMode(Enum):
    """SQLite journal modes"""

    DELETE = "DELETE"
    TRUNCATE = "TRUNCATE"
    PERSIST = "PERSIST"
    MEMORY = "MEMORY"
    WAL = "WAL"
    OFF = "OFF"


class DatabaseSyncMode(Enum):
    """SQLite synchronous modes"""

    OFF = "OFF"
    NORMAL = "NORMAL"
    FULL = "FULL"
    EXTRA = "EXTRA"


class WhisperModelSize(Enum):
    """Whisper model sizes"""

    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class SafeActionType(Enum):
    """Safe actions that can be auto-confirmed"""

    OPEN_APP = "open_app"
    FOCUS_WINDOW = "focus_window"
    CLICK = "click"
    TYPE = "type"
    SEARCH = "search"
    NAVIGATE = "navigate"
    COPY = "copy"
    SCROLL = "scroll"


# List of safe action type strings
SAFE_ACTIONS = [action.value for action in SafeActionType]


# ============================================================================
# FILE AND PATH CONSTANTS
# ============================================================================

# Default paths
DEFAULT_SESSION_STATE_FILE = "session_state.json"
DEFAULT_DATABASE_PATH = "data/janus.db"
DEFAULT_CALIBRATION_PROFILE_DIR = "calibration_profiles"
DEFAULT_LOG_FILE = "janus.log"


# ============================================================================
# STRING FORMATTING CONSTANTS
# ============================================================================

# JSON indentation
JSON_INDENT_COMPACT = None  # No indentation
JSON_INDENT_READABLE = 2  # 2-space indentation for readable output


# ============================================================================
# NETWORK CONSTANTS
# ============================================================================

# API endpoints
# Use environment variable if set, otherwise use default
import os

OLLAMA_DEFAULT_ENDPOINT = os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434")
OLLAMA_TAGS_PATH = "/api/tags"

# Search engine URL (TICKET-ARCH-002: Generic, privacy-focused default)
SEARCH_ENGINE_URL = os.environ.get("SEARCH_ENGINE_URL", "https://duckduckgo.com")


# ============================================================================
# UI CONSTANTS
# ============================================================================

# Line counts for output truncation
TAIL_LOG_LINES = 500  # Default number of log lines to tail


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def clamp_volume(volume: float) -> float:
    """
    Clamp volume to valid range [MIN_VOLUME, MAX_VOLUME]

    Args:
        volume: Volume level to clamp

    Returns:
        Clamped volume level
    """
    return max(MIN_VOLUME, min(MAX_VOLUME, volume))


def clamp_speech_rate(rate: int) -> int:
    """
    Clamp speech rate to valid range [MIN_SPEECH_RATE, MAX_SPEECH_RATE]

    Args:
        rate: Speech rate to clamp

    Returns:
        Clamped speech rate
    """
    return max(MIN_SPEECH_RATE, min(MAX_SPEECH_RATE, rate))


def validate_confidence(confidence: float) -> float:
    """
    Validate and clamp confidence score to [0.0, 1.0]

    Args:
        confidence: Confidence score to validate

    Returns:
        Validated confidence score
    """
    return max(0.0, min(1.0, confidence))
