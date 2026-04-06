"""
Consent manager for crash reporting opt-in

TICKET-OPS-002: Manages user consent for crash reporting
- Prompts user on first launch
- Stores consent in config.ini
- Allows users to opt-in or opt-out
"""

import configparser
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ConsentManager:
    """Manages user consent for crash reporting and telemetry"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize consent manager

        Args:
            config_path: Path to config.ini file (default: config.ini in project root)
        """
        self.config_path = Path(config_path) if config_path else Path("config.ini")
        self.config = configparser.ConfigParser()

        # Load existing config if it exists
        if self.config_path.exists():
            try:
                self.config.read(self.config_path)
            except Exception as e:
                logger.error(f"Failed to read config file: {e}")

    def has_answered(self) -> bool:
        """
        Check if user has already answered the consent prompt

        Returns:
            True if user has answered, False otherwise
        """
        if not self.config.has_section("telemetry"):
            return False

        return self.config.has_option("telemetry", "crash_reporting_consent")

    def get_consent(self) -> bool:
        """
        Get current consent status

        Returns:
            True if user has consented, False otherwise
        """
        if not self.has_answered():
            return False

        try:
            return self.config.getboolean("telemetry", "crash_reporting_consent")
        except Exception:
            return False

    def set_consent(self, consent: bool) -> bool:
        """
        Set consent status and save to config

        Args:
            consent: True to opt-in, False to opt-out

        Returns:
            True if successfully saved, False otherwise
        """
        try:
            # Ensure telemetry section exists
            if not self.config.has_section("telemetry"):
                self.config.add_section("telemetry")

            # Set consent
            self.config.set("telemetry", "crash_reporting_consent", str(consent).lower())

            # Save to file
            with open(self.config_path, "w") as f:
                self.config.write(f)

            logger.info(f"Crash reporting consent set to: {consent}")
            return True

        except Exception as e:
            logger.error(f"Failed to save consent: {e}")
            return False

    def revoke_consent(self) -> bool:
        """
        Revoke consent (opt-out)

        Returns:
            True if successfully revoked, False otherwise
        """
        return self.set_consent(False)


def prompt_for_consent(config_path: Optional[str] = None) -> bool:
    """
    Prompt user for crash reporting consent

    TICKET-OPS-002: Interactive prompt for first launch
    Shows information about what data is collected and how it's used

    Args:
        config_path: Path to config.ini file

    Returns:
        True if user consented, False otherwise
    """
    manager = ConsentManager(config_path)

    # Check if already answered
    if manager.has_answered():
        return manager.get_consent()

    # Display information and prompt
    print("\n" + "="*70)
    print("🔒 CRASH REPORTING & TELEMETRY (TICKET-OPS-002)")
    print("="*70)
    print("\nJanus can send anonymous crash reports to help improve the application.")
    print("\nWhat we collect:")
    print("  ✓ Stack traces and error messages (sanitized)")
    print("  ✓ System information (OS, Python version)")
    print("  ✓ Application version and configuration")
    print("\nWhat we DON'T collect:")
    print("  ✗ Screenshots or screen captures")
    print("  ✗ Your voice commands or prompts")
    print("  ✗ API keys, passwords, or tokens")
    print("  ✗ Personal files or data")
    print("\nAll reports are automatically sanitized to remove sensitive information.")
    print("You can opt-out at any time by editing config.ini")
    print("\n" + "="*70)

    while True:
        response = input("\nAllow anonymous crash reports? [y/N]: ").strip().lower()

        if response in ('y', 'yes'):
            manager.set_consent(True)
            print("✓ Crash reporting enabled. Thank you for helping improve Janus!")
            return True
        elif response in ('n', 'no', ''):
            manager.set_consent(False)
            print("✓ Crash reporting disabled. You can enable it later in config.ini")
            return False
        else:
            print("Please answer 'y' for yes or 'n' for no.")
