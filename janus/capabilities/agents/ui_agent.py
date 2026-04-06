"""
TICKET-AUDIT-002: Adapter layer removed. UIAdapter deleted.
TICKET-ARCH-AGENT: Migrated to use @agent_action decorator for consistency.

UIAgent - Generic UI Interactions and Feedback

This agent handles generic UI operations including:
- Clicking elements (with accessibility-first approach)
- Copy/paste operations
- Highlighting areas
- Showing overlays
- Displaying notifications

NOTE: UIAdapter has been deleted. Vision fallbacks should be removed.
CORE-FOUNDATION-003: Consolidated on SystemBridge (official HAL)
Uses SystemBridge for platform-agnostic UI operations.

PHASE-2: Accessibility Integration
Uses accessibility API for faster, more reliable element finding.
Falls back to vision when accessibility is unavailable.
"""

import asyncio
import time
from typing import Any, Dict, Optional

from .base_agent import AgentExecutionError, BaseAgent
from .decorators import agent_action
from janus.platform.os import get_system_bridge
from janus.platform.os.system_bridge import SystemBridge
from janus.platform.accessibility import AccessibilityRole


class UIAgent(BaseAgent):
    """
    Agent for generic UI interactions and feedback.
    
    TICKET-ARCH-AGENT: Migrated to use @agent_action decorator.
    
    Uses SystemBridge (official HAL) for platform-agnostic OS interactions.
    
    Supported actions:
    - click(selector: str | text: str)
    - copy()
    - paste()
    - highlight_area(area: dict)
    - overlay(message: str)
    - notify(message: str)
    """
    
    def __init__(self, system_bridge: Optional[SystemBridge] = None, provider: str = "native"):
        """
        Initialize UIAgent.
        
        Args:
            system_bridge: Optional SystemBridge instance. If not provided,
                          uses the default from factory.
            provider: UI automation provider ("native", "accessibility", "vision")
        """
        super().__init__("ui")
        self.provider = provider
        self._system_bridge = system_bridge
    
    @property
    def bridge(self) -> SystemBridge:
        """Lazy-load SystemBridge."""
        if self._system_bridge is None:
            self._system_bridge = get_system_bridge()
        return self._system_bridge
    
    def _map_role_to_enum(self, role: Optional[str]) -> Optional[AccessibilityRole]:
        """Map string role to AccessibilityRole enum."""
        if not role:
            return None
        
        role_map = {r.value: r for r in AccessibilityRole}
        return role_map.get(role.lower())
    
    def _is_accessibility_available(self) -> bool:
        """Check if accessibility API is available."""
        backend = self.bridge.get_accessibility_backend()
        return backend is not None and backend.is_available()

    async def execute(
        self,
        action: str,
        args: Dict[str, Any],
        context: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Execute a UI action by routing to decorated methods."""
        # P2: Dry-run mode - preview without executing UI actions
        if dry_run:
            self._log_dry_run_preview(action, args, f"Would perform UI action '{action}'")
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
        else:
            raise AgentExecutionError(
                module=self.agent_name,
                action=action,
                details=f"Unsupported action: {action}",
                recoverable=False
            )
    
    @agent_action(
        description="Click an element on the screen",
        required_args=[],
        optional_args={"selector": None, "text": None, "target": None, "element_id": None, "role": None},
        providers=["native", "accessibility", "vision"],
        examples=["ui.click(text='Submit')", "ui.click(selector='#button1')", "ui.click(element_id='elem_123')"]
    )
    async def _click(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Click an element with robust error handling and timeout.
        
        PHASE-2: Accessibility-first approach (3-5x faster than vision)
        1. Try accessibility API first (10-100ms)
        2. Fall back to fast-path SOM if available
        3. Fall back to VisionActionMapper as last resort
        
        TICKET-4: Fast-path for element_id clicks - bypass VisionActionMapper when possible.
        When element_id is provided and resolves in SOM, click directly via SystemBridge.
        This reduces latency from 10s+ to <300ms (excluding screenshot).
        """
        selector = args.get("selector")
        text = args.get("text") or args.get("target")  # Support both 'text' and 'target' params
        element_id = args.get("element_id")
        role = args.get("role")  # NEW: role parameter for accessibility
        
        if not selector and not text and not element_id:
            return self._error_result(
                error="Either 'selector', 'text', 'target', 'element_id', or 'role' required for click",
                recoverable=False
            )
        
        # PHASE-2: Try accessibility API first (FASTEST - 10-100ms)
        if text and self._is_accessibility_available():
            start_time = time.time()
            
            try:
                self.logger.info(f"ACCESSIBILITY: Attempting to click '{text}' with role={role}")
                
                # Use SystemBridge convenience method
                result = await asyncio.to_thread(
                    self.bridge.click_ui_element,
                    name=text,
                    role=role,
                    timeout=2.0  # Quick timeout for accessibility
                )
                
                duration_ms = (time.time() - start_time) * 1000
                
                if result.success:
                    self.logger.info(
                        f"ACCESSIBILITY: Clicked '{text}' successfully in {duration_ms:.0f}ms"
                    )
                    return self._success_result(
                        message=f"Clicked '{text}' via accessibility ({duration_ms:.0f}ms)",
                        data={"method": "accessibility", "duration_ms": duration_ms}
                    )
                else:
                    self.logger.debug(
                        f"ACCESSIBILITY: Failed to click '{text}': {result.error}. Falling back to vision."
                    )
                    # Fall through to next method
                    
            except Exception as e:
                self.logger.debug(f"ACCESSIBILITY: Exception: {e}. Falling back to vision.")
                # Fall through to next method
        
        # TICKET-4: FAST-PATH - Direct click via SystemBridge when element_id resolves in SOM
        if element_id:
            start_time = time.time()
            som_engine = context.get("vision_engine")
            
            if som_engine and som_engine.is_available():
                try:
                    # Try to resolve element_id from SOM cache
                    som_element = som_engine.get_element_by_id(element_id)
                    
                    if som_element:
                        # Element found in SOM - click directly without OCR/VisionActionMapper
                        self.logger.info(f"FAST-PATH: Resolved element_id '{element_id}' from SOM cache")
                        
                        # Calculate click coordinates from bbox (center)
                        x, y, width, height = som_element.bbox
                        click_x = x + width // 2
                        click_y = y + height // 2
                        
                        # Click via SystemBridge
                        click_result = await asyncio.to_thread(
                            self.bridge.click, click_x, click_y
                        )
                        
                        duration_ms = (time.time() - start_time) * 1000
                        
                        if click_result.success:
                            self.logger.info(
                                f"FAST-PATH: Clicked in {duration_ms:.0f}ms at ({click_x}, {click_y})"
                            )
                            return self._success_result(
                                message=f"Clicked element '{element_id}' at ({click_x}, {click_y}) (fast-path: {duration_ms:.0f}ms)",
                                data={"method": "som_fast_path", "duration_ms": duration_ms}
                            )
                        else:
                            self.logger.warning(f"SystemBridge click failed: {click_result.error}")
                            # Fall through to VisionActionMapper fallback
                    else:
                        self.logger.debug(f"Element ID '{element_id}' not found in SOM cache, using fallback")
                        # Fall through to VisionActionMapper fallback
                        
                except Exception as e:
                    self.logger.warning(f"Fast-path click failed: {e}, falling back to VisionActionMapper")
                    # Fall through to VisionActionMapper fallback
        
        # FALLBACK: Use VisionActionMapper for text-based search or when fast-path fails
        target_name = element_id or text or selector
        timeout_seconds = 10
        
        self.logger.info(f"Using VisionActionMapper to click: {target_name}")
        try:
            from janus.vision.vision_action_mapper import VisionActionMapper
            
            # Get the SOM engine from context (passed by ActionCoordinator._act)
            som_engine = context.get("vision_engine")
            
            loop = asyncio.get_event_loop()
            mapper = VisionActionMapper(som_engine=som_engine)
            
            # Use click_viz method from VisionActionMapper with timeout
            # VISION-FOUNDATION-001: Pass element_id explicitly for better handling
            try:
                vam_result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        mapper.click_viz,
                        target_name,
                        None,  # region
                        True,  # verify
                        element_id  # Pass element_id for SOM lookup
                    ),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                self.logger.warning(f"VAM click timed out after {timeout_seconds}s")
                return self._error_result(
                    error=f"Click timed out: Could not find '{target_name}' within {timeout_seconds}s. The text may not be visible on screen.",
                    recoverable=True
                )
            
            if vam_result.success:
                return self._success_result(
                    message=f"Clicked (VAM): {target_name}",
                    data={"method": "vision"}
                )
            else:
                # Graceful failure with helpful message
                return self._error_result(
                    error=f"Could not find '{target_name}' on screen. Try a different search term or scroll the page.",
                    recoverable=True
                )
        except Exception as e:
            self.logger.error(f"VAM fallback failed: {e}")
            return self._error_result(
                error=f"Click failed for '{target_name}': {e}. The element may not be visible.",
                recoverable=True
            )
    
    @agent_action(
        description="Copy selected content to clipboard",
        required_args=[],
        providers=["native", "accessibility"],
        examples=["ui.copy()"]
    )
    async def _copy(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Copy to clipboard using SystemBridge."""
        if self.bridge.is_available():
            # SystemBridge handles platform-specific modifiers
            # On macOS: Cmd+C, on Windows/Linux: Ctrl+C
            platform_name = self.bridge.get_platform_name()
            modifier = "command" if platform_name == "macOS" else "control"
            
            result = await asyncio.to_thread(
                self.bridge.press_key, "c", [modifier]
            )
            
            if result.success:
                return self._success_result(
                    message="Copied to clipboard"
                )
            else:
                return self._error_result(
                    error=f"Failed to copy: {result.error}",
                    recoverable=True
                )
        else:
            return self._error_result(
                error="Copy not available on this platform",
                recoverable=False
            )
    
    @agent_action(
        description="Paste from clipboard",
        required_args=[],
        providers=["native", "accessibility"],
        examples=["ui.paste()"]
    )
    async def _paste(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Paste from clipboard using SystemBridge."""
        if self.bridge.is_available():
            # SystemBridge handles platform-specific modifiers
            # On macOS: Cmd+V, on Windows/Linux: Ctrl+V
            platform_name = self.bridge.get_platform_name()
            modifier = "command" if platform_name == "macOS" else "control"
            
            result = await asyncio.to_thread(
                self.bridge.press_key, "v", [modifier]
            )
            
            if result.success:
                return self._success_result(
                    message="Pasted from clipboard"
                )
            else:
                return self._error_result(
                    error=f"Failed to paste: {result.error}",
                    recoverable=True
                )
        else:
            return self._error_result(
                error="Paste not available on this platform",
                recoverable=False
            )
    
    @agent_action(
        description="Type text at cursor position",
        required_args=["text"],
        providers=["native", "accessibility"],
        examples=["ui.type(text='Hello World')"]
    )
    async def _type(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Type text using SystemBridge."""
        text = args["text"]
        
        if self.bridge.is_available():
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
                error="Type not available on this platform",
                recoverable=False
            )
    
    @agent_action(
        description="Extract text from the active application window",
        required_args=[],
        optional_args={"app_name": None, "structured": False},
        providers=["native", "accessibility"],
        examples=["ui.extract_text()", "ui.extract_text(app_name='Notes')", "ui.extract_text(structured=True)"]
    )
    async def _extract_text(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text from the active application window using Accessibility APIs.
        
        This is a generic action that works with native apps (Notes, TextEdit, etc.)
        by accessing their accessibility tree to extract visible text content.
        
        Args:
            app_name: Optional specific app name to extract from (uses active window if not specified)
            structured: Whether to return StructuredDocument (default: False for backward compatibility)
        
        Returns:
            Success result with extracted text content (or StructuredDocument if structured=True)
        """
        app_name = args.get("app_name")
        structured = args.get("structured", False)
        
        # Get active window info
        win = self.bridge.get_active_window()
        active_app_name = "Unknown"
        window_title = ""
        if win.success:
            win_data = win.data.get("window", {})
            # Use getattr with defaults for safer attribute access
            if isinstance(win_data, dict):
                active_app_name = win_data.get("app_name", "Unknown")
                window_title = win_data.get("title", "")
            else:
                active_app_name = getattr(win_data, 'app_name', "Unknown")
                window_title = getattr(win_data, 'title', "")
        
        extracted_text = None
        extraction_method = None
        
        # Try accessibility API first (fastest and most reliable)
        if self._is_accessibility_available():
            try:
                backend = self.bridge.get_accessibility_backend()
                
                # Get the active window element
                if app_name:
                    # TODO: Find specific app window
                    self.logger.debug(f"Specific app extraction for '{app_name}' not yet implemented, using active window")
                
                # Use accessibility to extract text
                result = await asyncio.to_thread(
                    backend.get_window_text
                )
                
                if result and result.success:
                    extracted_text = result.data.get("text", "")
                    extraction_method = "accessibility"
                    
            except Exception as e:
                self.logger.warning(f"Accessibility extraction failed: {e}, trying clipboard fallback")
        
        # Fallback: Use Cmd+A + Cmd+C to copy all text to clipboard
        if not extracted_text and self.bridge.is_available():
            try:
                platform_name = self.bridge.get_platform_name()
                modifier = "command" if platform_name == "macOS" else "control"
                
                # Select all (Cmd+A / Ctrl+A)
                select_result = await asyncio.to_thread(
                    self.bridge.press_key, "a", [modifier]
                )
                
                if not select_result.success:
                    return self._error_result(
                        error=f"Failed to select all: {select_result.error}",
                        recoverable=True
                    )
                
                # Small delay to ensure selection completes
                await asyncio.sleep(0.1)
                
                # Copy (Cmd+C / Ctrl+C)
                copy_result = await asyncio.to_thread(
                    self.bridge.press_key, "c", [modifier]
                )
                
                if not copy_result.success:
                    return self._error_result(
                        error=f"Failed to copy: {copy_result.error}",
                        recoverable=True
                    )
                
                # Small delay to ensure copy completes
                await asyncio.sleep(0.1)
                
                # Get clipboard content
                clipboard_result = await asyncio.to_thread(
                    self.bridge.get_clipboard_text
                )
                
                if clipboard_result.success:
                    extracted_text = clipboard_result.data.get("text", "")
                    extraction_method = "clipboard"
                    
            except Exception as e:
                return self._error_result(
                    error=f"Text extraction failed: {str(e)}",
                    recoverable=True
                )
        
        if not extracted_text:
            return self._error_result(
                error="Text extraction failed: No text could be extracted",
                recoverable=False
            )
        
        # If structured output requested, convert to StructuredDocument
        if structured:
            try:
                from janus.content.extractor import ContentExtractor
                from janus.content.normalizer import ContentNormalizer
                
                extractor = ContentExtractor(system_bridge=self.bridge)
                normalizer = ContentNormalizer()
                
                # Extract structured content from plain text
                doc = extractor.extract_from_plain_text(
                    text=extracted_text,
                    source="app",
                    app_name=active_app_name,
                    window_title=window_title
                )
                
                # Normalize
                doc = normalizer.normalize(doc)
                
                self.logger.info(f"Extracted structured document from {active_app_name}: {doc.stats.block_count} blocks")
                
                return self._success_result(
                    data={
                        "document": doc.to_dict(),
                        "markdown": doc.to_markdown(),
                        "stats": doc.stats.to_dict(),
                        "method": f"structured_{extraction_method}"
                    },
                    message=f"Extracted structured content from {active_app_name}: {doc.stats.block_count} blocks"
                )
                
            except ImportError as e:
                self.logger.warning(f"ContentExtractor not available: {e}, returning plain text")
                # Fall through to plain text return
            except Exception as e:
                self.logger.error(f"Structured extraction failed: {e}, returning plain text")
                # Fall through to plain text return
        
        # Return plain text (backward compatible)
        return self._success_result(
            data={"text": extracted_text, "app": active_app_name, "method": extraction_method},
            message=f"Extracted {len(extracted_text)} characters from {active_app_name}"
        )
    
    @agent_action(
        description="Highlight an area on the screen",
        required_args=["x", "y", "width", "height"],
        providers=["native"],
        examples=["ui.highlight_area(x=100, y=200, width=300, height=150)"]
    )
    async def _highlight_area(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Highlight a screen area."""
        x = args["x"]
        y = args["y"]
        width = args["width"]
        height = args["height"]
        
        # TODO: Implement screen area highlighting
        return self._error_result(
            error="highlight_area not yet implemented",
            recoverable=False
        )
    
    @agent_action(
        description="Show an overlay message on screen",
        required_args=["message"],
        providers=["native"],
        examples=["ui.overlay(message='Processing...')"]
    )
    async def _overlay(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Show an overlay message."""
        message = args["message"]
        
        # TODO: Integrate with overlay UI
        return self._success_result(
            data={"message": message},
            message=f"Overlay: {message}"
        )
    
    @agent_action(
        description="Show a system notification",
        required_args=["title", "message"],
        providers=["native"],
        examples=["ui.notify(title='Task Complete', message='Your task has finished')"]
    )
    async def _notify(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Show a system notification."""
        title = args["title"]
        message = args["message"]
        
        try:
            if self.bridge.is_available():
                # Use SystemBridge to show notification
                result = await asyncio.to_thread(
                    self.bridge.show_notification, message, title
                )
                
                if result.success:
                    return self._success_result(
                        data={"title": title, "message": message},
                        message=f"Notification sent: {title}"
                    )
                else:
                    return self._error_result(
                        error=f"Failed to send notification: {result.error}",
                        recoverable=True
                    )
            else:
                return self._error_result(
                    error="Notifications not available on this platform",
                    recoverable=False
                )
        except Exception as e:
            return self._error_result(
                error=f"Failed to send notification: {str(e)}",
                recoverable=True
            )
    
    # ========== Helper Methods for Accessibility (PHASE-2) ==========
    
    async def click_button(self, label: str, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Helper: Click a button by label using accessibility-first approach.
        
        Args:
            label: Button text/label
            timeout: Maximum wait time
            
        Returns:
            Result dict with status and method used
        """
        return await self._click(
            {"target": label, "role": "button"},
            {}
        )
    
    async def fill_text_field(self, label: str, value: str) -> Dict[str, Any]:
        """
        Helper: Fill a text field using accessibility.
        
        Finds the field by label and sets its value directly (much faster than typing).
        Falls back to click + type if accessibility unavailable.
        
        Args:
            label: Text field label
            value: Value to set
            
        Returns:
            Result dict with status
        """
        if self._is_accessibility_available():
            try:
                backend = self.bridge.get_accessibility_backend()
                
                # Find text field
                role_enum = self._map_role_to_enum("text_field")
                element = await asyncio.to_thread(
                    backend.find_element,
                    name=label,
                    role=role_enum,
                    timeout=2.0
                )
                
                if element:
                    # Focus and set value directly
                    await asyncio.to_thread(backend.focus_element, element)
                    result = await asyncio.to_thread(backend.set_value, element, value)
                    
                    if result.success:
                        return self._success_result(
                            message=f"Filled '{label}' with '{value}' (accessibility)",
                            data={"method": "accessibility"}
                        )
            except Exception as e:
                self.logger.debug(f"Accessibility fill failed: {e}, using fallback")
        
        # Fallback: click field then type
        click_result = await self._click({"target": label, "role": "text_field"}, {})
        if not click_result.get("status") == "success":
            return click_result
        
        return await self._type({"text": value}, {})
    
    async def verify_element_state(
        self,
        label: str,
        role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Helper: Check element state (enabled, visible, focused) via accessibility.
        
        Much faster than OCR-based state checking (3ms vs 200ms).
        
        Args:
            label: Element label
            role: Element role (optional)
            
        Returns:
            Result dict with state information
        """
        if not self._is_accessibility_available():
            return self._error_result(
                error="Accessibility not available for state checking",
                recoverable=True
            )
        
        try:
            backend = self.bridge.get_accessibility_backend()
            role_enum = self._map_role_to_enum(role) if role else None
            
            element = await asyncio.to_thread(
                backend.find_element,
                name=label,
                role=role_enum,
                timeout=2.0
            )
            
            if not element:
                return self._error_result(
                    error=f"Element '{label}' not found",
                    recoverable=True
                )
            
            # Get element state
            states = await asyncio.to_thread(backend.get_element_state, element)
            
            return self._success_result(
                message=f"Retrieved state for '{label}'",
                data={
                    "enabled": element.is_enabled(),
                    "visible": element.is_visible(),
                    "focused": element.is_focused(),
                    "bounds": element.bounds,
                    "states": [s.value for s in states]
                }
            )
            
        except Exception as e:
            return self._error_result(
                error=f"Failed to get element state: {str(e)}",
                recoverable=True
            )
