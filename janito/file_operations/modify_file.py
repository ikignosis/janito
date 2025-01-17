"""
This module provides File modification operations based on line matching and modification.

Operations are performed on the in-memory File and written back to disk if successful.

Supported Operations:
1. Replace: Replace old lines with new lines
2. Delete: Delete sequence of lines matching old_lines
3. Add: Add sequence of new_lines after current_lines
"""
import os
from pathlib import Path
from typing import List, Tuple, Optional, Any
from .models import ChangeType, Change, OperationFailure
from .line_finder import LineFinder, MatchMethod
from rich.console import Console
from rich.table import Table
from dataclasses import dataclass

@dataclass
class QueuedOperation:
    """Represents an operation queued for execution"""
    type: ChangeType
    args: Tuple[Any, ...]
    kwargs: dict

class ModifyFile:
    """Provides methods to modify file content using line matching and modification operations.
    
    The class reads a file into memory, allows modifications through matching and modify operations,
    and can write the changes back to disk.

    Attributes:
        name (Path): Path to the file to modify
        target_dir (Path): Optional target directory for the file
        debug (bool): Whether to print debug information
        changelog (List[Change]): List of changes made to the file
        content (List[str]): Current content of the file as lines
        line_finder: LineFinder: LineFinder instance for line finding operations
        console: Console: Rich console instance for side-by-side diff visualization
        queued_operations: List[QueuedOperation]: List of queued operations
        failed_operations: List[OperationFailure]: List of failed operations
    """

    def __init__(self, name: Path, target_dir: Path):
        """Initialize ModifyFile.
        
        Args:
            name (Path): Path to the file to modify
            target_dir (Path): Target directory for output file
        """
        self.name = Path(name)  # Ensure name is a Path
        self.target_dir = Path(target_dir)  # Ensure target_dir is a Path
        self.debug = os.environ.get('DEBUG', '').lower() in ('true', '1', 't')
        self.changelog: List[Change] = []
        self.content: List[str] = []
        self.line_finder = None  # Will be initialized in prepare()
        self.console = Console()
        self.queued_operations: List[QueuedOperation] = []
        self.failed_operations: List[OperationFailure] = []

    def _debug_print(self, *args, **kwargs):
        """Print debug information only if DEBUG environment variable is set"""
        if self.debug:
            print(*args, **kwargs)

    def _find_lines(self, search_lines: List[str], start_pos: int = 0) -> int:
        """Delegate line finding to LineFinder."""
        return self.line_finder.find_first(search_lines, start_pos)

    def Replace(self, old_lines: str, new_lines: str, new_indent: int = None):
        """Queue a replace operation."""
        self.queued_operations.append(QueuedOperation(
            type=ChangeType.REPLACE,
            args=(old_lines, new_lines),
            kwargs={'new_indent': new_indent}
        ))

    def Modify(self, old_lines: str, new_lines: str, new_indent: int = None):
        """ This is an alias for Replace as LLMs are likely to use it instead of Replace """
        self.Replace(old_lines, new_lines, new_indent)

    def Delete(self, old_lines: str):
        """Queue a delete operation."""
        self.queued_operations.append(QueuedOperation(
            type=ChangeType.DELETE,
            args=(old_lines,),
            kwargs={}
        ))

    def Add(self, new_lines: str, current_lines: str = None, new_indent: int = None):
        """Queue an add operation."""
        self.queued_operations.append(QueuedOperation(
            type=ChangeType.ADD,
            args=(new_lines,),
            kwargs={'current_lines': current_lines, 'new_indent': new_indent}
        ))

    def _execute_delete(self, old_lines: str):
        """Execute a delete operation."""
        old_lines_list = old_lines.splitlines() if old_lines else []
        
        match_result = self._find_lines(old_lines_list)
        if match_result is None:
            self.failed_operations.append(OperationFailure(
                operation_type=ChangeType.DELETE,
                file_path=self.name,
                search_content=old_lines,
                error_message="Lines to delete not found"
            ))
            return False
            
        start = match_result.start_pos
        end = match_result.end_pos
        original = self.content[start:end]
        
        if self.debug:
            self._debug_print(f"\nDeleting lines (matched using {match_result.method.name}):")
            for i, line in enumerate(original):
                self._debug_print(f"  {start+i+1:4d}: {line}")
        
        self.content[start:end] = []
        
        self.changelog.append(Change(
            change_type=ChangeType.DELETE,
            original_content=original,
            new_content=[],
            start_line=start,
            end_line=end
        ))

    def _execute_replace(self, old_lines: str, new_lines: str, new_indent: int = None):
        """Execute a replace operation."""
        old_lines_list = old_lines.splitlines() if old_lines else []
        new_lines_list = new_lines.splitlines() if new_lines else []
        
        # Find the old lines
        match_result = self._find_lines(old_lines_list)
        if match_result is None:
            self.failed_operations.append(OperationFailure(
                operation_type=ChangeType.REPLACE,
                file_path=self.name,
                search_content=old_lines,
                error_message="Lines to replace not found"
            ))
            return False
            
        # Get the range to replace
        start = match_result.start_pos
        end = match_result.end_pos
        original = self.content[start:end]
        
        # Apply indentation if specified
        if new_indent is not None:
            indent = int(new_indent) if isinstance(new_indent, str) else new_indent
            new_lines_list = [' ' * indent + line.lstrip() for line in new_lines_list]
        
        if self.debug:
            # Create table for side-by-side comparison
            table = Table(show_header=True, header_style="bold")
            table.add_column("Before", style="red")
            table.add_column("After", style="green")
            table.add_column("Match Method", style="blue")
            
            # Get the maximum number of lines to show
            max_lines = max(len(original), len(new_lines_list))
            
            # Add rows with line numbers and content
            for i in range(max_lines):
                before = f"{start+i+1:4d}: {original[i]}" if i < len(original) else ""
                after = f"{start+i+1:4d}: {new_lines_list[i]}" if i < len(new_lines_list) else ""
                method = match_result.method.name if i == 0 else ""
                table.add_row(before, after, method)
            
            self._debug_print("\nReplacing content:")
            self.console.print(table)
        
        # Perform the replacement
        self.content[start:end] = new_lines_list
        
        self.changelog.append(Change(
            change_type=ChangeType.REPLACE,
            original_content=original,
            new_content=new_lines_list,
            start_line=start,
            end_line=start + len(new_lines_list)
        ))

    def _execute_add(self, new_lines: str, current_lines: str = None, new_indent: int = None):
        """Execute an add operation."""
        new_lines_list = new_lines.splitlines() if new_lines else []
        
        # Apply indentation if specified
        if new_indent is not None:
            indent = int(new_indent) if isinstance(new_indent, str) else new_indent
            new_lines_list = [' ' * indent + line.lstrip() for line in new_lines_list]
        
        if not current_lines:
            # Add to end of file
            start = end = len(self.content)
            original = []
            
            if self.debug:
                self._debug_print("\nAdding to end of file:")
                for i, line in enumerate(new_lines_list):
                    self._debug_print(f"  {start+i+1:4d}: {line}")
            
            self.content.extend(new_lines_list)
        else:
            # Find the current lines
            current_lines_list = current_lines.splitlines()
            match_result = self._find_lines(current_lines_list)
            if match_result is None:
                self.failed_operations.append(OperationFailure(
                    operation_type=ChangeType.ADD,
                    file_path=self.name,
                    search_content=current_lines,
                    error_message="Lines to add after not found"
                ))
                return False
            
            # Add after the current lines
            start = match_result.start_pos
            end = match_result.end_pos
            original = self.content[start:end]
            
            if self.debug:
                self._debug_print("\nAdding after lines:")
                for i, line in enumerate(original):
                    self._debug_print(f"  {start+i+1:4d}: {line}")
                self._debug_print("\nNew content:")
                for i, line in enumerate(new_lines_list):
                    self._debug_print(f"  {end+i+1:4d}: {line}")
            
            self.content[end:end] = new_lines_list
        
        self.changelog.append(Change(
            change_type=ChangeType.ADD,
            original_content=original,
            new_content=original + new_lines_list,
            start_line=start,
            end_line=end + len(new_lines_list)
        ))

    def prepare(self):
        """Prepare the file for modification by reading its content"""
        full_path = self._get_full_path(self.name)
        with open(full_path, 'r', encoding='utf-8') as file:
            self.content = [line.rstrip('\n') for line in file.readlines()]
        self.line_finder = LineFinder(self.content, self.debug)

    def _get_full_path(self, filename: Path) -> Path:
        """Get the full path to a file in the target directory"""
        return self.target_dir / filename

    def execute(self):
        """Execute all queued operations in the correct order.
        
        Operations are executed in this order:
        1. Deletes - Remove content first
        2. Adds - Add new content
        3. Replaces - Replace existing content
        """
        # Sort operations by type
        operations_by_type = {
            ChangeType.DELETE: [],
            ChangeType.ADD: [],
            ChangeType.REPLACE: []
        }
        
        # Group operations by type
        for op in self.queued_operations:
            operations_by_type[op.type].append(op)
        
        # Execute in specific order
        # 1. Deletes
        for op in operations_by_type[ChangeType.DELETE]:
            self._execute_delete(*op.args, **op.kwargs)
            
        # 2. Adds
        for op in operations_by_type[ChangeType.ADD]:
            self._execute_add(*op.args, **op.kwargs)
            
        # 3. Replaces
        for op in operations_by_type[ChangeType.REPLACE]:
            self._execute_replace(*op.args, **op.kwargs)
        
        # Clear the queue
        self.queued_operations = []
        
        # Write changes to file
        full_path = self._get_full_path(self.name)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        self.write_back(full_path)

    def write_back(self, file_path: Path):
        """Write the modified content back to the file"""
        # Ensure the target directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write('\n'.join(self.content) + '\n')

    def get_changes(self) -> List[Change]:
        """Return the list of changes made to the file."""
        return self.changelog

    def get_failures(self) -> List[OperationFailure]:
        """Return list of failed operations."""
        return self.failed_operations
