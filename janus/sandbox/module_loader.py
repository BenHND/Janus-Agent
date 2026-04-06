"""
Module loader with hot-reload capability for sandbox modules.
Phase 12 - Ticket 12.1: Sandbox Module Environment
"""

import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer


class ModuleFileWatcher(FileSystemEventHandler):
    """
    Watches module files for changes and triggers reloads
    """

    def __init__(self, sandbox_manager, auto_reload: bool = True):
        """
        Initialize file watcher

        Args:
            sandbox_manager: SandboxManager instance
            auto_reload: Whether to automatically reload on change
        """
        self.sandbox_manager = sandbox_manager
        self.auto_reload = auto_reload
        self.logger = logging.getLogger("module_file_watcher")

        # Debounce rapid file changes
        self._last_modified: Dict[str, float] = {}
        self._debounce_seconds = 1.0

    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return

        if not event.src_path.endswith(".py"):
            return

        # Debounce
        now = time.time()
        last_time = self._last_modified.get(event.src_path, 0)
        if now - last_time < self._debounce_seconds:
            return

        self._last_modified[event.src_path] = now

        # Find module by path
        file_path = Path(event.src_path)
        module_name = None

        for name, path in self.sandbox_manager.module_paths.items():
            if path.samefile(file_path):
                module_name = name
                break

        if module_name and self.auto_reload:
            self.logger.info(f"File changed: {file_path}, reloading {module_name}")
            result = self.sandbox_manager.reload_module(module_name)

            if result["status"] == "success":
                self.logger.info(f"Successfully reloaded {module_name}")
            else:
                self.logger.error(f"Failed to reload {module_name}: {result.get('error')}")


class SandboxModuleLoader:
    """
    Enhanced module loader with hot-reload capability

    Features:
    - Automatic file watching and reloading
    - Thread-safe reloading
    - Change notifications
    - Manual and automatic reload modes
    """

    def __init__(self, sandbox_manager):
        """
        Initialize module loader

        Args:
            sandbox_manager: SandboxManager instance to use
        """
        self.sandbox_manager = sandbox_manager
        self.observer: Optional[Observer] = None
        self.file_watcher: Optional[ModuleFileWatcher] = None
        self.auto_reload_enabled = False

        self.reload_callbacks: list[Callable] = []
        self.logger = logging.getLogger("sandbox_module_loader")

        self._lock = threading.Lock()

    def enable_auto_reload(self, watch_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Enable automatic module reloading when files change

        Args:
            watch_dir: Directory to watch (defaults to sandbox_dir)

        Returns:
            Result dictionary
        """
        if self.auto_reload_enabled:
            return {"status": "success", "message": "Auto-reload already enabled"}

        try:
            watch_dir = watch_dir or self.sandbox_manager.sandbox_dir

            self.file_watcher = ModuleFileWatcher(self.sandbox_manager, auto_reload=True)
            self.observer = Observer()
            self.observer.schedule(self.file_watcher, str(watch_dir), recursive=True)
            self.observer.start()

            self.auto_reload_enabled = True
            self.logger.info(f"Auto-reload enabled for {watch_dir}")

            return {"status": "success", "watch_dir": str(watch_dir), "auto_reload": True}
        except Exception as e:
            self.logger.error(f"Failed to enable auto-reload: {e}")
            return {"status": "error", "error": str(e)}

    def disable_auto_reload(self) -> Dict[str, Any]:
        """
        Disable automatic module reloading

        Returns:
            Result dictionary
        """
        if not self.auto_reload_enabled:
            return {"status": "success", "message": "Auto-reload already disabled"}

        try:
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5)
                self.observer = None

            self.file_watcher = None
            self.auto_reload_enabled = False
            self.logger.info("Auto-reload disabled")

            return {"status": "success", "auto_reload": False}
        except Exception as e:
            self.logger.error(f"Failed to disable auto-reload: {e}")
            return {"status": "error", "error": str(e)}

    def load_from_directory(self, directory: Path, pattern: str = "*.py") -> Dict[str, Any]:
        """
        Load all modules from a directory

        Args:
            directory: Directory containing module files
            pattern: File pattern to match (default: *.py)

        Returns:
            Results for all loaded modules
        """
        if not directory.exists():
            return {"status": "error", "error": f"Directory not found: {directory}"}

        results = {}
        module_files = list(directory.glob(pattern))

        for file_path in module_files:
            # Skip __init__.py and test files
            if file_path.name.startswith("__") or file_path.name.startswith("test_"):
                continue

            module_name = file_path.stem
            result = self.sandbox_manager.load_module(file_path, module_name)
            results[module_name] = result

        return {
            "status": "success",
            "directory": str(directory),
            "total_files": len(module_files),
            "results": results,
        }

    def add_reload_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """
        Add a callback to be called when a module is reloaded

        Args:
            callback: Function(module_name, reload_result) to call
        """
        self.reload_callbacks.append(callback)

    def remove_reload_callback(self, callback: Callable):
        """
        Remove a reload callback

        Args:
            callback: Callback to remove
        """
        if callback in self.reload_callbacks:
            self.reload_callbacks.remove(callback)

    def _trigger_reload_callbacks(self, module_name: str, result: Dict[str, Any]):
        """
        Trigger all reload callbacks

        Args:
            module_name: Name of reloaded module
            result: Reload result
        """
        for callback in self.reload_callbacks:
            try:
                callback(module_name, result)
            except Exception as e:
                self.logger.error(f"Error in reload callback: {e}")

    def reload_module_safe(self, module_name: str) -> Dict[str, Any]:
        """
        Thread-safe module reload

        Args:
            module_name: Name of module to reload

        Returns:
            Reload result
        """
        with self._lock:
            result = self.sandbox_manager.reload_module(module_name)
            self._trigger_reload_callbacks(module_name, result)
            return result

    def get_status(self) -> Dict[str, Any]:
        """
        Get loader status

        Returns:
            Status information
        """
        return {
            "status": "success",
            "auto_reload_enabled": self.auto_reload_enabled,
            "loaded_modules": len(self.sandbox_manager.loaded_modules),
            "watched_paths": [str(p) for p in self.sandbox_manager.module_paths.values()],
            "callbacks_registered": len(self.reload_callbacks),
        }

    def cleanup(self):
        """Clean up resources"""
        if self.auto_reload_enabled:
            self.disable_auto_reload()
