"""
This module provides file content modification operations to be used with the executor class.

Operations are performed on the in-memory file content, written back to disk if the operations are successful.

# Block definition
The class operates on blocks of lines. In order to identify the block from the current content that should be modified, the class uses context prefix and suffix, which are the lines that precede and follow the block.

## Context prefix and suffix

The context prefix and suffix are the lines that precede and follow the block. When the intention is to change the full context (including prefix and suffix) "ReplaceBlock" should be used.
When the intention is to preserve the context prefix and suffix, and only change the content between them, "AdaptBlock" should be used.

DeleteBlock is used to delete the block, including the context prefix and suffix.
MoveBlock is used to move the block to a new location, including the context prefix and suffix. MoveBlock also requires a target context prefix and suffix, which are the lines that precede and follow the new location.


"""
from typing import Optional, Tuple
import os


class ModifyFile:
    def __init__(self, name: str, target_dir: str = None):
        self.name = name
        self.target_dir = target_dir
        self.content: Optional[str] = None

    def _get_full_path(self) -> str:
        """Get the full path to the file, considering target_dir if set"""
        if self.target_dir:
            return os.path.join(self.target_dir, self.name)
        return self.name

    def prepare(self):
        """Read the file content and prepare for modifications"""
        full_path = self._get_full_path()
        with open(full_path, 'r') as file:
            self.content = file.read()

    def _find_block(self, start_context: str, end_context: str) -> Optional[Tuple[int, int]]:
        """
        Find the start and end line numbers of a block defined by context markers.
        Returns (start_line, end_line) or None if not found.
        Line numbers are 0-based.
        """
        if self.content is None:
            raise RuntimeError("prepare() must be called before any modifications")

        # Split content and context markers into lines
        lines = self.content.splitlines()
        start_context_lines = start_context.splitlines()
        end_context_lines = end_context.splitlines()

        print("\nDEBUG: _find_block")
        print(f"Looking for start context: {start_context_lines}")
        print(f"Looking for end context: {end_context_lines}")
        print("\nContent lines:")
        for i, line in enumerate(lines):
            print(f"{i:2d}: '{line}'")

        # Find the start line sequence
        start_line = -1
        for i in range(len(lines) - len(start_context_lines) + 1):
            if all(lines[i + j] == start_context_lines[j] 
                   for j in range(len(start_context_lines))):
                start_line = i
                print(f"Found start sequence at {i}")
                break

        if start_line == -1:
            print("Failed to find start sequence!")
            return None

        # Find the end line sequence after start_line
        end_line = -1
        for i in range(start_line + len(start_context_lines), 
                      len(lines) - len(end_context_lines) + 1):
            if all(lines[i + j] == end_context_lines[j] 
                   for j in range(len(end_context_lines))):
                end_line = i + len(end_context_lines) - 1
                print(f"Found end sequence at {i}")
                break

        if end_line == -1:
            print("Failed to find end sequence!")
            return None

        print(f"Block found from line {start_line} to {end_line}")
        return (start_line, end_line)

    def ReplaceBlock(self, start_context: str, end_context: str, new_content: str, 
                     indent: int = 0, preserve_context: bool = False):
        """
        Replace a block of text between start_context and end_context with new_content.
        """
        print("\nDEBUG: ReplaceBlock")
        print(f"Start context: '{start_context}'")
        print(f"End context: '{end_context}'")
        print(f"Original new content: '{new_content}'")
        print(f"Indent: {indent}")
        print(f"Preserve context: {preserve_context}")

        block_pos = self._find_block(start_context, end_context)
        if block_pos is None:
            raise ValueError(f"Could not find block between '{start_context}' and '{end_context}'")

        # Split content into lines
        lines = self.content.splitlines()
        start_line, end_line = block_pos
        start_context_lines = start_context.splitlines()
        end_context_lines = end_context.splitlines()

        # Process new content
        new_lines = new_content.splitlines()

        print("\nProcessed new content:")
        for i, line in enumerate(new_lines):
            print(f"{i:2d}: '{line}'")

        if indent > 0:
            new_lines = [' ' * indent + line for line in new_lines]

        if preserve_context:
            # Keep the context markers, only replace content between them
            start_marker_end = start_line + len(start_context_lines)
            end_marker_start = end_line - len(end_context_lines) + 1
            lines[start_marker_end:end_marker_start] = new_lines[1:-1]  # Exclude context lines from new content
        else:
            # Replace entire block including context markers
            lines[start_line:end_line + 1] = new_lines

        print("\nAfter replacement:")
        for i, line in enumerate(lines):
            print(f"{i:2d}: '{line}'")

        # Join lines back together with newlines
        self.content = '\n'.join(lines) + '\n'

    def DeleteBlock(self, start_context: str, end_context: str, preserve_context: bool = False):
        """
        Delete a block of text between start_context and end_context.
        Args:
            start_context: The text marking the start of the block
            end_context: The text marking the end of the block
            preserve_context: If True, keeps the context markers, if False removes them too
        """
        block_pos = self._find_block(start_context, end_context)
        if block_pos is None:
            raise ValueError(f"Could not find block between '{start_context}' and '{end_context}'")

        # Split content into lines
        lines = self.content.splitlines()
        start_line, end_line = block_pos

        if preserve_context:
            # Keep the markers but remove content between them
            del lines[start_line + 1:end_line]
        else:
            # Remove entire block including markers
            del lines[start_line:end_line + 1]

        # Join lines back together with newlines
        self.content = '\n'.join(lines) + '\n'

    def execute(self):
        """Write the modified content back to file"""
        if self.content is None:
            raise RuntimeError("prepare() must be called before execute()")

        # Write back to file
        full_path = self._get_full_path()
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as file:
            file.write(self.content)

