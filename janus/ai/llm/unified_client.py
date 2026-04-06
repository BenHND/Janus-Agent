"""
UnifiedLLMClient - Single interface for all LLM providers
Replaces the legacy LLMService with a cleaner adapter-based architecture

This module provides a unified interface for interacting with different LLM providers
(OpenAI, Anthropic, Ollama, Mistral, Local models) with consistent error handling,
fallback support, and configuration management.

ARCH-002: Single Source of Truth (SSOT) for all LLM interactions
- All LLM calls go through this client
- Instrumentation for transparency (call_site, model, tokens, latency)
- Centralized configuration from settings.llm.*
"""

import inspect
import json
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List, Optional

from janus.constants import (
    LLM_CONTEXT_SIZE,
    LLM_DEFAULT_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_THREAD_COUNT,
    NETWORK_TIMEOUT,
    OLLAMA_DEFAULT_ENDPOINT,
)
from janus.logging import get_logger
from janus.ai.llm.llm_utils import estimate_tokens

logger = get_logger("unified_llm_client")


# ARCH-002: Global metrics for LLM call tracking
_llm_metrics = {
    "total_calls": 0,
    "total_tokens_in": 0,
    "total_tokens_out": 0,
    "total_latency_ms": 0.0,
    "calls_by_site": {},  # call_site -> count
    "calls_by_model": {},  # model -> count
}


def get_llm_metrics() -> Dict[str, Any]:
    """
    Get global LLM metrics for transparency.
    
    Returns:
        Dictionary with metrics: total_calls, tokens, latency, by site/model
    """
    return _llm_metrics.copy()


def reset_llm_metrics():
    """Reset global LLM metrics (useful for testing)"""
    global _llm_metrics
    _llm_metrics = {
        "total_calls": 0,
        "total_tokens_in": 0,
        "total_tokens_out": 0,
        "total_latency_ms": 0.0,
        "calls_by_site": {},
        "calls_by_model": {},
    }


class LLMClientInterface(ABC):
    """Abstract interface for LLM clients"""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Generate text completion from a prompt
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Provider-specific options
            
        Returns:
            Generated text
        """
        pass

    @abstractmethod
    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Generate chat completion from message history
        
        Args:
            messages: List of chat messages with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Provider-specific options
            
        Returns:
            Generated response text
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM client is available and ready"""
        pass

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Generate streaming response (optional, not all providers support)
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Provider-specific options
            
        Yields:
            Chunks of generated text
        """
        # Default implementation: return full response at once
        response = self.generate(prompt, system_prompt, max_tokens, temperature, **kwargs)
        yield response


class OpenAIClientAdapter(LLMClientInterface):
    """Adapter for OpenAI API"""

    def __init__(
        self,
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        temperature: float = LLM_DEFAULT_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
        timeout: int = NETWORK_TIMEOUT,
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.client = None
        self._available = False
        self._initialize()

    def _initialize(self):
        """Initialize OpenAI client"""
        try:
            import openai

            if self.api_key:
                openai.api_key = self.api_key
                self.client = openai
                self._available = True
                logger.info(f"OpenAI client initialized with model: {self.model}")
            else:
                logger.warning("No OpenAI API key found. Set OPENAI_API_KEY environment variable.")
        except ImportError:
            logger.warning("openai package not installed. Install with: pip install openai")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI: {e}")

    def is_available(self) -> bool:
        return self._available

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        if not self._available:
            raise RuntimeError("OpenAI client not available")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return self.generate_chat(messages, max_tokens, temperature, **kwargs)

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        if not self._available:
            raise RuntimeError("OpenAI client not available")

        try:
            response = self.client.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                timeout=self.timeout,
                **kwargs
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class AnthropicClientAdapter(LLMClientInterface):
    """Adapter for Anthropic Claude API"""

    def __init__(
        self,
        model: str = "claude-3-sonnet-20240229",
        api_key: Optional[str] = None,
        temperature: float = LLM_DEFAULT_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
        timeout: int = NETWORK_TIMEOUT,
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.client = None
        self._available = False
        self._initialize()

    def _initialize(self):
        """Initialize Anthropic client"""
        try:
            import anthropic

            if self.api_key:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self._available = True
                logger.info(f"Anthropic client initialized with model: {self.model}")
            else:
                logger.warning("No Anthropic API key found. Set ANTHROPIC_API_KEY environment variable.")
        except ImportError:
            logger.warning("anthropic package not installed. Install with: pip install anthropic")
        except Exception as e:
            logger.warning(f"Failed to initialize Anthropic: {e}")

    def is_available(self) -> bool:
        return self._available

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        if not self._available:
            raise RuntimeError("Anthropic client not available")

        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
                system=system_prompt or "",
                messages=messages,
                timeout=self.timeout,
                **kwargs
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        if not self._available:
            raise RuntimeError("Anthropic client not available")

        # Extract system message if present
        system_prompt = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
                system=system_prompt,
                messages=user_messages,
                timeout=self.timeout,
                **kwargs
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


class OllamaClientAdapter(LLMClientInterface):
    """Adapter for Ollama local LLM server"""

    def __init__(
        self,
        model: str = "mistral",
        base_url: str = OLLAMA_DEFAULT_ENDPOINT,
        temperature: float = LLM_DEFAULT_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
        timeout: int = NETWORK_TIMEOUT,
    ):
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.client = None
        self._available = False
        self._initialize()

    def _initialize(self):
        """Initialize Ollama client"""
        try:
            from janus.ai.llm.ollama_client import OllamaClient

            self.client = OllamaClient(base_url=self.base_url, timeout=self.timeout)
            
            if not self.client.is_available():
                logger.warning(
                    f"Ollama server not responding at {self.base_url}. "
                    "Make sure Ollama is installed and running (ollama serve)."
                )
                return

            # Auto-download model if not available
            if not self.client.model_exists(self.model):
                logger.info(f"Model '{self.model}' not found in Ollama. Attempting auto-download...")
                logger.info("This may take several minutes depending on the model size.")
                try:
                    download_success = False
                    last_status = None
                    for progress in self.client.pull_model(self.model, stream=True):
                        if "error" in progress:
                            logger.error(f"Failed to download model: {progress['error']}")
                            break
                        # Log progress updates
                        status = progress.get("status")
                        if status and status != last_status:
                            logger.info(f"Download status: {status}")
                            last_status = status
                        if progress.get("status") == "success" or progress.get("done"):
                            download_success = True
                            logger.info(f"✓ Successfully downloaded model: {self.model}")
                            break
                    
                    if not download_success:
                        logger.warning(
                            f"Failed to download model '{self.model}'. "
                            f"You can download it manually with: ollama pull {self.model}"
                        )
                        return
                except Exception as e:
                    logger.error(
                        f"Error downloading model '{self.model}': {e}. "
                        f"Try manually: ollama pull {self.model}"
                    )
                    return

            self._available = True
            logger.info(f"Ollama client ready: {self.model} at {self.base_url}")

        except ImportError as e:
            logger.warning(f"Failed to import Ollama client: {e}")
        except Exception as e:
            logger.warning(f"Failed to initialize Ollama: {e}")

    def is_available(self) -> bool:
        return self._available

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        if not self._available:
            raise RuntimeError("Ollama client not available")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return self.generate_chat(messages, max_tokens, temperature, **kwargs)

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        if not self._available:
            raise RuntimeError("Ollama client not available")

        try:
            options = {
                "temperature": temperature or self.temperature,
                "num_predict": max_tokens or self.max_tokens,
            }
            options.update(kwargs.get("options", {}))

            # Get GPU recommendations if available
            gpu_info = self.client.detect_gpu()
            if gpu_info.get("available"):
                recommended = self.client.get_recommended_options(gpu_info)
                options.update(recommended)

            response = self.client.chat(
                model=self.model,
                messages=messages,
                stream=False,
                options=options,
            )

            # FIX: Handle generator response (streaming) even if stream=False was requested
            # This fixes the "Unexpected Ollama response format: <generator object ...>" bug
            import types
            if isinstance(response, types.GeneratorType):
                full_content = []
                for chunk in response:
                    if "error" in chunk:
                        raise RuntimeError(f"Ollama error: {chunk['error']}")
                    
                    if "message" in chunk:
                        full_content.append(chunk["message"].get("content", ""))
                    elif "response" in chunk:
                        full_content.append(chunk["response"])
                return "".join(full_content)

            if "error" in response:
                raise RuntimeError(f"Ollama error: {response['error']}")

            # Extract response content
            if "message" in response:
                return response["message"].get("content", "")
            elif "response" in response:
                return response["response"]
            else:
                logger.warning(f"Unexpected Ollama response format: {response}")
                return str(response)

        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        if not self._available:
            raise RuntimeError("Ollama client not available")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            options = {
                "temperature": temperature or self.temperature,
                "num_predict": max_tokens or self.max_tokens,
            }
            options.update(kwargs.get("options", {}))

            # Get GPU recommendations if available
            gpu_info = self.client.detect_gpu()
            if gpu_info.get("available"):
                recommended = self.client.get_recommended_options(gpu_info)
                options.update(recommended)

            for chunk in self.client.chat(
                model=self.model,
                messages=messages,
                stream=True,
                options=options,
            ):
                if "error" in chunk:
                    yield {"error": chunk["error"]}
                    return

                # Extract message content
                if "message" in chunk:
                    content = chunk["message"].get("content", "")
                    if content:
                        yield content
                elif "response" in chunk:
                    yield chunk["response"]

        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            yield {"error": str(e)}


class MistralClientAdapter(LLMClientInterface):
    """Adapter for Mistral AI API"""

    def __init__(
        self,
        model: str = "mistral-small",
        api_key: Optional[str] = None,
        temperature: float = LLM_DEFAULT_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
        timeout: int = NETWORK_TIMEOUT,
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("MISTRAL_API_KEY")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.client = None
        self._available = False
        self._initialize()

    def _initialize(self):
        """Initialize Mistral client"""
        try:
            from mistralai.client import MistralClient

            if self.api_key:
                self.client = MistralClient(api_key=self.api_key)
                self._available = True
                logger.info(f"Mistral client initialized with model: {self.model}")
            else:
                logger.warning("No Mistral API key found. Set MISTRAL_API_KEY environment variable.")
        except ImportError:
            logger.warning("mistralai package not installed. Install with: pip install mistralai")
        except Exception as e:
            logger.warning(f"Failed to initialize Mistral: {e}")

    def is_available(self) -> bool:
        return self._available

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        if not self._available:
            raise RuntimeError("Mistral client not available")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return self.generate_chat(messages, max_tokens, temperature, **kwargs)

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        if not self._available:
            raise RuntimeError("Mistral client not available")

        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Mistral API error: {e}")
            raise


class LocalLLMClientAdapter(LLMClientInterface):
    """Adapter for local LLM via llama-cpp-python"""

    def __init__(
        self,
        model_path: str,
        temperature: float = LLM_DEFAULT_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
        n_ctx: int = LLM_CONTEXT_SIZE,
        n_threads: int = LLM_THREAD_COUNT,
    ):
        self.model_path = model_path
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.client = None
        self._available = False
        self._initialize()

    def _initialize(self):
        """Initialize local LLM"""
        try:
            from llama_cpp import Llama

            if not os.path.exists(self.model_path):
                logger.warning(f"Model file not found: {self.model_path}")
                return

            self.client = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=False,
            )
            self._available = True
            logger.info(f"Local LLM initialized: {self.model_path}")

        except ImportError:
            logger.warning("llama-cpp-python not installed. Install with: pip install llama-cpp-python")
        except Exception as e:
            logger.warning(f"Failed to initialize local LLM: {e}")

    def is_available(self) -> bool:
        return self._available

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        if not self._available:
            raise RuntimeError("Local LLM client not available")

        # Combine system prompt and user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        try:
            response = self.client(
                full_prompt,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
                stop=kwargs.get("stop", []),
            )
            return response["choices"][0]["text"].strip()
        except Exception as e:
            logger.error(f"Local LLM error: {e}")
            raise

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        if not self._available:
            raise RuntimeError("Local LLM client not available")

        # Convert chat messages to a single prompt
        prompt_parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt_parts.append("Assistant:")
        full_prompt = "\n\n".join(prompt_parts)

        try:
            response = self.client(
                full_prompt,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
                stop=kwargs.get("stop", ["\nUser:", "\nSystem:"]),
            )
            return response["choices"][0]["text"].strip()
        except Exception as e:
            logger.error(f"Local LLM error: {e}")
            raise


class MockLLMClientAdapter(LLMClientInterface):
    """Mock client for testing"""

    def __init__(self):
        self._available = True
        logger.debug("Mock LLM client initialized")

    def is_available(self) -> bool:
        return self._available

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        return f"Mock response to: {prompt[:50]}..."

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        last_msg = messages[-1]["content"] if messages else ""
        return f"Mock chat response to: {last_msg[:50]}..."


class UnifiedLLMClient:
    """
    Unified LLM client that routes to appropriate provider
    
    This is the main entry point for all LLM interactions, replacing LLMService.
    It reads configuration from settings and provides a consistent interface
    across all providers.
    
    TICKET: P1 Hybrid LLM Optimization - FULL MIGRATION
    For Ollama provider: MANDATORY dual-model architecture for RAM optimization
    - reasoner: Complex reasoning model (default: qwen2.5:7b-instruct-q3_k_m)
    - reflex: Fast response model (default: qwen2.5:1.5b)
    """

    def __init__(
        self,
        provider: str = "ollama",
        api_key: Optional[str] = None,
        max_tokens: int = LLM_MAX_TOKENS,
        timeout: int = NETWORK_TIMEOUT,
        model_path: Optional[str] = None,
        fallback_providers: Optional[List[str]] = None,
        reasoner_model: Optional[str] = None,
        reflex_model: Optional[str] = None,
        model: Optional[str] = None,  # Deprecated - only for non-Ollama providers
    ):
        """
        Initialize unified LLM client
        
        FULL MIGRATION: Ollama provider now ALWAYS uses hybrid mode.
        No backward compatibility - dual models are mandatory for Ollama.
        
        Args:
            provider: LLM provider (openai, anthropic, ollama, mistral, local, mock)
            api_key: API key (if required by provider)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout
            model_path: Path to local model file (for local provider)
            fallback_providers: List of fallback providers
            reasoner_model: Model for complex reasoning (Ollama only)
            reflex_model: Model for fast tasks (Ollama only)
            model: DEPRECATED - only used for non-Ollama providers
        """
        self.provider = provider.lower()
        self.api_key = api_key
        self.max_tokens = max_tokens
        # Ensure timeout is valid (must be > 0)
        if timeout is None or timeout <= 0:
            logger.warning(f"Invalid timeout value ({timeout}), using default {NETWORK_TIMEOUT}")
            timeout = NETWORK_TIMEOUT
        self.timeout = timeout
        self.model_path = model_path
        self.fallback_providers = fallback_providers or []
        
        # TICKET: P1 - FULL MIGRATION: Hybrid is MANDATORY for Ollama
        self.reasoner_model = reasoner_model
        self.reflex_model = reflex_model
        
        # For non-Ollama providers only
        self.model = model or "mistral"
        
        self.client: Optional[LLMClientInterface] = None
        # TICKET: P1 - Dual clients (mandatory for Ollama)
        self.reasoner: Optional[LLMClientInterface] = None
        self.reflex: Optional[LLMClientInterface] = None
        
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate provider client(s)"""
        logger.info(f"Initializing LLM client: provider={self.provider}")
        
        # TICKET: P1 - FULL MIGRATION: Ollama ALWAYS uses hybrid mode
        if self.provider == "ollama":
            # Import model constants
            from janus.config.model_paths import REASONER_MODEL, REFLEX_MODEL
            
            # Use provided models or fall back to defaults
            reasoner_model = self.reasoner_model or REASONER_MODEL
            reflex_model = self.reflex_model or REFLEX_MODEL
            
            logger.info(f"Initializing Ollama hybrid mode: reasoner={reasoner_model}, reflex={reflex_model}")
            
            # Initialize reasoner (brain) - lower temperature for deterministic output
            self.reasoner = OllamaClientAdapter(
                model=reasoner_model,
                temperature=0.1,  # Lower temp for complex reasoning
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )
            
            # Initialize reflex (fast) - higher temperature for natural responses
            self.reflex = OllamaClientAdapter(
                model=reflex_model,
                temperature=0.3,  # Slightly higher for variety in simple tasks
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )
            
            # Set main client to reasoner by default
            self.client = self.reasoner
            
            # Check if both clients are available - MANDATORY for Ollama
            if not self.reasoner.is_available() or not self.reflex.is_available():
                logger.error("❌ One or both hybrid models not available for Ollama!")
                logger.error(f"   Required models: {reasoner_model}, {reflex_model}")
                logger.error("   Install with: python scripts/install/install_models.py")
                logger.error("   Or manually:")
                logger.error(f"     ollama pull {reasoner_model}")
                logger.error(f"     ollama pull {reflex_model}")
                # FULL MIGRATION: Don't fall back, raise error
                raise RuntimeError(
                    f"Ollama hybrid models not available. "
                    f"Install {reasoner_model} and {reflex_model} first."
                )
            
            logger.info(f"✓ Ollama hybrid mode initialized: {reasoner_model} + {reflex_model}")
            return
        
        # Non-Ollama providers use single-model mode
        try:
            if self.provider == "openai":
                self.client = OpenAIClientAdapter(
                    model=self.model,
                    api_key=self.api_key,
                    temperature=LLM_DEFAULT_TEMPERATURE,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout,
                )
            elif self.provider == "anthropic":
                self.client = AnthropicClientAdapter(
                    model=self.model,
                    api_key=self.api_key,
                    temperature=LLM_DEFAULT_TEMPERATURE,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout,
                )
            elif self.provider == "mistral":
                self.client = MistralClientAdapter(
                    model=self.model,
                    api_key=self.api_key,
                    temperature=LLM_DEFAULT_TEMPERATURE,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout,
                )
            elif self.provider == "local":
                if not self.model_path:
                    logger.error("model_path required for local provider")
                    self._try_fallback()
                    return
                self.client = LocalLLMClientAdapter(
                    model_path=self.model_path,
                    temperature=LLM_DEFAULT_TEMPERATURE,
                    max_tokens=self.max_tokens,
                )
            elif self.provider == "mock":
                self.client = MockLLMClientAdapter()
            else:
                logger.error(f"Unknown provider: {self.provider}")
                self._try_fallback()
                return

            # Check if client is available
            if self.client and not self.client.is_available():
                logger.warning(f"Provider {self.provider} not available")
                self._try_fallback()

        except Exception as e:
            logger.error(f"Failed to initialize {self.provider}: {e}")
            self._try_fallback()

    def _try_fallback(self):
        """Try fallback providers"""
        for fallback_provider in self.fallback_providers:
            logger.info(f"Trying fallback provider: {fallback_provider}")
            try:
                self.provider = fallback_provider
                self._initialize_client()
                if self.client and self.client.is_available():
                    logger.info(f"Successfully fell back to {fallback_provider}")
                    return
            except Exception as e:
                logger.warning(f"Fallback to {fallback_provider} failed: {e}")
        
        # Final fallback to mock
        logger.warning("All providers failed, falling back to mock")
        self.provider = "mock"
        self.client = MockLLMClientAdapter()

    @property
    def available(self) -> bool:
        """
        Check if client is available
        
        FULL MIGRATION: For Ollama, BOTH models must be available
        """
        if self.provider == "ollama":
            # Both reasoner and reflex must be available
            return (
                self.reasoner is not None and self.reasoner.is_available() and
                self.reflex is not None and self.reflex.is_available()
            )
        return self.client is not None and self.client.is_available()

    def _record_llm_call(
        self,
        call_site: str,
        tokens_in: int,
        tokens_out: int,
        latency_ms: float,
    ):
        """
        Record LLM call metrics for transparency (ARCH-002).
        
        Args:
            call_site: Where the call originated (module.function)
            tokens_in: Input tokens estimate
            tokens_out: Output tokens estimate
            latency_ms: Call latency in milliseconds
        """
        global _llm_metrics
        
        _llm_metrics["total_calls"] += 1
        _llm_metrics["total_tokens_in"] += tokens_in
        _llm_metrics["total_tokens_out"] += tokens_out
        _llm_metrics["total_latency_ms"] += latency_ms
        
        # Track by call site
        if call_site not in _llm_metrics["calls_by_site"]:
            _llm_metrics["calls_by_site"][call_site] = 0
        _llm_metrics["calls_by_site"][call_site] += 1
        
        # Track by model
        model_key = f"{self.provider}/{self.model}"
        if model_key not in _llm_metrics["calls_by_model"]:
            _llm_metrics["calls_by_model"][model_key] = 0
        _llm_metrics["calls_by_model"][model_key] += 1
        
        # Log for transparency
        logger.debug(
            f"LLM call: site={call_site}, model={model_key}, "
            f"tokens_in≈{tokens_in}, tokens_out≈{tokens_out}, "
            f"latency={latency_ms:.1f}ms"
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        mode: str = "smart",
        **kwargs
    ) -> str:
        """
        Generate text completion with instrumentation (ARCH-002).
        
        TICKET: P1 - FULL MIGRATION: Ollama always uses hybrid routing
        - "smart": Use reasoner model (complex reasoning, planning)
        - "fast": Use reflex model (simple tasks, routing, extraction)
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (overrides model defaults)
            mode: "smart" (reasoner) or "fast" (reflex) - Ollama only
            **kwargs: Provider-specific options
            
        Returns:
            Generated text
        """
        if not self.available:
            raise RuntimeError(f"LLM client not available (provider: {self.provider})")
        
        # TICKET: P1 - FULL MIGRATION: Select client based on mode for Ollama
        selected_client = self.client
        if self.provider == "ollama":
            if mode == "fast" and self.reflex:
                selected_client = self.reflex
                logger.debug(f"Using reflex model for fast task")
            elif mode == "smart" and self.reasoner:
                selected_client = self.reasoner
                logger.debug(f"Using reasoner model for smart task")
            elif mode not in ("smart", "fast"):
                logger.warning(f"Invalid mode '{mode}', defaulting to 'smart'")
                selected_client = self.reasoner if self.reasoner else self.client
        
        # Get call site for instrumentation
        frame = inspect.currentframe()
        caller_frame = frame.f_back if frame else None
        call_site = "unknown"
        if caller_frame:
            call_site = f"{caller_frame.f_code.co_filename.split('/')[-1]}:{caller_frame.f_code.co_name}"
        
        # Measure latency
        start_time = time.time()
        
        # Execute LLM call
        result = selected_client.generate(prompt, system_prompt, max_tokens, temperature, **kwargs)
        
        # Record metrics
        latency_ms = (time.time() - start_time) * 1000
        tokens_in = estimate_tokens(prompt + (system_prompt or ""))
        tokens_out = estimate_tokens(result)
        self._record_llm_call(call_site, tokens_in, tokens_out, latency_ms)
        
        return result

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        mode: str = "smart",
        **kwargs
    ) -> str:
        """
        Generate chat completion with instrumentation (ARCH-002).
        
        TICKET: P1 - FULL MIGRATION: Ollama always uses hybrid routing
        - "smart": Use reasoner model (complex reasoning, planning)
        - "fast": Use reflex model (simple tasks, routing, extraction)
        
        Args:
            messages: List of chat messages with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (overrides model defaults)
            mode: "smart" (reasoner) or "fast" (reflex) - Ollama only
            **kwargs: Provider-specific options
            
        Returns:
            Generated response text
        """
        if not self.available:
            raise RuntimeError(f"LLM client not available (provider: {self.provider})")
        
        # TICKET: P1 - FULL MIGRATION: Select client based on mode for Ollama
        selected_client = self.client
        if self.provider == "ollama":
            if mode == "fast" and self.reflex:
                selected_client = self.reflex
                logger.debug(f"Using reflex model for fast chat")
            elif mode == "smart" and self.reasoner:
                selected_client = self.reasoner
                logger.debug(f"Using reasoner model for smart chat")
            elif mode not in ("smart", "fast"):
                logger.warning(f"Invalid mode '{mode}', defaulting to 'smart'")
                selected_client = self.reasoner if self.reasoner else self.client
        
        # Get call site for instrumentation
        frame = inspect.currentframe()
        caller_frame = frame.f_back if frame else None
        call_site = "unknown"
        if caller_frame:
            call_site = f"{caller_frame.f_code.co_filename.split('/')[-1]}:{caller_frame.f_code.co_name}"
        
        # Measure latency
        start_time = time.time()
        
        # Execute LLM call
        result = selected_client.generate_chat(messages, max_tokens, temperature, **kwargs)
        
        # Record metrics
        latency_ms = (time.time() - start_time) * 1000
        # Estimate tokens from all messages
        all_text = " ".join(msg.get("content", "") for msg in messages)
        tokens_in = estimate_tokens(all_text)
        tokens_out = estimate_tokens(result)
        self._record_llm_call(call_site, tokens_in, tokens_out, latency_ms)
        
        return result

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Generate streaming response
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Provider-specific options
            
        Yields:
            Chunks of generated text
        """
        if not self.available:
            raise RuntimeError(f"LLM client not available (provider: {self.provider})")
        
        return self.client.generate_stream(prompt, system_prompt, max_tokens, temperature, **kwargs)

    # High-level utility methods
    
    def analyze_content(
        self, content: str, content_type: str = "text", task: str = "summarize"
    ) -> Dict[str, Any]:
        """
        Analyze and process content (code, text, etc.)
        
        Args:
            content: Content to analyze
            content_type: Type of content (text, code, json, etc.)
            task: Task to perform (summarize, analyze, explain, etc.)
            
        Returns:
            Analysis results with status, task, content_type, and result
        """
        if not self.available:
            return {
                "status": "error",
                "error": "LLM client not available",
                "task": task,
                "content_type": content_type,
            }
        
        # Build prompts
        task_instructions = {
            "summarize": "Provide a concise summary of the following content.",
            "analyze": "Provide a detailed analysis of the following content.",
            "explain": "Explain the following content in simple terms.",
            "review": "Review the following content and provide feedback.",
            "debug": "Debug the following code and identify issues.",
        }
        
        system_prompt = (
            f"You are an expert in {content_type} analysis. "
            f"{task_instructions.get(task, f'Perform the task: {task}')}"
        )
        user_prompt = f"Content:\n{content}"
        
        try:
            response = self.generate(user_prompt, system_prompt)
            return {
                "status": "success",
                "task": task,
                "content_type": content_type,
                "result": response,
            }
        except Exception as e:
            logger.error(f"Content analysis error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "task": task,
                "content_type": content_type,
            }

    def analyze_command(
        self, command: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a natural language command
        
        Args:
            command: Natural language command text
            context: Optional context (session state, history, etc.)
            
        Returns:
            Dictionary with analysis results
        """
        if not self.available:
            return {
                "status": "error",
                "error": "LLM client not available",
            }
        
        system_prompt = """You are a command analysis assistant.
Analyze natural language commands and extract intent and parameters.
Return a JSON object with:
- intent: the main action (e.g., "open_app", "search", "navigate")
- parameters: relevant parameters extracted from the command
- confidence: confidence score (0.0-1.0)
IMPORTANT: Return ONLY the raw JSON object. Do not use markdown formatting."""
        
        user_prompt = f"Command: {command}"
        if context:
            user_prompt += f"\nContext: {json.dumps(context)}"
        
        try:
            response = self.generate(user_prompt, system_prompt)
            
            # FIX: Clean markdown code blocks before parsing JSON
            # Mistral/Ollama often wraps JSON in ```json ... ```
            cleaned_response = response.strip()
            if "```" in cleaned_response:
                import re
                # Extract content between ```json and ``` or just ``` and ```
                match = re.search(r"```(?:json)?\s*(.*?)```", cleaned_response, re.DOTALL)
                if match:
                    cleaned_response = match.group(1).strip()
            
            # Try to parse as JSON
            try:
                result = json.loads(cleaned_response)
                result["status"] = "success"
                return result
            except json.JSONDecodeError:
                # Return raw response if not valid JSON
                logger.warning(f"Failed to parse JSON from LLM: {cleaned_response[:100]}...")
                return {
                    "status": "success",
                    "raw_response": response,
                    "intent": "unknown",
                    "confidence": 0.5,
                }
        except Exception as e:
            logger.error(f"Command analysis error: {e}")
            return {
                "status": "error",
                "error": str(e),
            }


def create_unified_client_from_settings(settings) -> UnifiedLLMClient:
    """
    Factory function to create UnifiedLLMClient from Janus settings
    
    Args:
        settings: Settings object with llm configuration
        
    Returns:
        Configured UnifiedLLMClient instance
    """
    return UnifiedLLMClient(
        provider=settings.llm.provider,
        model=settings.llm.model,
        temperature=settings.llm.temperature,
        max_tokens=settings.llm.max_tokens,
        timeout=settings.llm.request_timeout,
        model_path=settings.llm.model_path,
        fallback_providers=settings.llm.fallback_providers.split(",") if settings.llm.fallback_providers else [],
    )
