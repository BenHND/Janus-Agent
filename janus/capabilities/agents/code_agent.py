"""
CodeAgent - Code Editor Automation

TICKET-AUDIT-002: Adapter layer removed. This agent needs refactoring to atomic operations.
TICKET-ARCH-AGENT: Migrated to use @agent_action decorator for consistency.

Currently marked as deprecated until atomic operations are implemented.

This agent handles code editor operations for VSCode including:
- Opening files
- Navigating to lines  
- Finding text
- Pasting code
- Saving files

NOTE: VSCodeAdapter has been deleted as part of TICKET-AUDIT-002.
This agent needs to be refactored to use atomic OS operations instead.
"""

import asyncio
from typing import Any, Dict

from .base_agent import AgentExecutionError, BaseAgent
from .decorators import agent_action


class CodeAgent(BaseAgent):
    """
    Agent for code editor automation.
    
    TICKET-AUDIT-002: This agent is temporarily degraded due to adapter removal.
    TICKET-ARCH-AGENT: Migrated to use @agent_action decorator.
    Needs refactoring to use atomic operations via OSInterface.
    
    Supported actions:
    - open_file(path: str) - DEGRADED: uses OS open command
    - goto_line(line: int) - NOT IMPLEMENTED
    - find_text(query: str) - NOT IMPLEMENTED
    - paste() - DEGRADED: uses system paste
    - save_file() - DEGRADED: uses Cmd+S keystroke
    """
    
    def __init__(self, provider: str = "vscode"):
        """
        Initialize CodeAgent.
        
        Args:
            provider: Code editor provider ("vscode", "sublime", "atom", "vim")
        """
        super().__init__("code")
        self.provider = provider
        self.vscode_adapter = None  # Removed in TICKET-AUDIT-002
        self.logger.warning("CodeAgent: VSCodeAdapter removed in TICKET-AUDIT-002. Functionality degraded.")
    
    async def execute(
        self,
        action: str,
        args: Dict[str, Any],
        context: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Execute a code editor action by routing to decorated methods."""
        # P2: Dry-run mode - preview without executing
        if dry_run:
            self._log_dry_run_preview(action, args, f"Would execute code editor action '{action}'")
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
        description="Open a file in the code editor (DEGRADED - needs refactoring)",
        required_args=["path"],
        providers=["vscode", "sublime", "atom", "vim"],
        examples=["code.open_file(path='/path/to/file.py')"]
    )
    async def _open_file(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Open a file in the editor."""
        path = args["path"]
        
        if self.vscode_adapter:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.vscode_adapter.execute,
                "open_file",
                {"file_path": path}
            )
            
            if result.get("status") == "success":
                return self._success_result(
                    data={"path": path},
                    context_updates={"surface": "editor"},
                    message=f"Opened file: {path}"
                )
        
        return self._error_result(
            error="VSCode adapter not available",
            recoverable=True
        )
    
    @agent_action(
        description="Navigate to a specific line in the editor (NOT IMPLEMENTED)",
        required_args=["line"],
        providers=["vscode", "sublime", "atom", "vim"],
        examples=["code.goto_line(line=42)"]
    )
    async def _goto_line(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Navigate to a specific line."""
        line = args["line"]
        
        if self.vscode_adapter:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.vscode_adapter.execute,
                "goto_line",
                {"line": line}
            )
            
            if result.get("status") == "success":
                return self._success_result(
                    data={"line": line},
                    message=f"Navigated to line {line}"
                )
        
        return self._error_result(
            error="VSCode adapter not available",
            recoverable=True
        )
    
    @agent_action(
        description="Find text in the editor (NOT IMPLEMENTED)",
        required_args=["query"],
        providers=["vscode", "sublime", "atom", "vim"],
        examples=["code.find_text(query='def main')"]
    )
    async def _find_text(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Find text in the editor."""
        query = args["query"]
        
        if self.vscode_adapter:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.vscode_adapter.execute,
                "find",
                {"query": query}
            )
            
            if result.get("status") == "success":
                return self._success_result(
                    data=result.get("data"),
                    message=f"Found text: {query}"
                )
        
        return self._error_result(
            error="VSCode adapter not available",
            recoverable=True
        )
    
    @agent_action(
        description="Paste from clipboard (DEGRADED - needs refactoring)",
        required_args=[],
        providers=["vscode", "sublime", "atom", "vim"],
        examples=["code.paste()"]
    )
    async def _paste(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Paste from clipboard."""
        if self.vscode_adapter:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.vscode_adapter.execute,
                "paste",
                {}
            )
            
            if result.get("status") == "success":
                return self._success_result(
                    message="Pasted from clipboard"
                )
        
        return self._error_result(
            error="VSCode adapter not available",
            recoverable=True
        )
    
    @agent_action(
        description="Save the current file (DEGRADED - needs refactoring)",
        required_args=[],
        providers=["vscode", "sublime", "atom", "vim"],
        examples=["code.save_file()"]
    )
    async def _save_file(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Save the current file."""
        if self.vscode_adapter:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.vscode_adapter.execute,
                "save",
                {}
            )
            
            if result.get("status") == "success":
                return self._success_result(
                    message="Saved file"
                )
        
        return self._error_result(
            error="VSCode adapter not available",
            recoverable=True
        )
