"""
This module provides File modification operations based on line selection and modification.

Operations are performed on the in-memory File and written back to disk if successful.

Supported Operations:
1. Select Between: Select lines between (but not including) start and end lines
2. Select Over: Select lines between and including start and end lines  
3. Select Exact: Select lines matching exact content

Each selection can be followed by:
- Delete: Remove selected lines
- Replace: Replace selected lines with new content
- Insert: Insert new content before selected lines  
- Append: Append new content after selected lines
"""
import os
from pathlib import Path
from typing import List, Tuple
from .models import ChangeType, Change
from .line_finder import LineFinder

class ModifyFile:
    """Provides methods to modify file content using line selection and modification operations.
    
    The class reads a file into memory, allows modifications through select and modify operations,
    and can write the changes back to disk.

    Attributes:
        name (Path): Path to the file to modify
        target_dir (Path): Optional target directory for the file
        debug (bool): Whether to print debug information
        changelog (List[Change]): List of changes made to the file
        content (List[str]): Current content of the file as lines
        selected_range: Tuple[int, int]: Currently selected line range (start, end)
        line_finder: LineFinder: LineFinder instance for line finding operations
    """

    def __init__(self, name: Path, target_dir: Path):
        self.name = Path(name)
        self.target_dir = Path(target_dir) if target_dir else None
        self.debug = os.environ.get('DEBUG', '').lower() in ('true', '1', 't')
        self.changelog: List[Change] = []
        self.content: List[str] = []
        self.selected_range: Tuple[int, int] = None
        self.line_finder = None  # Will be initialized in prepare()

    def _debug_print(self, *args, **kwargs):
        """Print debug information only if DEBUG environment variable is set"""
        if self.debug:
            print(*args, **kwargs)

    def _find_lines(self, search_lines: List[str], start_pos: int = 0) -> int:
        """Delegate line finding to LineFinder."""
        return self.line_finder.find_first(search_lines, start_pos)

    def _update_selected_range(self, new_range: Tuple[int, int], operation: str):
        """Update selected range and log the change if in debug mode."""
        old_range = self.selected_range
        self.selected_range = new_range
        
        if self.debug:
            if new_range is None:
                self._debug_print(f"\nSelection cleared by {operation}")
                if old_range:
                    self._debug_print(f"Previous selection was lines {old_range[0] + 1} to {old_range[1]}")
            else:
                self._debug_print(f"\nSelection changed by {operation}")
                if old_range:
                    self._debug_print(f"Previous: lines {old_range[0] + 1} to {old_range[1]}")
                self._debug_print(f"New: lines {new_range[0] + 1} to {new_range[1]}")
                self._debug_print("Selected content:")
                for i in range(new_range[0], new_range[1]):
                    self._debug_print(f"  {i+1:4d}: {self.content[i]}")

    def SelectBetween(self, start_lines: str, end_lines: str):
        """Select lines between (not including) start_lines and end_lines."""
        start_lines_list = start_lines.splitlines() if start_lines else []
        end_lines_list = end_lines.splitlines() if end_lines else []
        
        # Try to find a valid start/end combination
        start_pos = 0
        while True:
            start_pos = self._find_lines(start_lines_list, start_pos)
            if start_pos == -1:
                raise ValueError(f"Start lines not found:\n{start_lines}")
            
            # Search for end_lines from the start position, not after it
            end_pos = self._find_lines(end_lines_list, start_pos)
            if end_pos != -1:
                # Found a valid combination
                self._update_selected_range(
                    (start_pos + len(start_lines_list), end_pos),
                    "SelectBetween"
                )
                return
            
            # Try next occurrence of start_lines
            start_pos += 1
            if start_pos >= len(self.content):
                raise ValueError(f"End lines not found after start lines:\nStart lines:\n{start_lines}\nEnd lines:\n{end_lines}")

    def SelectOver(self, start_lines: str, end_lines: str = None):
        """Select lines between and including start_lines and end_lines.
        If end_lines is not provided, selects only the start_lines."""
        start_lines_list = start_lines.splitlines() if start_lines else []
        
        # Find start position
        start_pos = self._find_lines(start_lines_list)
        if start_pos == -1:
            raise ValueError(f"Start lines not found:\n{start_lines}")
            
        if not end_lines:
            # If no end_lines provided, select only the start_lines
            self._update_selected_range(
                (start_pos, start_pos + len(start_lines_list)),
                "SelectOver"
            )
            return
            
        # Try to find a valid end position from the start position
        end_lines_list = end_lines.splitlines()
        end_pos = self._find_lines(end_lines_list, start_pos)
        if end_pos == -1:
            raise ValueError(f"End lines not found after start lines:\nStart lines:\n{start_lines}\nEnd lines:\n{end_lines}")
            
        # Found a valid combination
        self._update_selected_range(
            (start_pos, end_pos + len(end_lines_list)),
            "SelectOver"
        )

    def SelectExact(self, lines: str):
        """Select lines matching exact content."""
        lines_list = lines.splitlines() if lines else []
        pos = self._find_lines(lines_list)
        if pos == -1:
            raise ValueError(f"Exact lines not found:\n{lines}")
        self._update_selected_range(
            (pos, pos + len(lines_list)),
            "SelectExact"
        )

    def Delete(self):
        """Delete the currently selected lines."""
        if not self.selected_range:
            raise ValueError("No lines selected for Delete operation. Call a Select method first.")
            
        start, end = self.selected_range
        original = self.content[start:end]
        self.content[start:end] = []
        
        # Clear selection after delete since content no longer exists
        self._update_selected_range(None, "Delete")
        
        self.changelog.append(Change(
            change_type=ChangeType.DELETE,
            original_content=original,
            new_content=[],
            start_line=start,
            end_line=end
        ))

    def Replace(self, new_content: str, new_indent: int = None):
        """Replace the currently selected lines with new content."""
        if not self.selected_range:
            raise ValueError(f"No lines selected for Replace operation. Call a Select method first.\nNew content that would be used:\n{new_content}")
            
        start, end = self.selected_range
        original = self.content[start:end]
        
        # Split and optionally indent the new content
        content_list = new_content.splitlines() if new_content else []
        if new_indent is not None:
            # Convert new_indent to int if it's a string
            indent = int(new_indent) if isinstance(new_indent, str) else new_indent
            content_list = [' ' * indent + line.lstrip() for line in content_list]
        
        self.content[start:end] = content_list
        
        # Update selected range to cover the new content
        self._update_selected_range(
            (start, start + len(content_list)),
            "Replace"
        )

        self.changelog.append(Change(
            change_type=ChangeType.REPLACE,
            original_content=original,
            new_content=content_list,
            start_line=start,
            end_line=start + len(content_list)  # Use new end position
        ))

    def Insert(self, lines: str, new_indent: int = None):
        """Insert lines before the currently selected lines."""
        if not self.selected_range:
            raise ValueError(f"No lines selected for Insert operation. Call a Select method first.\nLines that would be inserted:\n{lines}")
            
        start, end = self.selected_range
        original = self.content[start:end]  # Get the selected text
        
        # Split and optionally indent the new content
        content_list = lines.splitlines() if lines else []
        if new_indent is not None:
            # Convert new_indent to int if it's a string
            indent = int(new_indent) if isinstance(new_indent, str) else new_indent
            content_list = [' ' * indent + line.lstrip() for line in content_list]
        
        # Insert lines before selected range
        self.content[start:start] = content_list
        
        # Update selected range to include both inserted content and original selection
        self._update_selected_range(
            (start, start + len(content_list) + len(original)),
            "Insert"
        )
        
        self.changelog.append(Change(
            change_type=ChangeType.INSERT,
            original_content=original,  # Selected text becomes original content
            new_content=content_list + original,  # New content includes both inserted lines and selected text
            start_line=start,
            end_line=start + len(content_list) + len(original)  # Update end line to include both
        ))

    def Append(self, new_content: str, new_indent: int = None):
        """Append new content after the currently selected lines.
        If no lines are selected, appends to the end of the file."""
        
        # Split and optionally indent the new content
        content_list = new_content.splitlines() if new_content else []
        if new_indent is not None:
            # Convert new_indent to int if it's a string
            indent = int(new_indent) if isinstance(new_indent, str) else new_indent
            content_list = [' ' * indent + line.lstrip() for line in content_list]
        
        if not self.selected_range:
            # Append to end of file
            start = end = len(self.content)
            original = []
            self.content.extend(content_list)
            
            # Update selected range to cover the appended content
            self._update_selected_range(
                (start, end + len(content_list)),
                "Append to end"
            )
        else:
            # Append after selected range
            start, end = self.selected_range
            original = self.content[start:end]  # Get the selected text
            
            # Append new content after selected range
            self.content[end:end] = content_list
            
            # Update selected range to include both original selection and appended content
            self._update_selected_range(
                (start, end + len(content_list)),
                "Append"
            )
        
        self.changelog.append(Change(
            change_type=ChangeType.APPEND,
            original_content=original,
            new_content=original + content_list,
            start_line=start,
            end_line=end + len(content_list)
        ))

    def prepare(self):
        """Prepare the file for modification by reading its content"""
        full_path = self._get_full_path(self.name)
        with open(full_path, 'r', encoding='utf-8') as file:
            self.content = [line.rstrip('\n') for line in file.readlines()]
        self.line_finder = LineFinder(self.content, self.debug)

    def _get_full_path(self, filename: Path) -> Path:
        """Get the full path to a file, considering target_dir if set"""
        if self.target_dir:
            return self.target_dir / filename
        return filename

    def execute(self):
        """Execute the modification by writing back to the same file that was read"""
        full_path = self._get_full_path(self.name)
        # Ensure the target directory exists
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
