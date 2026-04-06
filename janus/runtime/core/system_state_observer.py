"""
SystemStateObserver - System State Observation

Extracted from ActionCoordinator to separate system state observation concerns.
ARCH-004: Returns canonical SystemState instance for consistency.
"""

import logging
import time
from datetime import datetime
from typing import Optional

from janus.runtime.core.contracts import SystemState
from janus.platform.os.system_bridge import SystemBridgeStatus

logger = logging.getLogger(__name__)


class SystemStateObserver:
    """
    Observes current system state via SystemBridge.
    
    ARCH-004: Returns canonical SystemState instances for consistency.
    """
    
    def __init__(self, system_bridge, clipboard_manager=None):
        """
        Initialize SystemStateObserver.
        
        Args:
            system_bridge: SystemBridge instance for system queries
            clipboard_manager: Optional clipboard manager
        """
        self.system_bridge = system_bridge
        self.clipboard_manager = clipboard_manager
    
    async def observe_system_state(self) -> SystemState:
        """
        Capture current system state via SystemBridge.
        
        ARCH-004: Returns canonical SystemState instance for consistency.
        Replaces the old 'os.system_info' which returned url='' for Chrome.
        
        Returns:
            SystemState: Canonical system state snapshot
        """
        start_time = time.time()
        
        # Default values
        active_app = "Unknown"
        window_title = ""
        url = ""
        domain = None
        clipboard = ""
        
        try:
            # 1. Active App & Window Title
            win_res = self.system_bridge.get_active_window()
            if win_res.status == SystemBridgeStatus.SUCCESS and win_res.data.get("window"):
                win = win_res.data["window"]
                active_app = win.app_name
                window_title = win.title
                
                # 2. URL Extraction (Robust)
                # Use platform-specific scripts via bridge
                app_name = win.app_name
                url_script = None
                
                if app_name == "Safari":
                    url_script = 'tell application "Safari" to return URL of front document'
                elif app_name in ["Google Chrome", "Arc", "Brave Browser", "Microsoft Edge"]:
                    url_script = f'tell application "{app_name}" to return URL of active tab of front window'
                
                if url_script:
                    url_res = self.system_bridge.run_script(url_script)
                    if url_res.status == SystemBridgeStatus.SUCCESS:
                        url = url_res.data.get("stdout", "").strip()
                        
                        # BUG-FIX: Handle Safari returning "missing value" for unloaded documents
                        if url == "missing value" or url == "":
                            url = ""
                        
                        # Extract domain from URL
                        if url:
                            domain = self.extract_domain(url)
            
            # 3. Clipboard (via manager if available)
            if self.clipboard_manager:
                clipboard = await self.clipboard_manager.get_text()
                # Limit clipboard to 1000 chars for safety
                clipboard = clipboard[:1000] if clipboard else ""
            
            performance_ms = (time.time() - start_time) * 1000
            
            # ARCH-004: Return canonical SystemState
            system_state = SystemState(
                timestamp=datetime.now().isoformat(),
                active_app=active_app,
                window_title=window_title,
                url=url,
                domain=domain,
                clipboard=clipboard,
                performance_ms=round(performance_ms, 2)
            )
            
            logger.debug(f"👁️ Observed State: App={active_app}, URL={url}")
            return system_state
            
        except Exception as e:
            logger.error(f"Observation failed: {e}")
            # Return default state on error
            performance_ms = (time.time() - start_time) * 1000
            return SystemState(
                timestamp=datetime.now().isoformat(),
                active_app=active_app,
                window_title=window_title,
                url=url,
                domain=domain,
                clipboard=clipboard,
                performance_ms=round(performance_ms, 2)
            )
    
    def extract_domain(self, url: str) -> Optional[str]:
        """
        Extract domain from URL.
        
        Args:
            url: Full URL string
        
        Returns:
            Domain string (e.g., "example.com") or None
        
        Examples:
            >>> extract_domain("https://www.example.com/watch?v=123")
            "example.com"
            >>> extract_domain("http://github.com/user/repo")
            "github.com"
        """
        if not url:
            return None
        
        # Remove protocol
        if "://" in url:
            url = url.split("://", 1)[1]
        
        # Remove path and query
        if "/" in url:
            url = url.split("/", 1)[0]
        
        # Remove port
        if ":" in url:
            url = url.split(":", 1)[0]
        
        # Remove www. prefix
        if url.startswith("www."):
            url = url[4:]
        
        return url if url else None
