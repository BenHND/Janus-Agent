"""
Unit tests for main.py command-line flags
"""
import sys
import unittest
from io import StringIO
from unittest.mock import MagicMock, Mock, patch


class TestMainCommandLineFlags(unittest.TestCase):
    """Test cases for main.py command-line argument handling"""

    @patch("sys.argv", ["main.py", "--help"])
    def test_help_shows_setup_flags(self):
        """Test that help output includes setup flags"""
        # Import main to trigger argparse
        import main

        # Capture help output
        with patch("sys.stdout", new=StringIO()) as fake_out:
            try:
                main.main()
            except SystemExit:
                pass  # argparse exits on --help

        help_text = fake_out.getvalue()
        self.assertIn("--setup-vision", help_text)
        self.assertIn("--setup-llm", help_text)

    @patch("janus.vision.vision_config_wizard.VisionConfigWizard")
    @patch("sys.argv", ["main.py", "--setup-vision"])
    def test_setup_vision_flag(self, mock_wizard):
        """Test --setup-vision flag invokes Vision Config Wizard"""
        # Mock the wizard
        mock_wizard_instance = Mock()
        mock_config = Mock(enabled=True)
        mock_wizard_instance.run_interactive_setup.return_value = mock_config
        mock_wizard.return_value = mock_wizard_instance

        # Import and run main
        import main

        with patch("builtins.print"):
            result = main.main()

        # Verify wizard was called
        mock_wizard.assert_called_once()
        mock_wizard_instance.run_interactive_setup.assert_called_once()
        self.assertEqual(result, 0)

    @patch("janus.reasoning.llm_setup_wizard.LLMSetupWizard")
    @patch("sys.argv", ["main.py", "--setup-llm"])
    def test_setup_llm_flag(self, mock_wizard):
        """Test --setup-llm flag invokes LLM Setup Wizard"""
        # Mock the wizard
        mock_wizard_instance = Mock()
        mock_config = {"backend": "ollama"}
        mock_wizard_instance.run_interactive_setup.return_value = mock_config
        mock_wizard.return_value = mock_wizard_instance

        # Import and run main
        import main

        with patch("builtins.print"):
            result = main.main()

        # Verify wizard was called
        mock_wizard.assert_called_once()
        mock_wizard_instance.run_interactive_setup.assert_called_once()
        self.assertEqual(result, 0)

    @patch("janus.vision.vision_config_wizard.VisionConfigWizard")
    @patch("sys.argv", ["main.py", "--setup-vision"])
    def test_setup_vision_flag_disabled(self, mock_wizard):
        """Test --setup-vision when vision is disabled"""
        # Mock the wizard returning disabled config
        mock_wizard_instance = Mock()
        mock_config = Mock(enabled=False)
        mock_wizard_instance.run_interactive_setup.return_value = mock_config
        mock_wizard.return_value = mock_wizard_instance

        # Import and run main
        import main

        with patch("builtins.print") as mock_print:
            result = main.main()

        # Should still return success
        self.assertEqual(result, 0)

        # Check that appropriate message was printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("disabled" in str(call).lower() for call in print_calls))

    @patch("janus.reasoning.llm_setup_wizard.LLMSetupWizard")
    @patch("sys.argv", ["main.py", "--setup-llm"])
    def test_setup_llm_flag_cancelled(self, mock_wizard):
        """Test --setup-llm when setup is cancelled"""
        # Mock the wizard returning None (cancelled)
        mock_wizard_instance = Mock()
        mock_wizard_instance.run_interactive_setup.return_value = None
        mock_wizard.return_value = mock_wizard_instance

        # Import and run main
        import main

        with patch("builtins.print") as mock_print:
            result = main.main()

        # Should still return success
        self.assertEqual(result, 0)

        # Check that appropriate message was printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(
            any(
                "cancelled" in str(call).lower() or "incomplete" in str(call).lower()
                for call in print_calls
            )
        )

    @patch("janus.vision.vision_config_wizard.VisionConfigWizard")
    @patch("sys.argv", ["main.py", "--setup-vision"])
    def test_setup_vision_flag_error(self, mock_wizard):
        """Test --setup-vision handles errors gracefully"""
        # Mock the wizard raising an exception
        mock_wizard.side_effect = Exception("Test error")

        # Import and run main
        import main

        with patch("builtins.print"):
            result = main.main()

        # Should return error code
        self.assertEqual(result, 1)

    @patch("janus.reasoning.llm_setup_wizard.LLMSetupWizard")
    @patch("sys.argv", ["main.py", "--setup-llm"])
    def test_setup_llm_flag_error(self, mock_wizard):
        """Test --setup-llm handles errors gracefully"""
        # Mock the wizard raising an exception
        mock_wizard.side_effect = Exception("Test error")

        # Import and run main
        import main

        with patch("builtins.print"):
            result = main.main()

        # Should return error code
        self.assertEqual(result, 1)


class TestMainIntegration(unittest.TestCase):
    """Integration tests for main.py wizards"""

    @patch("sys.argv", ["main.py", "--version"])
    def test_version_flag_works(self):
        """Test that --version flag still works"""
        import main

        with patch("sys.stdout", new=StringIO()):
            try:
                main.main()
            except SystemExit as e:
                # --version should exit with code 0
                self.assertEqual(e.code, 0)


if __name__ == "__main__":
    unittest.main()
