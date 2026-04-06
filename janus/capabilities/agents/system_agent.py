"""
SystemAgent - Cross-platform System Interactions

TICKET-ARCH-AGENT: Migrated to use @agent_action decorator for consistency.

This agent handles system-level operations including:
- Opening/closing/switching applications
- Keyboard shortcuts and keystrokes
- Text typing
- Deep links to SaaS applications (TICKET-BIZ-003)

Uses SystemBridge for platform-agnostic automation.
CORE-FOUNDATION-003: Consolidated on SystemBridge (official HAL)
TICKET-BIZ-003: Generic Deep Linker for SaaS apps
"""

import asyncio
from typing import Any, Dict, Optional

from .base_agent import AgentExecutionError, BaseAgent
from .decorators import agent_action
from janus.platform.os import get_system_bridge
from janus.platform.os.system_bridge import SystemBridge, SystemBridgeStatus
from janus.platform.os.app_deep_links import DeepLinkError, get_deep_link_handler


class SystemAgent(BaseAgent):
    """
    Agent for system interactions.
    
    TICKET-ARCH-AGENT: Migrated to use @agent_action decorator.
    
    Uses SystemBridge (official HAL) for platform-agnostic operations.
    
    Supported actions:
    - open_application(app_name: str)
    - close_application(app_name: str)
    - switch_application(app_name: str)
    - keystroke(keys: str)
    - shortcut(name: str)
    - type(text: str)
    - open_deep_link(app: str, args: dict) [TICKET-BIZ-003]
    """
    
    def __init__(self, system_bridge: Optional[SystemBridge] = None, provider: str = "native"):
        """
        Initialize SystemAgent.
        
        Args:
            system_bridge: Optional SystemBridge instance. If not provided,
                          uses the default from factory.
            provider: System automation provider ("native", "applescript", "powershell")
        """
        super().__init__("system")
        self.provider = provider
        self._system_bridge = system_bridge
        
        if not self.bridge.is_available():
            self.logger.warning("SystemAgent: SystemBridge not available - limited functionality")
    
    @property
    def bridge(self) -> SystemBridge:
        """Lazy-load SystemBridge."""
        if self._system_bridge is None:
            self._system_bridge = get_system_bridge()
        return self._system_bridge
    
    async def execute(
        self,
        action: str,
        args: Dict[str, Any],
        context: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Execute a system action by routing to decorated methods."""
        # P2: Dry-run mode - preview without executing
        if dry_run:
            self._log_dry_run_preview(action, args, f"Would execute system action '{action}'")
            return {
                "status": "success",
                "data": {"preview": True, "action": action, "args": args},
                "dry_run": True,
                "reversible": False,
                "message": f"[DRY-RUN] Would execute {action}"
            }
        
        # Route to decorated method
        method_name = f"_{action}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return await method(args, context)
        
        # Handle aliases
        if action == "open_app":
            return await self._open_application(args, context)
        else:
            raise AgentExecutionError(
                module=self.agent_name,
                action=action,
                details=f"Unsupported action: {action}",
                recoverable=False
            )
    
    @agent_action(
        description="Open an application",
        required_args=["app_name"],
        providers=["native", "applescript", "powershell"],
        examples=["system.open_application(app_name='Safari')"]
    )
    async def _open_application(
        self,
        args: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Open an application."""
        app_name = args["app_name"]
        
        if self.bridge.is_available():
            # Use SystemBridge to open application
            result = await asyncio.to_thread(
                self.bridge.open_app, app_name, timeout=10.0
            )
            
            if result.success:
                return self._success_result(
                    data={"app_name": app_name},
                    context_updates={"app": app_name},
                    message=f"Opened {app_name}"
                )
            else:
                return self._error_result(
                    error=f"Failed to open {app_name}: {result.error}",
                    recoverable=True
                )
        else:
            return self._error_result(
                error="open_application not available on this platform",
                recoverable=False
            )
    
    @agent_action(
        description="Close an application",
        required_args=["app_name"],
        providers=["native", "applescript", "powershell"],
        examples=["system.close_application(app_name='Safari')"]
    )
    async def _close_application(
        self,
        args: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Close an application."""
        app_name = args["app_name"]
        
        if self.bridge.is_available():
            # Use SystemBridge to close application
            result = await asyncio.to_thread(
                self.bridge.close_app, app_name
            )
            
            if result.success:
                context_updates = {}
                if context.get("app") == app_name:
                    context_updates["app"] = None
                
                return self._success_result(
                    data={"app_name": app_name},
                    context_updates=context_updates if context_updates else None,
                    message=f"Closed {app_name}"
                )
            else:
                return self._error_result(
                    error=f"Failed to close {app_name}: {result.error}",
                    recoverable=True
                )
        else:
            return self._error_result(
                error="close_application not available on this platform",
                recoverable=False
            )
    
    @agent_action(
        description="Switch to an application",
        required_args=["app_name"],
        providers=["native", "applescript", "powershell"],
        examples=["system.switch_application(app_name='Safari')"]
    )
    async def _switch_application(
        self,
        args: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Switch to an application (same as open_application)."""
        return await self._open_application(args, context)
    
    @agent_action(
        description="Get the currently active application",
        required_args=[],
        providers=["native", "applescript", "powershell"],
        examples=["system.get_active_app()"]
    )
    async def _get_active_app(
        self,
        args: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get the active/frontmost application."""
        if self.bridge.is_available():
            result = await asyncio.to_thread(
                self.bridge.get_active_window
            )
            
            if result.success:
                app_name = result.data.get("window", {}).get("app_name", "Unknown")
                return self._success_result(
                    data={"app_name": app_name},
                    message=f"Active app: {app_name}"
                )
            else:
                return self._error_result(
                    error=f"Failed to get active app: {result.error}",
                    recoverable=True
                )
        else:
            return self._error_result(
                error="get_active_app not available on this platform",
                recoverable=False
            )
    
    @agent_action(
        description="Execute a keystroke with optional modifiers",
        required_args=["keys"],
        providers=["native", "applescript", "powershell"],
        examples=[
            "system.keystroke(keys='command l')",
            "system.keystroke(keys='return')"
        ]
    )
    async def _keystroke(
        self,
        args: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a keystroke.
        
        TICKET-FIX-GLOBAL: Fixed modifier parsing to prevent literal typing.
        
        Supports modifier key parsing: if the keys string contains spaces and
        includes modifier names (command, control, option, shift), it will be
        parsed as a key combination. The expected format is:
        "[modifier1] [modifier2] ... <key>"
        
        Examples:
        - "command l" -> sends 'l' with command modifier
        - "command shift t" -> sends 't' with command and shift modifiers
        - "a" -> sends 'a' with no modifiers
        - "return" -> sends 'return' (single key, no modifiers)
        """
        keys = args["keys"]
        
        if self.bridge.is_available():
            # TICKET-FIX-GLOBAL: Parse modifier keys from the keys string
            # Supported modifiers include aliases (cmd, ctrl, alt, fn)
            valid_modifiers = {"command", "cmd", "control", "ctrl", "option", "alt", "shift", "fn"}
            parts = keys.split()
            
            if len(parts) > 1:
                # Separate modifiers and key parts in a single pass
                modifiers = []
                key_parts = []
                for p in parts:
                    if p.lower() in valid_modifiers:
                        modifiers.append(p)
                    else:
                        key_parts.append(p)
                
                if modifiers and key_parts:
                    # We have modifiers and a key - use send_keys with modifiers
                    # Use the last non-modifier as the key to press
                    key = key_parts[-1]
                    result = await asyncio.to_thread(
                        self.bridge.send_keys, key, modifiers
                    )
                else:
                    # No modifiers found or no key found, send as-is
                    result = await asyncio.to_thread(
                        self.bridge.send_keys, keys
                    )
            else:
                # Single key, no modifiers
                result = await asyncio.to_thread(
                    self.bridge.send_keys, keys
                )
            
            if result.success:
                return self._success_result(
                    data={"keys": keys},
                    message=f"Executed keystroke: {keys}"
                )
            else:
                return self._error_result(
                    error=f"Failed to execute keystroke: {result.error}",
                    recoverable=True
                )
        else:
            return self._error_result(
                error="keystroke not available on this platform",
                recoverable=False
            )
    
    @agent_action(
        description="Execute a named shortcut (copy, paste, save, etc.)",
        required_args=["name"],
        providers=["native", "applescript", "powershell"],
        examples=["system.shortcut(name='copy')", "system.shortcut(name='save')"]
    )
    async def _shortcut(
        self,
        args: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a named shortcut."""
        name = args["name"]
        
        # Map common shortcuts to key combinations
        shortcuts_map = {
            "copy": "command c",
            "paste": "command v",
            "cut": "command x",
            "undo": "command z",
            "redo": "command shift z",
            "save": "command s",
            "find": "command f",
            "new": "command n",
            "close": "command w",
            "quit": "command q",
        }
        
        keys = shortcuts_map.get(name.lower())
        
        if not keys:
            return self._error_result(
                error=f"Unknown shortcut '{name}'. Supported shortcuts: {', '.join(shortcuts_map.keys())}",
                recoverable=False
            )
        
        if self.bridge.is_available():
            # Convert to modifiers list and key
            parts = keys.split()
            modifiers = [p for p in parts if p in ["command", "control", "option", "shift"]]
            key = parts[-1]
            
            # Use SystemBridge to send keys with modifiers
            result = await asyncio.to_thread(
                self.bridge.send_keys, key, modifiers
            )
            
            if result.success:
                return self._success_result(
                    data={"name": name, "keys": keys},
                    message=f"Executed shortcut: {name}"
                )
            else:
                return self._error_result(
                    error=f"Failed to execute shortcut: {result.error}",
                    recoverable=True
                )
        else:
            return self._error_result(
                error="shortcut not available on this platform",
                recoverable=False
            )
    
    @agent_action(
        description="Type text at current cursor position",
        required_args=["text"],
        providers=["native", "applescript", "powershell"],
        examples=["system.type(text='Hello World')"]
    )
    async def _type(
        self,
        args: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Type text."""
        text = args["text"]
        
        if self.bridge.is_available():
            # Use SystemBridge to type text
            result = await asyncio.to_thread(
                self.bridge.type_text, text
            )
            
            if result.success:
                return self._success_result(
                    data={"text": text},
                    message=f"Typed text ({len(text)} characters)"
                )
            else:
                return self._error_result(
                    error=f"Failed to type text: {result.error}",
                    recoverable=True
                )
        else:
            return self._error_result(
                error="type not available on this platform",
                recoverable=False
            )
    
    @agent_action(
        description="Open a deep link to a SaaS application",
        required_args=["app"],
        optional_args={"args": {}},
        providers=["native", "applescript", "powershell"],
        examples=["system.open_deep_link(app='salesforce', args={'record_id': '12345'})"]
    )
    async def _open_deep_link(
        self,
        args: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Open a deep link to a SaaS application.
        
        TICKET-BIZ-003: Generic Deep Linker for SaaS apps
        
        This action opens URLs using native app schemes (zoom://, notion://, etc.)
        or web fallbacks, avoiding the need to click through browser dialogs.
        
        Args:
            args: Must contain 'app' (app name) and 'args' (dict of params)
                  Optional: 'use_web_fallback' (bool)
            context: Execution context
            
        Returns:
            Success or error result
            
        Examples:
            args = {"app": "zoom", "args": {"id": "123-456-789"}}
            args = {"app": "spotify", "args": {"type": "track", "id": "abc123"}}
        """
        app_name = args["app"]
        deep_link_args = args.get("args", {})
        use_web_fallback = args.get("use_web_fallback", False)
        
        # Validate that args is a dictionary
        if not isinstance(deep_link_args, dict):
            return self._error_result(
                error=f"'args' must be a dictionary, got {type(deep_link_args).__name__}",
                recoverable=False
            )
        
        try:
            # Get deep link handler and open the link
            handler = get_deep_link_handler()
            
            # Execute in thread to avoid blocking
            success = await asyncio.to_thread(
                handler.open_deep_link,
                app_name,
                deep_link_args,
                use_web_fallback
            )
            
            if success:
                # Build URL for logging (don't fail if this errors)
                try:
                    url = handler.build_url(app_name, deep_link_args, use_web_fallback)
                    url_info = f" ({url})"
                except Exception:
                    url_info = ""
                
                return self._success_result(
                    data={
                        "app": app_name,
                        "args": deep_link_args,
                        "use_web_fallback": use_web_fallback
                    },
                    message=f"Opened deep link for {app_name}{url_info}"
                )
            else:
                return self._error_result(
                    error=f"Failed to open deep link for {app_name}",
                    recoverable=True
                )
                
        except DeepLinkError as e:
            # User-facing errors (app not found, missing args, etc.)
            return self._error_result(
                error=str(e),
                recoverable=False
            )
        except Exception as e:
            # Unexpected errors
            self.logger.error(f"Unexpected error in open_deep_link: {e}", exc_info=True)
            return self._error_result(
                error=f"Unexpected error opening deep link: {str(e)}",
                recoverable=True
            )
