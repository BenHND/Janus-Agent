"""
ReasonerLLM - Local LLM wrapper for cognitive planning
Phase 20B: Cognitive Planner (LLM Reasoner)

Supports local LLM inference via llama-cpp-python or ollama
for Mistral 7B Q4, Phi-3 mini, and similar models.

ARCH-002: Instrumentation for transparency - all LLM calls logged.
"""

import json
import re
import time
import warnings
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Template

from janus.constants import (
    LLM_JSON_MODE_MAX_TOKENS,
    LLM_REQUEST_TIMEOUT,
    LLM_RETRY_TIMEOUT,
    OLLAMA_DEFAULT_ENDPOINT,
    OLLAMA_TAGS_PATH,
    IntentType,
)
from janus.logging import get_logger
from janus.ai.reasoning.prompt_loader import load_prompt
from janus.ai.llm.llm_utils import estimate_tokens  # ARCH-002: Shared utility
from janus.ai.reasoning.context_assembler import ContextAssembler, BudgetConfig  # PERF-001

# Initialize logger
logger = get_logger("reasoner_llm")

# Mock testing constants
MOCK_FALLBACK_RECIPIENT = "recipient@example.com"

# TICKET-403: System Context (Grounding) rules for LLM prompt
SYSTEM_CONTEXT_GROUNDING_RULE_FR = (
    "RÈGLE: Si l'utilisateur dit 'ici', 'ça', 'cet onglet', "
    "'cette page', 'cette fenêtre', réfère-toi à l'état système ci-dessus."
)
SYSTEM_CONTEXT_GROUNDING_RULE_EN = (
    "RULE: If the user says 'here', 'this', 'this tab', "
    "'this page', 'this window', refer to the system state above."
)


class LLMBackend(Enum):
    """Supported LLM backends"""

    LLAMA_CPP = "llama-cpp"
    OLLAMA = "ollama"
    MOCK = "mock"


@dataclass
class LLMConfig:
    """Configuration for local LLM"""

    backend: LLMBackend
    model_path: Optional[str] = None
    model_name: Optional[str] = None  # For Ollama
    n_ctx: int = 2048  # Context window
    n_threads: int = 4  # CPU threads
    temperature: float = 0.1  # Low temperature for deterministic output
    max_tokens: int = 512
    top_p: float = 0.95
    repeat_penalty: float = 1.1
    # Timeout values (in milliseconds) - using constants from janus.constants
    # Default 120s for initial request (model may need to load into memory)
    # Default 60s for retry attempts (model already loaded)
    timeout_ms: int = LLM_REQUEST_TIMEOUT * 1000  # Convert seconds to ms
    short_timeout_ms: int = LLM_RETRY_TIMEOUT * 1000  # Convert seconds to ms
    # V4 strict mode: Raise exception on V4 contract violations (for development/testing)
    v4_strict_mode: bool = False


class ReasonerLLM:
    """
    Local LLM wrapper for cognitive planning

    Features:
    - Support for llama-cpp-python and ollama backends
    - Optimized for Llama 3.2 (3B) (default), Mistral 7B Q4, Phi-3 mini, Gemma models
    - TICKET-MIG-002: Default model changed to llama3.2 for optimal speed/intelligence balance
    - Fast inference (<500ms target on M-series, optimized from 800ms)
    - Graceful fallback when unavailable with detailed logging
    - Prompt templates for FR/EN
    - Performance metrics and comparison with classic parser
    """

    # Default model for Ollama backend - Qwen2.5:7b-instruct
    # Qwen2.5 7B Instruct offers superior reasoning, multilingual support,
    # and better instruction following than llama3.2
    DEFAULT_OLLAMA_MODEL = "qwen2.5:7b-instruct"

    def __init__(
        self,
        backend: str = "llama-cpp",
        model_path: Optional[str] = None,
        model_name: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ):
        """
        Initialize ReasonerLLM

        Args:
            backend: Backend type ("llama-cpp", "ollama", "mock")
            model_path: Path to GGUF model file (for llama-cpp)
            model_name: Model name (for ollama, e.g., "qwen2.5:7b-instruct", "mistral")
                        Defaults to qwen2.5:7b-instruct for Ollama backend if not specified.
            config: Optional LLMConfig for advanced settings
        """
        self.backend = LLMBackend(backend)
        self.model_path = Path(model_path) if model_path else None
        
        # Set default model for Ollama backend
        if model_name:
            self.model_name = model_name
        elif backend == "ollama":
            # Use qwen2.5:7b-instruct as default for optimal reasoning and multilingual support
            self.model_name = self.DEFAULT_OLLAMA_MODEL
        else:
            self.model_name = None

        # Use provided config or create default
        if config:
            self.config = config
        else:
            self.config = LLMConfig(
                backend=self.backend,
                model_path=str(self.model_path) if self.model_path else None,
                model_name=self.model_name,
            )

        # LLM client
        self.llm = None
        self.available = False

        # PERF-001: Context assembler for budget control
        self.context_assembler = ContextAssembler(config=BudgetConfig())
        
        # Performance metrics
        self.metrics = {
            "total_calls": 0,
            "total_time_ms": 0.0,
            "avg_latency_ms": 0.0,
            "fallback_count": 0,
            "timeout_count": 0,
            "llm_calls": 0,
            "llm_total_time_ms": 0.0,
            "fallback_total_time_ms": 0.0,
        }

        # Initialize backend
        self._initialize_backend()

    def _initialize_backend(self):
        """Initialize the LLM backend"""
        try:
            if self.backend == LLMBackend.LLAMA_CPP:
                self._init_llama_cpp()
            elif self.backend == LLMBackend.OLLAMA:
                self._init_ollama()
            elif self.backend == LLMBackend.MOCK:
                self._init_mock()
            else:
                raise ValueError(f"Unsupported backend: {self.backend}")
        except Exception as e:
            logger.warning(f"Failed to initialize {self.backend.value}: {e}")
            warnings.warn(f"Failed to initialize {self.backend.value}: {e}")
            self.available = False

    def _init_llama_cpp(self):
        """Initialize llama-cpp-python backend"""
        try:
            from llama_cpp import Llama

            if not self.model_path or not self.model_path.exists():
                raise FileNotFoundError(
                    f"Model file not found: {self.model_path}. "
                    "Please provide a valid GGUF model path."
                )

            self.llm = Llama(
                model_path=str(self.model_path),
                n_ctx=self.config.n_ctx,
                n_threads=self.config.n_threads,
                verbose=False,
            )
            self.available = True
            logger.info(f"ReasonerLLM initialized with llama-cpp: {self.model_path.name}")

        except ImportError:
            warnings.warn(
                "llama-cpp-python not installed. Install with: " "pip install llama-cpp-python"
            )
            self.available = False
        except Exception as e:
            warnings.warn(f"Failed to load llama-cpp model: {e}")
            self.available = False

    def _init_ollama(self):
        """Initialize Ollama backend with auto-download for missing models"""
        try:
            from janus.ai.llm.ollama_client import OllamaClient

            if not self.model_name:
                raise ValueError("model_name required for Ollama backend")

            # Initialize Ollama client
            self.llm = OllamaClient(timeout=int(self.config.timeout_ms / 1000))
            
            # Check if Ollama server is available
            if not self.llm.is_available():
                warnings.warn(f"Ollama server not responding at {OLLAMA_DEFAULT_ENDPOINT}")
                self.available = False
                return

            # Check if model is available
            if not self.llm.model_exists(self.model_name):
                models = self.llm.list_models()
                model_names = [m.get("name", "") for m in models]
                
                logger.info(
                    f"Model {self.model_name} not found in Ollama. "
                    f"Available models: {model_names}"
                )
                
                # TICKET-FIX: If llama3.2 is missing but llama3.2:latest exists, use it
                if self.model_name == "llama3.2" and "llama3.2:latest" in model_names:
                    logger.info("Found llama3.2:latest, using it instead of llama3.2")
                    self.model_name = "llama3.2:latest"
                    self.available = True
                    logger.info(f"ReasonerLLM initialized with Ollama: {self.model_name}")
                    return

                logger.info(f"Auto-downloading model: {self.model_name}")
                
                # Auto-download the model
                try:
                    download_success = False
                    for progress in self.llm.pull_model(self.model_name, stream=True):
                        if "error" in progress:
                            logger.error(f"Failed to download model: {progress['error']}")
                            break
                        
                        status = progress.get("status", "")
                        if "downloading" in status.lower() or "pulling" in status.lower():
                            # Log progress occasionally (not every chunk)
                            if progress.get("completed") and progress.get("total"):
                                percent = (progress["completed"] / progress["total"]) * 100
                                if int(percent) % 10 == 0:  # Log every 10%
                                    logger.info(f"Downloading {self.model_name}: {percent:.0f}%")
                        
                        if progress.get("status") == "success" or progress.get("done"):
                            download_success = True
                            logger.info(f"Successfully downloaded model: {self.model_name}")
                            break
                    
                    if not download_success:
                        warnings.warn(
                            f"Failed to download model {self.model_name}. "
                            f"Pull manually with: ollama pull {self.model_name}"
                        )
                        self.available = False
                        return
                        
                except Exception as e:
                    logger.error(f"Error downloading model: {e}")
                    warnings.warn(
                        f"Failed to download model {self.model_name}: {e}. "
                        f"Pull manually with: ollama pull {self.model_name}"
                    )
                    self.available = False
                    return

            self.available = True
            logger.info(f"ReasonerLLM initialized with Ollama: {self.model_name}")
            
            # Log GPU info if available
            gpu_info = self.llm.detect_gpu()
            if gpu_info.get("available"):
                logger.info(f"GPU detected: {gpu_info.get('type')} - {len(gpu_info.get('devices', []))} device(s)")

        except ImportError as e:
            warnings.warn(f"Failed to import OllamaClient: {e}")
            self.available = False
        except Exception as e:
            warnings.warn(f"Failed to connect to Ollama: {e}")
            self.available = False

    def _init_mock(self):
        """Initialize mock backend for testing"""
        self.llm = "mock"
        self.available = True
        logger.debug("Using mock ReasonerLLM for testing")

    # TICKET-REFACTOR-002: _get_system_prompt removed (unused after ReAct extraction)
    async def warmup_model_async(self) -> bool:
        """
        Asynchronously warm up the LLM model by loading it into memory.
        
        For Ollama backend, this sends a minimal prompt to force the model
        to load into memory, eliminating cold start delays on the first real request.
        
        This should be called during application startup to provide a better
        user experience (similar to vision model preloading).
        
        Returns:
            True if model was warmed up successfully, False otherwise
        """
        import asyncio
        
        if not self.available:
            logger.info(f"LLM backend '{self.backend.value}' not available, skipping warmup")
            return False
        
        if self.backend == LLMBackend.OLLAMA:
            logger.info(f"Starting LLM model warmup for '{self.model_name}'...")
            
            try:
                # Run the warmup in a thread pool to avoid blocking the event loop
                # TICKET-330: Use get_running_loop() instead of deprecated get_event_loop()
                loop = asyncio.get_running_loop()
                success = await loop.run_in_executor(
                    None,
                    lambda: self.llm.warmup_model(self.model_name)
                )
                
                if success:
                    logger.info(f"✓ LLM model '{self.model_name}' warmed up and ready")
                else:
                    logger.warning(f"LLM model warmup completed but may not be fully loaded")
                
                return success
                
            except Exception as e:
                logger.warning(f"Failed to warm up LLM model: {e}")
                logger.info("Model will load on first request (may be slower)")
                return False
        
        elif self.backend == LLMBackend.LLAMA_CPP:
            # llama-cpp-python models are already loaded during initialization
            logger.info("llama-cpp model already loaded during initialization")
            return True
        
        elif self.backend == LLMBackend.MOCK:
            logger.info("Mock backend, no warmup needed")
            return True
        
        return False

    def parse_command(
        self,
        text: str,
        language: str = "fr",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Parse command text into structured JSON intents
        
        ARCH-REMEDIATION-CRITICAL (Ticket: ARCH-REMEDIATION-CRITICAL):
        All fallback heuristics removed. LLM is the ONLY reasoning path.
        Timeouts and errors return explicit error states.

        Args:
            text: Raw command text from STT
            language: Language code ("fr" or "en")
            context: Optional context from Phase 19

        Returns:
            Dict with:
            - intents: List of parsed intents with parameters (empty on error)
            - confidence: Overall confidence score (0.0 on error)
            - source: "llm" (success) or "error" (failure)
            - error: Error message (only present on failure)
            - latency_ms: Processing time
            
        Note:
            When LLM is unavailable or times out, returns empty intents with
            source="error" and an error message. Callers should check the
            source field and handle errors appropriately.
        """
        start_time = time.time()
        
        # LLM unavailable → explicit error (NO FALLBACK)
        if not self.available:
            logger.error(f"🔥 LLM not available - cannot parse command: {text[:50]}...")
            self.metrics["fallback_count"] += 1
            latency_ms = (time.time() - start_time) * 1000
            self._update_metrics(latency_ms)
            return {
                "intents": [],
                "confidence": 0.0,
                "source": "error",
                "error": "LLM unavailable",
                "latency_ms": latency_ms,
            }

        try:
            # Build prompt
            prompt = self._build_parse_prompt(text, language, context)

            # Run inference with timeout
            # CRITICAL FIX: Always use json_mode=True to prevent 90s+ inference latency
            # Without json_mode, Qwen fills 1024 tokens with verbose text (~90s on M4)
            response = self.run_inference(prompt, max_tokens=256, json_mode=True)

            # Parse response
            result = self._parse_llm_response(response)
            result["source"] = "llm"
            self.metrics["llm_calls"] += 1
            llm_time = (time.time() - start_time) * 1000
            self.metrics["llm_total_time_ms"] += llm_time
            logger.debug(f"LLM parsed command in {llm_time:.2f}ms")

        except TimeoutError:
            logger.error(f"❌ LLM timeout - cannot parse command: {text[:50]}...")
            self.metrics["timeout_count"] += 1
            result = {
                "intents": [],
                "confidence": 0.0,
                "source": "error",
                "error": "LLM timeout",
            }

        except Exception as e:
            logger.error(f"❌ LLM parsing failed: {e} - cannot parse command: {text[:50]}...")
            result = {
                "intents": [],
                "confidence": 0.0,
                "source": "error",
                "error": f"LLM error: {str(e)}",
            }

        # Track metrics
        latency_ms = (time.time() - start_time) * 1000
        result["latency_ms"] = latency_ms
        self._update_metrics(latency_ms)

        return result



    # TICKET-REFACTOR-002: decide_next_action and decide_reflex_action moved to ActionCoordinator
    # ReasonerLLM is now just the LLM inference core
    # TICKET-REFACTOR-002: generate_structured_plan REMOVED
    # This was part of the OLD planning-based architecture.
    # Use ActionCoordinator with decide_next_action() for ReAct-style execution.


    def replan_with_vision(
        self,
        failed_action: Dict[str, Any],
        error: str,
        screenshot_description: str,
        execution_context: Optional[Dict[str, Any]] = None,
        language: str = "fr",
    ) -> Dict[str, Any]:
        """
        Generate corrective steps using vision information after action failure.
        
        TICKET-407: Smart Self-Healing with vision-based recovery.
        This method uses a screenshot description to generate minimal corrective steps.
        
        Args:
            failed_action: The action that failed (with module, action, args)
            error: Error message from the failure
            screenshot_description: Description of current screen state (from vision)
            execution_context: Current execution state including:
                - current_context: Current app/surface/url/domain
                - completed_steps: Successfully executed steps
                - original_command: The original user command
            language: Language code (fr/en)
        
        Returns:
            Dict with structure:
            {
                "steps": [...],  # Minimal corrective steps (2-3 max)
                "explanation": "Why the original failed and how this fixes it",
                "error": "error_message" (if failed)
            }
            
        Note:
            Returns dict with empty steps and error message when LLM unavailable.
        """
        start_time = time.time()

        if not self.available:
            logger.error(
                f"🔥 LLM not available - cannot replan with vision for action: {failed_action.get('action')}"
            )
            self.metrics["fallback_count"] += 1
            latency = (time.time() - start_time) * 1000
            self._update_metrics(latency)
            return {
                "steps": [],
                "explanation": "LLM unavailable for vision-based replanning",
                "error": "LLM unavailable"
            }

        try:
            # Build vision-based replan prompt
            prompt = self._build_replan_vision_prompt(
                failed_action, error, screenshot_description, execution_context, language
            )

            # Run inference with json_mode
            # ARCH-002: No legacy aliases - use run_inference directly
            response = self.run_inference(prompt, max_tokens=512, json_mode=True)

            # Parse replan response
            result = self._parse_structured_plan_response(response)

            # Add explanation if not present
            if "explanation" not in result:
                result["explanation"] = "Vision-based corrective plan generated"

            self.metrics["llm_calls"] += 1
            llm_time = (time.time() - start_time) * 1000
            self.metrics["llm_total_time_ms"] += llm_time
            logger.debug(f"LLM generated vision-based replan in {llm_time:.2f}ms")

        except TimeoutError:
            logger.error(f"❌ LLM timeout during vision-based replan")
            self.metrics["timeout_count"] += 1
            result = {
                "steps": [],
                "explanation": "LLM timeout during vision-based replanning",
                "error": "LLM timeout"
            }

        except Exception as e:
            logger.error(f"❌ Vision-based replan failed: {e}")
            result = {
                "steps": [],
                "explanation": f"Vision-based replanning error: {str(e)}",
                "error": str(e)
            }

        # Track metrics
        latency_ms = (time.time() - start_time) * 1000
        self._update_metrics(latency_ms)

        return result


    def _check_context_window(self, prompt: str, max_tokens: int) -> None:
        """
        Check if prompt + max_tokens fits within the model's context window.
        
        CRITICAL-P0: Prevents silent context window overflow that can cause
        degraded LLM performance or incorrect outputs.
        
        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum tokens to generate
            
        Raises:
            ValueError: If prompt + max_tokens exceeds context window
        """
        # Estimate prompt tokens
        prompt_tokens = estimate_tokens(prompt)
        total_tokens = prompt_tokens + max_tokens
        
        # Get context window size from config
        n_ctx = self.config.n_ctx
        
        # Check if we exceed context window
        if total_tokens > n_ctx:
            overflow = total_tokens - n_ctx
            logger.error(
                f"❌ Context window overflow: prompt={prompt_tokens} tokens, "
                f"max_tokens={max_tokens}, total={total_tokens}, "
                f"n_ctx={n_ctx}, overflow={overflow} tokens"
            )
            
            # Log truncation strategy
            logger.warning(
                f"⚠️ Recommend reducing prompt size by {overflow} tokens. "
                f"Consider: reducing visual context, action history, or tool schema."
            )
            
            raise ValueError(
                f"Context window overflow: {total_tokens} tokens exceeds n_ctx={n_ctx} "
                f"(prompt={prompt_tokens}, max_tokens={max_tokens}). "
                f"Reduce prompt by {overflow} tokens."
            )
        
        # Warn if we're using >90% of context window
        usage_percent = (total_tokens / n_ctx) * 100
        if usage_percent > 90:
            logger.warning(
                f"⚠️ High context window usage: {usage_percent:.1f}% "
                f"({total_tokens}/{n_ctx} tokens). Consider reducing prompt size."
            )
        else:
            logger.debug(
                f"✓ Context window check: {total_tokens}/{n_ctx} tokens ({usage_percent:.1f}%)"
            )

    def run_inference(self, prompt: str, max_tokens: int = 512, timeout_override: Optional[int] = None, json_mode: bool = False, temperature_override: Optional[float] = None) -> str:
        """
        Run LLM inference with timeout and context window verification
        
        ARCH-002: All LLM calls are logged for transparency (call tracking, tokens, latency).
        CRITICAL-P0: Added context window verification to prevent silent overflow.
        
        TICKET-REFACTOR-002: Made public for ActionCoordinator to call directly.
        TICKET-111 (A2): Added timeout_override parameter for short retry support.
        TICKET-315: Added json_mode parameter to force JSON output format.
        TICKET-OPT-001: Added temperature_override parameter for reflex mode.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            timeout_override: Optional timeout in milliseconds (overrides config.timeout_ms)
            json_mode: If True, force Ollama to output valid JSON only (format="json")
            temperature_override: Optional temperature (overrides config.temperature)

        Returns:
            LLM response text

        Raises:
            TimeoutError: If inference exceeds timeout
            ValueError: If prompt exceeds context window
        """
        # CRITICAL-P0: Check context window before inference
        self._check_context_window(prompt, max_tokens)
        
        # ARCH-002: Measure latency for instrumentation
        start_time = time.time()
        
        timeout_ms = timeout_override if timeout_override is not None else self.config.timeout_ms
        temperature = temperature_override if temperature_override is not None else self.config.temperature
        
        result_text = ""  # Track result for logging
        
        if self.backend == LLMBackend.LLAMA_CPP:
            response = self.llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=self.config.top_p,
                repeat_penalty=self.config.repeat_penalty,
                stop=["</s>", "\n\n"],
            )
            result_text = response["choices"][0]["text"].strip()
            
            # ARCH-002: Log LLM call for transparency
            latency_ms = (time.time() - start_time) * 1000
            tokens_in = estimate_tokens(prompt)
            tokens_out = estimate_tokens(result_text)
            logger.debug(
                f"[ARCH-002] LLM call: model={self.backend.value}/{self.model_path.name if self.model_path else 'unknown'}, "
                f"tokens_in≈{tokens_in}, tokens_out≈{tokens_out}, "
                f"latency={latency_ms:.1f}ms, json_mode={json_mode}"
            )
            
            return result_text

        elif self.backend == LLMBackend.OLLAMA:
            # Use OllamaClient for inference with timeout
            options = {
                "temperature": temperature,
                "top_p": self.config.top_p,
                "num_predict": max_tokens,
            }
            
            # Get GPU recommendations if available (apply FIRST so we can override)
            gpu_info = self.llm.detect_gpu()
            if gpu_info.get("available"):
                recommended = self.llm.get_recommended_options(gpu_info)
                options.update(recommended)
            
            # TICKET 3 (P0): Optimize stop tokens for JSON mode
            # Removed "\n\n" stop token as it can truncate valid JSON with double newlines
            # Keep only "```" to prevent markdown wrapping
            if json_mode:
                options["stop"] = [
                    "```",         # Code block end (prevents markdown wrapping)
                ]
                # CRITICAL: Reduce max tokens for JSON mode since plans are compact
                # A well-structured JSON plan rarely needs more than LLM_JSON_MODE_MAX_TOKENS
                # This prevents the model from generating excessive output
                if max_tokens > LLM_JSON_MODE_MAX_TOKENS:
                    options["num_predict"] = LLM_JSON_MODE_MAX_TOKENS
                    logger.info(f"📉 JSON mode: num_predict={LLM_JSON_MODE_MAX_TOKENS}, stop={options['stop']}")
            
            # Update timeout on client if needed
            original_timeout = self.llm.timeout
            if timeout_override:
                self.llm.timeout = int(timeout_ms / 1000)
            
            # TICKET-315: Set format to "json" if json_mode is enabled
            # This forces Qwen 2.5 to output ONLY valid JSON, not text
            fmt = "json" if json_mode else None
            
            # Log the actual parameters being sent to Ollama
            logger.info(f"🔧 Ollama: format={fmt}, num_predict={options.get('num_predict')}, stop={options.get('stop')}")
            
            try:
                # Use generate API
                for response in self.llm.generate(
                    model=self.model_name,
                    prompt=prompt,
                    format=fmt,  # Pass format parameter for JSON mode
                    stream=False,
                    options=options,
                ):
                    if "error" in response:
                        raise Exception(response["error"])
                    if "response" in response:
                        result_text = response["response"].strip()
                        
                        # ARCH-002: Log LLM call for transparency
                        latency_ms = (time.time() - start_time) * 1000
                        tokens_in = estimate_tokens(prompt)
                        tokens_out = estimate_tokens(result_text)
                        logger.debug(
                            f"[ARCH-002] LLM call: model={self.backend.value}/{self.model_name}, "
                            f"tokens_in≈{tokens_in}, tokens_out≈{tokens_out}, "
                            f"latency={latency_ms:.1f}ms, json_mode={json_mode}"
                        )
                        
                        return result_text
                
                raise Exception("No response from Ollama")
            finally:
                # Restore original timeout
                if timeout_override:
                    self.llm.timeout = original_timeout

        elif self.backend == LLMBackend.MOCK:
            return self._mock_inference(prompt)

        else:
            raise ValueError(f"Unsupported backend: {self.backend}")
    
    # TICKET-REFACTOR-002: Auto-repair methods removed (were for generate_structured_plan)

    def _build_parse_prompt(
        self,
        text: str,
        language: str,
        context: Optional[Dict[str, Any]],
    ) -> str:
        """Build prompt for command parsing"""
        # Load system prompt from template
        system = load_prompt("parse_command", language)
        
        # Fallback to hardcoded if template loading fails
        if system is None:
            logger.warning("Failed to load parse_command template, using fallback")
            if language == "fr":
                system = "Tu es un agent d'automatisation macOS intelligent."
            else:
                system = "You are an intelligent macOS automation agent."

        prompt = f"{system}\n\nCommande: {text}\n\nRéponds uniquement avec du JSON valide:"

        # Add context if available
        if context:
            ctx_str = f"\nContexte: {json.dumps(context, ensure_ascii=False)}"
            prompt = prompt.replace("Réponds uniquement", ctx_str + "\n\nRéponds uniquement")

        return prompt



    # TICKET-REFACTOR-002: _build_structured_plan_prompt removed (for generate_structured_plan)


    def _build_replan_vision_prompt(
        self,
        failed_action: Dict[str, Any],
        error: str,
        screenshot_description: str,
        execution_context: Optional[Dict[str, Any]],
        language: str,
    ) -> str:
        """
        Build prompt for vision-based re-planning after failure.
        
        DEPRECATED (TICKET-AUDIT-004): Vision-based replanning is deprecated.
        Returns a simple fallback prompt.
        """
        logger.warning("_build_replan_vision_prompt is deprecated - use ReAct loop instead")
        
        if language == "fr":
            system = """Tu es un expert en récupération d'erreurs UI (mode legacy).
Analyse l'écran et génère des étapes correctives minimales."""
        else:
            system = """You are a UI error recovery expert (legacy mode).
Analyze the screen and generate minimal corrective steps."""

        # Extract context information
        current_context = execution_context.get("current_context", {}) if execution_context else {}
        app = current_context.get("app", "unknown")
        surface = current_context.get("surface", "unknown")
        url = current_context.get("url", "")
        domain = current_context.get("domain", "")

        prompt = f"""{system}

CONTEXTE ACTUEL:
- Application: {app}
- Surface: {surface}
- URL: {url}
- Domaine: {domain}

ACTION QUI A ÉCHOUÉ:
{json.dumps(failed_action, ensure_ascii=False)}

ERREUR:
{error}

ÉTAT DE L'ÉCRAN (Vision):
{screenshot_description}
"""

        if execution_context and "completed_steps" in execution_context:
            completed = execution_context["completed_steps"]
            if completed:
                prompt += f"\nÉtapes déjà réussies: {len(completed)} étapes\n"

        prompt += """
RAPPEL: Génère UNIQUEMENT les 2-3 étapes correctives minimales (pas le plan complet).
Base-toi sur ce que tu vois dans le screenshot pour trouver une alternative.

Génère le plan de correction JSON:"""
        
        return prompt

    # TICKET-REFACTOR-002: _build_react_prompt, _build_reflex_prompt, _parse_react_response
    # moved to ActionCoordinator
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured format"""
        try:
            # Try to extract JSON from response
            # Handle cases where LLM adds text before/after JSON
            start = response.find("{")
            end = response.rfind("}") + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)

                # Validate structure
                if "intents" in data:
                    return {
                        "intents": data["intents"],
                        "confidence": data.get("confidence", 0.8),
                    }

            # If parsing fails, return low confidence
            return {
                "intents": [],
                "confidence": 0.0,
                "error": "Failed to parse LLM response",
            }

        except json.JSONDecodeError:
            return {
                "intents": [],
                "confidence": 0.0,
                "error": "Invalid JSON in LLM response",
            }



    # TICKET-REFACTOR-002: _parse_structured_plan_response removed (for generate_structured_plan)
    
    def _create_empty_context_v3(self) -> Dict[str, Any]:
        """Create empty V3 context structure"""
        return {
            "app": None,
            "surface": None,
            "url": None,
            "domain": None,
            "thread": None,
            "record": None
        }
    
    def _mock_inference(self, prompt: str) -> str:
        """
        Mock inference for testing - delegates to MockReasoner.
        
        Returns responses based on fixture templates loaded from JSON files.
        Production code uses real LLM backends.
        """
        # Lazy load MockReasoner on first use
        if not hasattr(self, '_mock_reasoner'):
            from janus.ai.reasoning.mock_reasoner import MockReasoner
            self._mock_reasoner = MockReasoner()
        
        return self._mock_reasoner.generate_response(prompt)





    def _update_metrics(self, latency_ms: float):
        """Update performance metrics"""
        self.metrics["total_calls"] += 1
        self.metrics["total_time_ms"] += latency_ms
        self.metrics["avg_latency_ms"] = self.metrics["total_time_ms"] / self.metrics["total_calls"]

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics with comparison data"""
        # Calculate average latencies for comparison
        llm_avg = (
            self.metrics["llm_total_time_ms"] / self.metrics["llm_calls"]
            if self.metrics["llm_calls"] > 0
            else 0.0
        )
        fallback_avg = (
            self.metrics["fallback_total_time_ms"] / self.metrics["fallback_count"]
            if self.metrics["fallback_count"] > 0
            else 0.0
        )

        return {
            **self.metrics,
            "available": self.available,
            "backend": self.backend.value,
            "model": self.model_name or (self.model_path.name if self.model_path else None),
            "llm_avg_latency_ms": llm_avg,
            "fallback_avg_latency_ms": fallback_avg,
            "llm_usage_percent": (
                (self.metrics["llm_calls"] / self.metrics["total_calls"] * 100)
                if self.metrics["total_calls"] > 0
                else 0.0
            ),
        }

    def reset_metrics(self):
        """Reset performance metrics"""
        self.metrics = {
            "total_calls": 0,
            "total_time_ms": 0.0,
            "avg_latency_ms": 0.0,
            "fallback_count": 0,
            "timeout_count": 0,
            "llm_calls": 0,
            "llm_total_time_ms": 0.0,
            "fallback_total_time_ms": 0.0,
        }

    def get_performance_comparison(self) -> Dict[str, Any]:
        """
        Get detailed performance comparison between LLM and fallback parser

        Returns:
            Dictionary with comparative metrics
        """
        metrics = self.get_metrics()

        comparison = {
            "backend": metrics["backend"],
            "model": metrics["model"],
            "llm_available": metrics["available"],
            "total_calls": metrics["total_calls"],
            "llm_calls": metrics["llm_calls"],
            "fallback_calls": metrics["fallback_count"],
            "llm_avg_latency_ms": metrics["llm_avg_latency_ms"],
            "fallback_avg_latency_ms": metrics["fallback_avg_latency_ms"],
            "overall_avg_latency_ms": metrics["avg_latency_ms"],
            "llm_usage_percent": metrics["llm_usage_percent"],
            "timeout_count": metrics["timeout_count"],
        }

        # Add performance rating
        if metrics["available"] and metrics["llm_calls"] > 0:
            if metrics["llm_avg_latency_ms"] < 500:
                comparison["performance_rating"] = "excellent"
            elif metrics["llm_avg_latency_ms"] < 800:
                comparison["performance_rating"] = "good"
            else:
                comparison["performance_rating"] = "acceptable"
        else:
            comparison["performance_rating"] = "fallback_only"

        # Speed comparison
        if metrics["fallback_count"] > 0 and metrics["llm_calls"] > 0:
            speedup = metrics["fallback_avg_latency_ms"] / metrics["llm_avg_latency_ms"]
            comparison["llm_speedup_factor"] = speedup
            if speedup > 1:
                comparison["speed_comparison"] = f"LLM is {speedup:.1f}x faster than fallback"
            else:
                comparison["speed_comparison"] = f"Fallback is {1/speedup:.1f}x faster than LLM"

        return comparison
    
    # ============================================================================
    # CORE-FOUNDATION-002: Burst OODA Mode
    # ============================================================================
    
    def decide_burst_actions(
        self,
        user_goal: str,
        system_state: Dict[str, Any],
        visual_context: str,
        action_history: List[Any],
        language: str = "fr",
        force_vision: bool = False,
        skill_hint: Optional[str] = None  # LEARNING-001
    ) -> Dict[str, Any]:
        """
        Generate a burst of 2-6 actions to execute together.
        
        CORE-FOUNDATION-002: Burst OODA pattern to reduce LLM calls.
        Instead of returning one action, returns a burst of actions that can
        be executed together before re-observing.
        
        LEARNING-001: Accepts optional skill hint as context suggestion.
        
        Args:
            user_goal: The user's goal
            system_state: Current system state (app, url, clipboard, etc.)
            visual_context: Visual elements from Set-of-Marks
            action_history: List of previous action results
            language: Language for prompt (fr/en)
            force_vision: Force needs_vision=True (e.g., after stagnation)
            skill_hint: Optional learned skill hint (suggestion, not execution)
        
        Returns:
            Dict with:
            - actions: List of {module, action, args, reasoning} (2-6 items)
            - stop_when: List of {type, value} stop conditions
            - needs_vision: bool indicating if vision is needed after burst
            - reasoning: Overall reasoning for the burst
            
            Or error dict:
            - error: error message
            - error_type: error type
        """
        if not self.available:
            logger.error("🔥 LLM not available - cannot generate burst actions")
            return {
                "error": "LLM unavailable",
                "error_type": "llm_unavailable"
            }
        
        try:
            start_time = time.time()
            
            # Build burst prompt
            prompt = self._build_burst_prompt(
                user_goal,
                system_state,
                visual_context,
                action_history,
                language,
                force_vision,
                skill_hint  # LEARNING-001
            )
            
            # Run inference with json_mode
            # TICKET 3 (P0): Reduced from 512 to 256 for faster burst decisions
            response = self.run_inference(prompt, max_tokens=256, json_mode=True)
            
            # Parse burst response
            result = self._parse_burst_response(response, force_vision)
            
            # Track metrics
            self.metrics["llm_calls"] += 1
            llm_time = (time.time() - start_time) * 1000
            self.metrics["llm_total_time_ms"] += llm_time
            self._update_metrics(llm_time)
            
            logger.debug(f"Generated burst with {len(result.get('actions', []))} actions in {llm_time:.2f}ms")
            
            return result
            
        except TimeoutError:
            logger.error("❌ LLM timeout during burst decision")
            self.metrics["timeout_count"] += 1
            return {
                "error": "LLM timeout",
                "error_type": "timeout"
            }
        
        except Exception as e:
            logger.error(f"❌ Burst decision failed: {e}", exc_info=True)
            return {
                "error": str(e),
                "error_type": "generation_error"
            }
    
    def _build_burst_prompt(
        self,
        user_goal: str,
        system_state: Dict[str, Any],
        visual_context: str,
        action_history: List[Any],
        language: str,
        force_vision: bool,
        skill_hint: Optional[str] = None  # LEARNING-001
    ) -> str:
        """
        Build prompt for burst action generation with budget control.
        
        PERF-001: Uses ContextAssembler to enforce budget limits.
        LEARNING-001: Integrates skill hints as suggestions (not commands).
        """
        
        # TICKET 3 (P0): Use compact schema to reduce token usage
        from janus.runtime.core.module_action_schema import get_compact_schema_section
        schema_section = get_compact_schema_section(language=language, top_k=4)
        
        # PERF-001 + LEARNING-001: Assemble context with budget enforcement
        budgeted_context = self.context_assembler.assemble_context(
            visual_context=visual_context,
            action_history=action_history,
            schema_section=schema_section,
            system_state=system_state,
            skill_hint=skill_hint  # LEARNING-001
        )
        
        # Extract budgeted components
        budgeted_visual = budgeted_context["visual_context"]
        budgeted_history = budgeted_context["action_history"]
        budgeted_schema = budgeted_context["schema_section"]
        budgeted_state = budgeted_context["system_state"]
        budgeted_hint = budgeted_context.get("skill_hint", "")  # LEARNING-001
        context_metrics = budgeted_context["metrics"]
        
        # Log budget metrics (LEARNING-001: include skill hint)
        logger.debug(
            f"Context budget: {context_metrics.total_tokens} tokens "
            f"(SOM:{context_metrics.som_tokens}, Mem:{context_metrics.memory_tokens}, "
            f"Tools:{context_metrics.tools_tokens}, State:{context_metrics.system_state_tokens}, "
            f"Hint:{context_metrics.skill_hint_tokens})"
        )
        if context_metrics.over_budget:
            logger.warning(
                f"⚠️ Context over budget by {context_metrics.budget_exceeded_by} tokens. "
                f"Shrinking applied: SOM={context_metrics.som_shrunk}, "
                f"Memory={context_metrics.memory_shrunk}, Tools={context_metrics.tools_shrunk}, "
                f"Hint={context_metrics.skill_hint_shrunk}"
            )
        
        # Format history
        history_txt = "Aucune action."
        if budgeted_history:
            history_txt = "\n".join([
                f"- {res.action_type if hasattr(res, 'action_type') else res.get('action_type', 'unknown')}: "
                f"{'SUCCÈS' if (res.success if hasattr(res, 'success') else res.get('success', False)) else 'ÉCHEC'} "
                f"({res.message if hasattr(res, 'message') else res.get('message', '')})"
                for res in budgeted_history
            ])
        
        if language == "fr":
            vision_hint = "\n⚠️ IMPORTANT: Mets needs_vision=true dans ta réponse!" if force_vision else ""
            
            # LEARNING-001: Add skill hint section if available
            hint_section = ""
            if budgeted_hint:
                hint_section = f"\n\n{budgeted_hint}\n"
            
            return f"""Tu es un assistant GUI expert qui génère des BURSTS d'actions (2-6 actions).

OBJECTIF: {user_goal}

HISTORIQUE:
{history_txt}

ÉTAT ACTUEL:
- App: {budgeted_state.get('active_app', 'Unknown')}
- URL: {budgeted_state.get('url', '')}
- Titre fenêtre: {budgeted_state.get('window_title', '')}
{hint_section}
{budgeted_schema}

ÉLÉMENTS VISUELS:
{budgeted_visual}

💡 UTILISATION DES ÉLÉMENTS VISUELS:
Pour cliquer sur un élément visuel, utilise ui.click avec:
- element_id: le numéro ID de l'élément (ex: {{"element_id": "2"}})
- OU text: le texte de l'élément (ex: {{"text": "Forgive - Burial"}})
Les IDs correspondent aux éléments listés dans ÉLÉMENTS VISUELS ci-dessus.

⚠️ FORMAT DE RÉPONSE OBLIGATOIRE (BURST MODE):
Tu DOIS répondre en JSON avec cette structure EXACTE:
{{
  "actions": [
    {{"module": "nom_module", "action": "nom_action", "args": {{}}, "reasoning": "pourquoi cette action"}},
    {{"module": "nom_module", "action": "nom_action", "args": {{}}, "reasoning": "pourquoi cette action"}}
  ],
  "stop_when": [
    {{"type": "url_contains", "value": "youtube.com"}},
    {{"type": "ui_element_visible", "value": "Search"}}
  ],
  "needs_vision": false,
  "reasoning": "Explication globale du burst"
}}

RÈGLES BURST:
1. Génère 2-6 actions atomiques qui peuvent s'exécuter ensemble
2. "stop_when" liste les conditions pour arrêter et réobserver (url_contains, ui_element_visible, app_active, window_title_contains, clipboard_contains)
3. "needs_vision" = true si tu as besoin de vision après le burst (ex: pour vérifier résultat visuel)
4. Si objectif atteint, dernière action doit être {{"module": "system", "action": "done", "args": {{}}}}
5. Pense "burst" = séquence rapide sans réobservation entre chaque action{vision_hint}

IMPORTANT:
- Chaque action doit avoir "module" (obligatoire), "action" (obligatoire), "args", "reasoning"
- Ne génère PAS qu'une seule action - c'est un BURST (minimum 2)
- Les actions doivent être atomiques et exécutables séquentiellement

Quel est le prochain burst d'actions ?"""
        
        else:  # English
            vision_hint = "\n⚠️ IMPORTANT: Set needs_vision=true in your response!" if force_vision else ""
            
            # LEARNING-001: Add skill hint section if available
            hint_section = ""
            if budgeted_hint:
                hint_section = f"\n\n{budgeted_hint}\n"
            
            return f"""You are a GUI expert that generates BURSTS of actions (2-6 actions).

GOAL: {user_goal}

HISTORY:
{history_txt}

CURRENT STATE:
- App: {budgeted_state.get('active_app', 'Unknown')}
- URL: {budgeted_state.get('url', '')}
- Window Title: {budgeted_state.get('window_title', '')}
{hint_section}
{budgeted_schema}

VISUAL ELEMENTS:
{budgeted_visual}

💡 USING VISUAL ELEMENTS:
To click on a visual element, use ui.click with:
- element_id: the ID number of the element (e.g., {{"element_id": "2"}})
- OR text: the text of the element (e.g., {{"text": "Forgive - Burial"}})
The IDs correspond to the elements listed in VISUAL ELEMENTS above.

⚠️ REQUIRED RESPONSE FORMAT (BURST MODE):
You MUST respond in JSON with this EXACT structure:
{{
  "actions": [
    {{"module": "module_name", "action": "action_name", "args": {{}}, "reasoning": "why this action"}},
    {{"module": "module_name", "action": "action_name", "args": {{}}, "reasoning": "why this action"}}
  ],
  "stop_when": [
    {{"type": "url_contains", "value": "youtube.com"}},
    {{"type": "ui_element_visible", "value": "Search"}}
  ],
  "needs_vision": false,
  "reasoning": "Overall explanation of burst"
}}

BURST RULES:
1. Generate 2-6 atomic actions that can execute together
2. "stop_when" lists conditions to stop and re-observe (url_contains, ui_element_visible, app_active, window_title_contains, clipboard_contains)
3. "needs_vision" = true if you need vision after burst (e.g., to verify visual result)
4. If goal achieved, last action must be {{"module": "system", "action": "done", "args": {{}}}}
5. Think "burst" = quick sequence without re-observation between actions{vision_hint}

IMPORTANT:
- Each action must have "module" (required), "action" (required), "args", "reasoning"
- Do NOT generate just one action - this is a BURST (minimum 2)
- Actions must be atomic and executable sequentially

What is the next burst of actions?"""
    
    def _parse_burst_response(self, response: str, force_vision: bool = False) -> Dict[str, Any]:
        """
        Parse burst response from LLM.
        
        Returns:
            Dict with actions, stop_when, needs_vision, reasoning
            Or error dict with error and error_type
        """
        try:
            # Extract JSON from response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start < 0:
                return {
                    "error": "No JSON found in response",
                    "error_type": "invalid_json"
                }
            
            data = json.loads(response[start:end])
            
            # Validate required fields
            if "actions" not in data:
                return {
                    "error": "Missing required field 'actions'",
                    "error_type": "invalid_burst_schema"
                }
            
            actions = data["actions"]
            
            # Validate actions is a list
            if not isinstance(actions, list):
                return {
                    "error": "'actions' must be a list",
                    "error_type": "invalid_burst_schema"
                }
            
            # Validate burst size (2-6 actions unless it's a single "done")
            if len(actions) < 1:
                return {
                    "error": "Burst must contain at least 1 action",
                    "error_type": "invalid_burst_size"
                }
            
            # Allow single action only if it's "done"
            if len(actions) == 1 and actions[0].get("action") != "done":
                return {
                    "error": "Burst must contain 2-6 actions (unless single 'done' action)",
                    "error_type": "invalid_burst_size"
                }
            
            if len(actions) > 6:
                # Truncate to 6 actions with warning
                logger.warning(f"Burst has {len(actions)} actions, truncating to 6")
                actions = actions[:6]
                data['actions'] = actions  # Update data dict to reflect truncation
            
            # Validate each action
            from janus.runtime.core.module_action_schema import validate_action_step
            
            validated_actions = []
            for i, action in enumerate(actions):
                # Validate required fields
                if "module" not in action or "action" not in action:
                    return {
                        "error": f"Action {i} missing 'module' or 'action' field",
                        "error_type": "invalid_action_schema"
                    }
                
                # Special case: "done" action is always valid
                if action["action"] == "done":
                    validated_actions.append({
                        "module": action.get("module", "system"),
                        "action": "done",
                        "args": action.get("args", {}),
                        "reasoning": action.get("reasoning", "Goal achieved")
                    })
                    continue
                
                # Validate against schema
                is_valid, error_msg = validate_action_step({
                    "module": action["module"],
                    "action": action["action"],
                    "args": action.get("args", {})
                })
                
                if not is_valid:
                    return {
                        "error": f"Action {i} validation failed: {error_msg}",
                        "error_type": "invalid_action"
                    }
                
                validated_actions.append({
                    "module": action["module"],
                    "action": action["action"],
                    "args": action.get("args", {}),
                    "reasoning": action.get("reasoning", "")
                })
            
            # Parse stop conditions
            stop_when = []
            for sc in data.get("stop_when", []):
                if isinstance(sc, dict) and "type" in sc and "value" in sc:
                    # Validate stop condition type
                    valid_types = ["url_contains", "url_equals", "ui_element_visible", 
                                   "ui_element_contains_text", "app_active", 
                                   "window_title_contains", "clipboard_contains"]
                    if sc["type"] in valid_types:
                        stop_when.append(sc)
                    else:
                        logger.warning(f"Invalid stop condition type: {sc['type']}")
            
            # Parse needs_vision (with force override)
            needs_vision = force_vision or data.get("needs_vision", False)
            
            return {
                "actions": validated_actions,
                "stop_when": stop_when,
                "needs_vision": needs_vision,
                "reasoning": data.get("reasoning", "")
            }
            
        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON: {e}",
                "error_type": "invalid_json"
            }
        
        except Exception as e:
            logger.error(f"Unexpected error in _parse_burst_response: {e}", exc_info=True)
            return {
                "error": f"Parse error: {e}",
                "error_type": "parse_error"
            }
