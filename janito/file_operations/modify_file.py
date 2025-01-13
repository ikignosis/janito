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
    """

    def __init__(self, name: Path, target_dir: Path):
        self.name = Path(name)
        self.target_dir = Path(target_dir) if target_dir else None
        self.debug = os.environ.get('DEBUG', '').lower() in ('true', '1', 't')
        self.changelog: List[Change] = []
        self.content: List[str] = []
        self.selected_range: Tuple[int, int] = None

    def _debug_print(self, *args, **kwargs):
        """Print debug information only if DEBUG environment variable is set"""
        if self.debug:
            print(*args, **kwargs)

    def _find_lines(self, search_lines: List[str], start_pos: int = 0) -> int:
        """Find first position where the search lines match in content.
        Returns the matching line number (0-based index) or -1 if not found."""
        if self.debug:
            self._debug_print(f"\nSearching for lines:")
            for i, line in enumerate(search_lines):
                self._debug_print(f"  {i+1:4d}: '{line.rstrip()}'")
            self._debug_print(f"\nStarting search from line {start_pos + 1}")
        
        for i in range(start_pos, len(self.content) - len(search_lines) + 1):
            match = True
            if self.debug:
                self._debug_print(f"\nTrying at line {i + 1}:")
            
            for j, search_line in enumerate(search_lines):
                content_line = self.content[i + j].rstrip()
                search_line = search_line.rstrip()
                
                if content_line != search_line:
                    if self.debug:
                        self._debug_print(f"  ✗ Line {i+j+1}: '{content_line}' != '{search_line}'")
                    match = False
                    break
                elif self.debug:
                    self._debug_print(f"  ✓ Line {i+j+1}: '{content_line}' == '{search_line}'")
            
            if match:
                if self.debug:
                    self._debug_print(f"\n✓ Found match at line {i + 1}:")
                    for j in range(len(search_lines)):
                        self._debug_print(f"  {i+j+1:4d}: {self.content[i+j].rstrip()}")
                return i
        
        if self.debug:
            self._debug_print("\n✗ No match found in content:")
            for i, line in enumerate(self.content[start_pos:], start=start_pos):
                self._debug_print(f"  {i+1:4d}: '{line.rstrip()}'")
        
        return -1

    def SelectBetween(self, start_lines: str, end_lines: str):
        """Select lines between (not including) start_lines and end_lines."""
        start_lines_list = start_lines.splitlines() if start_lines else []
        end_lines_list = end_lines.splitlines() if end_lines else []
        
        # Try to find a valid start/end combination
        start_pos = 0
        while True:
            start_pos = self._find_lines(start_lines_list, start_pos)
            if start_pos == -1:
                raise ValueError("Start lines not found")
            
            end_pos = self._find_lines(end_lines_list, start_pos + len(start_lines_list))
            if end_pos != -1:
                # Found a valid combination
                self.selected_range = (start_pos + len(start_lines_list), end_pos)
                return
            
            # Try next occurrence of start_lines
            start_pos += 1

    def SelectOver(self, start_lines: str, end_lines: str = None):
        """Select lines between and including start_lines and end_lines.
        If end_lines is not provided, selects only the start_lines."""
        start_lines_list = start_lines.splitlines() if start_lines else []
        
        # Find start position
        start_pos = self._find_lines(start_lines_list)
        if start_pos == -1:
            raise ValueError("Start lines not found")
            
        if not end_lines:
            # If no end_lines provided, select only the start_lines
            self.selected_range = (start_pos, start_pos + len(start_lines_list))
            return
            
        # Try to find a valid end position
        end_lines_list = end_lines.splitlines()
        end_pos = self._find_lines(end_lines_list, start_pos + len(start_lines_list))
        if end_pos == -1:
            raise ValueError("End lines not found")
            
        # Found a valid combination
        self.selected_range = (start_pos, end_pos + len(end_lines_list))

    def SelectExact(self, lines: str):
        """Select lines matching exact content."""
        lines_list = lines.splitlines() if lines else []
        pos = self._find_lines(lines_list)
        if pos == -1:
            raise ValueError("Exact lines not found")
        self.selected_range = (pos, pos + len(lines_list))

    def Delete(self):
        """Delete the currently selected lines."""
        if not self.selected_range:
            raise ValueError("No lines selected. Call a Select method first.")
            
        start, end = self.selected_range
        original = self.content[start:end]
        self.content[start:end] = []
        
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
            raise ValueError("No lines selected. Call a Select method first.")
            
        start, end = self.selected_range
        original = self.content[start:end]
        
        # Split and optionally indent the new content
        content_list = new_content.splitlines() if new_content else []
        if new_indent is not None:
            # Convert new_indent to int if it's a string
            indent = int(new_indent) if isinstance(new_indent, str) else new_indent
            content_list = [' ' * indent + line.lstrip() for line in content_list]
        
        self.content[start:end] = content_list
        
        self.changelog.append(Change(
            change_type=ChangeType.REPLACE,
            original_content=original,
            new_content=content_list,
            start_line=start,
            end_line=end
        ))

    def Insert(self, new_content: str, new_indent: int = None):
        """Insert new content before the currently selected lines."""
        if not self.selected_range:
            raise ValueError("No lines selected. Call a Select method first.")
            
        start, end = self.selected_range
        original = self.content[start:end]  # Get the selected text
        
        # Split and optionally indent the new content
        content_list = new_content.splitlines() if new_content else []
        if new_indent is not None:
            # Convert new_indent to int if it's a string
            indent = int(new_indent) if isinstance(new_indent, str) else new_indent
            content_list = [' ' * indent + line.lstrip() for line in content_list]
        
        # Insert new content before selected range
        self.content[start:start] = content_list
        
        # For changelog, include both new content and selected text
        self.changelog.append(Change(
            change_type=ChangeType.INSERT,
            original_content=original,  # Selected text becomes original content
            new_content=content_list + original,  # New content includes both inserted lines and selected text
            start_line=start,
            end_line=start + len(content_list) + len(original)  # Update end line to include both
        ))

    def Append(self, new_content: str, new_indent: int = None):
        """Append new content after the currently selected lines."""
        if not self.selected_range:
            raise ValueError("No lines selected. Call a Select method first.")
            
        start, end = self.selected_range
        original = self.content[start:end]  # Get the selected text
        
        # Split and optionally indent the new content
        content_list = new_content.splitlines() if new_content else []
        if new_indent is not None:
            # Convert new_indent to int if it's a string
            indent = int(new_indent) if isinstance(new_indent, str) else new_indent
            content_list = [' ' * indent + line.lstrip() for line in content_list]
        
        # Append new content after selected range
        self.content[end:end] = content_list
        
        # For changelog, include both selected text and new content
        self.changelog.append(Change(
            change_type=ChangeType.APPEND,
            original_content=original,  # Selected text becomes original content
            new_content=original + content_list,  # New content includes both selected text and appended lines
            start_line=start,
            end_line=end + len(content_list)  # Update end line to include both
        ))

    def prepare(self):
        """Prepare the file for modification by reading its content"""
        full_path = self._get_full_path(self.name)
        with open(full_path, 'r', encoding='utf-8') as file:
            self.content = [line.rstrip('\n') for line in file.readlines()]

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
