#!/usr/bin/env python3
"""
Janus - Voice-controlled computer automation
Main entry point

TICKET 1 (P0): Adds signal handlers for clean shutdown
"""
import atexit
import os
import signal
import sys

# Suppress tokenizers parallelism warning (occurs when process forks after using tokenizers)
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Use repo-local HuggingFace cache location (avoids TRANSFORMERS_CACHE deprecation and
# makes preloading reusable across runs/machines without touching global caches).
_cwd_repo_root = os.path.abspath(os.getcwd())
os.environ.setdefault("HF_HOME", os.path.join(_cwd_repo_root, ".hf_cache"))
os.environ.setdefault("TRANSFORMERS_CACHE", os.path.join(os.environ["HF_HOME"], "transformers"))
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", os.path.join(os.environ["HF_HOME"], "sentence_transformers"))

# Initialize model paths FIRST
try:
    from janus.config.model_paths import setup_model_paths
except ModuleNotFoundError as e:
    # Common dev footgun after repo reorg: running the file directly means the
    # project root (where `janus/` lives) is not on sys.path.
    if e.name == "janus":
        print("ERROR: Could not import 'janus'.")
        print("You're probably running this file directly (e.g. `python main.py`).")
        print("Run one of these from the repo root (Janus/):")
        print("  python -m apps.cli.main --debug")
        print("Or install editable once, then use the console script:")
        print("  pip install -e .")
        print("  janus --debug")
        raise SystemExit(2)
    raise

setup_model_paths()

from janus.cli import parse_arguments
from janus.app import JanusApplication
from janus.runtime.shutdown import request_shutdown

# Global reference to application for signal handlers
_app_instance = None


def _handle_shutdown_signal(signum, frame):
    """
    Handle SIGINT (Ctrl+C) and SIGTERM signals.
    
    TICKET 1 (P0): Request global shutdown to prevent any further OS actions.
    """
    signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
    print(f"\n🛑 Received {signal_name} - initiating shutdown...")
    
    # Request global shutdown
    request_shutdown(f"Received {signal_name}")
    
    # Cleanup pipeline if available
    if _app_instance and _app_instance.pipeline:
        try:
            from janus.app.initialization import cleanup_pipeline
            cleanup_pipeline(_app_instance.pipeline)
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    # Exit gracefully
    sys.exit(0)


def _atexit_handler():
    """
    Handle normal program exit.
    
    TICKET 1 (P0): Ensure cleanup on normal exit as well.
    """
    if _app_instance and _app_instance.pipeline:
        try:
            from janus.app.initialization import cleanup_pipeline
            # Cleanup BEFORE requesting shutdown so services can finish cleanly
            cleanup_pipeline(_app_instance.pipeline)
            request_shutdown("Normal program exit")
        except Exception:
            pass  # Don't raise during exit


def main():
    """Main entry point"""
    global _app_instance
    
    # Register signal handlers (TICKET 1 P0)
    signal.signal(signal.SIGINT, _handle_shutdown_signal)
    signal.signal(signal.SIGTERM, _handle_shutdown_signal)
    
    # Register atexit handler (TICKET 1 P0)
    atexit.register(_atexit_handler)
    
    args = parse_arguments()
    _app_instance = JanusApplication(args)
    return _app_instance.run()


if __name__ == "__main__":
    sys.exit(main())
