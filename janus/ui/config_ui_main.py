"""
Configuration UI - Main Window
Main configuration interface coordinating all sections
"""

import configparser
import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Callable, Dict, Optional

from janus.logging import get_logger

from .config_ui_advanced import ConfigUIAdvanced
from .config_ui_modules import ConfigUIModules
from .config_ui_settings import ConfigUISettings


class ConfigUIMain:
    """
    Main configuration interface for Janus settings
    Provides UI to enable/disable modules and adjust options
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
        self.logger = get_logger("config_ui_main")
        self.config_path = config_path
        self.ini_config_path = ini_config_path
        self.on_save = on_save
        self.config: Dict[str, Any] = self._load_config()
        self.ini_config = self._load_ini_config()
        self.window: Optional[tk.Tk] = None
        self.widgets: Dict[str, tk.Variable] = {}
        self.profiles_dir = "config_profiles"
        os.makedirs(self.profiles_dir, exist_ok=True)

        # Initialize section handlers
        self.modules_handler = ConfigUIModules(self.config, self.widgets)
        self.settings_handler = ConfigUISettings(self.config, self.ini_config, self.widgets)
        self.advanced_handler = ConfigUIAdvanced(self.config, self.widgets)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Error loading config: {e}")

        # Default configuration
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
                "cognitive_planner": {
                    "enabled": False,
                    "label": "Cognitive Planner (LLM Reasoner)",
                },
                "context_engine": {"enabled": True, "label": "Context Engine"},
            },
            "cognitive_planner": {
                "backend": {
                    "value": "mock",
                    "options": ["mock", "llama-cpp", "ollama"],
                    "label": "LLM Backend",
                },
                "model_path": {"value": "", "label": "Model Path (for llama-cpp)"},
                "model_name": {
                    "value": "mistral:7b-instruct-q4_K_M",
                    "options": ["mistral:7b-instruct-q4_K_M", "phi3:mini", "gemma:7b", "qwen:7b"],
                    "label": "Model (for ollama)",
                },
                "timeout_ms": {"value": 500, "min": 200, "max": 5000, "label": "Timeout (ms)"},
                "fallback_enabled": {"enabled": True, "label": "Enable Fallback to Classic Parser"},
            },
            "context_providers": {
                "calendar": {"enabled": False, "label": "Calendar Provider"},
                "email": {"enabled": False, "label": "Email Provider"},
            },
            "ui": {
                "show_overlay": {"enabled": True, "label": "Visual Feedback Overlay"},
                "confirmation_dialogs": {"enabled": True, "label": "Confirmation Dialogs"},
                "overlay_position": {
                    "value": "top-right",
                    "options": ["top-right", "top-left", "bottom-right", "bottom-left"],
                },
                "overlay_duration": {"value": 3000, "min": 1000, "max": 10000},
                "theme": {"value": "light", "options": ["light", "dark"], "label": "Theme"},
            },
            "shortcuts": {
                "show_dashboard": {"value": "Ctrl+Shift+D", "label": "Show Dashboard"},
                "show_logs": {"value": "Ctrl+Shift+L", "label": "Show Logs Viewer"},
                "show_stats": {"value": "Ctrl+Shift+S", "label": "Show Statistics"},
                "show_config": {"value": "Ctrl+Shift+C", "label": "Show Configuration"},
                "pause_listening": {"value": "Ctrl+Shift+P", "label": "Pause/Resume Listening"},
                "cancel_action": {"value": "Escape", "label": "Cancel Current Action"},
            },
            "ocr": {
                "backend": {
                    "value": "tesseract",
                    "options": ["tesseract", "easyocr"],
                    "label": "OCR Backend",
                },
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
            },
        }

    def _load_ini_config(self) -> configparser.ConfigParser:
        """Load INI configuration from file"""
        config = configparser.ConfigParser()
        if os.path.exists(self.ini_config_path):
            try:
                config.read(self.ini_config_path)
            except Exception as e:
                self.logger.warning(f"Error loading INI config: {e}")
        return config

    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)

            # Call callback if provided
            if self.on_save:
                self.on_save(self.config)

            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
            return False

    def _save_ini_config(self):
        """Save INI configuration to file"""
        try:
            with open(self.ini_config_path, "w") as f:
                self.ini_config.write(f)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save INI configuration: {e}")
            return False

    def _apply_changes(self):
        """Apply configuration changes"""
        import os
        
        # Update JSON config from widgets
        for key, var in self.widgets.items():
            if key.startswith("ini."):
                # Skip INI config widgets here, handle separately
                continue
            
            if key.startswith("microsoft365."):
                # Handle Microsoft 365 credentials specially
                # Store in config but also update environment variables
                continue
            
            if key.startswith("salesforce."):
                # Handle Salesforce credentials specially
                # Store in config but also update environment variables
                continue

            parts = key.split(".")
            if len(parts) == 2:
                section, option = parts
                if section in self.config and option in self.config[section]:
                    if isinstance(var, tk.BooleanVar):
                        self.config[section][option]["enabled"] = var.get()
                    elif isinstance(var, (tk.IntVar, tk.DoubleVar, tk.StringVar)):
                        self.config[section][option]["value"] = var.get()
        
        # Handle Microsoft 365 credentials
        if "microsoft365.client_id" in self.widgets:
            # Ensure microsoft365 section exists in config
            if "microsoft365" not in self.config:
                self.config["microsoft365"] = {}
            
            # Save credentials to config
            self.config["microsoft365"]["client_id"] = self.widgets["microsoft365.client_id"].get()
            self.config["microsoft365"]["client_secret"] = self.widgets["microsoft365.client_secret"].get()
            self.config["microsoft365"]["username"] = self.widgets["microsoft365.username"].get()
            
            # Also set environment variables for current session
            os.environ["O365_CLIENT_ID"] = self.widgets["microsoft365.client_id"].get()
            os.environ["O365_CLIENT_SECRET"] = self.widgets["microsoft365.client_secret"].get()
            if self.widgets["microsoft365.username"].get():
                os.environ["O365_USERNAME"] = self.widgets["microsoft365.username"].get()
        
        # Handle Salesforce credentials
        if "salesforce.username" in self.widgets:
            # Ensure salesforce section exists in config
            if "salesforce" not in self.config:
                self.config["salesforce"] = {}
            
            # Save credentials to config
            self.config["salesforce"]["username"] = self.widgets["salesforce.username"].get()
            self.config["salesforce"]["password"] = self.widgets["salesforce.password"].get()
            self.config["salesforce"]["security_token"] = self.widgets["salesforce.security_token"].get()
            self.config["salesforce"]["domain"] = self.widgets["salesforce.domain"].get()
            
            # Also set environment variables for current session
            os.environ["SALESFORCE_USERNAME"] = self.widgets["salesforce.username"].get()
            os.environ["SALESFORCE_PASSWORD"] = self.widgets["salesforce.password"].get()
            os.environ["SALESFORCE_SECURITY_TOKEN"] = self.widgets["salesforce.security_token"].get()
            os.environ["SALESFORCE_DOMAIN"] = self.widgets["salesforce.domain"].get()

        # Handle Messaging credentials (Slack & Teams)
        if "messaging.slack_bot_token" in self.widgets or "messaging.teams_client_id" in self.widgets:
            # Ensure messaging section exists in config
            if "messaging" not in self.config:
                self.config["messaging"] = {}
            
            # Save Slack credentials if present
            if "messaging.slack_bot_token" in self.widgets:
                self.config["messaging"]["slack_bot_token"] = self.widgets["messaging.slack_bot_token"].get()
                os.environ["SLACK_BOT_TOKEN"] = self.widgets["messaging.slack_bot_token"].get()
            
            # Save Teams credentials if present
            if "messaging.teams_client_id" in self.widgets:
                self.config["messaging"]["teams_client_id"] = self.widgets["messaging.teams_client_id"].get()
                self.config["messaging"]["teams_client_secret"] = self.widgets["messaging.teams_client_secret"].get()
                self.config["messaging"]["teams_tenant_id"] = self.widgets["messaging.teams_tenant_id"].get()
                
                os.environ["TEAMS_CLIENT_ID"] = self.widgets["messaging.teams_client_id"].get()
                os.environ["TEAMS_CLIENT_SECRET"] = self.widgets["messaging.teams_client_secret"].get()
                os.environ["TEAMS_TENANT_ID"] = self.widgets["messaging.teams_tenant_id"].get()

        # Update INI config from widgets
        for key, var in self.widgets.items():
            if not key.startswith("ini."):
                continue

            # Parse key: ini.section.option
            parts = key.split(".", 2)
            if len(parts) == 3:
                _, section, option = parts

                # Ensure section exists
                if not self.ini_config.has_section(section):
                    self.ini_config.add_section(section)

                # Set value
                value = var.get()
                self.ini_config.set(section, option, str(value))

        # Save both configurations
        json_saved = self._save_config()
        ini_saved = self._save_ini_config()

        if json_saved and ini_saved:
            messagebox.showinfo(
                "Success",
                "Configuration saved successfully!\n\nNote: Restart Janus for config.ini changes to take effect.",
            )
        elif json_saved:
            messagebox.showwarning(
                "Partial Success", "JSON config saved, but INI config failed to save."
            )
        elif ini_saved:
            messagebox.showwarning(
                "Partial Success", "INI config saved, but JSON config failed to save."
            )
        else:
            messagebox.showerror("Error", "Failed to save configuration.")

    def _open_context_viewer(self):
        """Open context viewer window"""
        try:
            import threading

            from janus.ui.context_viewer import show_context_viewer

            # Run in separate thread to avoid blocking
            viewer_thread = threading.Thread(target=show_context_viewer, daemon=True)
            viewer_thread.start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open context viewer: {e}")

    def _reset_to_defaults(self):
        """Reset all settings to defaults"""
        if messagebox.askyesno(
            "Confirm Reset",
            "Are you sure you want to reset all settings to defaults?\n\nThis will overwrite your current configuration.",
        ):
            # Reset JSON config
            self.config = self._load_config()  # This loads defaults if file doesn't exist

            # Reset INI config to defaults
            self.ini_config = configparser.ConfigParser()

            # Save both
            if self._save_config() and self._save_ini_config():
                messagebox.showinfo(
                    "Success",
                    "Settings reset to defaults!\n\nPlease close and reopen this window to see changes.",
                )
                self.window.destroy()
            else:
                messagebox.showerror("Error", "Failed to reset settings.")

    def _export_settings(self):
        """Export settings to a profile file"""
        filename = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=self.profiles_dir,
        )

        if filename:
            try:
                # Combine both configs for export
                export_data = {
                    "json_config": self.config,
                    "ini_config": {
                        section: dict(self.ini_config[section])
                        for section in self.ini_config.sections()
                    },
                }

                with open(filename, "w") as f:
                    json.dump(export_data, f, indent=2)

                messagebox.showinfo("Success", f"Settings exported to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export settings:\n{e}")

    def _import_settings(self):
        """Import settings from a profile file"""
        filename = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=self.profiles_dir,
        )

        if filename:
            try:
                with open(filename, "r") as f:
                    import_data = json.load(f)

                # Import JSON config
                if "json_config" in import_data:
                    self.config = import_data["json_config"]

                # Import INI config
                if "ini_config" in import_data:
                    self.ini_config = configparser.ConfigParser()
                    for section, options in import_data["ini_config"].items():
                        if not self.ini_config.has_section(section):
                            self.ini_config.add_section(section)
                        for key, value in options.items():
                            self.ini_config.set(section, key, str(value))

                # Save both
                if self._save_config() and self._save_ini_config():
                    messagebox.showinfo(
                        "Success",
                        "Settings imported successfully!\n\nPlease close and reopen this window to see changes.",
                    )
                    self.window.destroy()
                else:
                    messagebox.showerror("Error", "Failed to save imported settings.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import settings:\n{e}")

    def _save_profile(self):
        """Save current settings as a named profile"""
        profile_name = tk.simpledialog.askstring(
            "Save Profile", "Enter a name for this profile:", parent=self.window
        )

        if profile_name:
            # Sanitize filename
            safe_name = "".join(
                c for c in profile_name if c.isalnum() or c in (" ", "-", "_")
            ).strip()
            if not safe_name:
                messagebox.showerror("Error", "Invalid profile name.")
                return

            filename = os.path.join(self.profiles_dir, f"{safe_name}.json")

            try:
                # Combine both configs for export
                export_data = {
                    "profile_name": profile_name,
                    "json_config": self.config,
                    "ini_config": {
                        section: dict(self.ini_config[section])
                        for section in self.ini_config.sections()
                    },
                }

                with open(filename, "w") as f:
                    json.dump(export_data, f, indent=2)

                messagebox.showinfo("Success", f"Profile '{profile_name}' saved!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save profile:\n{e}")

    def _load_profile(self):
        """Load a saved profile"""
        # List available profiles
        profiles = []
        if os.path.exists(self.profiles_dir):
            profiles = [f for f in os.listdir(self.profiles_dir) if f.endswith(".json")]

        if not profiles:
            messagebox.showinfo(
                "No Profiles", "No saved profiles found.\n\nUse 'Save Profile' to create one."
            )
            return

        # Show profile selection dialog
        profile_window = tk.Toplevel(self.window)
        profile_window.title("Load Profile")
        profile_window.geometry("400x300")

        ttk.Label(profile_window, text="Select a profile to load:", font=("Arial", 11)).pack(
            pady=10
        )

        listbox = tk.Listbox(profile_window, height=10)
        listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        for profile in profiles:
            listbox.insert(tk.END, profile[:-5])  # Remove .json extension

        def load_selected():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a profile.")
                return

            profile_name = listbox.get(selection[0])
            filename = os.path.join(self.profiles_dir, f"{profile_name}.json")

            try:
                with open(filename, "r") as f:
                    import_data = json.load(f)

                # Import JSON config
                if "json_config" in import_data:
                    self.config = import_data["json_config"]

                # Import INI config
                if "ini_config" in import_data:
                    self.ini_config = configparser.ConfigParser()
                    for section, options in import_data["ini_config"].items():
                        if not self.ini_config.has_section(section):
                            self.ini_config.add_section(section)
                        for key, value in options.items():
                            self.ini_config.set(section, key, str(value))

                # Save both
                if self._save_config() and self._save_ini_config():
                    messagebox.showinfo(
                        "Success",
                        f"Profile '{profile_name}' loaded!\n\nPlease close and reopen this window to see changes.",
                    )
                    profile_window.destroy()
                    self.window.destroy()
                else:
                    messagebox.showerror("Error", "Failed to save loaded profile.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load profile:\n{e}")

        button_frame = ttk.Frame(profile_window)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Load", command=load_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=profile_window.destroy).pack(
            side=tk.LEFT, padx=5
        )

    def show(self):
        """Show configuration UI"""
        self.window = tk.Tk()
        self.window.title("Janus - Configuration")

        # Configure window size and position
        window_width = 500
        window_height = 700
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Main container with scrollbar
        main_container = ttk.Frame(self.window)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Canvas for scrolling
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas and scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Content frame with padding
        content_frame = ttk.Frame(scrollable_frame, padding=20)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(
            content_frame, text="Janus Configuration", font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 20))

        # Create sections using handlers
        self.settings_handler.create_core_settings_section(content_frame)
        self.settings_handler.create_microsoft365_section(content_frame)  # TICKET-APP-001
        self.settings_handler.create_salesforce_section(content_frame)  # TICKET-BIZ-001
        self.settings_handler.create_messaging_section(content_frame)  # TICKET-BIZ-002
        self.settings_handler.create_wake_word_section(content_frame)  # TICKET-P3-02
        self.modules_handler.create_module_section(content_frame)
        self.modules_handler.create_features_section(content_frame)
        self.advanced_handler.create_cognitive_planner_section(content_frame)
        self.modules_handler.create_context_providers_section(content_frame)
        self.settings_handler.create_ui_section(content_frame)
        self.settings_handler.create_shortcuts_section(content_frame)
        self.advanced_handler.create_performance_section(content_frame)

        # Buttons frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=20, pady=20)

        # Left side buttons
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side=tk.LEFT)

        # Cancel button
        cancel_button = ttk.Button(left_buttons, text="Cancel", command=self.window.destroy)
        cancel_button.pack(side=tk.LEFT)

        # Context Viewer button
        context_viewer_button = ttk.Button(
            left_buttons, text="View Context", command=self._open_context_viewer
        )
        context_viewer_button.pack(side=tk.LEFT, padx=(10, 0))

        # Middle buttons for profiles
        middle_buttons = ttk.Frame(button_frame)
        middle_buttons.pack(side=tk.LEFT, padx=20)

        # Save Profile button
        save_profile_button = ttk.Button(
            middle_buttons, text="Save Profile", command=self._save_profile
        )
        save_profile_button.pack(side=tk.LEFT)

        # Load Profile button
        load_profile_button = ttk.Button(
            middle_buttons, text="Load Profile", command=self._load_profile
        )
        load_profile_button.pack(side=tk.LEFT, padx=(5, 0))

        # Right side buttons
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side=tk.RIGHT)

        # Reset to defaults button
        reset_button = ttk.Button(
            right_buttons, text="Reset to Defaults", command=self._reset_to_defaults
        )
        reset_button.pack(side=tk.LEFT, padx=(0, 10))

        # Import button
        import_button = ttk.Button(right_buttons, text="Import", command=self._import_settings)
        import_button.pack(side=tk.LEFT, padx=(0, 5))

        # Export button
        export_button = ttk.Button(right_buttons, text="Export", command=self._export_settings)
        export_button.pack(side=tk.LEFT, padx=(0, 10))

        # Apply button
        apply_button = ttk.Button(right_buttons, text="Apply & Save", command=self._apply_changes)
        apply_button.pack(side=tk.LEFT)

        # Run main loop
        self.window.mainloop()

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self.config

    def is_module_enabled(self, module_name: str) -> bool:
        """Check if a module is enabled"""
        return self.config.get("modules", {}).get(module_name, {}).get("enabled", True)

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        return self.config.get("features", {}).get(feature_name, {}).get("enabled", True)

    def get_ui_setting(self, setting_name: str) -> Any:
        """Get UI setting value"""
        setting = self.config.get("ui", {}).get(setting_name, {})
        return setting.get("value") if "value" in setting else setting.get("enabled")
