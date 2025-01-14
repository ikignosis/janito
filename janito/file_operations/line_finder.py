import os
from typing import List

class LineFinder:
    """Class responsible for finding lines in text content."""

    def __init__(self, content: List[str], debug: bool = False):
        """Initialize with content to search in and debug flag."""
        self.content = content
        self.debug = debug

    def _debug_print(self, *args, **kwargs):
        """Print debug information only if debug is enabled."""
        if self.debug:
            print(*args, **kwargs)

    def _get_indent_level(self, line: str) -> int:
        """Get the indentation level of a line."""
        return len(line) - len(line.lstrip())

    def _get_indent_pattern(self, lines: List[str]) -> List[str]:
        """Get the indentation pattern between consecutive lines.
        Returns a list of '=', '>' or '<' indicating same, more or less indentation."""
        if not lines or len(lines) < 2:
            return []
            
        patterns = []
        prev_indent = self._get_indent_level(lines[0])
        
        for line in lines[1:]:
            curr_indent = self._get_indent_level(line)
            if curr_indent > prev_indent:
                patterns.append('>')
            elif curr_indent < prev_indent:
                patterns.append('<')
            else:
                patterns.append('=')
            prev_indent = curr_indent
            
        return patterns

    def find_first(self, search_lines: List[str], start_pos: int = 0) -> int:
        """Find first position where the search lines match in content.
        First tries exact match, then tries indent-pattern match.
        Returns the matching line number (0-based index) or -1 if not found."""
        # Try exact match first
        exact_match = self._find_exact(search_lines, start_pos)
        if exact_match != -1:
            return exact_match
            
        # If exact match fails, try indent pattern match
        return self._find_pattern(search_lines, start_pos)

    def _find_exact(self, search_lines: List[str], start_pos: int = 0) -> int:
        """Find first position where the search lines match exactly."""
        if self.debug:
            self._debug_print(f"\nTrying exact match from line {start_pos + 1}")
        
        for i in range(start_pos, len(self.content) - len(search_lines) + 1):
            match = True
            
            for j, search_line in enumerate(search_lines):
                content_line = self.content[i + j].rstrip()
                search_line = search_line.rstrip()
                
                if content_line != search_line:
                    match = False
                    break
                    
            if match:
                if self.debug:
                    self._debug_print(f"\n✓ Found exact match at line {i + 1}")
                return i
                
        return -1

    def _find_pattern(self, search_lines: List[str], start_pos: int = 0) -> int:
        """Find first position where the lines match the indent pattern."""
        if len(search_lines) < 2:
            return -1  # Need at least 2 lines to match pattern
            
        search_pattern = self._get_indent_pattern(search_lines)
        if self.debug:
            self._debug_print(f"\nTrying pattern match from line {start_pos + 1}")
            self._debug_print(f"Search pattern: {search_pattern}")
        
        for i in range(start_pos, len(self.content) - len(search_lines) + 1):
            content_slice = self.content[i:i + len(search_lines)]
            content_pattern = self._get_indent_pattern(content_slice)
            
            # Check if patterns match
            if content_pattern == search_pattern:
                # Verify content matches when stripped
                match = True
                for j, search_line in enumerate(search_lines):
                    if self.content[i + j].strip() != search_line.strip():
                        match = False
                        break
                
                if match:
                    if self.debug:
                        self._debug_print(f"\n✓ Found pattern match at line {i + 1}")
                        self._debug_print("Pattern matched:")
                        for j, line in enumerate(content_slice):
                            self._debug_print(f"  {i+j+1:4d}: '{line.rstrip()}'")
                    return i
        
        return -1 