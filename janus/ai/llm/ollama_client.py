"""
Ollama REST API Client
Provides comprehensive integration with Ollama local LLM server

Features:
- Model management (list, pull, delete)
- Streaming and non-streaming inference
- GPU detection and configuration
- Health checks and connection management
"""

import json
import platform
import subprocess
import time
import warnings
from typing import Any, Dict, Generator, List, Optional, Tuple

import requests

from janus.constants import (
    NETWORK_TIMEOUT,
    OLLAMA_DEFAULT_ENDPOINT,
    OLLAMA_HEALTH_CHECK_TIMEOUT,
    OLLAMA_TAGS_PATH,
)
from janus.logging import get_logger
from janus.ai.llm.retry_handler import get_retry_handler, LLMRetryHandler, RetryConfig
from janus.safety.circuit_breaker import get_circuit_breaker, CircuitBreakerError, CircuitBreakerConfig

# Streaming timeout configuration (PROBLEM 3: Fix infinite timeout)
STREAMING_CHUNK_TIMEOUT = 60  # 60s max between two chunks


class OllamaClient:
    """
    Client for interacting with Ollama REST API
    
    Provides model management, inference with streaming support,
    and GPU detection capabilities.
    """
    
    # TICKET-ARCHI: Performance thresholds for monitoring
    SLOW_PERFORMANCE_THRESHOLD = 20  # tokens/s below which we warn
    FAST_PERFORMANCE_THRESHOLD = 40  # tokens/s for "fast" emoji

    def __init__(
        self,
        base_url: str = OLLAMA_DEFAULT_ENDPOINT,
        timeout: int = NETWORK_TIMEOUT,
    ):
        """
        Initialize Ollama client
        
        Args:
            base_url: Ollama server base URL
            timeout: Default timeout for API requests
        """
        self.base_url = base_url.rstrip("/")
        # Ensure timeout is valid (must be > 0)
        if timeout is None or timeout <= 0:
            self.logger = get_logger("ollama_client")
            self.logger.warning(f"Invalid timeout value ({timeout}), using default {NETWORK_TIMEOUT}")
            timeout = NETWORK_TIMEOUT
        self.timeout = timeout
        self.logger = get_logger("ollama_client")
        self._available = None
        self._gpu_info = None
        
        # ✅ RESILIENCE: Initialize retry handler (PROBLEM 2)
        self.retry_handler = get_retry_handler()
        
        # ✅ RESILIENCE: Initialize circuit breaker (PROBLEM 5)
        # Protects against repeated failures when Ollama service is down
        self.circuit_breaker = get_circuit_breaker(
            f"ollama_{base_url}",
            CircuitBreakerConfig(
                failure_threshold=5,      # Open circuit after 5 failures
                success_threshold=2,      # Close circuit after 2 successes
                timeout_seconds=60.0,     # Try again after 60s
            )
        )

    def is_available(self) -> bool:
        """
        Check if Ollama server is available
        
        Returns:
            True if server is responding, False otherwise
        """
        if self._available is not None:
            return self._available
            
        try:
            response = requests.get(
                f"{self.base_url}{OLLAMA_TAGS_PATH}",
                timeout=OLLAMA_HEALTH_CHECK_TIMEOUT,
            )
            self._available = response.status_code == 200
            return self._available
        except Exception as e:
            self.logger.debug(f"Ollama server not available: {e}")
            self._available = False
            return False

    def get_version(self) -> Optional[str]:
        """
        Get Ollama version
        
        Returns:
            Version string or None if not available
        """
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            self.logger.debug(f"Could not get Ollama version: {e}")
        return None

    def list_models(self) -> List[Dict[str, Any]]:
        """
        List all available models in Ollama
        
        Returns:
            List of model dictionaries with metadata
        """
        try:
            response = requests.get(
                f"{self.base_url}{OLLAMA_TAGS_PATH}",
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            self.logger.error(f"Failed to list models: {e}")
            return []

    def model_exists(self, model_name: str) -> bool:
        """
        Check if a specific model exists locally
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            True if model exists, False otherwise
        """
        models = self.list_models()
        # Use exact match or prefix match for versioned models
        for model in models:
            model_full_name = model.get("name", "")
            # Exact match
            if model_full_name == model_name:
                return True
            # Prefix match for versioned models (e.g., "mistral" matches "mistral:7b")
            if model_full_name.startswith(model_name + ":"):
                return True
            # Reverse match: if we ask for "llama3.2:latest" but only "llama3.2" is listed
            if model_name.startswith(model_full_name + ":"):
                return True
        return False

    def pull_model(
        self,
        model_name: str,
        stream: bool = True,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Pull a model from Ollama library
        
        Args:
            model_name: Name of the model to pull
            stream: Whether to stream progress updates
            
        Yields:
            Progress dictionaries with status and completion info
        """
        try:
            payload = {"name": model_name, "stream": stream}
            
            response = requests.post(
                f"{self.base_url}/api/pull",
                json=payload,
                stream=stream,
                timeout=None if stream else self.timeout,
            )
            response.raise_for_status()
            
            if stream:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            yield data
                        except json.JSONDecodeError:
                            continue
            else:
                yield response.json()
                
        except Exception as e:
            self.logger.error(f"Failed to pull model {model_name}: {e}")
            yield {"status": "error", "error": str(e)}

    def delete_model(self, model_name: str) -> Tuple[bool, str]:
        """
        Delete a model from local storage
        
        Args:
            model_name: Name of the model to delete
            
        Returns:
            Tuple of (success, message)
        """
        try:
            response = requests.delete(
                f"{self.base_url}/api/delete",
                json={"name": model_name},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return True, f"Successfully deleted model: {model_name}"
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return False, f"Model not found: {model_name}"
            return False, f"Failed to delete model: {e}"
        except Exception as e:
            self.logger.error(f"Failed to delete model {model_name}: {e}")
            return False, f"Error deleting model: {str(e)}"

    def generate(
        self,
        model: str,
        prompt: str,
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None,
        system: Optional[str] = None,
        template: Optional[str] = None,
        context: Optional[List[int]] = None,
        format: Optional[str] = None,
        raw: bool = False,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Generate text completion with optional streaming
        
        Args:
            model: Model name to use
            prompt: Input prompt
            stream: Whether to stream the response
            options: Model parameters (temperature, top_p, etc.)
            system: System message
            template: Prompt template
            context: Conversation context
            format: Output format (e.g., "json" to force JSON output)
            raw: Whether to use raw mode (no formatting)
            
        Yields:
            Response dictionaries with generated text
        """
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": stream,
                "keep_alive": "5m",  # Keep model loaded for 5 minutes to avoid cold starts
            }
            
            if options:
                payload["options"] = options
            if system:
                payload["system"] = system
            if template:
                payload["template"] = template
            if context:
                payload["context"] = context
            if format:
                payload["format"] = format
            if raw:
                payload["raw"] = raw
            
            # Log the actual payload being sent (excluding long prompts)
            log_payload = {k: v for k, v in payload.items() if k != "prompt"}
            log_payload["prompt_length"] = len(prompt) if prompt else 0
            self.logger.info(f"📤 Ollama API request: {log_payload}")
            
            # ✅ RESILIENCE: Wrap request in circuit breaker + retry handler (PROBLEMS 2 & 5)
            # Circuit breaker fails fast if service is known to be down
            # Retry handler handles transient failures with exponential backoff
            # ✅ STABILITY: Fix streaming timeout (PROBLEM 3)
            # For streaming: Use tuple (connect_timeout, read_timeout) to avoid infinite hangs
            # - connect_timeout: Time to establish connection (10s)
            # - read_timeout: Time between chunks (60s) - prevents hang if server stops sending data
            # For non-streaming: Use single timeout value for entire request
            def _make_request_with_retry():
                def _make_request():
                    return requests.post(
                        f"{self.base_url}/api/generate",
                        json=payload,
                        stream=stream,
                        timeout=(10, STREAMING_CHUNK_TIMEOUT) if stream else self.timeout,
                    )
                
                return self.retry_handler.execute_with_retry(
                    _make_request,
                    operation_name=f"Ollama generate ({model})"
                )
            
            # Execute through circuit breaker for fail-fast protection
            response = self.circuit_breaker.call(_make_request_with_retry)
            response.raise_for_status()
            
            if stream:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            yield data
                        except json.JSONDecodeError:
                            continue
            else:
                result = response.json()
                # Log token counts from the response
                eval_count = result.get("eval_count", 0)
                prompt_eval_count = result.get("prompt_eval_count", 0)
                total_duration_ns = result.get("total_duration", 0)
                total_duration_s = total_duration_ns / 1_000_000_000 if total_duration_ns else 0
                
                # TICKET-ARCHI: Calculate and log tokens/second for performance monitoring
                # This helps identify if GPU acceleration is working properly
                # Expected on M4 with Metal: 60-80 tokens/s for 7B models
                tokens_per_sec = 0
                if total_duration_s > 0 and eval_count > 0:
                    tokens_per_sec = eval_count / total_duration_s
                
                # Log with performance warning if too slow
                perf_emoji = "⚡" if tokens_per_sec >= self.FAST_PERFORMANCE_THRESHOLD else "🐌"
                self.logger.info(
                    f"{perf_emoji} Ollama response: "
                    f"prompt_tokens={prompt_eval_count}, "
                    f"output_tokens={eval_count}, "
                    f"total_time={total_duration_s:.1f}s, "
                    f"speed={tokens_per_sec:.1f} tokens/s"
                )
                
                # TICKET-ARCHI: Warn if performance is significantly below expected
                if tokens_per_sec > 0 and tokens_per_sec < self.SLOW_PERFORMANCE_THRESHOLD:
                    self.logger.warning(
                        f"⚠️  Low inference speed ({tokens_per_sec:.1f} tokens/s). "
                        f"Expected 60-80 tokens/s on M4 with Metal GPU. "
                        f"Check: 1) GPU is enabled, 2) Model size fits in memory, 3) No thermal throttling"
                    )
                
                yield result
                
        except CircuitBreakerError as e:
            # Circuit breaker is open - service known to be down
            self.logger.error(f"Circuit breaker open for Ollama service: {e}")
            yield {"error": f"Service unavailable: {str(e)}"}
        except Exception as e:
            self.logger.error(f"Failed to generate with model {model}: {e}")
            yield {"error": str(e)}

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Chat completion with conversation history
        
        Args:
            model: Model name to use
            messages: List of message dictionaries with role and content
            stream: Whether to stream the response
            options: Model parameters
            
        Yields:
            Response dictionaries with assistant messages
        """
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": stream,
            }
            
            if options:
                payload["options"] = options
            
            # ✅ RESILIENCE: Wrap request in circuit breaker + retry handler (PROBLEMS 2 & 5)
            # Circuit breaker fails fast if service is known to be down
            # Retry handler handles transient failures with exponential backoff
            # ✅ STABILITY: Fix streaming timeout (PROBLEM 3)
            # For streaming: Use tuple (connect_timeout, read_timeout) to avoid infinite hangs
            # - connect_timeout: Time to establish connection (10s)
            # - read_timeout: Time between chunks (60s) - prevents hang if server stops sending data
            # For non-streaming: Use single timeout value for entire request
            def _make_request_with_retry():
                def _make_request():
                    return requests.post(
                        f"{self.base_url}/api/chat",
                        json=payload,
                        stream=stream,
                        timeout=(10, STREAMING_CHUNK_TIMEOUT) if stream else self.timeout,
                    )
                
                return self.retry_handler.execute_with_retry(
                    _make_request,
                    operation_name=f"Ollama chat ({model})"
                )
            
            # Execute through circuit breaker for fail-fast protection
            response = self.circuit_breaker.call(_make_request_with_retry)
            response.raise_for_status()
            
            if stream:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            yield data
                        except json.JSONDecodeError:
                            continue
            else:
                yield response.json()
                
        except CircuitBreakerError as e:
            # Circuit breaker is open - service known to be down
            self.logger.error(f"Circuit breaker open for Ollama service: {e}")
            yield {"error": f"Service unavailable: {str(e)}"}
        except Exception as e:
            self.logger.error(f"Failed to chat with model {model}: {e}")
            yield {"error": str(e)}

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific model
        
        Args:
            model_name: Name of the model
            
        Returns:
            Model information dictionary or None if not found
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": model_name},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Failed to get model info for {model_name}: {e}")
            return None

    def detect_gpu(self) -> Dict[str, Any]:
        """
        Detect GPU availability and configuration
        
        Returns:
            Dictionary with GPU information
        """
        if self._gpu_info is not None:
            return self._gpu_info
            
        gpu_info = {
            "available": False,
            "type": None,
            "devices": [],
            "memory": None,
        }
        
        system = platform.system()
        
        try:
            # Check for NVIDIA GPUs
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    gpu_info["available"] = True
                    gpu_info["type"] = "cuda"
                    for line in result.stdout.strip().split("\n"):
                        if line:
                            # Use rsplit to handle commas in GPU names
                            parts = line.rsplit(",", 1)
                            if len(parts) == 2:
                                name, memory = parts
                                gpu_info["devices"].append({
                                    "name": name.strip(),
                                    "memory": memory.strip(),
                                })
                            else:
                                # Fallback if format is unexpected
                                gpu_info["devices"].append({
                                    "name": line.strip(),
                                    "memory": "Unknown",
                                })
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            
            # Check for AMD ROCm on Linux
            if not gpu_info["available"] and system == "Linux":
                try:
                    result = subprocess.run(
                        ["rocm-smi", "--showproductname"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0 and result.stdout:
                        gpu_info["available"] = True
                        gpu_info["type"] = "rocm"
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
            
            # Check for Apple Metal (M-series chips)
            if system == "Darwin":
                try:
                    result = subprocess.run(
                        ["sysctl", "-n", "machdep.cpu.brand_string"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0 and "Apple" in result.stdout:
                        gpu_info["available"] = True
                        gpu_info["type"] = "metal"
                        gpu_info["devices"].append({
                            "name": result.stdout.strip(),
                            "memory": "Unified Memory",
                        })
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
                    
        except Exception as e:
            self.logger.debug(f"Error detecting GPU: {e}")
        
        self._gpu_info = gpu_info
        return gpu_info

    def get_recommended_options(self, gpu_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get recommended model options based on hardware
        
        TICKET-ARCHI: Optimized for Apple Silicon (Metal GPU)
        - Detects CPU core count for optimal threading
        - Ensures Metal GPU is used on M-series chips
        - Logs configuration for transparency
        
        Args:
            gpu_info: GPU information (auto-detected if not provided)
            
        Returns:
            Dictionary of recommended options
        """
        if gpu_info is None:
            gpu_info = self.detect_gpu()
        
        # TICKET-ARCHI: Auto-detect CPU core count instead of hardcoding 4
        try:
            import os
            cpu_count = os.cpu_count() or 4
            # Use 75% of cores to leave headroom for system
            num_threads = max(4, int(cpu_count * 0.75))
        except Exception:
            num_threads = 4
        
        options = {
            "num_thread": num_threads,
        }
        
        # Adjust for GPU if available
        if gpu_info.get("available"):
            gpu_type = gpu_info.get("type")
            if gpu_type == "cuda":
                options["num_gpu"] = len(gpu_info.get("devices", []))
                self.logger.info(f"🎮 CUDA GPU detected: {len(gpu_info.get('devices', []))} device(s)")
            elif gpu_type == "metal":
                options["num_gpu"] = -1  # Metal uses unified memory
                # TICKET-ARCHI: Log Metal configuration with explicit GPU usage confirmation
                device_name = gpu_info.get("devices", [{}])[0].get("name", "Apple Silicon")
                self.logger.info(
                    f"🎮 Metal GPU enabled: {device_name} (unified memory, num_gpu=-1)"
                )
                self.logger.info(
                    f"💡 GPU acceleration active. "
                    f"Expected performance: 60-80 tokens/s for 7B models on M4"
                )
        else:
            self.logger.warning(f"⚠️  No GPU detected - using CPU only with {num_threads} threads. Performance will be significantly slower.")
                
        return options

    def warmup_model(self, model: str, timeout: Optional[int] = None) -> bool:
        """
        Warm up a model by loading it into memory.
        
        Sends a minimal prompt to force Ollama to load the model into memory.
        This eliminates cold start delays on the first real request.
        
        TICKET-ARCHI: Enhanced to use recommended GPU options during warmup
        to ensure Metal GPU is properly initialized.
        
        Args:
            model: Model name to warm up
            timeout: Optional timeout in seconds (default: 120s for cold start)
            
        Returns:
            True if model was warmed up successfully, False otherwise
        """
        warmup_timeout = timeout if timeout else 120  # 120s default for cold start
        
        self.logger.info(f"Warming up model '{model}'...")
        start_time = time.time()
        
        try:
            # TICKET-ARCHI: Get recommended options to ensure GPU is used during warmup
            gpu_info = self.detect_gpu()
            recommended_opts = self.get_recommended_options(gpu_info)
            
            # Send a minimal prompt to load the model into memory
            payload = {
                "model": model,
                "prompt": "Hello",  # Minimal prompt
                "stream": False,
                "options": {
                    "num_predict": 1,  # Generate only 1 token
                    **recommended_opts,  # Include GPU/thread settings
                },
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=warmup_timeout,
            )
            response.raise_for_status()
            
            duration = time.time() - start_time
            self.logger.info(f"✓ Model '{model}' warmed up successfully in {duration:.2f}s")
            return True
            
        except requests.exceptions.Timeout:
            duration = time.time() - start_time
            self.logger.warning(f"Model warmup timed out after {duration:.2f}s")
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Failed to warm up model '{model}' after {duration:.2f}s: {e}")
            return False

    def embeddings(
        self,
        model: str,
        prompt: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Optional[List[float]]:
        """
        Generate embeddings for text
        
        Args:
            model: Model name to use
            prompt: Text to embed
            options: Model parameters
            
        Returns:
            List of embedding values or None on error
        """
        try:
            payload = {
                "model": model,
                "prompt": prompt,
            }
            
            if options:
                payload["options"] = options
                
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding")
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings: {e}")
            return None
