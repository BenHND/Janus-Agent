#!/usr/bin/env python3
"""
Smart model installation script for Janus.

Downloads and configures models based on config.ini settings:
- Ollama models (if provider=ollama) - auto-downloads if missing
- Semantic correction model (phi-2 GGUF) - only if explicitly configured

TICKET: P1 Hybrid LLM Optimization
Supports hybrid dual-model installation for RAM optimization:
- Reasoner (Brain): qwen2.5:7b-instruct-q3_k_m (~3.8 GB)
- Reflex (Fast): qwen2.5:1.5b (~1.2 GB)

Behavior:
1. If [llm] provider is Ollama:
   - Checks if Ollama is installed
   - Checks if configured model exists
   - Auto-downloads model if missing (with user consent)
   - Optionally downloads hybrid models for RAM optimization

2. If [whisper] semantic_correction_model_path is set:
   - Downloads the phi-2 GGUF model if it doesn't exist
   - User must download manually or via this script

3. If semantic_correction_model_path is empty:
   - Semantic correction will use the main LLM from [llm] section
   - No local model download needed
"""

import configparser
import os
import subprocess
import sys
from pathlib import Path

# TICKET: P1 - Import model constants at top level with error handling
try:
    # Add parent directory to path to import janus modules
    script_dir = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(script_dir))
    from janus.config.model_paths import REASONER_MODEL, REFLEX_MODEL
    HYBRID_MODELS_AVAILABLE = True
except ImportError as e:
    # Fallback constants if import fails
    REASONER_MODEL = "qwen2.5:7b-instruct-q3_k_m"
    REFLEX_MODEL = "qwen2.5:1.5b"
    HYBRID_MODELS_AVAILABLE = False
    print(f"⚠️  Warning: Could not import model constants: {e}")
    print(f"   Using fallback values: {REASONER_MODEL}, {REFLEX_MODEL}")

# Configuration constants
OLLAMA_CHECK_TIMEOUT = 5  # seconds to wait for ollama version check
OLLAMA_PULL_TIMEOUT = 600  # seconds to wait for ollama model download (10 minutes)
MODEL_DOWNLOAD_TIMEOUT = 1800  # seconds to wait for phi-2 download (30 minutes)

# Model download URLs (can be updated here for different variants)
PHI2_MODEL_URL = "https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf"
PHI2_MODEL_FILENAME = "phi-2.Q4_K_M.gguf"


def install_wakeword_models():
    """Download openWakeWord models to models/wakeword"""
    print("\n🎤 Checking openWakeWord models...")
    try:
        # Try to import openwakeword
        import openwakeword
        from openwakeword.utils import download_models
        
        # Define target directory
        target_dir = Path("models/wakeword")
        target_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"   Downloading models to {target_dir}...")
        # Download only infrastructure models (embedding, melspectrogram, VAD)
        # We skip other pre-trained wake words (alexa, etc.) as we use custom hey_janus
        models_to_download = ["embedding_model", "melspectrogram", "silero_vad"]
        download_models(model_names=models_to_download, target_directory=str(target_dir))
        
        print("   ✅ openWakeWord models installed")
        
    except ImportError:
        print("   ⚠️ openWakeWord not installed, skipping model download")
        print("      Install with: pip install openwakeword")
    except Exception as e:
        print(f"   ❌ Error downloading wake word models: {e}")


def read_config():
    """Read configuration from config.ini"""
    config_path = Path("config.ini")
    if not config_path.exists():
        print("❌ config.ini not found!")
        return None
    
    config = configparser.ConfigParser()
    config.read(config_path)
    return config


def check_ollama_installed():
    """Check if Ollama is installed and accessible"""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=OLLAMA_CHECK_TIMEOUT
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except subprocess.TimeoutExpired:
        print("⚠️  Ollama command timed out")
        return False


def check_ollama_server_running():
    """Check if Ollama server is running"""
    try:
        # Import requests here to avoid requiring it in minimal installations
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def list_ollama_models():
    """List available Ollama models"""
    try:
        # Import requests here to avoid requiring it in minimal installations
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [model.get("name", "") for model in data.get("models", [])]
        return []
    except Exception:
        return []


def model_exists_in_ollama(model_name):
    """Check if a specific model exists in Ollama"""
    models = list_ollama_models()
    # Check for exact match or prefix match (e.g., "mistral" matches "mistral:7b")
    for model in models:
        if model == model_name or model.startswith(model_name + ":"):
            return True
    return False


def download_ollama_model(model_name):
    """Download an Ollama model"""
    print(f"📥 Downloading Ollama model: {model_name}")
    print("   This may take several minutes...")
    
    try:
        result = subprocess.run(
            ["ollama", "pull", model_name],
            capture_output=False,
            text=True,
            timeout=OLLAMA_PULL_TIMEOUT
        )
        
        if result.returncode == 0:
            print(f"✓ Successfully downloaded {model_name}")
            return True
        else:
            print(f"❌ Failed to download {model_name} (exit code: {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout while downloading {model_name} (>10 minutes)")
        print(f"   The model may still be downloading in the background.")
        print(f"   Check with: ollama list")
        return False
    except Exception as e:
        print(f"❌ Error downloading {model_name}: {e}")
        return False


def download_phi2_model():
    """Download phi-2 model for semantic correction"""
    models_dir = Path("models")
    model_file = models_dir / PHI2_MODEL_FILENAME
    
    if model_file.exists():
        print(f"✓ Semantic correction model already exists: {model_file}")
        size_mb = model_file.stat().st_size / (1024 * 1024)
        print(f"  Size: {size_mb:.1f}MB")
        return True
    
    print(f"📥 Downloading phi-2 semantic correction model (~1.6GB)")
    print("   This may take 5-15 minutes depending on your connection...")
    
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Try wget first, then curl
    try:
        result = subprocess.run(
            ["wget", "--progress=bar:force:noscroll", "-O", str(model_file), PHI2_MODEL_URL],
            capture_output=False,
            timeout=MODEL_DOWNLOAD_TIMEOUT
        )
        
        if result.returncode == 0 and model_file.exists():
            size_mb = model_file.stat().st_size / (1024 * 1024)
            print(f"✓ Model downloaded successfully!")
            print(f"  Path: {model_file}")
            print(f"  Size: {size_mb:.1f}MB")
            return True
    except FileNotFoundError:
        # wget not found, try curl
        try:
            result = subprocess.run(
                ["curl", "-L", "--progress-bar", "-o", str(model_file), PHI2_MODEL_URL],
                capture_output=False,
                timeout=MODEL_DOWNLOAD_TIMEOUT
            )
            
            if result.returncode == 0 and model_file.exists():
                size_mb = model_file.stat().st_size / (1024 * 1024)
                print(f"✓ Model downloaded successfully!")
                print(f"  Path: {model_file}")
                print(f"  Size: {size_mb:.1f}MB")
                return True
        except FileNotFoundError:
            print("❌ Error: Neither wget nor curl is available")
            print("   Please install one of them:")
            print("   - macOS: brew install wget")
            print("   - Linux: sudo apt-get install wget")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Timeout while downloading model (>30 minutes)")
        return False
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        return False
    
    print("❌ Model download failed")
    return False


def main():
    """Main installation logic"""
    print("🤖 Janus Model Installation")
    print("==============================")
    print("")
    
    # Read configuration
    config = read_config()
    if config is None:
        sys.exit(1)
    
    success = True
    
    # Check LLM provider and download Ollama models if needed
    llm_provider = config.get("llm", "provider", fallback="mock")
    print(f"📦 LLM Provider: {llm_provider}")
    
    if llm_provider == "ollama":
        print("")
        print("Checking Ollama installation...")
        
        if not check_ollama_installed():
            print("❌ Ollama is not installed!")
            print("")
            print("   Ollama is required for the configured LLM provider.")
            print("   Install it from: https://ollama.ai")
            print("   Or run: brew install ollama (macOS)")
            print("")
            success = False
        else:
            print("✓ Ollama binary is installed")
            
            # Check if server is running
            if not check_ollama_server_running():
                print("")
                print("⚠️  Ollama server is not running!")
                print("   Start it with: ollama serve")
                print("   Or: brew services start ollama (macOS)")
                print("")
                print("   The model cannot be downloaded while the server is not running.")
                success = False
            else:
                print("✓ Ollama server is running")
                
                # Get model name - TICKET-MIG-002: Default to llama3.2 for optimal speed/intelligence
                model_name = config.get("llm", "model", fallback="llama3.2")
                print(f"   Configured model: {model_name}")
                
                # Check if model exists
                if model_exists_in_ollama(model_name):
                    print(f"✓ Model '{model_name}' is already available")
                else:
                    print(f"⚠️  Model '{model_name}' is not downloaded yet")
                    print("")
                    # TICKET-MIG-002: Show info about llama3.2 benefits
                    if "llama3.2" in model_name:
                        print("ℹ️  llama3.2 is the recommended model for optimal speed/intelligence:")
                        print("   • 2-4s response on Apple M4")
                        print("   • ~2GB RAM usage")
                        print("   • Specifically designed for laptops")
                        print("")
                    print(f"Do you want to download the Ollama model '{model_name}' now?")
                    print(f"(You can also do this later with: ollama pull {model_name})")
                    response = input("Download now? (y/N): ").strip().lower()
                    
                    if response in ('y', 'yes'):
                        if not download_ollama_model(model_name):
                            success = False
                    else:
                        print(f"⏭️  Skipping Ollama model download")
                        print(f"   Remember to run: ollama pull {model_name}")
                        print(f"   Semantic correction will not work until the model is available.")
                
                # TICKET: P1 - Hybrid LLM Optimization: Offer to install dual models
                print("")
                print("🧠 Hybrid LLM Optimization (Optional)")
                print("   Dual-model architecture for RAM optimization (< 5 GB total)")
                print("")
                print("   This installs two specialized models:")
                print("   • Reasoner (Brain): qwen2.5:7b-instruct-q3_k_m (~3.8 GB)")
                print("     For: Planning, Complex Tool Use, Code, Deep Visual Analysis")
                print("   • Reflex (Fast): qwen2.5:1.5b (~1.2 GB)")
                print("     For: Simple Summary, Chat, Routing, Extraction")
                print("")
                print("   Benefits:")
                print("   • Total VRAM: ~5 GB (vs 6 GB with single Q4 model)")
                print("   • Faster simple tasks (< 500ms routing with 1.5B model)")
                print("   • Better resource efficiency")
                print("")
                
                response = input("Install hybrid models for RAM optimization? (y/N): ").strip().lower()
                
                if response in ('y', 'yes'):
                    # Model constants already imported at top of file
                    # with fallback values if import fails
                    
                    hybrid_success = True
                    
                    # Download reasoner model
                    print("")
                    print(f"📥 Downloading Reasoner model: {REASONER_MODEL}")
                    if not model_exists_in_ollama(REASONER_MODEL):
                        if not download_ollama_model(REASONER_MODEL):
                            hybrid_success = False
                    else:
                        print(f"✓ Model '{REASONER_MODEL}' already available")
                    
                    # Download reflex model
                    print("")
                    print(f"📥 Downloading Reflex model: {REFLEX_MODEL}")
                    if not model_exists_in_ollama(REFLEX_MODEL):
                        if not download_ollama_model(REFLEX_MODEL):
                            hybrid_success = False
                    else:
                        print(f"✓ Model '{REFLEX_MODEL}' already available")
                    
                    if hybrid_success:
                        print("")
                        print("✅ Hybrid models installed successfully!")
                        print("")
                        print("   To enable hybrid mode, use:")
                        print("   UnifiedLLMClient(enable_hybrid=True)")
                    else:
                        print("")
                        print("⚠️  Some hybrid models failed to install")
                        success = False
                else:
                    print("⏭️  Skipping hybrid model installation")
                    print("   You can install them later with:")
                    print("   ollama pull qwen2.5:7b-instruct-q3_k_m")
                    print("   ollama pull qwen2.5:1.5b")
        print("")
    elif llm_provider in ("openai", "anthropic", "mistral"):
        print("   API-based provider - no local model download needed")
        print("")
    else:
        print(f"   Provider '{llm_provider}' - check configuration if semantic correction is needed")
        print("")
    
    # Check semantic correction model path
    semantic_model_path = config.get("whisper", "semantic_correction_model_path", fallback="").strip()
    
    if semantic_model_path:
        # User has explicitly configured a local model path
        print("📦 Semantic Correction: Dedicated local model")
        print(f"   Configured path: {semantic_model_path}")
        
        # Check if file exists
        if os.path.exists(semantic_model_path):
            print(f"✓ Model file already exists")
            size_mb = os.path.getsize(semantic_model_path) / (1024 * 1024)
            print(f"  Size: {size_mb:.1f}MB")
        else:
            # Model doesn't exist - offer to download phi-2
            if PHI2_MODEL_FILENAME in semantic_model_path:
                print(f"⚠️  Model file not found")
                print("")
                print(f"Do you want to download the phi-2 semantic correction model (~1.6GB)?")
                response = input("Download now? (y/N): ").strip().lower()
                
                if response in ('y', 'yes'):
                    if not download_phi2_model():
                        success = False
                else:
                    print("⏭️  Skipping phi-2 model download")
                    print(f"   Semantic correction will use main LLM instead")
            else:
                print(f"⚠️  Model file not found: {semantic_model_path}")
                print(f"   Please ensure the file exists or update config.ini")
                success = False
        print("")
    else:
        # No dedicated model path - semantic correction will use main LLM
        print("📦 Semantic Correction: Using main LLM")
        print(f"   Provider: {llm_provider}")
        if llm_provider == "ollama":
            model_name = config.get("llm", "model", fallback="mistral")
            print(f"   Model: {model_name}")
            print(f"   ℹ️  Semantic correction will use the Ollama model configured above")
        elif llm_provider in ("openai", "anthropic", "mistral"):
            print(f"   ℹ️  Semantic correction will use the API-based LLM")
        else:
            print(f"   ⚠️  Provider '{llm_provider}' may not support semantic correction")
        print("")
    
    # Install Wake Word models
    install_wakeword_models()

    # Summary
    print("")
    if success:
        print("✅ Model installation complete!")
        print("")
        print("Configuration summary:")
        print(f"  • LLM Provider: {llm_provider}")
        if llm_provider == "ollama":
            model_name = config.get("llm", "model", fallback="mistral")
            print(f"  • Ollama Model: {model_name}")
        if semantic_model_path:
            print(f"  • Semantic Correction: Dedicated model ({semantic_model_path})")
        else:
            print(f"  • Semantic Correction: Main LLM")
    else:
        print("⚠️  Model installation completed with some issues")
        print("   Review the messages above and retry if needed")
        print("")
        print("   You can retry later by running:")
        print("   python3 janus/scripts/install_models.py")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
