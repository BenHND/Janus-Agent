"""CLI commands for Janus (wizards, viewers, etc.)"""
import asyncio
import logging

logger = logging.getLogger(__name__)


def run_vision_wizard():
    """Run the Vision Config Wizard"""
    from janus.vision.vision_config_wizard import VisionConfigWizard

    logger.info("Starting Vision Config Wizard...")
    print("=" * 60)
    print("Vision Config Wizard")
    print("=" * 60)
    wizard = VisionConfigWizard()
    config = wizard.run_interactive_setup()

    if config and config.enabled:
        print("\n✓ Vision AI configuration complete!")
        print("  Vision features are now enabled.")
        return 0
    elif config and not config.enabled:
        print("\n✓ Vision AI disabled.")
        print("  You can re-run this wizard anytime with: python main.py --setup-vision")
        return 0
    else:
        print("\n⚠ Vision AI configuration cancelled.")
        return 1


def run_llm_wizard():
    """Run the LLM Setup Wizard"""
    from janus.ai.reasoning.llm_setup_wizard import LLMSetupWizard

    logger.info("Starting LLM Setup Wizard...")
    wizard = LLMSetupWizard()
    config = wizard.run_interactive_setup()

    if config:
        print("\n✓ LLM configuration complete!")
        print("  You can now use advanced reasoning features.")
        return 0
    else:
        print("\n⚠ LLM configuration cancelled or incomplete.")
        print("  You can re-run this wizard anytime with: python main.py --setup-llm")
        return 1


def show_logs_viewer():
    """Open the logs viewer UI"""
    from janus.ui.logs_viewer import show_logs_viewer as show_viewer

    logger.info("Opening logs viewer...")
    print("Opening Janus Logs Viewer...")
    show_viewer()
    return 0


def show_history_viewer():
    """Open the action history viewer UI"""
    from janus.ui.history_viewer import show_history_viewer as show_viewer

    logger.info("Opening action history viewer...")
    print("Opening Janus Action History Viewer...")
    show_viewer()
    return 0


# REMOVED: recover_workflow function (TICKET-AUDIT-001)
# Legacy workflow recovery has been deleted with SmartOrchestrator.
# Use ActionCoordinator instead for new workflows.

