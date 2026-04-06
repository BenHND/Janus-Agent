"""
BrowserAgent - Pure Execution

TICKET-ARCH-AGENT: Migrated to use @agent_action decorator for consistency.

No magic logic. No hardcoded defaults.
It executes what the LLM asks. If the LLM fails args, it errors out.
"""

import logging
from urllib.parse import urlparse
import asyncio
import webbrowser
from typing import Any, Dict

from .base_agent import AgentExecutionError, BaseAgent
from .decorators import agent_action
from janus.platform.os import get_system_bridge
from janus.platform.os.system_bridge import SystemBridgeStatus

logger = logging.getLogger(__name__)

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    logger.warning("trafilatura not available - web content extraction will use basic innerText")

logger = logging.getLogger(__name__)


def _escape_applescript_string(s: str) -> str:
    """
    Escape a string for safe use in AppleScript.
    
    TICKET-ARCHI: Prevents AppleScript injection by escaping special characters.
    
    Args:
        s: String to escape
        
    Returns:
        Escaped string safe for AppleScript
    """
    # Escape backslash first (order matters!)
    s = s.replace('\\', '\\\\')
    # Escape double quotes
    s = s.replace('"', '\\"')
    return s


# On garde la liste pour savoir comment injecter le JS, c'est technique, pas métier.
BROWSER_DIALECTS = {
    "Safari": "webkit",
    "Safari Technology Preview": "webkit",
    "Orion": "webkit",
    "Google Chrome": "chromium",
    "Google Chrome Canary": "chromium",
    "Arc": "chromium",
    "Brave Browser": "chromium",
    "Microsoft Edge": "chromium",
    "Opera": "chromium",
    "Vivaldi": "chromium",
    "Chromium": "chromium",
}

class BrowserAgent(BaseAgent):
    def __init__(self, provider: str = "safari"):
        """
        Initialize BrowserAgent.
        
        Args:
            provider: Browser provider ("safari", "chrome", "firefox", "edge", "arc", "brave")
        """
        super().__init__("browser")
        self.provider = provider
        self.bridge = get_system_bridge()
    
    async def execute(self, action: str, args: Dict[str, Any], context: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """Execute browser action by routing to decorated methods."""
        # P2: Dry-run mode - preview without executing
        if dry_run:
            self._log_dry_run_preview(action, args, f"Would execute browser action '{action}'")
            return {
                "status": "success",
                "data": {"preview": True, "action": action, "args": args},
                "dry_run": True,
                "reversible": False,
                "message": f"[DRY-RUN] Would execute {action}"
            }
        
        if not self.bridge.is_available():
            raise AgentExecutionError(self.agent_name, action, "SystemBridge unavailable")
        
        if args is None: 
            args = {}
        
        # Route to decorated method  
        method_name = f"_{action}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            # Check if method accepts context parameter
            import inspect
            sig = inspect.signature(method)
            if 'context' in sig.parameters:
                return await method(args, context)
            else:
                # Legacy methods without context
                return await method(args)
        else:
            # Handle special cases that map to _run_js
            if action == "click":
                return await self._run_js(args, "click", context)
            elif action == "extract_text":
                return await self._run_js(args, "extract", context)
            else:
                raise AgentExecutionError(self.agent_name, action, f"Unknown action: {action}", recoverable=False)


    @agent_action(
        description="Navigate forward in browser history",
        required_args=[],
        providers=["safari", "chrome", "firefox", "edge", "arc", "brave"],
        examples=["browser.navigate_forward()"]
    )
    async def _navigate_forward(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Navigate forward in history (best-effort)."""
        platform = self.bridge.get_platform_name()
        if platform == "macOS":
            win = self.bridge.get_active_window()
            app = win.data["window"].app_name if win.success else "Safari"
            target_app = app if app in BROWSER_DIALECTS else "Safari"

            script = f'\n            tell application "{target_app}" to activate\n            tell application "System Events"\n                -- Safari/Chromium: Cmd+] is forward\n                keystroke "]" using command down\n            end tell\n            '
            res = self.bridge.run_script(script)
            return self._success_result("Navigated forward") if res.success else self._error_result(f"Navigate forward failed: {res.error}")

        return self._error_result("Navigate forward not supported on this platform")

    @agent_action(
        description="Navigate back in browser history",
        required_args=[],
        providers=["safari", "chrome", "firefox", "edge", "arc", "brave"],
        examples=["browser.navigate_back()"]
    )
    async def _navigate_back(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Navigate back in history (best-effort)."""
        platform = self.bridge.get_platform_name()
        if platform == "macOS":
            win = self.bridge.get_active_window()
            app = win.data["window"].app_name if win.success else "Safari"
            target_app = app if app in BROWSER_DIALECTS else "Safari"

            script = f'\n            tell application "{target_app}" to activate\n            tell application "System Events"\n                -- Safari/Chromium: Cmd+[ is back\n                keystroke "[" using command down\n            end tell\n            '
            res = self.bridge.run_script(script)
            return self._success_result("Navigated back") if res.success else self._error_result(f"Navigate back failed: {res.error}")

        return self._error_result("Navigate back not supported on this platform")

    @agent_action(
        description="Open a new browser tab",
        required_args=[],
        providers=["safari", "chrome", "firefox", "edge", "arc", "brave"],
        examples=["browser.open_tab()"]
    )
    async def _open_tab(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Open a new tab in the active browser (best-effort)."""
        platform = self.bridge.get_platform_name()
        if platform == "macOS":
            win = self.bridge.get_active_window()
            app = win.data["window"].app_name if win.success else "Safari"
            target_app = app if app in BROWSER_DIALECTS else "Safari"

            script = f'''
            tell application "{target_app}"
                activate
                try
                    if "{target_app}" is "Safari" then
                        tell application "System Events" to keystroke "t" using command down
                    else
                        tell application "System Events" to keystroke "t" using command down
                    end if
                on error errMsg
                    return errMsg
                end try
            end tell
            '''
            res = self.bridge.run_script(script)
            return self._success_result("Opened a new tab") if res.success else self._error_result(f"Open tab failed: {res.error}")

        # Fallback: do nothing
        return self._error_result("Open tab not supported on this platform")

    @agent_action(
        description="Close the current browser tab",
        required_args=[],
        providers=["safari", "chrome", "firefox", "edge", "arc", "brave"],
        examples=["browser.close_tab()"]
    )
    async def _close_tab(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Close the current tab (best-effort)."""
        platform = self.bridge.get_platform_name()
        if platform == "macOS":
            win = self.bridge.get_active_window()
            app = win.data["window"].app_name if win.success else "Safari"
            target_app = app if app in BROWSER_DIALECTS else "Safari"

            script = f'''
            tell application "{target_app}" to activate
            tell application "System Events" to keystroke "w" using command down
            '''
            res = self.bridge.run_script(script)
            return self._success_result("Closed current tab") if res.success else self._error_result(f"Close tab failed: {res.error}")

        return self._error_result("Close tab not supported on this platform")

    @agent_action(
        description="Refresh the current browser page",
        required_args=[],
        providers=["safari", "chrome", "firefox", "edge", "arc", "brave"],
        examples=["browser.refresh()"]
    )
    async def _refresh(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Refresh the current page (best-effort)."""
        platform = self.bridge.get_platform_name()
        if platform == "macOS":
            win = self.bridge.get_active_window()
            app = win.data["window"].app_name if win.success else "Safari"
            target_app = app if app in BROWSER_DIALECTS else "Safari"
            script = f'''
            tell application "{target_app}" to activate
            tell application "System Events" to keystroke "r" using command down
            '''
            res = self.bridge.run_script(script)
            return self._success_result("Refreshed page") if res.success else self._error_result(f"Refresh failed: {res.error}")

        return self._error_result("Refresh not supported on this platform")

    @agent_action(
        description="Search using browser's address bar or page search field",
        required_args=["query"],
        providers=["safari", "chrome", "firefox", "edge", "arc", "brave"],
        examples=["browser.search(query='python tutorials')"]
    )
    async def _search(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search using the current tab's address/search bar or page-specific search.
        
        TICKET-ARCHI: Improved to handle page-specific searches (e.g., YouTube)
        and increased delays for page stabilization.
        """
        query = (args.get("query") or args.get("text") or "").strip()
        if not query:
            return self._error_result("ARGUMENT_ERROR: 'query' parameter is missing or empty.")

        platform = self.bridge.get_platform_name()
        if platform == "macOS":
            # TICKET-ARCHI: Check if we're on a known site with page search
            # For YouTube, use direct URL navigation instead of Cmd+L
            system_state = context.get("system_state", {})
            current_url = system_state.get("browser_url", "")
            
            # SECURITY: Use proper URL parsing to avoid URL confusion attacks
            # Check for youtube.com as the actual domain (not just substring)
            if current_url:
                from urllib.parse import urlparse
                try:
                    parsed = urlparse(current_url.lower())
                    # Check if domain is youtube.com or a subdomain (e.g., www.youtube.com)
                    is_youtube = (parsed.netloc == "youtube.com" or 
                                 parsed.netloc.endswith(".youtube.com"))
                except Exception:
                    is_youtube = False
            else:
                is_youtube = False
            
            if is_youtube:
                # Use direct YouTube search URL
                from urllib.parse import quote_plus
                search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
                self.logger.info(f"YouTube detected - using direct search URL: {search_url}")
                
                # Delegate to open_url for navigation
                return await self._open_url({"url": search_url}, context)
            
            # Default: Use address bar search
            win = self.bridge.get_active_window()
            app = win.data["window"].app_name if win.success else "Safari"
            target_app = app if app in BROWSER_DIALECTS else "Safari"

            # Cmd+L focuses address bar, then type, then Enter
            # TICKET-ARCHI: Increased delays for page stabilization:
            # - 0.5s after focus to allow address bar to be ready and prevent autocomplete interference
            # - 0.2s after typing to ensure text is fully entered before pressing Enter
            # TICKET-ARCHI: Properly escape query to prevent AppleScript injection
            query_safe = _escape_applescript_string(query)
            script = f'''
            tell application "{target_app}" to activate
            tell application "System Events"
                keystroke "l" using command down
                delay 0.5
                keystroke "{query_safe}"
                delay 0.2
                key code 36
            end tell
            '''
            res = self.bridge.run_script(script)
            return self._success_result(f"Searched for: {query}") if res.success else self._error_result(f"Search failed: {res.error}")

        return self._error_result("Search not supported on this platform")

    @agent_action(
        description="Open a URL in the browser",
        required_args=["url"],
        providers=["safari", "chrome", "firefox", "edge", "arc", "brave"],
        examples=["browser.open_url(url='https://example.com')"]
    )
    async def _open_url(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        url = args.get("url", "").strip()
        
        # NO HACK. If no URL is provided, it's an LLM error.
        if not url:
            return self._error_result(error="ARGUMENT_ERROR: 'url' parameter is missing or empty.")

        # Minimal protocol cleanup to avoid system errors
        if not url.startswith("http") and "://" not in url:
            url = f"https://{url}"

        logger.info(f"Executing navigation to: {url}")

        # 1. Get the active app to optimize
        win = self.bridge.get_active_window()
        active_app = win.data["window"].app_name if win.success else "Unknown"
        
        platform = self.bridge.get_platform_name()
        
        if platform == "macOS":
            # On privilégie l'app active si c'est un navigateur, sinon Safari
            target_app = active_app if active_app in BROWSER_DIALECTS else "Safari"
            
            # TICKET-ARCHI: Properly escape URL to prevent AppleScript injection
            url_safe = _escape_applescript_string(url)
            
            script = f'''
            tell application "{target_app}"
                activate
                try
                    -- On essaie d'utiliser l'onglet courant
                    if (count of windows) > 0 then
                        set URL of active tab of front window to "{url_safe}"
                    else
                        -- Si pas de fenêtre, on en crée une (specifique Safari vs Chrome)
                        if "{target_app}" is "Safari" then
                            make new document with properties {{URL:"{url_safe}"}}
                        else
                            make new window
                            set URL of active tab of front window to "{url_safe}"
                        end if
                    end if
                on error
                    -- Fallback ultime
                    open location "{url_safe}"
                end try
            end tell
            '''
            # Si c'est Safari, la syntaxe est légèrement différente pour "active tab"
            if target_app == "Safari":
                # TICKET-ARCHI: Properly escape URL to prevent AppleScript injection
                url_safe = _escape_applescript_string(url)
                
                # Extract domain from URL for comparison
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc or parsed.path.split('/')[0]
                except (ValueError, AttributeError, IndexError):
                    domain = ""
                
                # BUG-FIX: Escape domain for AppleScript safety
                domain_safe = _escape_applescript_string(domain) if domain else ""
                
                # BUG-FIX: Check if already on target domain before creating new tab
                # This prevents opening 5 Safari windows for the same YouTube session
                script = f'''
                tell application "Safari"
                    activate
                    try
                        set currentURL to URL of front document
                        if currentURL contains "{domain_safe}" and "{domain_safe}" is not "" then
                            -- Already on target domain, just update URL if different
                            set URL of front document to "{url_safe}"
                        else
                            -- Different domain or no domain match, create new document
                            make new document with properties {{URL:"{url_safe}"}}
                        end if
                    on error
                        -- No document exists, create one
                        make new document with properties {{URL:"{url_safe}"}}
                    end try
                end tell
                '''

            res = self.bridge.run_script(script)
            if res.success:
                return self._success_result(f"Navigated to {url} in {target_app}")
            else:
                return self._error_result(f"Navigation failed: {res.error}")

        # Fallback Linux/Windows
        await asyncio.get_event_loop().run_in_executor(None, webbrowser.open, url)
        return self._success_result(f"Opened {url} (System Default)")

    @agent_action(
        description="Get clean text content from the current web page",
        required_args=[],
        optional_args={"use_trafilatura": True, "structured": False},
        providers=["safari", "chrome", "firefox", "edge", "arc", "brave"],
        examples=["browser.get_page_content()", "browser.get_page_content(use_trafilatura=False)", "browser.get_page_content(structured=True)"]
    )
    async def _get_page_content(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract clean text content from the current web page.
        
        Uses trafilatura for intelligent HTML parsing when available,
        which extracts main content while removing navigation, ads, etc.
        Falls back to simple innerText extraction if trafilatura is not available.
        
        Args:
            use_trafilatura: Whether to use trafilatura for parsing (default: True)
            structured: Whether to return StructuredDocument (default: False for backward compatibility)
        
        Returns:
            Success result with cleaned page content (or StructuredDocument if structured=True)
        """
        use_trafilatura = args.get("use_trafilatura", True)
        structured = args.get("structured", False)
        
        # First, try to get the URL for better extraction
        url = context.get("url") or ""
        
        # If structured output requested, use ContentExtractor
        if structured:
            try:
                from janus.content.extractor import ContentExtractor
                from janus.content.normalizer import ContentNormalizer
                
                extractor = ContentExtractor(system_bridge=self.bridge)
                normalizer = ContentNormalizer()
                
                # Get HTML content
                win = self.bridge.get_active_window()
                if not win.success:
                    return self._error_result("Cannot execute JS: No active window detected")
                
                app = win.data["window"].app_name
                dialect = BROWSER_DIALECTS.get(app)
                
                if dialect:
                    js_html = "document.documentElement.outerHTML"
                    js_safe = js_html.replace('"', '\\"').replace("'", "\\'")
                    
                    if dialect == "webkit":
                        script = f'tell application "{app}" to do JavaScript "{js_safe}" in document 1'
                    elif dialect == "chromium":
                        script = f'tell application "{app}" to execute front window\'s active tab javascript "{js_safe}"'
                    else:
                        return self._error_result("Current browser not supported for structured extraction")
                    
                    res = self.bridge.run_script(script)
                    if res.success:
                        html_content = res.data.get("stdout", "").strip()
                        
                        # Extract structured content
                        doc = extractor.extract_from_web(
                            html=html_content,
                            url=url,
                            use_trafilatura=use_trafilatura
                        )
                        
                        # Normalize
                        doc = normalizer.normalize(doc)
                        
                        logger.info(f"Extracted structured document: {doc.stats.block_count} blocks, {doc.stats.char_count} chars")
                        
                        return self._success_result(
                            data={
                                "document": doc.to_dict(),
                                "markdown": doc.to_markdown(),
                                "stats": doc.stats.to_dict(),
                                "method": "structured_extraction"
                            },
                            message=f"Extracted structured content: {doc.stats.block_count} blocks"
                        )
                    else:
                        return self._error_result(f"Failed to get HTML: {res.error}")
                else:
                    return self._error_result("Current app is not a supported browser")
                    
            except ImportError as e:
                logger.warning(f"ContentExtractor not available: {e}, falling back to plain text")
                # Fall through to regular extraction
            except Exception as e:
                logger.error(f"Structured extraction failed: {e}, falling back to plain text")
                # Fall through to regular extraction
        
        # Regular extraction (backward compatible)
        # If trafilatura is available and enabled, use it for better content extraction
        if TRAFILATURA_AVAILABLE and use_trafilatura:
            # Get the full HTML content
            js_html = "document.documentElement.outerHTML"
            
            win = self.bridge.get_active_window()
            if not win.success:
                return self._error_result("Cannot execute JS: No active window detected")
                
            app = win.data["window"].app_name
            dialect = BROWSER_DIALECTS.get(app)
            
            if not dialect:
                # Fallback to basic extraction if not in a browser
                return await self._run_js(args, "content", context)
            
            # Get HTML via JavaScript
            js_safe = js_html.replace('"', '\\"').replace("'", "\\'")
            
            if dialect == "webkit":  # Safari
                script = f'tell application "{app}" to do JavaScript "{js_safe}" in document 1'
            elif dialect == "chromium":  # Chrome, Brave, Arc...
                script = f'tell application "{app}" to execute front window\'s active tab javascript "{js_safe}"'
            else:
                return await self._run_js(args, "content", context)
            
            res = self.bridge.run_script(script)
            if res.success:
                html_content = res.data.get("stdout", "").strip()
                
                # Use trafilatura to extract clean text
                try:
                    # Extract main content using trafilatura
                    extracted_text = trafilatura.extract(
                        html_content,
                        url=url if url else None,
                        include_comments=False,
                        include_tables=True,
                        no_fallback=False
                    )
                    
                    if extracted_text:
                        return self._success_result(
                            data={"content": extracted_text, "method": "trafilatura"},
                            message=f"Extracted {len(extracted_text)} characters using trafilatura"
                        )
                    else:
                        # Trafilatura returned nothing, fallback to innerText
                        logger.warning("Trafilatura extraction returned no content, falling back to innerText")
                        return await self._run_js(args, "content", context)
                        
                except Exception as e:
                    logger.warning(f"Trafilatura extraction failed: {e}, falling back to innerText")
                    return await self._run_js(args, "content", context)
            else:
                return self._error_result(f"Failed to get HTML: {res.error}")
        
        # Fallback to basic innerText extraction
        return await self._run_js(args, "content", context)

    @agent_action(
        description="Run JavaScript in the browser (internal use)",
        required_args=["selector", "mode"],
        providers=["safari", "chrome", "firefox", "edge", "arc", "brave"],
        examples=["browser._run_js(selector='.btn', mode='click')"]
    )
    async def _run_js(self, args: Dict[str, Any], mode: str, context: Dict[str, Any]) -> Dict[str, Any]:
        selector = args.get("selector", "")
        js = ""
        
        # JS pur, pas de logique pythonique
        if mode == "click":
            js = f"document.querySelector('{selector}') ? (document.querySelector('{selector}').click() || 'clicked') : 'element_not_found'"
        elif mode == "extract":
            js = f"document.querySelector('{selector}') ? document.querySelector('{selector}').innerText : 'element_not_found'"
        elif mode == "content":
            js = "document.body.innerText"

        # On a besoin de savoir à qui parler
        win = self.bridge.get_active_window()
        if not win.success:
            return self._error_result("Cannot execute JS: No active window detected")
            
        app = win.data["window"].app_name
        dialect = BROWSER_DIALECTS.get(app)
        
        if not dialect:
            return self._error_result(f"Current app '{app}' does not support JavaScript injection.")

        script = ""
        # Encapsulation AppleScript
        js_safe = js.replace('"', '\\"').replace("'", "\\'")
        
        if dialect == "webkit": # Safari
            script = f'tell application "{app}" to do JavaScript "{js_safe}" in document 1'
        elif dialect == "chromium": # Chrome, Brave, Arc...
            script = f'tell application "{app}" to execute front window\'s active tab javascript "{js_safe}"'
            
        res = self.bridge.run_script(script)
        if res.success:
            data = res.data.get("stdout", "").strip()
            if "element_not_found" in data:
                return self._error_result(f"Element '{selector}' not found in DOM")
            return self._success_result(data)
            
        return self._error_result(f"JS execution failed: {res.error}")

    @agent_action(
        description="Type text in the browser",
        required_args=["text"],
        providers=["safari", "chrome", "firefox", "edge", "arc", "brave"],
        examples=["browser.type_text(text='Hello World')"]
    )
    async def _type_text(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        text = args.get("text", "")
        if not text: return self._error_result("No text provided")
        
        res = self.bridge.type_text(text)
        return self._success_result(f"Typed {len(text)} chars") if res.success else self._error_result(f"Typing failed: {res.error}")

    @agent_action(
        description="Press a key in the browser",
        required_args=["key"],
        providers=["safari", "chrome", "firefox", "edge", "arc", "brave"],
        examples=["browser.press_key(key='Enter')"]
    )
    async def _press_key(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        keys = args.get("keys", "")
        if not keys: return self._error_result("No keys provided")
        
        res = self.bridge.press_key(keys)
        return self._success_result(f"Pressed {keys}") if res.success else self._error_result(f"Key press failed: {res.error}")