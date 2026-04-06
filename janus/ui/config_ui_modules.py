"""
Configuration UI - Module Management Sections
Handles creation of module, feature, and context provider sections
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Dict

from janus.logging import get_logger

logger = get_logger("config_ui_modules")


class ConfigUIModules:
    """Module management sections for configuration UI"""

    def __init__(self, config: Dict[str, Any], widgets: Dict[str, tk.Variable]):
        """
        Initialize module management

        Args:
            config: Configuration dictionary
            widgets: Widget variables dictionary
        """
        self.config = config
        self.widgets = widgets

    def create_module_section(self, parent: ttk.Frame):
        """Create modules configuration section"""
        section_frame = ttk.LabelFrame(parent, text="Modules", padding=15)
        section_frame.pack(fill=tk.X, pady=(0, 10))

        for module_name, module_config in self.config.get("modules", {}).items():
            var = tk.BooleanVar(value=module_config.get("enabled", True))
            self.widgets[f"modules.{module_name}"] = var

            check = ttk.Checkbutton(section_frame, text=module_name.capitalize(), variable=var)
            check.pack(anchor=tk.W, pady=2)

    def create_features_section(self, parent: ttk.Frame):
        """Create features configuration section"""
        section_frame = ttk.LabelFrame(parent, text="Features", padding=15)
        section_frame.pack(fill=tk.X, pady=(0, 10))

        for feature_name, feature_config in self.config.get("features", {}).items():
            var = tk.BooleanVar(value=feature_config.get("enabled", True))
            self.widgets[f"features.{feature_name}"] = var

            label = feature_config.get("label", feature_name.replace("_", " ").title())
            check = ttk.Checkbutton(section_frame, text=label, variable=var)
            check.pack(anchor=tk.W, pady=2)

    def create_context_providers_section(self, parent: ttk.Frame):
        """Create context providers configuration section"""
        section_frame = ttk.LabelFrame(parent, text="Context Providers", padding=15)
        section_frame.pack(fill=tk.X, pady=(0, 10))

        providers_config = self.config.get("context_providers", {})

        for provider_name, provider_config in providers_config.items():
            if "enabled" in provider_config:
                var = tk.BooleanVar(value=provider_config.get("enabled", False))
                self.widgets[f"context_providers.{provider_name}"] = var

                label = provider_config.get("label", provider_name.replace("_", " ").title())
                check = ttk.Checkbutton(section_frame, text=label, variable=var)
                check.pack(anchor=tk.W, pady=2)

        # Help text
        help_text = ttk.Label(
            section_frame,
            text="Note: Calendar and Email providers require platform-specific integration.\nThey are disabled by default.",
            font=("Arial", 9),
            foreground="gray",
        )
        help_text.pack(anchor=tk.W, pady=(10, 0))
