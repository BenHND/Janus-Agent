"""
Configuration Manager - Programmatic API for module and feature configuration
Ticket 10.2: Interface config module for runtime configuration management
"""

import json
import os
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from janus.logging import get_logger


class ConfigManager:
    """
    Programmatic configuration manager for Janus
    Allows enabling/disabling modules and features at runtime without UI
    """

    def __init__(self, config_path: str = "config.json", auto_save: bool = True):
        """
        Initialize configuration manager

        Args:
            config_path: Path to configuration file
            auto_save: Automatically save configuration when modified
        """
        self.logger = get_logger("config_manager")
        self.config_path = config_path
        self.auto_save = auto_save
        self.config: Dict[str, Any] = self._load_config()
        self._lock = threading.Lock()
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Error loading config: {e}, using defaults")

        # Default configuration
        return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "modules": {
                "chrome": {"enabled": True},
                "vscode": {"enabled": True},
                "terminal": {"enabled": True},
                "finder": {"enabled": True},
                "slack": {"enabled": True},
            },
            "features": {
                "vision_fallback": {"enabled": True, "label": "Vision/OCR Fallback"},
                "llm_integration": {"enabled": False, "label": "LLM Integration"},
                "action_history": {"enabled": True, "label": "Action History"},
                "undo_redo": {"enabled": True, "label": "Undo/Redo System"},
                "workflow_persistence": {"enabled": True, "label": "Workflow Persistence"},
            },
            "ui": {
                "show_overlay": {"enabled": True, "label": "Visual Feedback Overlay"},
                "enhanced_overlay": {"enabled": True, "label": "Enhanced Overlay with Highlights"},
                "screenshot_overlay": {"enabled": True, "label": "Mini Screenshot Overlay"},
                "confirmation_dialogs": {"enabled": True, "label": "Confirmation Dialogs"},
                "overlay_position": {
                    "value": "top-right",
                    "options": ["top-right", "top-left", "bottom-right", "bottom-left"],
                },
                "overlay_duration": {"value": 3000, "min": 1000, "max": 10000},
                "show_coordinates": {"enabled": True, "label": "Show Element Coordinates"},
                "highlight_color": {"value": "#FF0000", "label": "Highlight Color"},
                "highlight_width": {"value": 3, "min": 1, "max": 10, "label": "Highlight Width"},
                "screenshot_max_size": {"value": 200, "min": 100, "max": 400, "label": "Screenshot Max Size (px)"},
                "screenshot_position": {
                    "value": "bottom-right",
                    "options": ["top-right", "top-left", "bottom-right", "bottom-left"],
                    "label": "Screenshot Overlay Position",
                },
            },
            "ocr": {
                "cache_results": {"enabled": True, "label": "Cache OCR Results"},
                "cache_ttl": {"value": 300, "min": 60, "max": 3600, "label": "Cache TTL (seconds)"},
            },
            "performance": {
                "safety_delay": {
                    "value": 0.5,
                    "min": 0.0,
                    "max": 2.0,
                    "label": "Safety Delay (seconds)",
                },
                "rendering_optimization": {
                    "enabled": True,
                    "label": "Enable Rendering Optimization",
                },
                "update_throttle_ms": {
                    "value": 50,
                    "min": 10,
                    "max": 200,
                    "label": "Update Throttle (ms)",
                },
            },
        }

    def save(self) -> bool:
        """Save configuration to file"""
        with self._lock:
            try:
                # Ensure directory exists
                Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)

                with open(self.config_path, "w") as f:
                    json.dump(self.config, f, indent=2)

                return True
            except Exception as e:
                self.logger.error(f"Error saving config: {e}", exc_info=True)
                return False

    def reload(self) -> bool:
        """Reload configuration from file"""
        with self._lock:
            try:
                self.config = self._load_config()
                self._notify_listeners()
                return True
            except Exception as e:
                self.logger.error(f"Error reloading config: {e}", exc_info=True)
                return False

    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults"""
        with self._lock:
            self.config = self._get_default_config()
            if self.auto_save:
                return self.save()
            return True

    def get_config(self) -> Dict[str, Any]:
        """Get entire configuration"""
        with self._lock:
            return self.config.copy()

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get configuration section"""
        with self._lock:
            return self.config.get(section, {}).copy()

    def set_section(self, section: str, values: Dict[str, Any]) -> bool:
        """Set entire configuration section"""
        with self._lock:
            if section in self.config:
                self.config[section] = values
                self._notify_listeners()
                if self.auto_save:
                    return self.save()
                return True
            return False

    # Module management

    def is_module_enabled(self, module_name: str) -> bool:
        """Check if a module is enabled"""
        with self._lock:
            return self.config.get("modules", {}).get(module_name, {}).get("enabled", False)

    def enable_module(self, module_name: str) -> bool:
        """Enable a module"""
        return self.set_module_state(module_name, True)

    def disable_module(self, module_name: str) -> bool:
        """Disable a module"""
        return self.set_module_state(module_name, False)

    def set_module_state(self, module_name: str, enabled: bool) -> bool:
        """Set module enabled state"""
        with self._lock:
            if "modules" not in self.config:
                self.config["modules"] = {}

            if module_name not in self.config["modules"]:
                self.config["modules"][module_name] = {}

            self.config["modules"][module_name]["enabled"] = enabled
            self._notify_listeners()

            if self.auto_save:
                return self.save()
            return True

    def get_enabled_modules(self) -> List[str]:
        """Get list of enabled modules"""
        with self._lock:
            modules = []
            for module_name, module_config in self.config.get("modules", {}).items():
                if module_config.get("enabled", False):
                    modules.append(module_name)
            return modules

    # Feature management

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        with self._lock:
            return self.config.get("features", {}).get(feature_name, {}).get("enabled", False)

    def enable_feature(self, feature_name: str) -> bool:
        """Enable a feature"""
        return self.set_feature_state(feature_name, True)

    def disable_feature(self, feature_name: str) -> bool:
        """Disable a feature"""
        return self.set_feature_state(feature_name, False)

    def set_feature_state(self, feature_name: str, enabled: bool) -> bool:
        """Set feature enabled state"""
        with self._lock:
            if "features" not in self.config:
                self.config["features"] = {}

            if feature_name not in self.config["features"]:
                self.config["features"][feature_name] = {}

            self.config["features"][feature_name]["enabled"] = enabled
            self._notify_listeners()

            if self.auto_save:
                return self.save()
            return True

    # Setting management

    def get_setting(self, section: str, setting_name: str, default: Any = None) -> Any:
        """
        Get setting value from a section

        Args:
            section: Configuration section (e.g., 'ui', 'performance')
            setting_name: Setting name
            default: Default value if not found

        Returns:
            Setting value (from 'value' or 'enabled' field) or default
        """
        with self._lock:
            setting = self.config.get(section, {}).get(setting_name, {})
            if isinstance(setting, dict):
                return setting.get("value", setting.get("enabled", default))
            return default

    def set_setting(self, section: str, setting_name: str, value: Any) -> bool:
        """
        Set setting value in a section

        Args:
            section: Configuration section
            setting_name: Setting name
            value: New value

        Returns:
            True if successful
        """
        with self._lock:
            if section not in self.config:
                self.config[section] = {}

            if setting_name not in self.config[section]:
                self.config[section][setting_name] = {}

            # Determine if this is a value or enabled field
            if isinstance(value, bool) and "enabled" in self.config[section][setting_name]:
                self.config[section][setting_name]["enabled"] = value
            else:
                if not isinstance(self.config[section][setting_name], dict):
                    self.config[section][setting_name] = {}
                self.config[section][setting_name]["value"] = value

            self._notify_listeners()

            if self.auto_save:
                return self.save()
            return True

    def get_ui_setting(self, setting_name: str, default: Any = None) -> Any:
        """Get UI setting value"""
        return self.get_setting("ui", setting_name, default)

    def set_ui_setting(self, setting_name: str, value: Any) -> bool:
        """Set UI setting value"""
        return self.set_setting("ui", setting_name, value)

    def get_performance_setting(self, setting_name: str, default: Any = None) -> Any:
        """Get performance setting value"""
        return self.get_setting("performance", setting_name, default)

    def set_performance_setting(self, setting_name: str, value: Any) -> bool:
        """Set performance setting value"""
        return self.set_setting("performance", setting_name, value)

    # Listener management

    def add_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Add configuration change listener

        Args:
            callback: Function to call when configuration changes
        """
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Remove configuration change listener"""
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def _notify_listeners(self):
        """Notify all listeners of configuration change"""
        # Make a copy to avoid lock issues
        listeners = self._listeners.copy()
        config_copy = self.config.copy()

        for listener in listeners:
            try:
                listener(config_copy)
            except Exception as e:
                self.logger.error(f"Error notifying config listener: {e}", exc_info=True)

    # Bulk operations

    def update_multiple(self, updates: Dict[str, Dict[str, Any]]) -> bool:
        """
        Update multiple settings at once

        Args:
            updates: Dictionary of section -> {setting: value} mappings

        Returns:
            True if successful
        """
        with self._lock:
            for section, settings in updates.items():
                if section not in self.config:
                    self.config[section] = {}

                for setting_name, value in settings.items():
                    if setting_name not in self.config[section]:
                        self.config[section][setting_name] = {}

                    if isinstance(value, bool) and "enabled" in self.config[section][setting_name]:
                        self.config[section][setting_name]["enabled"] = value
                    else:
                        if not isinstance(self.config[section][setting_name], dict):
                            self.config[section][setting_name] = {}
                        self.config[section][setting_name]["value"] = value

            self._notify_listeners()

            if self.auto_save:
                return self.save()
            return True


# Global instance for easy access
_global_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: str = "config.json") -> ConfigManager:
    """Get or create global configuration manager instance"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager(config_path)
    return _global_config_manager
