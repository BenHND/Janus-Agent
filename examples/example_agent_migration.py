"""
Example: Migrating an Agent to use @agent_action Decorator

TICKET-ARCH-AGENT: Architecture Agentique - Solution propre, stable et extensible

This example demonstrates how to migrate an existing agent to use the @agent_action
decorator to reduce boilerplate and enable auto-discovery.

BEFORE: Manual validation, logging, and error handling in each method
AFTER: Declarative @agent_action decorator handles all boilerplate
"""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict

from janus.capabilities.agents.base_agent import BaseAgent
from janus.capabilities.agents.decorators import agent_action


# ============================================================================
# BEFORE: Traditional approach with manual boilerplate
# ============================================================================

class FilesAgentOld(BaseAgent):
    """Old-style FilesAgent with manual boilerplate."""
    
    def __init__(self):
        super().__init__("files")
    
    async def execute(self, action: str, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute file operation - needs manual routing."""
        # Manual action routing
        if action == "read_file":
            return await self._read_file(args, context)
        elif action == "write_file":
            return await self._write_file(args, context)
        else:
            return self._error_result(f"Unsupported action: {action}")
    
    async def _read_file(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Read file - LOTS OF BOILERPLATE."""
        import time
        start_time = time.time()
        
        # Manual logging
        self._log_before("read_file", args, context)
        
        try:
            # Manual validation
            if "path" not in args:
                raise ValueError("Missing required argument: path")
            
            path = args["path"]
            
            # Actual logic
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, lambda: Path(path).read_text())
            
            # Manual success result
            result = self._success_result(data={"content": content, "path": path})
            
            # Manual logging
            duration_ms = (time.time() - start_time) * 1000
            self._log_after("read_file", True, duration_ms)
            
            return result
        
        except Exception as e:
            # Manual error handling
            duration_ms = (time.time() - start_time) * 1000
            self._log_after("read_file", False, duration_ms, str(e))
            return self._error_result(f"Failed to read file: {str(e)}")


# ============================================================================
# AFTER: Clean approach with @agent_action decorator
# ============================================================================

class FilesAgentNew(BaseAgent):
    """New-style FilesAgent using @agent_action decorator."""
    
    def __init__(self, provider: str = "local"):
        """
        Initialize FilesAgent.
        
        Args:
            provider: Storage provider ("local", "onedrive", "dropbox", "gdrive", "icloud")
        """
        super().__init__("files")
        self.provider = provider
    
    async def execute(self, action: str, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute file operation.
        
        Note: With @agent_action, we can still keep execute() for routing,
        or we could auto-generate it from decorated methods in the future.
        """
        # Get the method
        method_name = f"_{action}"
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return await method(args, context)
        else:
            return self._error_result(f"Unsupported action: {action}")
    
    @agent_action(
        description="Read contents of a file",
        required_args=["path"],
        optional_args={"encoding": "utf-8"},
        providers=["local", "onedrive", "dropbox", "gdrive", "icloud"],
        examples=[
            "files.read_file(path='/path/to/file.txt')",
            "files.read_file(path='/path/to/file.txt', encoding='latin-1')"
        ]
    )
    async def _read_file(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read file - CLEAN AND SIMPLE.
        
        Decorator handles:
        - Logging before/after
        - Validation of required args
        - Error handling
        - Performance tracking
        - Metadata collection
        """
        path = args["path"]
        encoding = args["encoding"]
        provider = args.get("provider", self.provider)
        
        # Just the actual logic - no boilerplate!
        if provider == "local":
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None, 
                lambda: Path(path).read_text(encoding=encoding)
            )
            return self._success_result(data={"content": content, "path": path})
        else:
            # Future: Handle cloud providers
            return self._error_result(f"Provider '{provider}' not yet implemented")
    
    @agent_action(
        description="Write content to a file",
        required_args=["path", "content"],
        optional_args={"encoding": "utf-8", "create_dirs": True},
        providers=["local", "onedrive", "dropbox", "gdrive", "icloud"],
        examples=[
            "files.write_file(path='/path/to/file.txt', content='Hello World')",
            "files.write_file(path='/path/to/file.txt', content='Data', encoding='utf-8', create_dirs=True)"
        ]
    )
    async def _write_file(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Write to file - CLEAN AND SIMPLE."""
        path = args["path"]
        content = args["content"]
        encoding = args["encoding"]
        create_dirs = args["create_dirs"]
        provider = args.get("provider", self.provider)
        
        if provider == "local":
            loop = asyncio.get_event_loop()
            
            # Create parent directories if needed
            if create_dirs:
                await loop.run_in_executor(None, lambda: Path(path).parent.mkdir(parents=True, exist_ok=True))
            
            # Write file
            await loop.run_in_executor(
                None,
                lambda: Path(path).write_text(content, encoding=encoding)
            )
            
            return self._success_result(data={"path": path, "bytes_written": len(content)})
        else:
            return self._error_result(f"Provider '{provider}' not yet implemented")
    
    @agent_action(
        description="List files in a directory",
        required_args=["path"],
        optional_args={"recursive": False, "pattern": "*"},
        providers=["local", "onedrive", "dropbox", "gdrive", "icloud"],
        examples=[
            "files.list_directory(path='/path/to/dir')",
            "files.list_directory(path='/path/to/dir', recursive=True, pattern='*.py')"
        ]
    )
    async def _list_directory(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """List directory contents - CLEAN AND SIMPLE."""
        path = args["path"]
        recursive = args["recursive"]
        pattern = args["pattern"]
        provider = args.get("provider", self.provider)
        
        if provider == "local":
            loop = asyncio.get_event_loop()
            
            if recursive:
                # Use glob for recursive listing
                entries = await loop.run_in_executor(
                    None,
                    lambda: [str(p) for p in Path(path).rglob(pattern)]
                )
            else:
                # Simple listing
                entries = await loop.run_in_executor(
                    None,
                    lambda: [str(p) for p in Path(path).glob(pattern)]
                )
            
            return self._success_result(data={"entries": entries, "count": len(entries), "path": path})
        else:
            return self._error_result(f"Provider '{provider}' not yet implemented")


# ============================================================================
# COMPARISON
# ============================================================================

async def demo_comparison():
    """Demonstrate the difference between old and new approaches."""
    
    print("=" * 80)
    print("BEFORE: Old-style agent with manual boilerplate")
    print("=" * 80)
    
    old_agent = FilesAgentOld()
    
    # Need to manually validate and handle errors
    result = await old_agent.execute("read_file", {"path": "/tmp/test.txt"}, {})
    print(f"Result: {result}")
    
    print("\n" + "=" * 80)
    print("AFTER: New-style agent with @agent_action decorator")
    print("=" * 80)
    
    new_agent = FilesAgentNew(provider="local")
    
    # Validation, logging, error handling all automatic!
    result = await new_agent.execute("read_file", {"path": "/tmp/test.txt"}, {})
    print(f"Result: {result}")
    
    # Bonus: Auto-discovery works!
    from janus.capabilities.agents.decorators import list_agent_actions
    actions = list_agent_actions(new_agent)
    
    print("\n" + "=" * 80)
    print("BONUS: Auto-discovered actions")
    print("=" * 80)
    
    for action in actions:
        print(f"\n{action.name}:")
        print(f"  Description: {action.description}")
        print(f"  Required: {action.required_args}")
        print(f"  Optional: {action.optional_args}")
        print(f"  Providers: {action.providers}")


# ============================================================================
# MIGRATION CHECKLIST
# ============================================================================

MIGRATION_CHECKLIST = """
MIGRATION CHECKLIST FOR AGENTS
================================

1. Add @agent_action decorator to all action methods
   - Specify description (clear, user-facing)
   - List required_args
   - List optional_args with defaults
   - Specify providers (if multi-provider)
   - Add examples for documentation

2. Remove manual boilerplate from action methods:
   - Remove manual logging (before/after)
   - Remove manual validation (required args)
   - Remove manual error handling (try/catch wrapper)
   - Remove manual performance tracking
   - Keep only the actual business logic

3. Add explicit provider parameter support:
   - Add 'provider' to __init__ with default
   - Store as instance variable
   - Use in action methods when applicable
   - Document supported providers

4. Update execute() method (optional):
   - Simplify to just route to decorated methods
   - Or keep existing logic - decorator is complementary

5. Test the migration:
   - Verify all actions still work
   - Check that metadata is collected
   - Verify auto-discovery finds the agent
   - Generate documentation to review

6. Measure improvements:
   - Lines of code reduced
   - Complexity reduced
   - Time to add new action (should be <30min)
   - Time to add new provider (should be <1h)

Benefits:
- Less boilerplate (30-50% code reduction per action)
- Automatic documentation generation
- Auto-discovery and registration
- Consistent error handling and logging
- Easier testing and debugging
- Faster development (add action in <30min)
"""

if __name__ == "__main__":
    print(MIGRATION_CHECKLIST)
    print("\n")
    asyncio.run(demo_comparison())
