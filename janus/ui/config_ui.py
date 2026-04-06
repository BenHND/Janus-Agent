"""
Configuration UI - Interface for managing Janus settings
Allows enabling/disabling modules and configuring agent options

This module acts as a facade for the configuration UI.
The actual implementation is split across multiple modules:
- config_ui_main.py: Main window and core functionality
- config_ui_modules.py: Module management sections
- config_ui_settings.py: Settings forms
- config_ui_advanced.py: Advanced options
"""

from typing import Any, Callable, Dict, Optional

from .config_ui_main import ConfigUIMain


class ConfigUI:
    """
    Configuration interface for Janus settings (Facade)
    Provides UI to enable/disable modules and adjust options

    This class delegates to ConfigUIMain.
    """

    def __init__(
        self,
        config_path: str = "config.json",
        ini_config_path: str = "config.ini",
        on_save: Optional[Callable] = None,
    ):
        """
        Initialize configuration UI

        Args:
            config_path: Path to JSON configuration file
            ini_config_path: Path to INI configuration file
            on_save: Callback function when configuration is saved
        """
        # Delegate to main implementation
        self._main = ConfigUIMain(config_path, ini_config_path, on_save)

    # Delegate all public methods to the main implementation

    @property
    def logger(self):
        """Get logger"""
        return self._main.logger

    @property
    def config_path(self):
        """Get config path"""
        return self._main.config_path

    @property
    def ini_config_path(self):
        """Get INI config path"""
        return self._main.ini_config_path

    @property
    def on_save(self):
        """Get on_save callback"""
        return self._main.on_save

    @property
    def config(self):
        """Get configuration"""
        return self._main.config

    @config.setter
    def config(self, value):
        """Set configuration"""
        self._main.config = value

    @property
    def ini_config(self):
        """Get INI configuration"""
        return self._main.ini_config

    @ini_config.setter
    def ini_config(self, value):
        """Set INI configuration"""
        self._main.ini_config = value

    @property
    def window(self):
        """Get window"""
        return self._main.window

    @window.setter
    def window(self, value):
        """Set window"""
        self._main.window = value

    @property
    def widgets(self):
        """Get widgets"""
        return self._main.widgets

    @property
    def profiles_dir(self):
        """Get profiles directory"""
        return self._main.profiles_dir

    def show(self):
        """Show configuration UI"""
        return self._main.show()

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self._main.get_config()

    def is_module_enabled(self, module_name: str) -> bool:
        """Check if a module is enabled"""
        return self._main.is_module_enabled(module_name)

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        return self._main.is_feature_enabled(feature_name)

    def get_ui_setting(self, setting_name: str) -> Any:
        """Get UI setting value"""
        return self._main.get_ui_setting(setting_name)
    
    def _save_config(self) -> bool:
        """Save configuration to file (delegated to main implementation)"""
        return self._main._save_config()
