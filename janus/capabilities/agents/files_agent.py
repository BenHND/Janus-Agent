"""
FilesAgent - Atomic File System Operations

TICKET-AUDIT-002: Simplified file agent with atomic operations only.
FinderAdapter merged into this agent - no separate adapter layer.

TICKET-ARCH-AGENT: Migrated to use @agent_action decorator for consistency.

Provides atomic file operations:
- open_path: Open file/folder in system viewer
- read_file: Read file contents
- write_file: Write to file
- move_file: Move/rename file
- copy_file: Copy file
- delete_file: Delete file
- list_directory: List directory contents

No complex workflows, no retry logic - just mechanical operations.
"""

import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

from .base_agent import AgentExecutionError, BaseAgent
from .decorators import agent_action
from janus.safety.path_validator import validate_path, PathValidationError


class FilesAgent(BaseAgent):
    """
    Atomic file system operations agent.
    
    TICKET-AUDIT-002: Merged FinderAdapter logic, kept only atomic operations.
    TICKET-ARCH-AGENT: Migrated to use @agent_action decorator.
    No smart logic, no fallbacks - just direct file operations.
    
    Supported actions:
    - open_path: Open file/folder in OS default app
    - read_file: Read file content
    - write_file: Write content to file  
    - move_file: Move/rename file
    - copy_file: Copy file or directory
    - delete_file: Delete file or directory
    - list_directory: List directory contents
    """
    
    def __init__(self, provider: str = "local"):
        """
        Initialize FilesAgent with atomic operations.
        
        Args:
            provider: Storage provider ("local", "onedrive", "dropbox", "gdrive", "icloud")
        
        Platform detection (is_mac, is_windows, is_linux) inherited from BaseAgent.
        """
        super().__init__("files")
        self.provider = provider
    
    async def execute(
        self,
        action: str,
        args: Dict[str, Any],
        context: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Execute atomic file operation by routing to decorated methods."""
        # P2: Dry-run mode - preview without executing (prevents file deletion/modification)
        if dry_run:
            self._log_dry_run_preview(action, args, f"Would perform file operation '{action}'")
            return {
                "status": "success",
                "data": {"preview": True, "action": action, "args": args},
                "dry_run": True,
                "reversible": action in ["create_file", "write_file", "delete_file", "move_file"],
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
        description="Open file or folder in OS default application",
        required_args=["path"],
        providers=["local", "onedrive", "dropbox", "gdrive", "icloud"],
        examples=["files.open_path(path='/path/to/file')"]
    )
    async def _open_path(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Open file or folder in OS default app."""
        path = args["path"]
        
        # ✅ SECURITY: Validate path to prevent traversal attacks
        try:
            validated_path = validate_path(path, operation="open")
        except PathValidationError as e:
            return self._error_result(
                error=f"SECURITY_ERROR: {str(e)}",
                recoverable=False
            )
        
        # Use OS-specific open command
        # ✅ SECURITY: Avoid shell=True to prevent command injection
        if self.is_mac:
            await asyncio.create_subprocess_exec("open", str(validated_path))
        elif self.is_windows:
            # On Windows, 'start' is a shell builtin, but we can use os.startfile instead
            # However, since we're in async context, we use cmd.exe with proper escaping
            await asyncio.create_subprocess_exec("cmd", "/c", "start", "", str(validated_path))
        else:  # Linux
            await asyncio.create_subprocess_exec("xdg-open", str(validated_path))
        
        return self._success_result(
            data={"path": str(validated_path)},
            context_updates={"surface": "file_browser"},
            message=f"Opened {validated_path}"
        )
    
    # Alias for open_path
    _open_file = _open_path
    
    @agent_action(
        description="Read contents of a text file",
        required_args=["path"],
        optional_args={"encoding": "utf-8"},
        providers=["local", "onedrive", "dropbox", "gdrive", "icloud"],
        examples=["files.read_file(path='/path/to/file.txt')"]
    )
    async def _read_file(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Read file contents."""
        path = args["path"]
        encoding = args["encoding"]
        
        # ✅ SECURITY: Validate path to prevent traversal attacks
        try:
            validated_path = validate_path(path, operation="read")
        except PathValidationError as e:
            return self._error_result(
                error=f"SECURITY_ERROR: {str(e)}",
                recoverable=False
            )
        
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            None, 
            lambda: validated_path.read_text(encoding=encoding)
        )
        return self._success_result(
            data={"content": content, "path": str(validated_path)},
            message=f"Read file: {validated_path}"
        )
    
    @agent_action(
        description="Write content to a file",
        required_args=["path", "content"],
        optional_args={"encoding": "utf-8", "create_dirs": True},
        providers=["local", "onedrive", "dropbox", "gdrive", "icloud"],
        examples=["files.write_file(path='/path/to/file.txt', content='Hello World')"]
    )
    async def _write_file(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Write content to file."""
        path = args["path"]
        content = args["content"]
        encoding = args["encoding"]
        create_dirs = args["create_dirs"]
        
        # ✅ SECURITY: Validate path to prevent traversal attacks
        try:
            validated_path = validate_path(path, operation="write")
        except PathValidationError as e:
            return self._error_result(
                error=f"SECURITY_ERROR: {str(e)}",
                recoverable=False
            )
        
        loop = asyncio.get_event_loop()
        
        # P2: Check if file exists for compensation data
        file_exists = await loop.run_in_executor(None, os.path.exists, str(validated_path))
        backup_content = None
        if file_exists:
            try:
                backup_content = await loop.run_in_executor(
                    None,
                    lambda: validated_path.read_text(encoding=encoding)
                )
            except Exception:
                pass  # If we can't read it, we can't back it up
        
        # Create parent directories if needed
        if create_dirs:
            await loop.run_in_executor(
                None, 
                lambda: validated_path.parent.mkdir(parents=True, exist_ok=True)
            )
        
        await loop.run_in_executor(
            None,
            lambda: validated_path.write_text(content, encoding=encoding)
        )
        
        # P2: Include compensation data for rollback
        result = self._success_result(
            data={"path": str(validated_path)},
            message=f"Wrote to file: {validated_path}"
        )
        result["reversible"] = True
        result["compensation_data"] = {
            "path": str(validated_path),
            "backup_content": backup_content,
            "existed_before": file_exists
        }
        return result
    
    # Alias for write_file
    _save_file = _write_file
    
    @agent_action(
        description="List files and directories in a directory",
        required_args=["path"],
        optional_args={"recursive": False, "pattern": "*"},
        providers=["local", "onedrive", "dropbox", "gdrive", "icloud"],
        examples=["files.list_directory(path='/path/to/dir')"]
    )
    async def _list_directory(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """List directory contents."""
        path = args["path"]
        recursive = args["recursive"]
        pattern = args["pattern"]
        
        # ✅ SECURITY: Validate path to prevent traversal attacks
        try:
            validated_path = validate_path(path, operation="list")
        except PathValidationError as e:
            return self._error_result(
                error=f"SECURITY_ERROR: {str(e)}",
                recoverable=False
            )
        
        loop = asyncio.get_event_loop()
        
        if recursive:
            # Use glob for recursive listing
            entries = await loop.run_in_executor(
                None,
                lambda: [str(p) for p in validated_path.rglob(pattern)]
            )
        else:
            # Simple listing
            entries = await loop.run_in_executor(
                None,
                lambda: [str(p) for p in validated_path.glob(pattern)]
            )
        
        return self._success_result(
            data={"entries": entries, "path": str(validated_path), "count": len(entries)},
            message=f"Listed directory: {validated_path}"
        )
    
    @agent_action(
        description="Move or rename a file or directory",
        required_args=["src", "dest"],
        providers=["local", "onedrive", "dropbox", "gdrive", "icloud"],
        examples=["files.move_file(src='/path/to/source', dest='/path/to/dest')"]
    )
    async def _move_file(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Move/rename file or directory."""
        src, dest = args["src"], args["dest"]
        
        # ✅ SECURITY: Validate both source and destination paths
        try:
            validated_src = validate_path(src, operation="move_from")
            validated_dest = validate_path(dest, operation="move_to")
        except PathValidationError as e:
            return self._error_result(
                error=f"SECURITY_ERROR: {str(e)}",
                recoverable=False
            )
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, shutil.move, str(validated_src), str(validated_dest))
        
        # P2: Include compensation data for rollback
        result = self._success_result(
            data={"src": str(validated_src), "dest": str(validated_dest)},
            message=f"Moved {validated_src} to {validated_dest}"
        )
        result["reversible"] = True
        result["compensation_data"] = {
            "from": str(validated_src),
            "to": str(validated_dest)
        }
        return result
    
    @agent_action(
        description="Copy a file or directory",
        required_args=["src", "dest"],
        providers=["local", "onedrive", "dropbox", "gdrive", "icloud"],
        examples=["files.copy_file(src='/path/to/source', dest='/path/to/dest')"]
    )
    async def _copy_file(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Copy file or directory."""
        src, dest = args["src"], args["dest"]
        
        # ✅ SECURITY: Validate both source and destination paths
        try:
            validated_src = validate_path(src, operation="copy_from")
            validated_dest = validate_path(dest, operation="copy_to")
        except PathValidationError as e:
            return self._error_result(
                error=f"SECURITY_ERROR: {str(e)}",
                recoverable=False
            )
        
        loop = asyncio.get_event_loop()
        is_dir = await loop.run_in_executor(None, os.path.isdir, str(validated_src))
        
        if is_dir:
            await loop.run_in_executor(None, shutil.copytree, str(validated_src), str(validated_dest))
        else:
            await loop.run_in_executor(None, shutil.copy2, str(validated_src), str(validated_dest))
        
        return self._success_result(
            data={"src": str(validated_src), "dest": str(validated_dest)},
            message=f"Copied {validated_src} to {validated_dest}"
        )
    
    @agent_action(
        description="Delete a file or directory",
        required_args=["path"],
        providers=["local", "onedrive", "dropbox", "gdrive", "icloud"],
        examples=["files.delete_file(path='/path/to/file')"]
    )
    async def _delete_file(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Delete file or directory."""
        path = args["path"]
        
        # ✅ SECURITY: Validate path to prevent traversal attacks
        try:
            validated_path = validate_path(path, operation="delete")
        except PathValidationError as e:
            return self._error_result(
                error=f"SECURITY_ERROR: {str(e)}",
                recoverable=False
            )
        
        loop = asyncio.get_event_loop()
        is_dir = await loop.run_in_executor(None, os.path.isdir, str(validated_path))
        
        # P2: Backup content before deletion for compensation
        backup_content = None
        if not is_dir:
            try:
                backup_content = await loop.run_in_executor(
                    None,
                    lambda: validated_path.read_text()
                )
            except Exception:
                pass  # If we can't read it, we can't back it up
        
        if is_dir:
            await loop.run_in_executor(None, shutil.rmtree, str(validated_path))
        else:
            await loop.run_in_executor(None, os.remove, str(validated_path))
        
        # P2: Include compensation data for rollback
        result = self._success_result(
            data={"path": str(validated_path)},
            message=f"Deleted {validated_path}"
        )
        result["reversible"] = not is_dir  # Only files can be restored (not dirs)
        result["compensation_data"] = {
            "path": str(validated_path),
            "backup_content": backup_content,
            "was_dir": is_dir
        }
        return result
    
    @agent_action(
        description="Create a new folder/directory",
        required_args=["path"],
        optional_args={"parents": True, "exist_ok": True},
        providers=["local", "onedrive", "dropbox", "gdrive", "icloud"],
        examples=["files.create_folder(path='/path/to/folder')"]
    )
    async def _create_folder(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a folder/directory."""
        path = args["path"]
        parents = args["parents"]
        exist_ok = args["exist_ok"]
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, 
            lambda: Path(path).mkdir(parents=parents, exist_ok=exist_ok)
        )
        
        return self._success_result(
            data={"path": path},
            message=f"Created folder {path}"
        )
    
    @agent_action(
        description="Search for files matching a query pattern",
        required_args=["query"],
        optional_args={"directory": ".", "recursive": True},
        providers=["local", "onedrive", "dropbox", "gdrive", "icloud"],
        examples=["files.search_files(query='*.py', directory='/path/to/search')"]
    )
    async def _search_files(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Search for files matching a pattern."""
        query = args["query"]
        directory = args["directory"]
        recursive = args["recursive"]
        
        import glob
        loop = asyncio.get_event_loop()
        
        # Use glob to search for files
        if recursive:
            search_pattern = os.path.join(directory, f"**/*{query}*")
            matches = await loop.run_in_executor(
                None,
                lambda: glob.glob(search_pattern, recursive=True)
            )
        else:
            search_pattern = os.path.join(directory, f"*{query}*")
            matches = await loop.run_in_executor(
                None,
                lambda: glob.glob(search_pattern)
            )
        
        return self._success_result(
            data={"matches": matches, "count": len(matches)},
            message=f"Found {len(matches)} matches for '{query}'"
        )
