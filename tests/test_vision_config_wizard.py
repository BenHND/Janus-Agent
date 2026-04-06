"""
Unit tests for Vision Configuration Wizard
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from janus.vision.vision_config_wizard import VisionConfig, VisionConfigWizard


class TestVisionConfig(unittest.TestCase):
    """Test cases for VisionConfig dataclass"""

    def test_default_config(self):
        """Test default configuration values"""
        config = VisionConfig()

        self.assertTrue(config.enabled)
        self.assertTrue(config.auto_verify_actions)
        self.assertEqual(config.model_type, "blip2")
        self.assertEqual(config.device, "auto")
        self.assertTrue(config.enable_cache)
        self.assertEqual(config.cache_size, 50)
        self.assertEqual(config.min_confidence, 0.5)
        self.assertTrue(config.fallback_to_ocr)
        self.assertTrue(config.show_visual_feedback)
        self.assertTrue(config.gpu_optimization)

    def test_config_to_dict(self):
        """Test conversion to dictionary"""
        config = VisionConfig(enabled=False, auto_verify_actions=False, device="cpu")

        config_dict = config.to_dict()

        self.assertIsInstance(config_dict, dict)
        self.assertFalse(config_dict["enabled"])
        self.assertFalse(config_dict["auto_verify_actions"])
        self.assertEqual(config_dict["device"], "cpu")

    def test_config_from_dict(self):
        """Test creation from dictionary"""
        data = {
            "enabled": False,
            "auto_verify_actions": True,
            "model_type": "clip",
            "device": "cuda",
            "enable_cache": False,
            "cache_size": 100,
            "min_confidence": 0.7,
            "fallback_to_ocr": False,
            "show_visual_feedback": False,
            "gpu_optimization": True,
        }

        config = VisionConfig.from_dict(data)

        self.assertFalse(config.enabled)
        self.assertTrue(config.auto_verify_actions)
        self.assertEqual(config.model_type, "clip")
        self.assertEqual(config.device, "cuda")
        self.assertFalse(config.enable_cache)
        self.assertEqual(config.cache_size, 100)


class TestVisionConfigWizard(unittest.TestCase):
    """Test cases for VisionConfigWizard"""

    def setUp(self):
        """Set up test fixtures"""
        # Use temporary directory for config
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_vision_config.json"
        self.wizard = VisionConfigWizard(config_path=self.config_path)

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test wizard initialization"""
        self.assertIsNotNone(self.wizard)
        self.assertEqual(self.wizard.config_path, self.config_path)
        self.assertIsInstance(self.wizard.config, VisionConfig)

    def test_save_and_load_config(self):
        """Test saving and loading configuration"""
        # Create custom config
        config = VisionConfig(enabled=False, auto_verify_actions=False, device="cpu")

        # Save
        success = self.wizard.save_config(config)
        self.assertTrue(success)
        self.assertTrue(self.config_path.exists())

        # Load
        loaded_config = self.wizard.load_config()
        self.assertFalse(loaded_config.enabled)
        self.assertFalse(loaded_config.auto_verify_actions)
        self.assertEqual(loaded_config.device, "cpu")

    def test_load_nonexistent_config(self):
        """Test loading when config doesn't exist"""
        # Use path that doesn't exist
        wizard = VisionConfigWizard(config_path=Path(self.temp_dir) / "nonexistent.json")

        config = wizard.load_config()

        # Should return default config
        self.assertIsInstance(config, VisionConfig)
        self.assertTrue(config.enabled)

    def test_detect_capabilities_no_torch(self):
        """Test capability detection without PyTorch"""
        with patch("builtins.__import__", side_effect=ImportError("torch not found")):
            capabilities = self.wizard.detect_capabilities()

        self.assertFalse(capabilities["torch_available"])
        self.assertFalse(capabilities["cuda_available"])
        self.assertFalse(capabilities["mps_available"])
        self.assertEqual(capabilities["recommended_device"], "cpu")
        self.assertGreater(len(capabilities["warnings"]), 0)

    @patch("torch.cuda.is_available")
    @patch("torch.backends.mps.is_available")
    def test_detect_capabilities_with_cuda(self, mock_mps, mock_cuda):
        """Test capability detection with CUDA"""
        mock_cuda.return_value = True
        mock_mps.return_value = False

        try:
            import torch

            capabilities = self.wizard.detect_capabilities()

            self.assertTrue(capabilities["torch_available"])
            self.assertTrue(capabilities["cuda_available"])
            self.assertEqual(capabilities["recommended_device"], "cuda")
        except ImportError:
            self.skipTest("PyTorch not available")

    @patch("torch.cuda.is_available")
    @patch("torch.backends.mps.is_available")
    def test_detect_capabilities_with_mps(self, mock_mps, mock_cuda):
        """Test capability detection with Apple Silicon"""
        mock_cuda.return_value = False
        mock_mps.return_value = True

        try:
            import torch

            capabilities = self.wizard.detect_capabilities()

            self.assertTrue(capabilities["torch_available"])
            self.assertTrue(capabilities["mps_available"])
            self.assertEqual(capabilities["recommended_device"], "mps")
        except ImportError:
            self.skipTest("PyTorch not available")

    def test_run_quick_setup(self):
        """Test quick setup with defaults"""
        config = self.wizard.run_quick_setup()

        self.assertIsInstance(config, VisionConfig)
        self.assertEqual(config.model_type, "auto")
        self.assertTrue(config.enable_cache)
        self.assertTrue(config.show_visual_feedback)

        # Config should be saved
        self.assertTrue(self.config_path.exists())

    def test_get_config(self):
        """Test getting current configuration"""
        config = self.wizard.get_config()

        self.assertIsInstance(config, VisionConfig)

    def test_reset_config(self):
        """Test resetting configuration"""
        # Set custom config
        custom_config = VisionConfig(enabled=False, device="cpu")
        self.wizard.save_config(custom_config)

        # Reset
        self.wizard.reset_config()

        # Should be back to defaults
        loaded = self.wizard.load_config()
        self.assertTrue(loaded.enabled)  # Default is True
        self.assertEqual(loaded.device, "auto")  # Default is auto

    def test_test_configuration_without_models(self):
        """Test configuration testing without models"""
        # Set config with vision disabled
        self.wizard.config = VisionConfig(enabled=False)

        results = self.wizard.test_configuration()

        self.assertIn("success", results)
        self.assertIn("engine_available", results)
        self.assertIn("performance_ms", results)

    @patch("janus.vision.vision_config_wizard.VisionCognitiveEngine")
    def test_test_configuration_with_mocked_engine(self, mock_engine):
        """Test configuration testing with mocked engine"""
        # Mock successful engine
        mock_engine_instance = Mock()
        mock_engine_instance.is_available.return_value = True
        mock_engine_instance.describe.return_value = {
            "description": "Test image",
            "confidence": 0.9,
            "duration_ms": 100,
        }
        mock_engine.return_value = mock_engine_instance

        # Enable vision
        self.wizard.config = VisionConfig(enabled=True)

        results = self.wizard.test_configuration()

        self.assertTrue(results.get("success", False))
        self.assertTrue(results.get("engine_available", False))
        self.assertGreater(results.get("performance_ms", 0), 0)

    def test_ask_yes_no_default_yes(self):
        """Test yes/no question with default yes"""
        # Simulate empty input (use default)
        with patch("builtins.input", return_value=""):
            result = self.wizard._ask_yes_no("Test?", default=True)

        self.assertTrue(result)

    def test_ask_yes_no_explicit_no(self):
        """Test yes/no question with explicit no"""
        with patch("builtins.input", return_value="n"):
            result = self.wizard._ask_yes_no("Test?", default=True)

        self.assertFalse(result)

    def test_ask_choice_default(self):
        """Test multiple choice with default"""
        choices = ["option1", "option2", "option3"]

        # Simulate empty input (use default)
        with patch("builtins.input", return_value=""):
            result = self.wizard._ask_choice("Choose:", choices, default="option2")

        self.assertEqual(result, "option2")

    def test_ask_choice_explicit(self):
        """Test multiple choice with explicit selection"""
        choices = ["option1", "option2", "option3"]

        # Simulate selecting option 3
        with patch("builtins.input", return_value="3"):
            result = self.wizard._ask_choice("Choose:", choices)

        self.assertEqual(result, "option3")

    def test_print_config(self):
        """Test printing configuration"""
        config = VisionConfig(enabled=True, device="cpu")

        # Should not raise exception
        with patch("builtins.print"):
            self.wizard._print_config(config)


class TestDependencyChecking(unittest.TestCase):
    """Test cases for dependency checking"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_vision_config.json"
        self.wizard = VisionConfigWizard(config_path=self.config_path)

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_check_dependencies_all_installed(self):
        """Test dependency checking when all deps installed"""
        with patch.object(self.wizard, "detect_capabilities") as mock_detect:
            mock_detect.return_value = {
                "torch_available": True,
                "transformers_available": True,
                "missing_dependencies": [],
            }

            all_installed, missing = self.wizard.check_dependencies()

            self.assertTrue(all_installed)
            self.assertEqual(len(missing), 0)

    def test_check_dependencies_missing(self):
        """Test dependency checking when deps are missing"""
        with patch.object(self.wizard, "detect_capabilities") as mock_detect:
            mock_detect.return_value = {
                "torch_available": False,
                "transformers_available": False,
                "missing_dependencies": ["torch", "transformers"],
            }

            all_installed, missing = self.wizard.check_dependencies()

            self.assertFalse(all_installed)
            self.assertEqual(len(missing), 2)
            self.assertIn("torch", missing)
            self.assertIn("transformers", missing)

    def test_get_installation_instructions_torch(self):
        """Test getting installation instructions for torch"""
        instructions = self.wizard.get_installation_instructions(["torch"])

        self.assertIn("PyTorch", instructions)
        self.assertIn("pip install", instructions)
        self.assertIn("torch", instructions.lower())

    def test_get_installation_instructions_transformers(self):
        """Test getting installation instructions for transformers"""
        instructions = self.wizard.get_installation_instructions(["transformers"])

        self.assertIn("Transformers", instructions)
        self.assertIn("pip install", instructions)
        self.assertIn("transformers", instructions.lower())

    def test_get_installation_instructions_multiple(self):
        """Test getting installation instructions for multiple deps"""
        instructions = self.wizard.get_installation_instructions(["torch", "transformers"])

        self.assertIn("PyTorch", instructions)
        self.assertIn("Transformers", instructions)

    def test_get_installation_instructions_none_missing(self):
        """Test installation instructions when no deps missing"""
        instructions = self.wizard.get_installation_instructions([])

        self.assertIn("All dependencies", instructions)
        self.assertIn("installed", instructions)

    def test_detect_capabilities_tracks_missing(self):
        """Test that detect_capabilities tracks missing dependencies"""
        capabilities = self.wizard.detect_capabilities()

        self.assertIn("missing_dependencies", capabilities)
        self.assertIsInstance(capabilities["missing_dependencies"], list)


class TestVisionConfigWizardMain(unittest.TestCase):
    """Test main function"""

    @patch("janus.vision.vision_config_wizard.VisionConfigWizard")
    @patch("sys.argv", ["script", "--quick"])
    def test_main_quick_setup(self, mock_wizard):
        """Test main with quick setup"""
        from janus.vision.vision_config_wizard import main

        mock_wizard_instance = Mock()
        mock_config = VisionConfig(enabled=False)
        mock_wizard_instance.run_quick_setup.return_value = mock_config
        mock_wizard_instance.test_configuration.return_value = {
            "success": False,
            "errors": ["Test error"],
        }
        mock_wizard.return_value = mock_wizard_instance

        # Should not raise exception
        with patch("builtins.print"):
            main()

        mock_wizard_instance.run_quick_setup.assert_called_once()


if __name__ == "__main__":
    unittest.main()
