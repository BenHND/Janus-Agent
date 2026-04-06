"""
LLM Setup Wizard - Guided installation for local LLM models
Helps users install and configure Ollama or llama-cpp-python

Phase 20B Enhancement (TICKET-011)
TICKET-ARCH-FINAL-EXT: Zero hardcoding - all text externalized to i18n

ARCH-002: This is a setup/diagnostic tool that directly manages Ollama installation.
Direct OllamaClient usage is acceptable here for model management and diagnostics.
For application logic, use UnifiedLLMClient or ReasonerLLM instead.
"""

import os
import platform
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from janus.constants import OLLAMA_DEFAULT_ENDPOINT, OLLAMA_TAGS_PATH
from janus.resources.locale_loader import get_locale_loader


class LLMSetupWizard:
    """
    Interactive wizard for setting up local LLM backends

    Features:
    - Detect installed backends (Ollama, llama-cpp)
    - Guide installation process
    - Download/pull recommended models
    - Test configuration
    - Save configuration to config.json
    """

    def __init__(self, language: str = "en"):
        """
        Initialize setup wizard
        
        Args:
            language: Language code for UI text (e.g., "en", "fr")
        """
        self.system = platform.system()
        self.arch = platform.machine()
        self.recommendations: Dict[str, Any] = {}
        self.language = language
        self.locale_loader = get_locale_loader()
    
    def _t(self, key: str, **kwargs) -> str:
        """
        Translate a key using the locale loader.
        
        Args:
            key: Translation key in locale file
            **kwargs: Format parameters
            
        Returns:
            Translated string
        """
        full_key = f"llm_wizard.{key}"
        text = self.locale_loader.get(full_key, language=self.language, default=f"[{key}]")
        
        if kwargs:
            return text.format(**kwargs)
        return text
    
    def _print(self, key: str, **kwargs):
        """Print a translated message."""
        print(self._t(key, **kwargs))
    
    def _input(self, key: str, **kwargs) -> str:
        """Get input with a translated prompt."""
        return input(self._t(key, **kwargs))

    def detect_ollama(self) -> Tuple[bool, Optional[str]]:
        """
        Detect if Ollama is installed and running
        
        ARCH-002: This is a setup/diagnostic tool, so direct OllamaClient usage is allowed here.
        For application logic, use UnifiedLLMClient or ReasonerLLM instead.

        Returns:
            Tuple of (is_available, version_or_error)
        """
        try:
            # ARCH-002: Direct OllamaClient usage is acceptable in setup/diagnostic tools
            from janus.ai.llm.ollama_client import OllamaClient
            
            # Check if Ollama server is running
            client = OllamaClient()
            if client.is_available():
                version = client.get_version()
                return True, version or "Unknown version"
            else:
                return False, "Ollama installed but server not running"

        except Exception as e:
            return False, str(e)

    def detect_llama_cpp(self) -> Tuple[bool, Optional[str]]:
        """
        Detect if llama-cpp-python is installed

        Returns:
            Tuple of (is_available, version_or_error)
        """
        try:
            import llama_cpp

            version = getattr(llama_cpp, "__version__", "unknown")
            return True, version
        except ImportError:
            return False, None
        except Exception as e:
            return False, str(e)

    def get_installation_instructions(self, backend: str) -> str:
        """
        Get installation instructions for specific backend

        Args:
            backend: "ollama" or "llama-cpp"

        Returns:
            Formatted installation instructions
        """
        if backend == "ollama":
            if self.system == "Darwin":  # macOS
                return self._t("install_instructions_ollama_macos")
            elif self.system == "Linux":
                return self._t("install_instructions_ollama_linux")
            else:  # Windows
                return self._t("install_instructions_ollama_windows")

        elif backend == "llama-cpp":
            return self._t("install_instructions_llama_cpp")

        return self._t("unknown_backend")

    def list_ollama_models(self) -> List[Dict[str, Any]]:
        """
        List models available in Ollama
        
        ARCH-002: Direct OllamaClient usage acceptable in setup/diagnostic tools.

        Returns:
            List of model dictionaries with name, size, etc.
        """
        try:
            # ARCH-002: Direct usage acceptable for model management in setup wizard
            from janus.ai.llm.ollama_client import OllamaClient
            
            client = OllamaClient()
            return client.list_models()
        except Exception as e:
            warnings.warn(f"Failed to list Ollama models: {e}")
            return []

    def get_recommended_models(self, backend: str) -> List[Dict[str, Any]]:
        """
        Get recommended models for the backend

        Args:
            backend: "ollama" or "llama-cpp"

        Returns:
            List of recommended model configurations
        """
        if backend == "ollama":
            return [
                {
                    "name": "mistral:7b-instruct-q4_K_M",
                    "display_name": "Mistral 7B (Q4, Recommended)",
                    "size": "~4.4GB",
                    "performance": "Best balance of speed and quality",
                    "command": "ollama pull mistral:7b-instruct-q4_K_M",
                },
                {
                    "name": "phi3:mini",
                    "display_name": "Phi-3 Mini (3.8B)",
                    "size": "~2.3GB",
                    "performance": "Fastest, good for quick responses",
                    "command": "ollama pull phi3:mini",
                },
                {
                    "name": "gemma:7b",
                    "display_name": "Gemma 7B",
                    "size": "~5.0GB",
                    "performance": "High quality, slightly slower",
                    "command": "ollama pull gemma:7b",
                },
                {
                    "name": "qwen:7b",
                    "display_name": "Qwen 7B",
                    "size": "~4.7GB",
                    "performance": "Good multilingual support",
                    "command": "ollama pull qwen:7b",
                },
            ]

        elif backend == "llama-cpp":
            return [
                {
                    "name": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
                    "display_name": "Mistral 7B Instruct Q4",
                    "size": "~4.4GB",
                    "performance": "Best balance",
                    "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
                },
                {
                    "name": "phi-3-mini-4k-instruct-q4.gguf",
                    "display_name": "Phi-3 Mini Q4",
                    "size": "~2.3GB",
                    "performance": "Fastest",
                    "url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf",
                },
            ]

        return []

    def pull_ollama_model(self, model_name: str) -> Tuple[bool, str]:
        """
        Pull a model in Ollama

        Args:
            model_name: Name of the model to pull

        Returns:
            Tuple of (success, message)
        """
        try:
            self._print("pulling_model", model=model_name)
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes timeout
            )

            if result.returncode == 0:
                return True, self._t("model_pulled", model=model_name)
            else:
                return False, self._t("model_pull_failed", error=result.stderr)

        except subprocess.TimeoutExpired:
            return False, self._t("model_pull_timeout")
        except Exception as e:
            return False, self._t("model_pull_error", error=str(e))

    def delete_ollama_model(self, model_name: str) -> Tuple[bool, str]:
        """
        Delete a model from Ollama

        Args:
            model_name: Name of the model to delete

        Returns:
            Tuple of (success, message)
        """
        try:
            from janus.ai.llm.ollama_client import OllamaClient
            
            client = OllamaClient()
            return client.delete_model(model_name)
        except Exception as e:
            return False, f"Error deleting model: {str(e)}"

    def get_ollama_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about an Ollama model

        Args:
            model_name: Name of the model

        Returns:
            Model information dictionary or None
        """
        try:
            from janus.ai.llm.ollama_client import OllamaClient
            
            client = OllamaClient()
            return client.get_model_info(model_name)
        except Exception as e:
            warnings.warn(f"Failed to get model info: {e}")
            return None

    def detect_gpu(self) -> Dict[str, Any]:
        """
        Detect available GPU hardware

        Returns:
            Dictionary with GPU information
        """
        try:
            from janus.ai.llm.ollama_client import OllamaClient
            
            client = OllamaClient()
            return client.detect_gpu()
        except Exception as e:
            warnings.warn(f"Failed to detect GPU: {e}")
            return {"available": False}

    def test_backend(self, backend: str, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Test if backend is working with given configuration

        Args:
            backend: "ollama" or "llama-cpp"
            config: Configuration dictionary

        Returns:
            Tuple of (success, message)
        """
        try:
            from janus.ai.reasoning.reasoner_llm import ReasonerLLM

            # Create ReasonerLLM with config
            if backend == "ollama":
                llm = ReasonerLLM(backend="ollama", model_name=config.get("model_name"))
            else:  # llama-cpp
                llm = ReasonerLLM(backend="llama-cpp", model_path=config.get("model_path"))

            if not llm.available:
                return False, self._t("backend_failed")

            # Test with simple command
            result = llm.parse_command("test command", language="en")

            if result and "intents" in result:
                latency = result.get("latency_ms", 0)
                return True, self._t("backend_working", latency=latency)
            else:
                return False, self._t("backend_no_result")

        except Exception as e:
            return False, self._t("test_failed", error=str(e))

    def validate_openai_api_key(self, api_key: str) -> Tuple[bool, str]:
        """
        Validate OpenAI API key by making a test request

        Args:
            api_key: OpenAI API key to validate

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            import openai

            # Set the API key
            openai.api_key = api_key

            # Make a minimal test request
            response = openai.models.list()

            return True, self._t("key_valid", provider="OpenAI")

        except ImportError:
            return False, "OpenAI package not installed. Install with: pip install openai"
        except openai.AuthenticationError:
            return False, self._t("key_invalid")
        except openai.RateLimitError:
            return True, self._t("key_valid", provider="OpenAI")
        except Exception as e:
            return False, self._t("key_error", error=str(e))

    def validate_anthropic_api_key(self, api_key: str) -> Tuple[bool, str]:
        """
        Validate Anthropic API key by making a test request

        Args:
            api_key: Anthropic API key to validate

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            import anthropic

            # Create client with the API key
            client = anthropic.Anthropic(api_key=api_key)

            # Make a minimal test request to validate the key
            # Using a very short max_tokens to minimize cost
            response = client.messages.create(
                model="claude-3-haiku-20240307",  # Use the cheapest model
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
            )

            return True, self._t("key_valid", provider="Anthropic")

        except ImportError:
            return False, "Anthropic package not installed. Install with: pip install anthropic"
        except anthropic.AuthenticationError:
            return False, self._t("key_invalid")
        except anthropic.RateLimitError:
            return True, self._t("key_valid", provider="Anthropic")
        except Exception as e:
            return False, self._t("key_error", error=str(e))

    def _configure_cloud_provider(self) -> Optional[Dict[str, Any]]:
        """
        Configure a cloud LLM provider (OpenAI or Anthropic)

        Returns:
            Configuration dictionary or None if cancelled
        """
        print("\n" + "=" * 60)
        self._print("cloud_header")
        print("=" * 60 + "\n")

        self._print("cloud_choose")
        print()
        print(f"1. {self._t('cloud_openai')}")
        print(f"2. {self._t('cloud_anthropic')}")
        print(f"3. {self._t('cloud_cancel')}")

        choice = self._input("choice_prompt", max=3).strip()

        if choice == "3":
            return None

        if choice == "1":
            provider = "openai"
            print()
            self._print("openai_header")
            print()
            self._print("openai_info")
            print()

            # Check for existing API key in environment
            existing_key = os.environ.get("OPENAI_API_KEY")
            if existing_key:
                self._print("api_key_found", provider="OPENAI", key=existing_key[:8])
                use_existing = self._input("use_existing_key").strip().lower()
                if use_existing != "n":
                    api_key = existing_key
                else:
                    api_key = self._input("enter_api_key", provider="OpenAI").strip()
            else:
                api_key = self._input("enter_api_key", provider="OpenAI").strip()

            if not api_key:
                self._print("no_api_key")
                return None

            # Validate the API key
            print()
            self._print("validating_key")
            valid, message = self.validate_openai_api_key(api_key)
            print(message)

            if not valid:
                return None

            # Choose model
            print()
            self._print("choose_model")
            print()
            print(f"1. {self._t('model_gpt4')}")
            print(f"2. {self._t('model_gpt4_turbo')}")
            print(f"3. {self._t('model_gpt3_5')}")

            model_choice = input(f"\n{self._t('choice_prompt', max=3)} ").strip() or "2"

            model_map = {"1": "gpt-4", "2": "gpt-4-turbo", "3": "gpt-3.5-turbo"}
            model = model_map.get(model_choice, "gpt-4-turbo")

            config = {"backend": "openai", "model_name": model, "api_key": api_key}

        elif choice == "2":
            provider = "anthropic"
            print()
            self._print("anthropic_header")
            print()
            self._print("anthropic_info")
            print()

            # Check for existing API key in environment
            existing_key = os.environ.get("ANTHROPIC_API_KEY")
            if existing_key:
                self._print("api_key_found", provider="ANTHROPIC", key=existing_key[:8])
                use_existing = self._input("use_existing_key").strip().lower()
                if use_existing != "n":
                    api_key = existing_key
                else:
                    api_key = self._input("enter_api_key", provider="Anthropic").strip()
            else:
                api_key = self._input("enter_api_key", provider="Anthropic").strip()

            if not api_key:
                self._print("no_api_key")
                return None

            # Validate the API key
            print()
            self._print("validating_key")
            valid, message = self.validate_anthropic_api_key(api_key)
            print(message)

            if not valid:
                return None

            # Choose model
            print()
            self._print("choose_model")
            print()
            print(f"1. {self._t('model_claude_opus')}")
            print(f"2. {self._t('model_claude_sonnet')}")
            print(f"3. {self._t('model_claude_haiku')}")

            model_choice = input(f"\n{self._t('choice_prompt', max=3)} ").strip() or "2"

            model_map = {
                "1": "claude-3-opus-20240229",
                "2": "claude-3-sonnet-20240229",
                "3": "claude-3-haiku-20240307",
            }
            model = model_map.get(model_choice, "claude-3-sonnet-20240229")

            config = {"backend": "anthropic", "model_name": model, "api_key": api_key}
        else:
            self._print("invalid_choice")
            return None

        # Save configuration
        print()
        self._print("saving_config")
        print()

        # Save API key to environment file
        env_file = Path.home() / ".janus" / "env"
        env_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Read existing .env file if it exists
            env_lines = []
            if env_file.exists():
                with open(env_file, "r") as f:
                    env_lines = f.readlines()

            # Update or add the API key line
            key_name = f"{provider.upper()}_API_KEY"
            key_line = f"{key_name}={api_key}\n"

            # Remove old key if exists
            env_lines = [line for line in env_lines if not line.startswith(f"{key_name}=")]
            env_lines.append(key_line)

            # Write back
            with open(env_file, "w") as f:
                f.writelines(env_lines)

            self._print("key_saved", path=env_file)
            self._print("key_save_hint", key_name=key_name, value="your_key")

        except Exception as e:
            self._print("key_save_failed", error=str(e))
            self._print("key_save_manual", key_name=key_name)

        if self.save_configuration(config):
            self._print("config_saved")
            return config
        else:
            self._print("config_test_ok")
            return config

    def save_configuration(self, config: Dict[str, Any], config_path: str = "config.json") -> bool:
        """
        Save LLM configuration to config file

        Args:
            config: Configuration dictionary
            config_path: Path to config file

        Returns:
            Success status
        """
        try:
            import json

            # Load existing config
            existing_config = {}
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    existing_config = json.load(f)

            # Update cognitive planner config
            if "cognitive_planner" not in existing_config:
                existing_config["cognitive_planner"] = {}

            existing_config["cognitive_planner"].update(config)

            # Enable cognitive planner feature
            if "features" not in existing_config:
                existing_config["features"] = {}
            if "cognitive_planner" not in existing_config["features"]:
                existing_config["features"]["cognitive_planner"] = {}
            existing_config["features"]["cognitive_planner"]["enabled"] = True

            # Save config
            with open(config_path, "w") as f:
                json.dump(existing_config, f, indent=2)

            return True

        except Exception as e:
            warnings.warn(f"Failed to save configuration: {e}")
            return False

    def run_interactive_setup(self) -> Optional[Dict[str, Any]]:
        """
        Run interactive setup wizard (for CLI usage)

        Returns:
            Configuration dictionary or None if cancelled
        """
        print("\n" + "=" * 60)
        print(f"  {self._t('header')}")
        print("=" * 60 + "\n")

        # Detect installed backends
        self._print("detecting_backends")
        print()

        ollama_available, ollama_info = self.detect_ollama()
        llama_cpp_available, llama_cpp_info = self.detect_llama_cpp()

        print(self._t("ollama_available") if ollama_available else self._t("ollama_not_available"))
        if ollama_info:
            print(f"  {ollama_info}")

        print(self._t("llama_cpp_available") if llama_cpp_available else self._t("llama_cpp_not_available"))
        if llama_cpp_info:
            print(f"  {llama_cpp_info}")

        print()

        # Choose backend
        if not ollama_available and not llama_cpp_available:
            self._print("choose_option")
            print()
            print(f"1. {self._t('option_ollama')}")
            print(f"2. {self._t('option_llama_cpp')}")
            print(f"3. {self._t('option_cloud')}")
            print(f"4. {self._t('option_skip')}")

            choice = self._input("choice_prompt", max=4).strip()

            if choice == "1":
                print(self.get_installation_instructions("ollama"))
                return None
            elif choice == "2":
                print(self.get_installation_instructions("llama-cpp"))
                return None
            elif choice == "3":
                return self._configure_cloud_provider()
            else:
                return {"backend": "mock"}

        # Give option for cloud providers even if local backends are available
        self._print("choose_backend_type")
        print()
        print(f"1. {self._t('backend_local')}")
        print(f"2. {self._t('backend_cloud')}")

        backend_type = self._input("choice_prompt", max=2).strip()

        if backend_type == "2":
            return self._configure_cloud_provider()

        # Select backend if multiple available
        backend = None
        if ollama_available and llama_cpp_available:
            print()
            self._print("multiple_backends")
            print()
            print(f"1. {self._t('backend_ollama_easy')}")
            print(f"2. {self._t('backend_llama_cpp')}")

            choice = self._input("choice_prompt", max=2).strip()
            backend = "ollama" if choice == "1" else "llama-cpp"
        elif ollama_available:
            backend = "ollama"
        else:
            backend = "llama-cpp"

        print()
        self._print("using_backend", backend=backend)
        print()

        # Configure backend
        config = {"backend": backend}

        if backend == "ollama":
            # List available models
            models = self.list_ollama_models()

            if models:
                self._print("available_models")
                for i, model in enumerate(models, 1):
                    name = model.get("name", "unknown")
                    size = model.get("size", 0) / (1024**3)  # Convert to GB
                    print(f"{i}. {name} ({size:.1f}GB)")

                print(self._t("install_new_model", count=len(models) + 1))

                choice = input(f"\n{self._t('select_model', count=len(models) + 1)} ").strip()

                if choice.isdigit() and 1 <= int(choice) <= len(models):
                    selected_model = models[int(choice) - 1]
                    config["model_name"] = selected_model.get("name")
                else:
                    # Show recommended models
                    print()
                    self._print("recommended_models")
                    print()
                    recommended = self.get_recommended_models("ollama")
                    for i, model in enumerate(recommended, 1):
                        print(f"{i}. {model['display_name']}")
                        print(self._t("model_size", size=model['size'], performance=model['performance']))
                        print(self._t("model_install", command=model['command']))
                        print()

                    choice = input(self._t("select_model_install", count=len(recommended)) + " ").strip()
                    if choice.isdigit() and 1 <= int(choice) <= len(recommended):
                        model = recommended[int(choice) - 1]
                        success, message = self.pull_ollama_model(model["name"])
                        print(message)
                        if success:
                            config["model_name"] = model["name"]
                        else:
                            return None
            else:
                self._print("no_models_installed")
                recommended = self.get_recommended_models("ollama")[0]
                success, message = self.pull_ollama_model(recommended["name"])
                print(message)
                if success:
                    config["model_name"] = recommended["name"]
                else:
                    return None

        elif backend == "llama-cpp":
            self._print("llama_cpp_info")
            print()
            self._print("recommended_models")
            print()

            recommended = self.get_recommended_models("llama-cpp")
            for i, model in enumerate(recommended, 1):
                print(f"{i}. {model['display_name']}")
                print(self._t("model_size", size=model['size'], performance=model['performance']))
                print(f"   Download from: {model['url']}")
                print()

            model_path = self._input("enter_model_path").strip()
            if model_path and os.path.exists(model_path):
                config["model_path"] = model_path
            else:
                self._print("model_not_found")
                return None

        # Test configuration
        print()
        self._print("testing_backend")
        success, message = self.test_backend(backend, config)
        print(message)

        if success:
            # Save configuration
            if self.save_configuration(config):
                print()
                self._print("config_saved")
                return config
            else:
                print()
                self._print("config_test_ok")
                return config
        else:
            print()
            self._print("backend_test_failed")
            return None


def run_setup_wizard(language: str = "en"):
    """
    Convenience function to run setup wizard
    
    Args:
        language: Language code for UI text (e.g., "en", "fr")
    """
    wizard = LLMSetupWizard(language=language)
    return wizard.run_interactive_setup()
