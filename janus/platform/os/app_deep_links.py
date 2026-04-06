"""
Generic Deep Link Handler for SaaS Applications

TICKET-BIZ-003: Le "Generic Deep Linker" (Pour le reste)

This module provides a registry-based deep link system for opening URLs
in SaaS applications (Zoom, Notion, Spotify, Slack, etc.) using their
native URL schemes or web fallbacks.

Features:
    - JSON-based registry of URL patterns
    - Support for URL schemes (zoom://, notion://, spotify:, etc.)
    - Web fallback URLs when native scheme not available
    - Cross-platform URL opening (macOS, Windows, Linux)
    - Template-based URL building with parameter substitution

Usage:
    from janus.platform.os.app_deep_links import DeepLinkHandler
    
    handler = DeepLinkHandler()
    
    # Open Zoom meeting
    handler.open_deep_link("zoom", {"id": "123-456-789"})
    
    # Open Spotify track
    handler.open_deep_link("spotify", {"type": "track", "id": "3n3Ppam7vgaVa1iaRUc9Lp"})
    
    # Open Notion page
    handler.open_deep_link("notion", {"slug": "My-Page-123abc"})
"""

import json
import logging
import platform
import subprocess
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DeepLinkError(Exception):
    """Exception raised for deep link errors."""
    pass


class DeepLinkHandler:
    """
    Handler for opening deep links to SaaS applications.
    
    Loads URL patterns from deep_links.json and provides methods to build
    and open URLs using platform-specific commands.
    
    Attributes:
        registry: Dictionary of app configurations from deep_links.json
        registry_path: Path to the deep_links.json file
    """
    
    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize DeepLinkHandler.
        
        Args:
            registry_path: Optional custom path to deep_links.json.
                          Defaults to janus/resources/deep_links.json
        """
        if registry_path is None:
            # Default to resources/deep_links.json
            current_dir = Path(__file__).parent.parent
            registry_path = current_dir / "resources" / "deep_links.json"
        
        self.registry_path = registry_path
        self.registry = self._load_registry()
        
        logger.info(f"DeepLinkHandler initialized with {len(self.registry)} apps")
    
    def _load_registry(self) -> Dict[str, Any]:
        """
        Load deep link registry from JSON file.
        
        Returns:
            Dictionary of app configurations
            
        Raises:
            DeepLinkError: If registry file not found or invalid JSON
        """
        try:
            if not self.registry_path.exists():
                raise DeepLinkError(f"Registry file not found: {self.registry_path}")
            
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if "apps" not in data:
                raise DeepLinkError("Invalid registry format: missing 'apps' key")
            
            return data["apps"]
            
        except json.JSONDecodeError as e:
            raise DeepLinkError(f"Invalid JSON in registry: {e}")
        except Exception as e:
            raise DeepLinkError(f"Failed to load registry: {e}")
    
    def get_supported_apps(self) -> List[str]:
        """
        Get list of supported app names.
        
        Returns:
            List of app names (keys) from registry
        """
        return list(self.registry.keys())
    
    def get_app_info(self, app: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific app.
        
        Args:
            app: App name (case-insensitive)
            
        Returns:
            App configuration dict or None if not found
        """
        app_lower = app.lower()
        return self.registry.get(app_lower)
    
    def build_url(
        self,
        app: str,
        args: Dict[str, Any],
        use_web_fallback: bool = False
    ) -> str:
        """
        Build URL from template and arguments.
        
        Args:
            app: App name (zoom, notion, spotify, etc.)
            args: Dictionary of arguments to substitute in template
            use_web_fallback: If True, use web URL instead of native scheme
            
        Returns:
            Built URL string
            
        Raises:
            DeepLinkError: If app not found or required args missing
        """
        app_config = self.get_app_info(app)
        if not app_config:
            raise DeepLinkError(
                f"Unknown app '{app}'. Supported apps: {', '.join(self.get_supported_apps())}"
            )
        
        # Choose template: web fallback or URL scheme
        if use_web_fallback and app_config.get("web_fallback"):
            template = app_config["web_fallback"]
        else:
            template = app_config["url_scheme"]
        
        # Substitute arguments in template
        try:
            url = template.format(**args)
            return url
        except KeyError as e:
            missing_arg = str(e).strip("'")
            raise DeepLinkError(
                f"Missing required argument '{missing_arg}' for app '{app}'. "
                f"Template: {template}"
            )
    
    def open_url(self, url: str) -> bool:
        """
        Open URL using platform-specific command.
        
        Uses:
        - macOS: 'open' command
        - Windows: 'start' command
        - Linux: 'xdg-open' command
        - Fallback: webbrowser module
        
        Args:
            url: URL to open (can be URL scheme or web URL)
            
        Returns:
            True if successfully opened, False otherwise
        """
        system = platform.system()
        
        try:
            if system == "Darwin":  # macOS
                subprocess.run(
                    ["open", url],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.info(f"Opened URL on macOS: {url}")
                return True
                
            elif system == "Windows":
                # Use 'start' command on Windows
                subprocess.run(
                    ["cmd", "/c", "start", "", url],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.info(f"Opened URL on Windows: {url}")
                return True
                
            elif system == "Linux":
                subprocess.run(
                    ["xdg-open", url],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.info(f"Opened URL on Linux: {url}")
                return True
                
            else:
                # Fallback to webbrowser module
                webbrowser.open(url)
                logger.info(f"Opened URL using webbrowser: {url}")
                return True
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to open URL '{url}': {e}")
            # Try webbrowser as fallback
            try:
                webbrowser.open(url)
                logger.info(f"Opened URL using webbrowser fallback: {url}")
                return True
            except Exception as fallback_error:
                logger.error(f"Webbrowser fallback also failed: {fallback_error}")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error opening URL '{url}': {e}")
            return False
    
    def open_deep_link(
        self,
        app: str,
        args: Dict[str, Any],
        use_web_fallback: bool = False
    ) -> bool:
        """
        Build and open a deep link URL.
        
        This is the main entry point for opening deep links.
        
        Args:
            app: App name (zoom, notion, spotify, etc.)
            args: Dictionary of arguments (id, type, slug, etc.)
            use_web_fallback: If True, use web URL instead of native scheme
            
        Returns:
            True if successfully opened, False otherwise
            
        Raises:
            DeepLinkError: If app not found or required args missing
            
        Examples:
            >>> handler = DeepLinkHandler()
            >>> handler.open_deep_link("zoom", {"id": "123-456-789"})
            True
            >>> handler.open_deep_link("spotify", {"type": "track", "id": "abc123"})
            True
        """
        try:
            # Build URL from template and args
            url = self.build_url(app, args, use_web_fallback)
            logger.info(f"Opening deep link for {app}: {url}")
            
            # Open URL using platform-specific command
            success = self.open_url(url)
            
            if not success:
                raise DeepLinkError(f"Failed to open URL: {url}")
            
            return success
            
        except DeepLinkError:
            # Re-raise DeepLinkError as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise DeepLinkError(f"Unexpected error opening deep link: {e}")


# Singleton instance for convenience
_default_handler: Optional[DeepLinkHandler] = None


def get_deep_link_handler() -> DeepLinkHandler:
    """
    Get the default DeepLinkHandler singleton instance.
    
    Returns:
        Default DeepLinkHandler instance
    """
    global _default_handler
    if _default_handler is None:
        _default_handler = DeepLinkHandler()
    return _default_handler
