"""
Diagnostic information collector for Janus
Gathers system info, configuration, and diagnostic data for troubleshooting
"""

import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from janus.utils.paths import get_config_file_path

from .logger import get_logger


class DiagnosticCollector:
    """
    Collects diagnostic information for troubleshooting
    """

    def __init__(self):
        """Initialize diagnostic collector"""
        self.logger = get_logger("diagnostic")

    def collect_system_info(self) -> Dict[str, Any]:
        """
        Collect system information

        Returns:
            Dictionary with system info
        """
        info = {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
            },
            "python": {
                "version": sys.version,
                "implementation": platform.python_implementation(),
                "executable": sys.executable,
            },
            "environment": {
                "cwd": os.getcwd(),
                "home": os.path.expanduser("~"),
                "path": os.environ.get("PATH", ""),
            },
        }

        # macOS specific info
        if platform.system() == "Darwin":
            info["macos"] = self._collect_macos_info()

        return info

    def _collect_macos_info(self) -> Dict[str, Any]:
        """Collect macOS specific information"""
        macos_info = {}

        try:
            # Get macOS version
            result = subprocess.run(["sw_vers"], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        macos_info[key.strip()] = value.strip()
        except Exception as e:
            self.logger.warning(f"Could not collect macOS version info: {e}")

        try:
            # Get system profiler info (hardware)
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                hardware_info = {}
                for line in result.stdout.strip().split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        hardware_info[key.strip()] = value.strip()
                macos_info["hardware"] = hardware_info
        except Exception as e:
            self.logger.warning(f"Could not collect hardware info: {e}")

        return macos_info

    def collect_dependencies(self) -> Dict[str, str]:
        """
        Collect installed Python dependencies

        Returns:
            Dictionary of package names and versions
        """
        dependencies = {}

        try:
            import pkg_resources

            for dist in pkg_resources.working_set:
                dependencies[dist.key] = dist.version
        except Exception as e:
            self.logger.warning(f"Could not collect dependencies: {e}")

        return dependencies

    def collect_janus_config(self) -> Dict[str, Any]:
        """
        Collect Janus configuration

        Returns:
            Dictionary with Janus config
        """
        config = {}

        # Check for config files
        config_locations = [
            Path.cwd() / "config.ini",
            Path.cwd() / "config.json",
            get_config_file_path("config.ini", ensure_dir_exists=False),
            get_config_file_path("config.json", ensure_dir_exists=False),
        ]

        for location in config_locations:
            if location.exists():
                config[str(location)] = {
                    "exists": True,
                    "size": location.stat().st_size,
                    "modified": datetime.fromtimestamp(location.stat().st_mtime).isoformat(),
                }
            else:
                config[str(location)] = {"exists": False}

        return config

    def check_requirements(self) -> Dict[str, Any]:
        """
        Check system requirements for Janus

        Returns:
            Dictionary with requirement check results
        """
        requirements = {
            "python_version": {
                "required": "3.8+",
                "current": platform.python_version(),
                "satisfied": sys.version_info >= (3, 8),
            },
            "platform": {
                "required": "macOS (primary)",
                "current": platform.system(),
                "supported": platform.system() in ["Darwin", "Linux", "Windows"],
            },
        }

        # Check for required modules
        required_modules = [
            "whisper",
            "pyaudio",
            "numpy",
            "pyautogui",
            "pyperclip",
        ]

        module_status = {}
        for module in required_modules:
            try:
                __import__(module)
                module_status[module] = {"installed": True}
            except ImportError:
                module_status[module] = {"installed": False}

        requirements["modules"] = module_status

        # Check for optional modules
        optional_modules = {
            "pytesseract": "OCR support",
            "easyocr": "Alternative OCR",
            "openai": "LLM integration",
        }

        optional_status = {}
        for module, description in optional_modules.items():
            try:
                __import__(module)
                optional_status[module] = {
                    "installed": True,
                    "description": description,
                }
            except ImportError:
                optional_status[module] = {
                    "installed": False,
                    "description": description,
                }

        requirements["optional_modules"] = optional_status

        # Check for macOS specific requirements
        if platform.system() == "Darwin":
            macos_requirements = self._check_macos_requirements()
            requirements["macos"] = macos_requirements

        return requirements

    def _check_macos_requirements(self) -> Dict[str, Any]:
        """Check macOS specific requirements"""
        checks = {}

        # Check for Tesseract
        try:
            result = subprocess.run(
                ["which", "tesseract"], capture_output=True, text=True, timeout=5
            )
            checks["tesseract"] = {
                "installed": result.returncode == 0,
                "path": result.stdout.strip() if result.returncode == 0 else None,
            }
        except Exception as e:
            checks["tesseract"] = {
                "installed": False,
                "error": str(e),
            }

        # Check for Homebrew
        try:
            result = subprocess.run(["which", "brew"], capture_output=True, text=True, timeout=5)
            checks["homebrew"] = {
                "installed": result.returncode == 0,
                "path": result.stdout.strip() if result.returncode == 0 else None,
            }
        except Exception as e:
            checks["homebrew"] = {
                "installed": False,
                "error": str(e),
            }

        return checks

    def generate_diagnostic_report(self) -> str:
        """
        Generate comprehensive diagnostic report

        Returns:
            Formatted diagnostic report as string
        """
        import json

        report = {
            "timestamp": datetime.now().isoformat(),
            "system_info": self.collect_system_info(),
            "dependencies": self.collect_dependencies(),
            "janus_config": self.collect_janus_config(),
            "requirements": self.check_requirements(),
        }

        # Log report generation
        self.logger.info("Generated diagnostic report")

        return json.dumps(report, indent=2)

    def save_diagnostic_report(self, output_path: Optional[str] = None) -> str:
        """
        Save diagnostic report to file

        Args:
            output_path: Output file path (default: janus_diagnostic_<timestamp>.json)

        Returns:
            Path to saved report
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"janus_diagnostic_{timestamp}.json"

        report = self.generate_diagnostic_report()

        with open(output_path, "w") as f:
            f.write(report)

        self.logger.info(f"Diagnostic report saved to: {output_path}")

        return output_path
