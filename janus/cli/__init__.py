"""CLI argument parsing for Janus"""
import argparse
from janus import __version__


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Janus - Voice-controlled computer automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                        # Run with persistent overlay UI (default)
  python main.py --no-ui                # Run in terminal mode (no GUI)
  python main.py --once "ouvre Safari"  # Execute single command
  python main.py --model small --lang en  # Use small model with English
  python main.py --debug                # Enable debug logging
  python main.py --logs                 # Open the logs viewer UI
  python main.py --history              # Open the action history viewer UI
  python main.py --setup-vision         # Run Vision Config Wizard
  python main.py --setup-llm            # Run LLM Setup Wizard
  python main.py --recover TXN_ID       # Recover interrupted workflow from checkpoint
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show version information and exit",
    )

    parser.add_argument(
        "--model",
        default=None,
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (overrides config.ini if specified)",
    )

    parser.add_argument(
        "--lang",
        default=None,
        help="Language code for transcription (overrides config.ini if specified)",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=40.0,
        help="Voice activation threshold (default: 40.0, lower = more sensitive)",
    )

    parser.add_argument(
        "--once",
        metavar="COMMAND",
        help="Execute a single command and exit",
    )

    parser.add_argument(
        "--no-ui",
        action="store_true",
        help="Run in terminal mode without GUI (for headless environments)",
    )

    parser.add_argument(
        "--ui",
        action="store_true",
        help="Run with GUI overlay (default). Provided for explicitness.",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    parser.add_argument(
        "--enable-tts",
        action="store_true",
        help="Enable Text-to-Speech (overrides config.ini)",
    )

    parser.add_argument(
        "--disable-tts",
        action="store_true",
        help="Disable Text-to-Speech (overrides config.ini)",
    )

    parser.add_argument(
        "--session-id",
        metavar="ID",
        help="Session ID to use or resume",
    )

    parser.add_argument(
        "--get-session",
        action="store_true",
        help="Display session information and exit",
    )

    parser.add_argument(
        "--logs",
        action="store_true",
        help="Open the logs viewer UI",
    )

    parser.add_argument(
        "--history",
        action="store_true",
        help="Open the action history viewer UI",
    )

    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Path to custom config.ini file (default: ./config.ini)",
    )

    parser.add_argument(
        "--setup-vision",
        action="store_true",
        help="Run the Vision Config Wizard to set up vision AI features",
    )

    parser.add_argument(
        "--setup-llm",
        action="store_true",
        help="Run the LLM Setup Wizard to configure local LLM backend",
    )

    parser.add_argument(
        "--recover",
        metavar="TRANSACTION_ID",
        help="Recover and resume an interrupted workflow from a checkpoint",
    )

    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run startup self-tests (services wiring) and exit",
    )

    parser.add_argument(
        "--self-test-strict",
        action="store_true",
        help="Fail if any optional dependency/service is unavailable",
    )

    return parser.parse_args()
