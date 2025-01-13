"""
This module provides File modification operations to be used with the executor class.

Operations are performed on the in-memory File, written back to disk if the operations are successful.

# Block definition
The class operates on blocks of lines. In order to identify the block from the current content that should be modified, the class uses before_lines and after_lines, which are the lines that precede and follow the block to be modified.

## Before and After lines

The before_lines and after_lines are used to locate the block of code to be modified. When using "ReplaceBlock", 
the before and after lines are included in the replacement.

DeleteBlock removes the block including the before and after lines.
MoveBlock relocates the block (including before and after lines) to a new location, which is identified by its own 
set of before and after lines at the target position.
"""
import os
from typing import List
from .models import ChangeType, Change

class ModifyFile:

    def __init__(self, name: str, target_dir: str):
        self.name = name
        self.target_dir = target_dir
        self.debug = os.environ.get('DEBUG', '').lower() in ('true', '1', 't')
        self.changelog: List[Change] = []

    def _debug_print(self, *args, **kwargs):
        """Print debug information only if DEBUG environment variable is set"""
        if self.debug:
            print(*args, **kwargs)

    def _find_matching_lines(self, search_lines: list[str], start_pos: int, label: str) -> int:
        """Find position where lines match in content, starting from start_pos.
        Returns the matching position or -1 if not found."""
        self._debug_print(f"\nSearching for {label}:")
        self._debug_print(f"{label} lines to match:")
        for i, line in enumerate(search_lines):
            self._debug_print(f"  {i+1:4d}: '{line.rstrip()}'")

        if not search_lines:
            return start_pos

        self._debug_print(f"\nAttempting matches starting from position {start_pos + 1}:")
        for i in range(start_pos, len(self.content) - len(search_lines) + 1):
            self._debug_print(f"\nTrying at position {i+1}:")
            match = True
            for j in range(len(search_lines)):
                content_line = self.content[i + j].rstrip()
                search_line = search_lines[j].rstrip()
                if content_line != search_line:
                    self._debug_print(f"  ✗ Line {i+j+1}: '{content_line}' != '{search_line}'")
                    match = False
                    break
                else:
                    self._debug_print(f"  ✓ Line {i+j+1}: '{content_line}' == '{search_line}'")

            if match:
                self._debug_print(f"\n{label} match found at line {i + 1}")
                self._debug_print("Matched lines:")
                for j in range(len(search_lines)):
                    self._debug_print(f"  {i+j+1:4d}: {self.content[i+j].rstrip()}")
                return i

        self._debug_print(f"\nNo {label} match found in content:")
        self._debug_print("Content lines:")
        for i, line in enumerate(self.content[start_pos:]):
            self._debug_print(f"  {i+start_pos+1:4d}: '{line.rstrip()}'")
        return -1

    def _get_block(self, before_lines: str, after_lines: str = None) -> tuple[int, int]:
        """Get the start and end positions of a block defined by before and after lines.
        Returns (before_start_pos, after_end_pos)."""
        # Find before position
        before_lines_list = before_lines.splitlines() if before_lines else []
        before_start = self._find_matching_lines(before_lines_list, 0, "before") if before_lines_list else 0
        if before_lines_list and before_start == -1:
            raise ValueError(f"Before lines not found: {before_lines}")

        # Find after position, starting after before_lines
        after_lines_list = after_lines.splitlines() if after_lines else []
        if not after_lines_list:
            return before_start, before_start + len(before_lines_list)

        search_start = before_start + len(before_lines_list)
        after_start = self._find_matching_lines(after_lines_list, search_start, "after")
        if after_start == -1:
            raise ValueError(f"After lines not found following before lines: {after_lines}")

        return before_start, after_start + len(after_lines_list)

    def ReplaceBlock(self, before_lines: str, after_lines: str, new_content: str, new_indent: str = None):
        """Replace the block of lines between before_lines and after_lines with new_content.
        Replaces both the before and after lines along with the content between them.
        Both before_lines and after_lines must be provided."""
        if not before_lines or not after_lines:
            raise ValueError("ReplaceBlock requires both before_lines and after_lines")

        block_start, block_end = self._get_block(before_lines, after_lines)
        
        # Store original content before replacement
        original_content = self.content[block_start:block_end]
        
        lines = new_content.splitlines()
        if new_indent is not None:
            indent = int(new_indent)
            lines = [' ' * indent + line.lstrip() for line in lines]
        
        # Record the change
        self.changelog.append(Change(
            change_type=ChangeType.REPLACE,
            original_content=original_content,
            new_content=lines,
            start_line=block_start,
            end_line=block_end
        ))
        
        self.content[block_start:block_end] = lines

    def _get_full_path(self, filename: str) -> str:
        """Get the full path to a file, considering target_dir if set"""
        if self.target_dir:
            return os.path.join(self.target_dir, filename)
        return filename

    def prepare(self):
        """Prepare the file for modification"""
        with open(self._get_full_path(self.name), 'r', encoding='utf-8') as file:
            # Strip newlines to be consistent with splitlines()
            self.content = [line.rstrip('\n') for line in file.readlines()]

    def DeleteBlock(self, before_lines: str = None, after_lines: str = None):
        """Delete block based on before and after lines.
        If both provided: deletes everything between and including the lines.
        If only before_lines: deletes those lines and everything after until next line.
        If only after_lines: deletes everything from previous line until and including after_lines.
        At least one set of lines must be provided."""
        if not before_lines and not after_lines:
            raise ValueError("DeleteBlock requires at least before_lines or after_lines")

        block_start, block_end = self._get_block(before_lines, after_lines)
        
        if before_lines and after_lines:
            # Store original content before deletion
            original_content = self.content[block_start:block_end]
            # Record the change
            self.changelog.append(Change(
                change_type=ChangeType.DELETE,
                original_content=original_content,
                new_content=None,
                start_line=block_start,
                end_line=block_end
            ))
            # Delete everything including both sets of lines
            self.content[block_start:block_end] = []
        elif before_lines:
            before_line_count = len(before_lines.splitlines())
            delete_end = block_start + before_line_count + 1
            original_content = self.content[block_start:delete_end]
            self.changelog.append(Change(
                change_type=ChangeType.DELETE,
                original_content=original_content,
                new_content=None,
                start_line=block_start,
                end_line=delete_end
            ))
            self.content[block_start:delete_end] = []
        else:
            after_line_count = len(after_lines.splitlines())
            delete_start = block_end - after_line_count - 1
            original_content = self.content[delete_start:block_end]
            self.changelog.append(Change(
                change_type=ChangeType.DELETE,
                original_content=original_content,
                new_content=None,
                start_line=delete_start,
                end_line=block_end
            ))
            self.content[delete_start:block_end] = []

    def write_back(self, file_path: str):
        """Write the modified content back to the file"""
        with open(file_path, 'w', encoding='utf-8') as file:
            # Add newlines back when writing
            file.write('\n'.join(self.content) + '\n')

    def execute(self):
        """Execute the modification by writing back to the same file that was read"""
        self.write_back(self._get_full_path(self.name))

    def get_changes(self) -> List[Change]:
        """Return the list of changes made to the file.
        
        Returns:
            List[Change]: A list of Change objects representing modifications made to the file.
            Each Change object contains:
            - change_type: The type of change (REPLACE, DELETE, MOVE)
            - original_content: The original content that was modified/deleted
            - new_content: The new content that replaced the original (None for deletions)
            - start_line: Starting line number of the change
            - end_line: Ending line number of the change
        """
        return self.changelog
