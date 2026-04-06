"""
Vision Configuration Wizard - Using OmniParser
TICKET-CLEANUP-VISION: Migrated from Florence-2 to OmniParser

Helps users set up OmniParser AI model for vision cognitive features.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from janus.utils.paths import get_vision_config_path

logger = logging.getLogger(__name__)


@dataclass
class VisionConfig:
    """Configuration for OmniParser vision cognitive features"""

    enabled: bool = True
    auto_verify_actions: bool = True  # Automatically verify actions with vision
    model_type: str = "florence2"  # florence2 (TICKET-302: no legacy options)
    device: str = "auto"  # "auto", "cpu", "cuda", "mps"
    enable_cache: bool = True
    cache_size: int = 50
    min_confidence: float = 0.5  # Minimum confidence for vision verification
    fallback_to_ocr: bool = True  # Fallback to OCR if OmniParser unavailable
    show_visual_feedback: bool = True  # Show detections in overlay
    gpu_optimization: bool = True  # Use GPU optimizations if available

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisionConfig":
        """Create from dictionary"""
        # TICKET-302: Force florence2 model type
        data["model_type"] = "florence2"
        return cls(**data)


class VisionConfigWizard:
    """
    Interactive configuration wizard for Florence-2 vision model.
    
    TICKET-302: Uses only Florence-2, no legacy BLIP-2/CLIP code.

    Features:
    - Detect GPU support
    - Guide users through setup
    - Test Florence-2 performance
    - Save/load configuration
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration wizard

        Args:
            config_path: Path to save configuration (default: platform-specific config directory)
        """
        if config_path is None:
            config_path = get_vision_config_path()

        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Current configuration
        self.config = self.load_config()

    def load_config(self) -> VisionConfig:
        """Load configuration from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                return VisionConfig.from_dict(data)
            except Exception as e:
                logger.warning(f"Could not load config from {self.config_path}: {e}")

        # Return default config
        return VisionConfig()

    def save_config(self, config: Optional[VisionConfig] = None) -> bool:
        """
        Save configuration to file

        Args:
            config: Configuration to save (uses self.config if None)

        Returns:
            True if saved successfully
        """
        if config is None:
            config = self.config

        try:
            with open(self.config_path, "w") as f:
                json.dump(config.to_dict(), f, indent=2)
            logger.info(f"Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Could not save config to {self.config_path}: {e}")
            return False

    def detect_capabilities(self) -> Dict[str, Any]:
        """
        Detect available vision AI capabilities

        Returns:
            Dictionary with available features and recommendations
        """
        capabilities = {
            "torch_available": False,
            "transformers_available": False,
            "cuda_available": False,
            "mps_available": False,
            "recommended_device": "cpu",
            "blip2_available": False,
            "clip_available": False,
            "estimated_memory_gb": 0,
            "warnings": [],
            "missing_dependencies": [],
        }

        # Check PyTorch
        try:
            import torch

            capabilities["torch_available"] = True

            # Check CUDA (NVIDIA GPU)
            if torch.cuda.is_available():
                capabilities["cuda_available"] = True
                capabilities["recommended_device"] = "cuda"
                capabilities["estimated_memory_gb"] = 3.5

            # Check MPS (Apple Silicon)
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                capabilities["mps_available"] = True
                capabilities["recommended_device"] = "mps"
                capabilities["estimated_memory_gb"] = 3.0

            else:
                capabilities["recommended_device"] = "cpu"
                capabilities["estimated_memory_gb"] = 4.0
                capabilities["warnings"].append("No GPU detected. Models will run on CPU (slower).")

        except ImportError:
            capabilities["warnings"].append(
                "PyTorch not installed. Install with: pip install torch"
            )
            capabilities["missing_dependencies"].append("torch")

        # Check transformers
        try:
            import transformers

            capabilities["transformers_available"] = True

            # Check if models are cached in local directory
            # Use environment variable if set, otherwise use transformers default
            cache_path = Path(
                os.environ.get("TRANSFORMERS_CACHE", transformers.utils.TRANSFORMERS_CACHE)
            )

            # Check for BLIP-2
            if cache_path.exists() and any(
                "blip2" in str(p).lower() for p in cache_path.glob("**/*")
            ):
                capabilities["blip2_available"] = True

            # Check for CLIP
            if cache_path.exists() and any(
                "clip" in str(p).lower() for p in cache_path.glob("**/*")
            ):
                capabilities["clip_available"] = True

        except ImportError:
            capabilities["warnings"].append(
                "Transformers not installed. Install with: pip install transformers"
            )
            capabilities["missing_dependencies"].append("transformers")

        return capabilities

    def check_dependencies(self) -> Tuple[bool, List[str]]:
        """
        Check if all required dependencies are installed

        Returns:
            Tuple of (all_installed, missing_packages)
        """
        capabilities = self.detect_capabilities()
        missing = capabilities.get("missing_dependencies", [])

        return len(missing) == 0, missing

    def get_installation_instructions(self, missing_deps: List[str]) -> str:
        """
        Get installation instructions for missing dependencies

        Args:
            missing_deps: List of missing dependency names

        Returns:
            Formatted installation instructions
        """
        if not missing_deps:
            return "All dependencies are installed!"

        instructions = "\n" + "=" * 60 + "\n"
        instructions += "Missing Dependencies Detected\n"
        instructions += "=" * 60 + "\n\n"

        instructions += "To use Vision AI features, you need to install:\n\n"

        for dep in missing_deps:
            if dep == "torch":
                instructions += "• PyTorch:\n"
                instructions += "  pip install torch torchvision\n\n"
                instructions += "  Or for Apple Silicon (M1/M2/M3):\n"
                instructions += "  pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu\n\n"

            elif dep == "transformers":
                instructions += "• Transformers:\n"
                instructions += "  pip install transformers\n\n"

        instructions += "After installation, run this wizard again:\n"
        instructions += "  python main.py --setup-vision\n"
        instructions += "=" * 60 + "\n"

        return instructions

    def run_interactive_setup(self) -> VisionConfig:
        """
        Run interactive setup wizard

        Returns:
            Configured VisionConfig
        """
        print("=" * 60)
        print("Vision AI Configuration Wizard")
        print("=" * 60)
        print()

        # Check dependencies first
        all_deps_installed, missing_deps = self.check_dependencies()

        if not all_deps_installed:
            print("\n⚠️  Missing Required Dependencies\n")
            print(self.get_installation_instructions(missing_deps))

            # Ask if user wants to continue anyway
            continue_anyway = self._ask_yes_no(
                "\nDo you want to continue setup anyway? (Vision features will be disabled)",
                default=False,
            )

            if not continue_anyway:
                print("\nSetup cancelled. Please install dependencies and try again.")
                return None
            else:
                # Create disabled config
                config = VisionConfig(enabled=False)
                self.config = config
                self.save_config()
                print("\n✓ Vision AI disabled (missing dependencies)")
                return config

        # Detect capabilities
        print("Detecting available capabilities...")
        capabilities = self.detect_capabilities()

        print("\n--- System Capabilities ---")
        print(f"PyTorch: {'✓' if capabilities['torch_available'] else '✗'}")
        print(f"Transformers: {'✓' if capabilities['transformers_available'] else '✗'}")
        print(f"CUDA (NVIDIA GPU): {'✓' if capabilities['cuda_available'] else '✗'}")
        print(f"MPS (Apple Silicon): {'✓' if capabilities['mps_available'] else '✗'}")
        print(f"Recommended device: {capabilities['recommended_device']}")

        if capabilities["warnings"]:
            print("\n⚠️  Warnings:")
            for warning in capabilities["warnings"]:
                print(f"  - {warning}")

        # Ask questions
        print("\n--- Configuration ---")

        # Enable vision AI?
        enabled = self._ask_yes_no("Enable vision AI for action verification?", default=True)

        if not enabled:
            print("\nVision AI disabled. Using OCR-only mode.")
            config = VisionConfig(enabled=False)
            self.config = config
            self.save_config()
            return config

        # Auto-verify actions?
        auto_verify = self._ask_yes_no(
            "Automatically verify actions after execution?", default=True
        )

        # Device selection
        if capabilities["torch_available"]:
            device = self._ask_choice(
                "Select compute device:",
                ["auto", "cpu", "cuda", "mps"],
                default=capabilities["recommended_device"],
            )
        else:
            device = "cpu"

        # Model type
        model_type = self._ask_choice(
            "Select AI model:",
            ["blip2", "clip", "auto"],
            default="auto",
            help_text={
                "blip2": "Best for image captioning and Q&A",
                "clip": "Best for element finding",
                "auto": "Use both models (recommended)",
            },
        )

        # Advanced options
        print("\n--- Advanced Options ---")

        enable_cache = self._ask_yes_no(
            "Enable result caching for better performance?", default=True
        )

        show_feedback = self._ask_yes_no("Show visual feedback in overlay?", default=True)

        gpu_optimization = False
        if capabilities["cuda_available"] or capabilities["mps_available"]:
            gpu_optimization = self._ask_yes_no("Enable GPU optimizations?", default=True)

        # Create configuration
        config = VisionConfig(
            enabled=enabled,
            auto_verify_actions=auto_verify,
            model_type=model_type,
            device=device,
            enable_cache=enable_cache,
            show_visual_feedback=show_feedback,
            gpu_optimization=gpu_optimization,
        )

        # Save configuration
        print("\n--- Summary ---")
        self._print_config(config)

        save = self._ask_yes_no("\nSave this configuration?", default=True)

        if save:
            if self.save_config(config):
                print(f"✓ Configuration saved to {self.config_path}")
            else:
                print("✗ Failed to save configuration")

        self.config = config
        return config

    def run_quick_setup(self) -> VisionConfig:
        """
        Run quick setup with defaults

        Returns:
            Configured VisionConfig with smart defaults
        """
        capabilities = self.detect_capabilities()

        config = VisionConfig(
            enabled=capabilities["torch_available"] and capabilities["transformers_available"],
            auto_verify_actions=True,
            model_type="auto",
            device=capabilities["recommended_device"],
            enable_cache=True,
            show_visual_feedback=True,
            gpu_optimization=capabilities["cuda_available"] or capabilities["mps_available"],
        )

        self.config = config
        self.save_config()

        return config

    def _ask_yes_no(self, question: str, default: bool = True) -> bool:
        """Ask a yes/no question"""
        default_str = "Y/n" if default else "y/N"
        response = input(f"{question} [{default_str}]: ").strip().lower()

        if not response:
            return default

        return response in ["y", "yes"]

    def _ask_choice(
        self,
        question: str,
        choices: List[str],
        default: str = None,
        help_text: Dict[str, str] = None,
    ) -> str:
        """Ask a multiple choice question"""
        print(f"\n{question}")

        for i, choice in enumerate(choices, 1):
            marker = "*" if choice == default else " "
            help_msg = f" - {help_text[choice]}" if help_text and choice in help_text else ""
            print(f"  {marker} {i}. {choice}{help_msg}")

        while True:
            if default:
                response = input(f"Choice [1-{len(choices)}] (default: {default}): ").strip()
            else:
                response = input(f"Choice [1-{len(choices)}]: ").strip()

            if not response and default:
                return default

            try:
                idx = int(response) - 1
                if 0 <= idx < len(choices):
                    return choices[idx]
            except ValueError as e:
                logger.debug(f"Invalid numeric choice: {response}")

            print("Invalid choice. Please try again.")

    def _print_config(self, config: VisionConfig):
        """Print configuration summary"""
        print(f"Enabled: {config.enabled}")
        print(f"Auto-verify actions: {config.auto_verify_actions}")
        print(f"Model type: {config.model_type}")
        print(f"Device: {config.device}")
        print(f"Enable cache: {config.enable_cache}")
        print(f"Show visual feedback: {config.show_visual_feedback}")
        print(f"GPU optimization: {config.gpu_optimization}")

    def test_configuration(self) -> Dict[str, Any]:
        """
        Test the current configuration with OmniParser.
        
        TICKET-CLEANUP-VISION: Uses OmniParser instead of Florence-2.

        Returns:
            Test results with performance metrics
        """
        from PIL import Image, ImageDraw

        results = {
            "success": False,
            "engine_available": False,
            "description_test": None,
            "performance_ms": 0,
            "errors": [],
            "engine_type": "omniparser",
        }

        try:
            # Create test image
            test_image = Image.new("RGB", (400, 300), color="white")
            draw = ImageDraw.Draw(test_image)
            draw.text((100, 100), "Test Image", fill="black")

            # Initialize OmniParser engine
            import time

            start = time.time()

            try:
                from janus.vision.omniparser_adapter import OmniParserVisionEngine
                engine = OmniParserVisionEngine(
                    device=self.config.device,
                    enable_cache=self.config.enable_cache,
                    lazy_load=False,
                )
            except ImportError as e:
                results["errors"].append(f"OmniParser not installed: {e}")
                return results
            except Exception as e:
                results["errors"].append(f"OmniParser failed: {e}")
                return results

            results["engine_available"] = engine.is_available()

            # Test description
            if results["engine_available"]:
                desc_result = engine.describe(test_image)
                results["description_test"] = desc_result
                results["success"] = True
            else:
                results["errors"].append("OmniParser not available")

            results["performance_ms"] = int((time.time() - start) * 1000)

        except Exception as e:
            results["errors"].append(str(e))

        return results

    def get_config(self) -> VisionConfig:
        """Get current configuration"""
        return self.config

    def reset_config(self):
        """Reset configuration to defaults"""
        self.config = VisionConfig()
        self.save_config()


def main():
    """Run configuration wizard"""
    wizard = VisionConfigWizard()

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        print("Running quick setup...")
        config = wizard.run_quick_setup()
        print("\n✓ Quick setup complete!")
    else:
        config = wizard.run_interactive_setup()

    # Test configuration
    if config.enabled:
        print("\nTesting configuration...")
        results = wizard.test_configuration()

        if results["success"]:
            print("✓ Configuration test passed!")
            if results["description_test"]:
                print(f"  Performance: {results['performance_ms']}ms")
        else:
            print("✗ Configuration test failed:")
            for error in results["errors"]:
                print(f"  - {error}")
