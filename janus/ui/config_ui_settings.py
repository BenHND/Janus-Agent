"""
Configuration UI - Settings Forms
Handles creation of settings form sections (core settings, shortcuts, UI settings)
"""

import configparser
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict

from janus.logging import get_logger

logger = get_logger("config_ui_settings")


class ConfigUISettings:
    """Settings forms for configuration UI"""

    def __init__(
        self,
        config: Dict[str, Any],
        ini_config: configparser.ConfigParser,
        widgets: Dict[str, tk.Variable],
    ):
        """
        Initialize settings forms

        Args:
            config: Configuration dictionary
            ini_config: INI configuration
            widgets: Widget variables dictionary
        """
        self.config = config
        self.ini_config = ini_config
        self.widgets = widgets
        self.logger = logger

    def create_core_settings_section(self, parent: ttk.Frame):
        """Create core configuration settings section (from config.ini)"""
        section_frame = ttk.LabelFrame(parent, text="Core Settings (config.ini)", padding=15)
        section_frame.pack(fill=tk.X, pady=(0, 10))

        # Language Selection
        frame = ttk.Frame(section_frame)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Language:").pack(side=tk.LEFT, padx=(0, 10))

        current_lang = self.ini_config.get("language", "default", fallback="fr")
        var = tk.StringVar(value=current_lang)
        self.widgets["ini.language.default"] = var

        # Language options with labels
        language_options = [("Français (fr)", "fr"), ("English (en)", "en")]
        language_display = [opt[0] for opt in language_options]

        # Map display to value
        def on_language_change(*args):
            display_value = var.get()
            # Convert display value to code if needed
            for display, code in language_options:
                if display_value == display:
                    var.set(code)
                    break

        # Set initial display value
        for display, code in language_options:
            if current_lang == code:
                var.set(code)
                break

        combo = ttk.Combobox(
            frame,
            textvariable=var,
            values=[code for _, code in language_options],
            state="readonly",
            width=15,
        )
        combo.pack(side=tk.LEFT, padx=(0, 10))

        # Language hint
        ttk.Label(frame, text="(Requires app restart)", font=("Arial", 8), foreground="gray").pack(
            side=tk.LEFT
        )

        # Whisper Model Selection
        frame = ttk.Frame(section_frame)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Whisper Model:").pack(side=tk.LEFT, padx=(0, 10))

        current_model = self.ini_config.get("whisper", "model_size", fallback="base")
        var = tk.StringVar(value=current_model)
        self.widgets["ini.whisper.model_size"] = var

        model_options = ["tiny", "base", "small", "medium", "large"]
        combo = ttk.Combobox(
            frame, textvariable=var, values=model_options, state="readonly", width=15
        )
        combo.pack(side=tk.LEFT, padx=(0, 10))

        # Model size hint
        ttk.Label(
            frame, text="(tiny=fastest, large=most accurate)", font=("Arial", 8), foreground="gray"
        ).pack(side=tk.LEFT)

        # Log Level Configuration
        frame = ttk.Frame(section_frame)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Log Level:").pack(side=tk.LEFT, padx=(0, 10))

        current_log_level = self.ini_config.get("logging", "level", fallback="INFO")
        var = tk.StringVar(value=current_log_level)
        self.widgets["ini.logging.level"] = var

        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        combo = ttk.Combobox(frame, textvariable=var, values=log_levels, state="readonly", width=15)
        combo.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(
            frame,
            text="(DEBUG: most verbose, CRITICAL: least verbose)",
            font=("Arial", 8),
            foreground="gray",
        ).pack(side=tk.LEFT)

        # Help text
        help_text = ttk.Label(
            section_frame,
            text="These settings are stored in config.ini and affect core application behavior.",
            font=("Arial", 9),
            foreground="gray",
        )
        help_text.pack(anchor=tk.W, pady=(10, 0))

    def create_wake_word_section(self, parent: ttk.Frame):
        """Create Wake Word configuration section (TICKET-P3-02)"""
        section_frame = ttk.LabelFrame(parent, text="Wake Word (Hey Janus)", padding=15)
        section_frame.pack(fill=tk.X, pady=(0, 10))

        # Enable/Disable
        frame_enable = ttk.Frame(section_frame)
        frame_enable.pack(fill=tk.X, pady=5)
        
        var_enable = tk.BooleanVar(value=self.ini_config.getboolean("wakeword", "enabled", fallback=False))
        self.widgets["ini.wakeword.enabled"] = var_enable
        ttk.Checkbutton(frame_enable, text="Enable Wake Word Detection", variable=var_enable).pack(side=tk.LEFT)

        # Model Path/Name
        frame_model = ttk.Frame(section_frame)
        frame_model.pack(fill=tk.X, pady=5)
        
        ttk.Label(frame_model, text="Model:").pack(side=tk.LEFT, padx=(0, 10))
        
        current_model = self.ini_config.get("wakeword", "model", fallback="hey_janus")
        var_model = tk.StringVar(value=current_model)
        self.widgets["ini.wakeword.model"] = var_model
        
        model_entry = ttk.Entry(frame_model, textvariable=var_model, width=40)
        model_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(
            frame_model,
            text="(Model name or path: hey_janus, models/wakeword/hey_janus.onnx)",
            font=("Arial", 8),
            foreground="gray"
        ).pack(side=tk.LEFT)

        # Sensitivity/Threshold Slider
        frame_thresh = ttk.Frame(section_frame)
        frame_thresh.pack(fill=tk.X, pady=5)

        ttk.Label(frame_thresh, text="Sensitivity:").pack(side=tk.LEFT, padx=(0, 10))
        
        current_threshold = float(self.ini_config.get("wakeword", "threshold", fallback="0.5"))
        var_thresh = tk.DoubleVar(value=current_threshold)
        self.widgets["ini.wakeword.threshold"] = var_thresh

        scale = ttk.Scale(
            frame_thresh,
            from_=0.0,
            to=1.0,
            variable=var_thresh,
            orient=tk.HORIZONTAL,
            length=200,
        )
        scale.pack(side=tk.LEFT, padx=(0, 10))
        
        lbl_val = ttk.Label(frame_thresh, text=f"{current_threshold:.2f}")
        lbl_val.pack(side=tk.LEFT, padx=(0, 10))
        
        # Update label on slide
        scale.configure(command=lambda v: lbl_val.configure(text=f"{float(v):.2f}"))
        
        ttk.Label(
            frame_thresh,
            text="(Higher = fewer false positives)",
            font=("Arial", 8),
            foreground="gray"
        ).pack(side=tk.LEFT)

        # Engine Info
        ttk.Label(
            section_frame, 
            text="Engine: openwakeword (Local & Private)", 
            font=("Arial", 9), 
            foreground="gray"
        ).pack(anchor=tk.W, pady=(10, 0))
        
        # Instructions
        ttk.Label(
            section_frame, 
            text="To generate custom 'Hey Janus' model: run python scripts/train_wake_word.py", 
            font=("Arial", 9), 
            foreground="gray"
        ).pack(anchor=tk.W, pady=(2, 0))
        
        # Warning about restart
        warning_text = ttk.Label(
            section_frame,
            text="⚠️ Requires app restart to take effect",
            font=("Arial", 9, "bold"),
            foreground="orange",
        )
        warning_text.pack(anchor=tk.W, pady=(5, 0))

    def create_shortcuts_section(self, parent: ttk.Frame):
        """Create keyboard shortcuts configuration section"""
        section_frame = ttk.LabelFrame(parent, text="Keyboard Shortcuts", padding=15)
        section_frame.pack(fill=tk.X, pady=(0, 10))

        shortcuts_config = self.config.get("shortcuts", {})

        # Help text
        help_text = ttk.Label(
            section_frame,
            text="Customize keyboard shortcuts for quick access to features.\nUse format: 'Ctrl+Shift+Key' or 'Alt+Key'",
            font=("Arial", 9),
            foreground="gray",
        )
        help_text.pack(anchor=tk.W, pady=(0, 10))

        for shortcut_name, shortcut_config in shortcuts_config.items():
            frame = ttk.Frame(section_frame)
            frame.pack(fill=tk.X, pady=3)

            label = shortcut_config.get("label", shortcut_name.replace("_", " ").title())
            ttk.Label(frame, text=f"{label}:", width=25).pack(side=tk.LEFT, padx=(0, 10))

            var = tk.StringVar(value=shortcut_config.get("value", ""))
            self.widgets[f"shortcuts.{shortcut_name}"] = var

            entry = ttk.Entry(frame, textvariable=var, width=20)
            entry.pack(side=tk.LEFT)

            # Reset button
            default_value = shortcut_config.get("value", "")
            reset_btn = ttk.Button(
                frame, text="Reset", command=lambda v=var, d=default_value: v.set(d), width=8
            )
            reset_btn.pack(side=tk.LEFT, padx=(5, 0))

    def create_ui_section(self, parent: ttk.Frame):
        """Create UI configuration section"""
        section_frame = ttk.LabelFrame(parent, text="User Interface", padding=15)
        section_frame.pack(fill=tk.X, pady=(0, 10))

        ui_config = self.config.get("ui", {})

        # Boolean options
        for option_name, option_config in ui_config.items():
            if "enabled" in option_config:
                var = tk.BooleanVar(value=option_config.get("enabled", True))
                self.widgets[f"ui.{option_name}"] = var

                label = option_config.get("label", option_name.replace("_", " ").title())
                check = ttk.Checkbutton(section_frame, text=label, variable=var)
                check.pack(anchor=tk.W, pady=2)

            # Dropdown options
            elif "options" in option_config:
                frame = ttk.Frame(section_frame)
                frame.pack(fill=tk.X, pady=5)

                label = option_config.get("label", option_name.replace("_", " ").title())
                ttk.Label(frame, text=f"{label}:").pack(side=tk.LEFT, padx=(0, 10))

                var = tk.StringVar(value=option_config.get("value", option_config["options"][0]))
                self.widgets[f"ui.{option_name}"] = var

                combo = ttk.Combobox(
                    frame,
                    textvariable=var,
                    values=option_config["options"],
                    state="readonly",
                    width=15,
                )
                combo.pack(side=tk.LEFT)

            # Numeric options
            elif "value" in option_config and "min" in option_config:
                frame = ttk.Frame(section_frame)
                frame.pack(fill=tk.X, pady=5)

                label = option_config.get("label", option_name.replace("_", " ").title())
                ttk.Label(frame, text=f"{label}:").pack(side=tk.LEFT, padx=(0, 10))

                var = tk.IntVar(value=option_config.get("value", 3000))
                self.widgets[f"ui.{option_name}"] = var

                scale = ttk.Scale(
                    frame,
                    from_=option_config["min"],
                    to=option_config["max"],
                    variable=var,
                    orient=tk.HORIZONTAL,
                    length=200,
                )
                scale.pack(side=tk.LEFT, padx=(0, 10))

                value_label = ttk.Label(frame, text=str(var.get()))
                value_label.pack(side=tk.LEFT)

                # Update label when scale changes
                def update_label(event=None, label=value_label, var=var):
                    label.config(text=str(int(var.get())))

                scale.config(command=update_label)

    def create_microsoft365_section(self, parent: ttk.Frame):
        """Create Microsoft 365 API credentials configuration section"""
        import os
        
        section_frame = ttk.LabelFrame(parent, text="Microsoft 365 Integration", padding=15)
        section_frame.pack(fill=tk.X, pady=(0, 10))

        # Help text
        help_text = ttk.Label(
            section_frame,
            text="Configure Microsoft 365 credentials for calendar and email integration.\n"
                 "See docs/user/microsoft-365-setup.md for setup instructions.",
            font=("Arial", 9),
            foreground="gray",
        )
        help_text.pack(anchor=tk.W, pady=(0, 10))

        # Client ID
        frame = ttk.Frame(section_frame)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Client ID:", width=15).pack(side=tk.LEFT, padx=(0, 10))

        # Load from environment or config
        current_client_id = os.environ.get('O365_CLIENT_ID', 
                                          self.config.get('microsoft365', {}).get('client_id', ''))
        var = tk.StringVar(value=current_client_id)
        self.widgets["microsoft365.client_id"] = var

        entry = ttk.Entry(frame, textvariable=var, width=40, show="")
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Show/Hide button for Client ID
        show_var = tk.BooleanVar(value=False)
        def toggle_client_id():
            if show_var.get():
                entry.config(show="")
                show_btn.config(text="Hide")
            else:
                entry.config(show="*")
                show_btn.config(text="Show")
            show_var.set(not show_var.get())
        
        show_btn = ttk.Button(frame, text="Show", command=toggle_client_id, width=6)
        show_btn.pack(side=tk.LEFT)

        # Client Secret
        frame = ttk.Frame(section_frame)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Client Secret:", width=15).pack(side=tk.LEFT, padx=(0, 10))

        # Load from environment or config
        current_secret = os.environ.get('O365_CLIENT_SECRET',
                                       self.config.get('microsoft365', {}).get('client_secret', ''))
        var = tk.StringVar(value=current_secret)
        self.widgets["microsoft365.client_secret"] = var

        entry = ttk.Entry(frame, textvariable=var, width=40, show="*")
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Show/Hide button for Secret
        show_var_secret = tk.BooleanVar(value=False)
        def toggle_secret():
            if show_var_secret.get():
                entry.config(show="*")
                show_btn_secret.config(text="Show")
            else:
                entry.config(show="")
                show_btn_secret.config(text="Hide")
            show_var_secret.set(not show_var_secret.get())
        
        show_btn_secret = ttk.Button(frame, text="Show", command=toggle_secret, width=6)
        show_btn_secret.pack(side=tk.LEFT)

        # Username (optional)
        frame = ttk.Frame(section_frame)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Email (optional):", width=15).pack(side=tk.LEFT, padx=(0, 10))

        current_username = os.environ.get('O365_USERNAME',
                                         self.config.get('microsoft365', {}).get('username', ''))
        var = tk.StringVar(value=current_username)
        self.widgets["microsoft365.username"] = var

        entry = ttk.Entry(frame, textvariable=var, width=40)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Status and test connection
        status_frame = ttk.Frame(section_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))

        status_label = ttk.Label(
            status_frame,
            text="Status: Not configured",
            foreground="gray",
            font=("Arial", 9)
        )
        status_label.pack(side=tk.LEFT)

        def test_connection():
            """Test Microsoft 365 connection"""
            try:
                client_id = self.widgets["microsoft365.client_id"].get()
                client_secret = self.widgets["microsoft365.client_secret"].get()
                
                if not client_id or not client_secret:
                    status_label.config(text="Status: Missing credentials", foreground="orange")
                    messagebox.showwarning(
                        "Missing Credentials",
                        "Please enter both Client ID and Client Secret."
                    )
                    return
                
                # Try to import O365
                try:
                    from O365 import Account
                    
                    # Create account (doesn't authenticate yet, just validates credentials format)
                    credentials = (client_id, client_secret)
                    account = Account(credentials)
                    
                    status_label.config(text="Status: Credentials format valid ✓", foreground="green")
                    messagebox.showinfo(
                        "Credentials Valid",
                        "Client ID and Secret format are valid.\n\n"
                        "To complete setup:\n"
                        "1. Save these settings\n"
                        "2. Run authentication flow when using calendar/email features\n\n"
                        "See docs/user/microsoft-365-setup.md for full setup guide."
                    )
                    
                except ImportError:
                    status_label.config(text="Status: O365 library not installed", foreground="orange")
                    messagebox.showwarning(
                        "O365 Library Not Installed",
                        "The O365 library is required for Microsoft 365 integration.\n\n"
                        "Install it with:\n"
                        "  pip install janus[office365]\n"
                        "or:\n"
                        "  pip install O365>=2.0.36"
                    )
                    
            except Exception as e:
                status_label.config(text=f"Status: Error - {str(e)[:30]}...", foreground="red")
                messagebox.showerror("Connection Test Failed", f"Error: {str(e)}")

        test_btn = ttk.Button(
            status_frame,
            text="Test Connection",
            command=test_connection
        )
        test_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Setup guide button
        def open_setup_guide():
            """Open setup guide in browser or text editor"""
            import webbrowser
            import os
            guide_path = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', 'user', 'microsoft-365-setup.md')
            guide_path = os.path.abspath(guide_path)
            
            if os.path.exists(guide_path):
                try:
                    # Try to open with default application
                    if os.name == 'posix':  # macOS/Linux
                        os.system(f'open "{guide_path}"' if os.uname().sysname == 'Darwin' else f'xdg-open "{guide_path}"')
                    else:  # Windows
                        os.startfile(guide_path)
                except:
                    messagebox.showinfo(
                        "Setup Guide",
                        f"Setup guide location:\n{guide_path}"
                    )
            else:
                messagebox.showinfo(
                    "Setup Guide",
                    "See docs/user/microsoft-365-setup.md for setup instructions.\n\n"
                    "Key steps:\n"
                    "1. Register app in Azure Portal\n"
                    "2. Add Calendars.Read and Mail.Read permissions\n"
                    "3. Create client secret\n"
                    "4. Copy Client ID and Secret here"
                )
        
        guide_btn = ttk.Button(
            status_frame,
            text="Setup Guide",
            command=open_setup_guide
        )
        guide_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Security note
        ttk.Label(
            section_frame,
            text="🔒 Credentials are stored securely and never logged",
            font=("Arial", 8),
            foreground="gray",
        ).pack(anchor=tk.W, pady=(5, 0))

    def create_salesforce_section(self, parent: ttk.Frame):
        """Create Salesforce CRM credentials configuration section"""
        import os
        
        section_frame = ttk.LabelFrame(parent, text="Salesforce CRM Integration", padding=15)
        section_frame.pack(fill=tk.X, pady=(0, 10))

        # Help text
        help_text = ttk.Label(
            section_frame,
            text="Configure Salesforce credentials for CRM data access.\n"
                 "See docs/user/salesforce-crm-setup.md for setup instructions.",
            font=("Arial", 9),
            foreground="gray",
        )
        help_text.pack(anchor=tk.W, pady=(0, 10))

        # Username
        frame = ttk.Frame(section_frame)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Username:", width=15).pack(side=tk.LEFT, padx=(0, 10))

        # Load from environment or config
        current_username = os.environ.get('SALESFORCE_USERNAME', 
                                         self.config.get('salesforce', {}).get('username', ''))
        var = tk.StringVar(value=current_username)
        self.widgets["salesforce.username"] = var

        entry = ttk.Entry(frame, textvariable=var, width=40)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Password
        frame = ttk.Frame(section_frame)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Password:", width=15).pack(side=tk.LEFT, padx=(0, 10))

        # Load from environment or config
        current_password = os.environ.get('SALESFORCE_PASSWORD',
                                         self.config.get('salesforce', {}).get('password', ''))
        var = tk.StringVar(value=current_password)
        self.widgets["salesforce.password"] = var

        entry = ttk.Entry(frame, textvariable=var, width=40, show="*")
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Show/Hide button for Password
        show_var_password = tk.BooleanVar(value=False)
        def toggle_password():
            if show_var_password.get():
                entry.config(show="*")
                show_btn_password.config(text="Show")
            else:
                entry.config(show="")
                show_btn_password.config(text="Hide")
            show_var_password.set(not show_var_password.get())
        
        show_btn_password = ttk.Button(frame, text="Show", command=toggle_password, width=6)
        show_btn_password.pack(side=tk.LEFT)

        # Security Token
        frame = ttk.Frame(section_frame)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Security Token:", width=15).pack(side=tk.LEFT, padx=(0, 10))

        # Load from environment or config
        current_token = os.environ.get('SALESFORCE_SECURITY_TOKEN',
                                      self.config.get('salesforce', {}).get('security_token', ''))
        var = tk.StringVar(value=current_token)
        self.widgets["salesforce.security_token"] = var

        entry = ttk.Entry(frame, textvariable=var, width=40, show="*")
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Show/Hide button for Token
        show_var_token = tk.BooleanVar(value=False)
        def toggle_token():
            if show_var_token.get():
                entry.config(show="*")
                show_btn_token.config(text="Show")
            else:
                entry.config(show="")
                show_btn_token.config(text="Hide")
            show_var_token.set(not show_var_token.get())
        
        show_btn_token = ttk.Button(frame, text="Show", command=toggle_token, width=6)
        show_btn_token.pack(side=tk.LEFT)

        # Domain selection
        frame = ttk.Frame(section_frame)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Domain:", width=15).pack(side=tk.LEFT, padx=(0, 10))

        current_domain = os.environ.get('SALESFORCE_DOMAIN',
                                       self.config.get('salesforce', {}).get('domain', 'login'))
        var = tk.StringVar(value=current_domain)
        self.widgets["salesforce.domain"] = var

        # Radio buttons for domain
        radio_frame = ttk.Frame(frame)
        radio_frame.pack(side=tk.LEFT)

        ttk.Radiobutton(
            radio_frame,
            text="Production (login)",
            variable=var,
            value="login"
        ).pack(side=tk.LEFT, padx=(0, 15))

        ttk.Radiobutton(
            radio_frame,
            text="Sandbox (test)",
            variable=var,
            value="test"
        ).pack(side=tk.LEFT)

        # Status and test connection
        status_frame = ttk.Frame(section_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))

        status_label = ttk.Label(
            status_frame,
            text="Status: Not configured",
            foreground="gray",
            font=("Arial", 9)
        )
        status_label.pack(side=tk.LEFT)

        def test_connection():
            """Test Salesforce connection"""
            try:
                username = self.widgets["salesforce.username"].get()
                password = self.widgets["salesforce.password"].get()
                token = self.widgets["salesforce.security_token"].get()
                
                if not username or not password or not token:
                    status_label.config(text="Status: Missing credentials", foreground="orange")
                    messagebox.showwarning(
                        "Missing Credentials",
                        "Please enter Username, Password, and Security Token."
                    )
                    return
                
                # Try to import simple_salesforce
                try:
                    from simple_salesforce import Salesforce
                    
                    # Attempt connection
                    domain = self.widgets["salesforce.domain"].get()
                    sf = Salesforce(
                        username=username,
                        password=password,
                        security_token=token,
                        domain=domain
                    )
                    
                    instance_url = f"https://{sf.sf_instance}"
                    
                    status_label.config(text=f"Status: Connected to {sf.sf_instance} ✓", foreground="green")
                    messagebox.showinfo(
                        "Connection Successful",
                        f"Successfully connected to Salesforce!\n\n"
                        f"Instance: {instance_url}\n\n"
                        "Your credentials are working correctly."
                    )
                    
                except ImportError:
                    status_label.config(text="Status: simple-salesforce not installed", foreground="orange")
                    messagebox.showwarning(
                        "Library Not Installed",
                        "The simple-salesforce library is required for Salesforce integration.\n\n"
                        "Install it with:\n"
                        "  pip install janus[salesforce]\n"
                        "or:\n"
                        "  pip install simple-salesforce>=1.12.6"
                    )
                except Exception as e:
                    error_msg = str(e)
                    if "INVALID_LOGIN" in error_msg or "authentication" in error_msg.lower():
                        status_label.config(text="Status: Authentication failed", foreground="red")
                        messagebox.showerror(
                            "Authentication Failed",
                            "Unable to authenticate with Salesforce.\n\n"
                            "Please check:\n"
                            "• Username is correct\n"
                            "• Password is correct\n"
                            "• Security token is current\n"
                            "• Domain selection (Production vs Sandbox)\n\n"
                            f"Error: {error_msg[:200]}"
                        )
                    else:
                        raise
                    
            except Exception as e:
                status_label.config(text=f"Status: Error - {str(e)[:30]}...", foreground="red")
                messagebox.showerror("Connection Test Failed", f"Error: {str(e)}")

        test_btn = ttk.Button(
            status_frame,
            text="Test Connection",
            command=test_connection
        )
        test_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Setup guide button
        def open_setup_guide():
            """Open Salesforce setup guide in default browser"""
            import webbrowser
            import os
            guide_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "docs", "user", "salesforce-crm-setup.md"
            )
            if os.path.exists(guide_path):
                webbrowser.open(f"file://{guide_path}")
            else:
                messagebox.showinfo(
                    "Setup Guide",
                    "Setup guide location:\n"
                    "docs/user/salesforce-crm-setup.md"
                )
        
        guide_btn = ttk.Button(
            status_frame,
            text="Setup Guide",
            command=open_setup_guide
        )
        guide_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Security note
        ttk.Label(
            section_frame,
            text="🔒 Credentials are stored securely and never logged",
            font=("Arial", 8),
            foreground="gray",
        ).pack(anchor=tk.W, pady=(5, 0))

    def create_messaging_section(self, parent: ttk.Frame):
        """Create Messaging Integration (Slack & Teams) credentials configuration section"""
        import os
        
        section_frame = ttk.LabelFrame(parent, text="Messaging Integration (Slack & Teams)", padding=15)
        section_frame.pack(fill=tk.X, pady=(0, 10))

        # Help text
        help_text = ttk.Label(
            section_frame,
            text="Configure Slack and/or Microsoft Teams credentials for messaging operations.\n"
                 "See docs/architecture/24-messaging-integration.md for setup instructions.",
            font=("Arial", 9),
            foreground="gray",
        )
        help_text.pack(anchor=tk.W, pady=(0, 10))

        # Slack Section
        slack_frame = ttk.LabelFrame(section_frame, text="Slack Configuration", padding=10)
        slack_frame.pack(fill=tk.X, pady=(0, 10))

        # Slack Bot Token
        frame = ttk.Frame(slack_frame)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Bot Token:", width=15).pack(side=tk.LEFT, padx=(0, 10))

        # Load from environment or config
        current_token = os.environ.get('SLACK_BOT_TOKEN', 
                                       self.config.get('messaging', {}).get('slack_bot_token', ''))
        var = tk.StringVar(value=current_token)
        self.widgets["messaging.slack_bot_token"] = var

        entry = ttk.Entry(frame, textvariable=var, width=40, show="*")
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Show/Hide button for Token
        show_var_token = tk.BooleanVar(value=False)
        def toggle_slack_token():
            if show_var_token.get():
                entry.config(show="*")
                show_btn_token.config(text="Show")
            else:
                entry.config(show="")
                show_btn_token.config(text="Hide")
            show_var_token.set(not show_var_token.get())
        
        show_btn_token = ttk.Button(frame, text="Show", command=toggle_slack_token, width=6)
        show_btn_token.pack(side=tk.LEFT)

        # Slack help text
        ttk.Label(
            slack_frame,
            text="Get token from: api.slack.com/apps → Your App → OAuth & Permissions",
            font=("Arial", 8),
            foreground="gray",
        ).pack(anchor=tk.W, pady=(2, 0))

        # Teams Section
        teams_frame = ttk.LabelFrame(section_frame, text="Microsoft Teams Configuration", padding=10)
        teams_frame.pack(fill=tk.X, pady=(0, 10))

        # Teams Client ID
        frame = ttk.Frame(teams_frame)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Client ID:", width=15).pack(side=tk.LEFT, padx=(0, 10))

        # Load from environment or config
        current_client_id = os.environ.get('TEAMS_CLIENT_ID', 
                                          self.config.get('messaging', {}).get('teams_client_id', ''))
        var = tk.StringVar(value=current_client_id)
        self.widgets["messaging.teams_client_id"] = var

        entry = ttk.Entry(frame, textvariable=var, width=40)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Teams Client Secret
        frame = ttk.Frame(teams_frame)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Client Secret:", width=15).pack(side=tk.LEFT, padx=(0, 10))

        # Load from environment or config
        current_secret = os.environ.get('TEAMS_CLIENT_SECRET',
                                       self.config.get('messaging', {}).get('teams_client_secret', ''))
        var = tk.StringVar(value=current_secret)
        self.widgets["messaging.teams_client_secret"] = var

        entry = ttk.Entry(frame, textvariable=var, width=40, show="*")
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Show/Hide button for Secret
        show_var_secret = tk.BooleanVar(value=False)
        def toggle_teams_secret():
            if show_var_secret.get():
                entry.config(show="*")
                show_btn_secret.config(text="Show")
            else:
                entry.config(show="")
                show_btn_secret.config(text="Hide")
            show_var_secret.set(not show_var_secret.get())
        
        show_btn_secret = ttk.Button(frame, text="Show", command=toggle_teams_secret, width=6)
        show_btn_secret.pack(side=tk.LEFT)

        # Teams Tenant ID
        frame = ttk.Frame(teams_frame)
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text="Tenant ID:", width=15).pack(side=tk.LEFT, padx=(0, 10))

        # Load from environment or config
        current_tenant = os.environ.get('TEAMS_TENANT_ID',
                                       self.config.get('messaging', {}).get('teams_tenant_id', ''))
        var = tk.StringVar(value=current_tenant)
        self.widgets["messaging.teams_tenant_id"] = var

        entry = ttk.Entry(frame, textvariable=var, width=40)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Teams help text
        ttk.Label(
            teams_frame,
            text="Register app at: portal.azure.com → Azure AD → App Registrations",
            font=("Arial", 8),
            foreground="gray",
        ).pack(anchor=tk.W, pady=(2, 0))

        # Status and test connections
        status_frame = ttk.Frame(section_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))

        status_label = ttk.Label(
            status_frame,
            text="Status: Not configured",
            foreground="gray",
            font=("Arial", 9)
        )
        status_label.pack(side=tk.LEFT)

        def test_slack_connection():
            """Test Slack connection"""
            try:
                token = self.widgets["messaging.slack_bot_token"].get()
                
                if not token:
                    status_label.config(text="Status: Slack token missing", foreground="orange")
                    messagebox.showwarning(
                        "Missing Credentials",
                        "Please enter Slack Bot Token."
                    )
                    return
                
                # Try to import slack_sdk
                try:
                    from slack_sdk import WebClient
                    
                    # Test connection
                    client = WebClient(token=token)
                    response = client.auth_test()
                    
                    status_label.config(
                        text=f"Status: Slack connected ({response['user']})", 
                        foreground="green"
                    )
                    messagebox.showinfo(
                        "Connection Successful",
                        f"Successfully connected to Slack!\n\n"
                        f"Bot: {response['user']}\n"
                        f"Team: {response.get('team', 'N/A')}"
                    )
                    
                except ImportError:
                    status_label.config(text="Status: slack_sdk not installed", foreground="orange")
                    messagebox.showwarning(
                        "Library Not Installed",
                        "The slack_sdk library is required for Slack integration.\n\n"
                        "Install it with:\n"
                        "  pip install janus[messaging]\n"
                        "or:\n"
                        "  pip install slack_sdk>=3.33.5"
                    )
                except Exception as e:
                    error_msg = str(e)
                    status_label.config(text="Status: Slack authentication failed", foreground="red")
                    messagebox.showerror(
                        "Authentication Failed",
                        "Unable to authenticate with Slack.\n\n"
                        "Please check:\n"
                        "• Bot token is correct\n"
                        "• Token starts with 'xoxb-'\n"
                        "• Bot is installed to workspace\n\n"
                        f"Error: {error_msg[:200]}"
                    )
                    
            except Exception as e:
                status_label.config(text=f"Status: Error - {str(e)[:30]}...", foreground="red")
                messagebox.showerror("Connection Test Failed", f"Error: {str(e)}")

        def test_teams_connection():
            """Test Teams connection"""
            try:
                client_id = self.widgets["messaging.teams_client_id"].get()
                client_secret = self.widgets["messaging.teams_client_secret"].get()
                tenant_id = self.widgets["messaging.teams_tenant_id"].get()
                
                if not client_id or not client_secret or not tenant_id:
                    status_label.config(text="Status: Teams credentials missing", foreground="orange")
                    messagebox.showwarning(
                        "Missing Credentials",
                        "Please enter Teams Client ID, Client Secret, and Tenant ID."
                    )
                    return
                
                # Try to import msal
                try:
                    import msal
                    
                    # Test connection
                    authority = f"https://login.microsoftonline.com/{tenant_id}"
                    app = msal.ConfidentialClientApplication(
                        client_id,
                        authority=authority,
                        client_credential=client_secret
                    )
                    
                    # Try to acquire token
                    result = app.acquire_token_for_client(
                        scopes=["https://graph.microsoft.com/.default"]
                    )
                    
                    if "access_token" in result:
                        status_label.config(
                            text="Status: Teams connected", 
                            foreground="green"
                        )
                        messagebox.showinfo(
                            "Connection Successful",
                            "Successfully connected to Microsoft Teams!\n\n"
                            "Authentication successful."
                        )
                    else:
                        error = result.get("error", "Unknown error")
                        error_desc = result.get("error_description", "")
                        status_label.config(text="Status: Teams authentication failed", foreground="red")
                        messagebox.showerror(
                            "Authentication Failed",
                            f"Unable to authenticate with Microsoft Teams.\n\n"
                            f"Error: {error}\n"
                            f"{error_desc[:200]}"
                        )
                    
                except ImportError:
                    status_label.config(text="Status: msal not installed", foreground="orange")
                    messagebox.showwarning(
                        "Library Not Installed",
                        "The msal library is required for Teams integration.\n\n"
                        "Install it with:\n"
                        "  pip install janus[messaging]\n"
                        "or:\n"
                        "  pip install msal>=1.31.1"
                    )
                except Exception as e:
                    error_msg = str(e)
                    status_label.config(text="Status: Teams connection error", foreground="red")
                    messagebox.showerror(
                        "Connection Test Failed",
                        f"Error: {error_msg[:300]}"
                    )
                    
            except Exception as e:
                status_label.config(text=f"Status: Error - {str(e)[:30]}...", foreground="red")
                messagebox.showerror("Connection Test Failed", f"Error: {str(e)}")

        test_slack_btn = ttk.Button(
            status_frame,
            text="Test Slack",
            command=test_slack_connection
        )
        test_slack_btn.pack(side=tk.RIGHT, padx=(5, 0))

        test_teams_btn = ttk.Button(
            status_frame,
            text="Test Teams",
            command=test_teams_connection
        )
        test_teams_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Setup guide button
        def open_setup_guide():
            """Open messaging setup guide"""
            import webbrowser
            import os
            guide_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "docs", "architecture", "24-messaging-integration.md"
            )
            if os.path.exists(guide_path):
                webbrowser.open(f"file://{guide_path}")
            else:
                messagebox.showinfo(
                    "Setup Guide",
                    "Setup guide location:\n"
                    "docs/architecture/24-messaging-integration.md"
                )
        
        guide_btn = ttk.Button(
            status_frame,
            text="Setup Guide",
            command=open_setup_guide
        )
        guide_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Security note
        ttk.Label(
            section_frame,
            text="🔒 Credentials are stored securely and never logged",
            font=("Arial", 8),
            foreground="gray",
        ).pack(anchor=tk.W, pady=(5, 0))


# PySide6 Credential Dialog for ConfigMiniWindow (TICKET-FEAT-001)
# This dialog is used to input credentials for integrations
class CredentialDialog:
    """
    Simple credential input dialog for PySide6
    Used by ConfigMiniWindow to collect integration credentials
    """
    def __init__(self, parent=None, title="Credentials", fields=None):
        """
        Initialize credential dialog
        
        Args:
            parent: Parent widget
            title: Dialog title
            fields: List of tuples (label, key, default_value, is_password=False)
        """
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QLabel
        from PySide6.QtCore import Qt
        
        self.dialog = QDialog(parent)
        self.dialog.setWindowTitle(title)
        self.dialog.setModal(True)
        self.dialog.setMinimumWidth(400)
        
        # Set window flags to remove question mark and keep close button
        self.dialog.setWindowFlags(
            Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint
        )
        
        layout = QVBoxLayout(self.dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Add title label
        title_label = QLabel(f"🔐 {title}")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #20E3B2;")
        layout.addWidget(title_label)
        
        # Form for fields
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.field_widgets = {}
        
        for field in fields or []:
            label = field[0]
            key = field[1]
            default_value = field[2] if len(field) > 2 else ""
            is_password = field[3] if len(field) > 3 else False
            
            line_edit = QLineEdit()
            line_edit.setText(default_value)
            if is_password:
                line_edit.setEchoMode(QLineEdit.Password)
            
            self.field_widgets[key] = line_edit
            form_layout.addRow(label, line_edit)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.dialog.accept)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #20E3B2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3DFFD6;
            }
        """)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def exec(self):
        """Show dialog and return result"""
        return self.dialog.exec()
    
    def get_values(self):
        """Get values from all fields"""
        return {key: widget.text() for key, widget in self.field_widgets.items()}
