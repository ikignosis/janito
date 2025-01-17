import os
from typing import List, Callable, Optional, Tuple
from enum import Enum, auto
from dataclasses import dataclass

class MatchMethod(Enum):
    """Different methods for matching content blocks."""
    EXACT = auto()          # Match content exactly
    STRIPPED = auto()       # Match ignoring leading/trailing whitespace
    PYTHON = auto()         # Match with Python-specific rules
    INDENT_PATTERN = auto() # Match based on indentation pattern


@dataclass
class MatchResult:
    """Result of a content match."""
    start_pos: int      # Start position of the match (0-based)
    end_pos: int        # End position of the match (exclusive)
    method: MatchMethod # Method that found the match

class LineFinder:
    """Class responsible for finding content blocks in text."""

    def __init__(self, content: List[str], debug: bool = False):
        """Initialize with content to search in and debug flag."""
        self.content = content
        self.debug = debug
        
        # Define match methods
        self._match_methods = {
            MatchMethod.EXACT: self._exact_content_match,
            MatchMethod.STRIPPED: self._stripped_content_match,
            MatchMethod.PYTHON: self._python_content_match,
            MatchMethod.INDENT_PATTERN: self._indent_pattern_match
        }

    def _debug_print(self, *args, **kwargs):
        """Print debug information only if debug is enabled."""
        if self.debug:
            print(*args, **kwargs)

    def find_first(self, search_lines: List[str], start_pos: int = 0, 
                  methods: Optional[List[MatchMethod]] = None) -> Optional[MatchResult]:
        """Find first position where the content block matches using specified methods."""
        if methods is None:
            methods = [
                MatchMethod.EXACT,
                MatchMethod.STRIPPED,
                MatchMethod.PYTHON,
                MatchMethod.INDENT_PATTERN
            ]
        
        search_block = search_lines
        for method in methods:
            if self.debug:
                self._debug_print(f"\nTrying {method.name.lower()} match from line {start_pos + 1}")
            
            result = self._find_with_method(search_block, start_pos, method)
            if result is not None:
                return result
        
        return None

    def _find_with_method(self, search_block: List[str], start_pos: int, 
                         method: MatchMethod) -> Optional[MatchResult]:
        """Find first position using a specific match method."""
        match_func = self._match_methods[method]
        max_search_position = len(self.content) - len(search_block) + 1

        for content_pos in range(start_pos, max_search_position):
            # For all methods, we use fixed block size
            content_block = self.content[content_pos:content_pos + len(search_block)]
            if self.debug:
                self._debug_print(f"\nTrying at line {content_pos + 1}:")
                self._debug_print("Search block:")
                for i, line in enumerate(search_block):
                    self._debug_print(f"  {i+1:4d}: '{line}'")
                self._debug_print("Content block:")
                for i, line in enumerate(content_block):
                    self._debug_print(f"  {content_pos+i+1:4d}: '{line}'")
            
            if match_func(content_block, search_block):
                end_pos = content_pos + len(search_block)
                if self.debug:
                    self._debug_print(f"\n✓ Found {method.name.lower()} match at lines {content_pos + 1}-{end_pos}")
                return MatchResult(content_pos, end_pos, method)
            elif self.debug:
                self._debug_print("✗ No match")
        
        return None

    def _exact_content_match(self, content_block: List[str], search_block: List[str]) -> bool:
        """Match content blocks exactly (after rstrip)."""
        if len(content_block) != len(search_block):
            return False
        return all(c.rstrip() == s.rstrip() for c, s in zip(content_block, search_block))

    def _stripped_content_match(self, content_block: List[str], search_block: List[str]) -> bool:
        """Match content blocks ignoring all whitespace."""
        if len(content_block) != len(search_block):
            return False
        return all(c.strip() == s.strip() for c, s in zip(content_block, search_block))

    def _python_content_match(self, content_block: List[str], search_block: List[str]) -> bool:
        """Match content blocks with Python-specific rules."""
        if len(content_block) != len(search_block):
            return False
            
        for content_line, search_line in zip(content_block, search_block):
            c = content_line.rstrip()
            s = search_line.rstrip()
            
            if c.startswith('def ') and s.startswith('def '):
                # Remove return type hint and trailing colon
                c = c.split(' -> ')[0].rstrip(':').rstrip()
                s = s.split(' -> ')[0].rstrip(':').rstrip()
            
            if c != s:
                return False
                
        return True

    def _indent_pattern_match(self, content_block: List[str], search_block: List[str]) -> bool:
        """Match content blocks based on indentation pattern."""
        if len(content_block) != len(search_block):
            return False
            
        # Get indentation patterns
        content_pattern = self._get_indent_pattern(content_block)
        search_pattern = self._get_indent_pattern(search_block)
        
        # Check patterns match
        if content_pattern != search_pattern:
            return False
            
        # Check stripped content matches
        return all(c.strip() == s.strip() for c, s in zip(content_block, search_block))

    def _get_indent_level(self, line: str) -> int:
        """Get the indentation level of a line."""
        return len(line) - len(line.lstrip())

    def _get_indent_pattern(self, lines: List[str]) -> List[str]:
        """Get the indentation pattern between consecutive lines."""
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

    def _nonspace_content_match(self, content_lines: List[str], search_block: List[str]) -> Optional[int]:
        """Match content by comparing concatenated non-whitespace characters.
        Returns the number of content lines consumed if matched, None if no match."""
        # Join and strip all non-whitespace chars from search block
        search_chars = ''.join(c for line in search_block 
                              for c in line.strip() if not c.isspace())
        
        if self.debug:
            self._debug_print("\nSearch block without spaces:", repr(search_chars))
        
        # Build content string incrementally
        content_chars = ""
        for i, line in enumerate(content_lines):
            # Strip each line before removing spaces
            content_chars += ''.join(c for c in line.strip() if not c.isspace())
            
            if self.debug:
                self._debug_print(f"Content without spaces (lines 1-{i+1}):", repr(content_chars))
            
            if content_chars == search_chars:
                if self.debug:
                    self._debug_print(f"✓ Found match consuming {i+1} lines")
                return i + 1  # Return number of lines consumed
            elif len(content_chars) > len(search_chars):
                if self.debug:
                    self._debug_print("✗ Content longer than search, stopping")
                break  # Stop if we've collected too many characters
        
        if self.debug:
            self._debug_print("✗ No match found")
        return None 