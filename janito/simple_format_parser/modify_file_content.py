"""
This module provides file content modification operations to be used with the executor class.

Operations are performed on the in-memory file content, written back to disk if the operations are successful.

# Block definition
The class operates on blocks of lines. In order to identify the block from the current content that should be modified, the class uses before_lines and after_lines, which are the lines that precede and follow the block to be modified.

## Before and After lines

The before_lines and after_lines are used to locate the block of code to be modified. When using "ReplaceBlock", 
the before and after lines are included in the replacement. When using "AdaptBlock", the before and after lines are 
preserved, and only the content between them is modified.

DeleteBlock removes the block including the before and after lines.
MoveBlock relocates the block (including before and after lines) to a new location, which is identified by its own 
set of before and after lines at the target position.
"""
import os

class ModifyFileContent:

    def __init__(self, name: str, target_dir: str):
        self.name = name
        self.target_dir = target_dir

    def _find_matching_lines(self, search_lines: list[str], start_pos: int, label: str) -> int:
        """Find position where lines match in content, starting from start_pos.
        Returns the matching position or -1 if not found."""
        print(f"\nSearching for {label}:")
        print(f"{label} lines to match:")
        for i, line in enumerate(search_lines):
            print(f"  {i+1:4d}: '{line.rstrip()}'")

        if not search_lines:
            return start_pos

        print(f"\nAttempting matches starting from position {start_pos + 1}:")
        for i in range(start_pos, len(self.content) - len(search_lines) + 1):
            print(f"\nTrying at position {i+1}:")
            match = True
            for j in range(len(search_lines)):
                content_line = self.content[i + j].rstrip()
                search_line = search_lines[j].rstrip()
                if content_line != search_line:
                    print(f"  ✗ Line {i+j+1}: '{content_line}' != '{search_line}'")
                    match = False
                    break
                else:
                    print(f"  ✓ Line {i+j+1}: '{content_line}' == '{search_line}'")

            if match:
                print(f"\n{label} match found at line {i + 1}")
                print("Matched lines:")
                for j in range(len(search_lines)):
                    print(f"  {i+j+1:4d}: {self.content[i+j].rstrip()}")
                return i

        print(f"\nNo {label} match found in content:")
        print("Content lines:")
        for i, line in enumerate(self.content[start_pos:]):
            print(f"  {i+start_pos+1:4d}: '{line.rstrip()}'")
        return -1

    def _get_block(self, before_lines: str, after_lines: str = None) -> tuple[int, int]:
        """Get the start and end positions of a block defined by before and after lines.
        Returns (before_start_pos, after_end_pos).
        If only before_lines provided, returns position after those lines.
        If only after_lines provided, returns position before those lines."""
        # Find before position
        before_lines_list = before_lines.splitlines() if before_lines else []
        before_start = self._find_matching_lines(before_lines_list, 0, "before") if before_lines_list else 0
        if before_lines_list and before_start == -1:
            raise ValueError(f"Before lines not found: {before_lines}")

        # Find after position, starting after before_lines
        after_lines_list = after_lines.splitlines() if after_lines else []
        if not after_lines_list:
            # If no after lines, for AdaptBlock we want to insert after before_lines
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
        lines = new_content.splitlines()
        if new_indent is not None:
            indent = int(new_indent)
            lines = [' ' * indent + line.lstrip() for line in lines]
        self.content[block_start:block_end] = lines

    def AdaptBlock(self, before_lines: str, after_lines: str = None, new_content: str = "", new_indent: str = None):
        """Adapt the block based on before and after lines.
        If both provided: preserves the before/after lines and replaces content between them.
        If only before_lines: adds content after those lines.
        If only after_lines: adds content before those lines.
        At least one marker must be provided."""
        if not before_lines and not after_lines:
            raise ValueError("AdaptBlock requires at least before_lines or after_lines")

        block_start, block_end = self._get_block(before_lines, after_lines)
        lines = new_content.splitlines()
        if new_indent is not None:
            indent = int(new_indent)
            lines = [' ' * indent + line.lstrip() for line in lines]

        if before_lines and after_lines:
            # Replace content between markers while preserving them
            before_line_count = len(before_lines.splitlines())
            after_line_count = len(after_lines.splitlines())
            self.content[block_start + before_line_count:block_end - after_line_count] = lines
        elif before_lines:
            # Insert after before_lines, preserving them
            before_line_count = len(before_lines.splitlines())
            self.content[block_start + before_line_count:block_end] = lines
        else:
            # Insert before after_lines
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
            # Delete everything including both sets of lines
            self.content[block_start:block_end] = []
        elif before_lines:
            # Delete before_lines and the line after them
            before_line_count = len(before_lines.splitlines())
            self.content[block_start:block_start + before_line_count + 1] = []
        else:
            # Delete the line before after_lines and the after_lines
            after_line_count = len(after_lines.splitlines())
            self.content[block_end - after_line_count - 1:block_end] = []

    def write_back(self, file_path: str):
        """Write the modified content back to the file"""
        with open(file_path, 'w', encoding='utf-8') as file:
            # Add newlines back when writing
            file.write('\n'.join(self.content) + '\n')

    def execute(self):
        """Execute the modification by writing back to the same file that was read"""
        self.write_back(self._get_full_path(self.name))
