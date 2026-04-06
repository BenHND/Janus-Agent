"""
Cross-platform path utilities for Janus
Uses platformdirs to provide correct paths for all platforms
"""

from pathlib import Path
from typing import Optional

from platformdirs import user_cache_dir, user_config_dir, user_data_dir, user_log_dir

# Application identifiers for platformdirs
APP_NAME = "Janus"
APP_AUTHOR = "BenHND"


def get_data_dir(ensure_exists: bool = True) -> Path:
    """
    Get platform-specific data directory for Janus

    Examples:
    - macOS: ~/Library/Application Support/Janus
    - Linux: ~/.local/share/Janus
    - Windows: C:\\Users\\<user>\\AppData\\Local\\BenHND\\Janus

    Args:
        ensure_exists: Create directory if it doesn't exist

    Returns:
        Path to data directory
    """
    path = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    if ensure_exists:
        path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_dir(ensure_exists: bool = True) -> Path:
    """
    Get platform-specific config directory for Janus

    Examples:
    - macOS: ~/Library/Application Support/Janus
    - Linux: ~/.config/Janus
    - Windows: C:\\Users\\<user>\\AppData\\Local\\BenHND\\Janus

    Args:
        ensure_exists: Create directory if it doesn't exist

    Returns:
        Path to config directory
    """
    path = Path(user_config_dir(APP_NAME, APP_AUTHOR))
    if ensure_exists:
        path.mkdir(parents=True, exist_ok=True)
    return path


def get_log_dir(ensure_exists: bool = True) -> Path:
    """
    Get platform-specific log directory for Janus

    Examples:
    - macOS: ~/Library/Logs/Janus
    - Linux: ~/.local/state/Janus/log
    - Windows: C:\\Users\\<user>\\AppData\\Local\\BenHND\\Janus\\Logs

    Args:
        ensure_exists: Create directory if it doesn't exist

    Returns:
        Path to log directory
    """
    path = Path(user_log_dir(APP_NAME, APP_AUTHOR))
    if ensure_exists:
        path.mkdir(parents=True, exist_ok=True)
    return path


def get_cache_dir(ensure_exists: bool = True) -> Path:
    """
    Get platform-specific cache directory for Janus

    Examples:
    - macOS: ~/Library/Caches/Janus
    - Linux: ~/.cache/Janus
    - Windows: C:\\Users\\<user>\\AppData\\Local\\BenHND\\Janus\\Cache

    Args:
        ensure_exists: Create directory if it doesn't exist

    Returns:
        Path to cache directory
    """
    path = Path(user_cache_dir(APP_NAME, APP_AUTHOR))
    if ensure_exists:
        path.mkdir(parents=True, exist_ok=True)
    return path


def get_models_dir(ensure_exists: bool = True) -> Path:
    """
    Get directory for storing AI models

    Uses cache directory as models can be re-downloaded

    Args:
        ensure_exists: Create directory if it doesn't exist

    Returns:
        Path to models directory
    """
    path = get_cache_dir(ensure_exists) / "models"
    if ensure_exists:
        path.mkdir(parents=True, exist_ok=True)
    return path


def get_encryption_key_path(ensure_dir_exists: bool = True) -> Path:
    """
    Get path for encryption key file

    Stored in data directory for security

    Args:
        ensure_dir_exists: Create parent directory if it doesn't exist

    Returns:
        Path to encryption key file
    """
    data_dir = get_data_dir(ensure_exists=ensure_dir_exists)
    return data_dir / ".encryption_key"


def get_config_file_path(filename: str = "config.ini", ensure_dir_exists: bool = True) -> Path:
    """
    Get path for a config file

    Args:
        filename: Name of config file
        ensure_dir_exists: Create config directory if it doesn't exist

    Returns:
        Path to config file
    """
    config_dir = get_config_dir(ensure_exists=ensure_dir_exists)
    return config_dir / filename


def get_vision_config_path(ensure_dir_exists: bool = True) -> Path:
    """
    Get path for vision configuration file

    Args:
        ensure_dir_exists: Create config directory if it doesn't exist

    Returns:
        Path to vision config file
    """
    return get_config_file_path("vision_config.json", ensure_dir_exists)


# Backward compatibility: provide old paths as alternatives for migration

