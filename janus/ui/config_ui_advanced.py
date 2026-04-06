"""
Configuration UI - Advanced Options
Handles advanced configuration sections (cognitive planner, performance, OCR)
"""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, Optional

from janus.logging import get_logger

logger = get_logger("config_ui_advanced")


class ConfigUIAdvanced:
    """Advanced options for configuration UI"""

    def __init__(self, config: Dict[str, Any], widgets: Dict[str, tk.Variable]):
        """
        Initialize advanced options

        Args:
            config: Configuration dictionary
            widgets: Widget variables dictionary
        """
        self.config = config
        self.widgets = widgets
        self.logger = logger

    def create_cognitive_planner_section(self, parent: ttk.Frame):
        """Create cognitive planner configuration section"""
        section_frame = ttk.LabelFrame(parent, text="Cognitive Planner (LLM Reasoner)", padding=15)
        section_frame.pack(fill=tk.X, pady=(0, 10))

        planner_config = self.config.get("cognitive_planner", {})

        # Status indicator
        status_frame = ttk.Frame(section_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(status_frame, text="Status:").pack(side=tk.LEFT, padx=(0, 10))

        # Check backend availability
        status = self._check_llm_backend_status()
        status_color = "green" if status["available"] else "orange"
        status_text = status["message"]

        status_label = ttk.Label(
            status_frame, text=status_text, foreground=status_color, font=("Arial", 9, "bold")
        )
        status_label.pack(side=tk.LEFT)

        # Setup wizard button
        wizard_button = ttk.Button(
            status_frame, text="Run Setup Wizard", command=self._run_setup_wizard
        )
        wizard_button.pack(side=tk.RIGHT)

        # Test backend button
        test_button = ttk.Button(status_frame, text="Test Backend", command=self._test_backend)
        test_button.pack(side=tk.RIGHT, padx=(0, 5))

        # Backend dropdown
        if "backend" in planner_config:
            frame = ttk.Frame(section_frame)
            frame.pack(fill=tk.X, pady=5)

            ttk.Label(frame, text="Backend:").pack(side=tk.LEFT, padx=(0, 10))

            var = tk.StringVar(value=planner_config["backend"].get("value", "mock"))
            self.widgets["cognitive_planner.backend"] = var

            combo = ttk.Combobox(
                frame,
                textvariable=var,
                values=planner_config["backend"]["options"],
                state="readonly",
                width=15,
            )
            combo.pack(side=tk.LEFT)

        # Model path (for llama-cpp)
        if "model_path" in planner_config:
            frame = ttk.Frame(section_frame)
            frame.pack(fill=tk.X, pady=5)

            ttk.Label(frame, text="Model Path:").pack(side=tk.LEFT, padx=(0, 10))

            var = tk.StringVar(value=planner_config["model_path"].get("value", ""))
            self.widgets["cognitive_planner.model_path"] = var

            entry = ttk.Entry(frame, textvariable=var, width=30)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

            browse_button = ttk.Button(
                frame, text="Browse", command=lambda: self._browse_model_file(var)
            )
            browse_button.pack(side=tk.LEFT)

        # Model name (for ollama)
        if "model_name" in planner_config:
            frame = ttk.Frame(section_frame)
            frame.pack(fill=tk.X, pady=5)

            ttk.Label(frame, text="Model Name:").pack(side=tk.LEFT, padx=(0, 10))

            var = tk.StringVar(
                value=planner_config["model_name"].get("value", "mistral:7b-instruct-q4_K_M")
            )
            self.widgets["cognitive_planner.model_name"] = var

            combo = ttk.Combobox(
                frame, textvariable=var, values=planner_config["model_name"]["options"], width=25
            )
            combo.pack(side=tk.LEFT)

        # Timeout
        if "timeout_ms" in planner_config:
            frame = ttk.Frame(section_frame)
            frame.pack(fill=tk.X, pady=5)

            ttk.Label(frame, text="Timeout (ms):").pack(side=tk.LEFT, padx=(0, 10))

            var = tk.IntVar(value=planner_config["timeout_ms"].get("value", 500))
            self.widgets["cognitive_planner.timeout_ms"] = var

            spinbox = ttk.Spinbox(
                frame,
                from_=planner_config["timeout_ms"]["min"],
                to=planner_config["timeout_ms"]["max"],
                textvariable=var,
                width=10,
            )
            spinbox.pack(side=tk.LEFT)

            ttk.Label(frame, text="(Target: <500ms)", font=("Arial", 8), foreground="gray").pack(
                side=tk.LEFT, padx=(5, 0)
            )

        # Fallback option
        if "fallback_enabled" in planner_config:
            var = tk.BooleanVar(value=planner_config["fallback_enabled"].get("enabled", True))
            self.widgets["cognitive_planner.fallback_enabled"] = var

            check = ttk.Checkbutton(
                section_frame, text=planner_config["fallback_enabled"]["label"], variable=var
            )
            check.pack(anchor=tk.W, pady=2)

        # Help text
        help_text = ttk.Label(
            section_frame,
            text="Note: Install Ollama or llama-cpp-python to use LLM features.\nMock backend is for testing only. Run Setup Wizard for guided installation.",
            font=("Arial", 9),
            foreground="gray",
        )
        help_text.pack(anchor=tk.W, pady=(10, 0))

    def create_performance_section(self, parent: ttk.Frame):
        """Create performance configuration section"""
        section_frame = ttk.LabelFrame(parent, text="Performance & OCR", padding=15)
        section_frame.pack(fill=tk.X, pady=(0, 10))

        # OCR options
        ocr_config = self.config.get("ocr", {})
        for option_name, option_config in ocr_config.items():
            if "enabled" in option_config:
                var = tk.BooleanVar(value=option_config.get("enabled", True))
                self.widgets[f"ocr.{option_name}"] = var

                label = option_config.get("label", option_name.replace("_", " ").title())
                check = ttk.Checkbutton(section_frame, text=label, variable=var)
                check.pack(anchor=tk.W, pady=2)

            elif "options" in option_config:
                # Dropdown for backend selection
                frame = ttk.Frame(section_frame)
                frame.pack(fill=tk.X, pady=5)

                label = option_config.get("label", option_name.replace("_", " ").title())
                ttk.Label(frame, text=f"{label}:").pack(side=tk.LEFT, padx=(0, 10))

                var = tk.StringVar(value=option_config.get("value", option_config["options"][0]))
                self.widgets[f"ocr.{option_name}"] = var

                combo = ttk.Combobox(
                    frame,
                    textvariable=var,
                    values=option_config["options"],
                    state="readonly",
                    width=15,
                )
                combo.pack(side=tk.LEFT, padx=(0, 10))

                # Add hint for OCR backend
                if option_name == "backend":
                    ttk.Label(
                        frame,
                        text="(tesseract: faster, easyocr: more accurate)",
                        font=("Arial", 8),
                        foreground="gray",
                    ).pack(side=tk.LEFT)

            elif "value" in option_config and "min" in option_config:
                frame = ttk.Frame(section_frame)
                frame.pack(fill=tk.X, pady=5)

                label = option_config.get("label", option_name.replace("_", " ").title())
                ttk.Label(frame, text=f"{label}:").pack(side=tk.LEFT, padx=(0, 10))

                var = tk.IntVar(value=option_config.get("value", 300))
                self.widgets[f"ocr.{option_name}"] = var

                spinbox = ttk.Spinbox(
                    frame,
                    from_=option_config["min"],
                    to=option_config["max"],
                    textvariable=var,
                    width=10,
                )
                spinbox.pack(side=tk.LEFT)

        # Performance options
        perf_config = self.config.get("performance", {})
        for option_name, option_config in perf_config.items():
            frame = ttk.Frame(section_frame)
            frame.pack(fill=tk.X, pady=5)

            label = option_config.get("label", option_name.replace("_", " ").title())
            ttk.Label(frame, text=f"{label}:").pack(side=tk.LEFT, padx=(0, 10))

            var = tk.DoubleVar(value=option_config.get("value", 0.5))
            self.widgets[f"performance.{option_name}"] = var

            spinbox = ttk.Spinbox(
                frame,
                from_=option_config["min"],
                to=option_config["max"],
                textvariable=var,
                increment=0.1,
                width=10,
                format="%.1f",
            )
            spinbox.pack(side=tk.LEFT)

    def _check_llm_backend_status(self) -> Dict[str, Any]:
        """
        Check the status of LLM backends

        Returns:
            Dictionary with status information
        """
        try:
            from janus.ai.reasoning.llm_setup_wizard import LLMSetupWizard

            wizard = LLMSetupWizard()
            ollama_available, ollama_info = wizard.detect_ollama()
            llama_cpp_available, llama_cpp_info = wizard.detect_llama_cpp()

            if ollama_available:
                return {"available": True, "message": f"✅ Ollama available ({ollama_info})"}
            elif llama_cpp_available:
                return {"available": True, "message": f"✅ llama-cpp available ({llama_cpp_info})"}
            else:
                return {"available": False, "message": "⚠️  No LLM backend available"}
        except Exception as e:
            return {"available": False, "message": "⚠️  Unable to check status"}

    def _run_setup_wizard(self):
        """Run the LLM setup wizard"""
        try:
            from janus.ai.reasoning.llm_setup_wizard import run_setup_wizard

            def run_wizard():
                config = run_setup_wizard()
                if config:
                    # Update UI with new config
                    if "backend" in config and "cognitive_planner.backend" in self.widgets:
                        self.widgets["cognitive_planner.backend"].set(config["backend"])
                    if "model_name" in config and "cognitive_planner.model_name" in self.widgets:
                        self.widgets["cognitive_planner.model_name"].set(config["model_name"])
                    if "model_path" in config and "cognitive_planner.model_path" in self.widgets:
                        self.widgets["cognitive_planner.model_path"].set(config["model_path"])

                    messagebox.showinfo("Success", "LLM backend configured successfully!")

            # Run in separate thread
            wizard_thread = threading.Thread(target=run_wizard, daemon=True)
            wizard_thread.start()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to run setup wizard: {e}")

    def _test_backend(self):
        """Test the current LLM backend configuration"""
        try:
            from janus.ai.reasoning.reasoner_llm import ReasonerLLM

            # Get current configuration
            backend = self.widgets.get("cognitive_planner.backend", tk.StringVar()).get()
            model_name = self.widgets.get("cognitive_planner.model_name", tk.StringVar()).get()
            model_path = self.widgets.get("cognitive_planner.model_path", tk.StringVar()).get()

            # Test backend
            if backend == "ollama":
                llm = ReasonerLLM(backend="ollama", model_name=model_name)
            elif backend == "llama-cpp":
                llm = ReasonerLLM(backend="llama-cpp", model_path=model_path)
            else:
                llm = ReasonerLLM(backend="mock")

            if llm.available:
                # Test with a simple command
                result = llm.parse_command("test command", language="en")
                latency = result.get("latency_ms", 0)

                messagebox.showinfo(
                    "Backend Test",
                    f"✅ Backend is working!\n\n"
                    f"Backend: {backend}\n"
                    f"Model: {model_name or model_path or 'mock'}\n"
                    f"Latency: {latency:.0f}ms\n"
                    f"Source: {result.get('source', 'unknown')}",
                )
            else:
                messagebox.showwarning(
                    "Backend Test",
                    f"⚠️  Backend not available\n\n"
                    f"Backend: {backend}\n"
                    f"The backend could not be initialized.\n"
                    f"Please check your configuration or run the Setup Wizard.",
                )

        except Exception as e:
            messagebox.showerror("Backend Test", f"❌ Test failed:\n\n{str(e)}")

    def _browse_model_file(self, var: tk.StringVar):
        """Browse for model file"""
        filename = filedialog.askopenfilename(
            title="Select GGUF Model File",
            filetypes=[("GGUF files", "*.gguf"), ("All files", "*.*")],
        )

        if filename:
            var.set(filename)
