"""
Configuration loader for Janus
Loads settings from config.ini file
"""

import configparser
import os
from pathlib import Path
from typing import Any, Optional

from janus.utils.paths import get_config_file_path


class ConfigLoader:
    """
    Simple configuration loader for config.ini
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader

        Args:
            config_path: Path to config.ini file. If None, searches in standard locations.
        """
        self.config = configparser.ConfigParser()

        if config_path:
            self.config_path = Path(config_path)
        else:
            # Search for config.ini in standard locations
            search_paths = [
                Path.cwd() / "config.ini",
                Path(__file__).parent.parent.parent / "config.ini",
                get_config_file_path("config.ini", ensure_dir_exists=False),
            ]

            self.config_path = None
            for path in search_paths:
                if path.exists():
                    self.config_path = path
                    break

            if not self.config_path:
                # Use default location in project root
                self.config_path = Path.cwd() / "config.ini"

        # Load config if file exists
        if self.config_path.exists():
            self.config.read(self.config_path)

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """
        Get configuration value

        Args:
            section: Configuration section
            key: Configuration key
            fallback: Fallback value if key not found

        Returns:
            Configuration value or fallback
        """
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """
        Get boolean configuration value

        Args:
            section: Configuration section
            key: Configuration key
            fallback: Fallback value if key not found

        Returns:
            Boolean configuration value or fallback
        """
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """
        Get integer configuration value

        Args:
            section: Configuration section
            key: Configuration key
            fallback: Fallback value if key not found

        Returns:
            Integer configuration value or fallback
        """
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """
        Get float configuration value

        Args:
            section: Configuration section
            key: Configuration key
            fallback: Fallback value if key not found

        Returns:
            Float configuration value or fallback
        """
        try:
            return self.config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback

    def has_section(self, section: str) -> bool:
        """
        Check if configuration section exists

        Args:
            section: Configuration section

        Returns:
            True if section exists, False otherwise
        """
        return self.config.has_section(section)

    def has_option(self, section: str, key: str) -> bool:
        """
        Check if configuration option exists

        Args:
            section: Configuration section
            key: Configuration key

        Returns:
            True if option exists, False otherwise
        """
        return self.config.has_option(section, key)


# Global config loader instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader(config_path: Optional[str] = None) -> ConfigLoader:
    """
    Get global configuration loader instance

    Args:
        config_path: Optional path to config file

    Returns:
        ConfigLoader instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(config_path)
    return _config_loader
