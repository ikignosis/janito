from typing import List, Optional, Dict, Type
from abc import ABC, abstractmethod
import re

LINE_OVER_LINE_DEBUG = False

class SearchStrategy(ABC):
    """Base class for search strategies."""
    @abstractmethod
    def match(self, source_lines: List[str], pattern_lines: List[str], pos: int, searcher: 'Searcher') -> bool:
        pass

class ExactMatchStrategy(SearchStrategy):
    """Exact match including indentation."""
    def match(self, source_lines: List[str], pattern_lines: List[str], pos: int, searcher: 'Searcher') -> bool:
        if pos + len(pattern_lines) > len(source_lines):
            return False
        return all(source_lines[pos + i] == pattern_line 
                  for i, pattern_line in enumerate(pattern_lines))

class ExactContentStrategy(SearchStrategy):
    """Exact content match ignoring all indentation."""
    def match(self, source_lines: List[str], pattern_lines: List[str], pos: int, searcher: 'Searcher') -> bool:
        if pos + len(pattern_lines) > len(source_lines):
            return False
        return all(source_lines[pos + i].strip() == pattern_line.strip()
                  for i, pattern_line in enumerate(pattern_lines)
                  if pattern_line.strip())

class IndentAwareStrategy(SearchStrategy):
    """Indentation-aware matching preserving relative indentation."""
    def match(self, source_lines: List[str], pattern_lines: List[str], pos: int, searcher: 'Searcher') -> bool:
        if pos + len(pattern_lines) > len(source_lines):
            return False
        match_indent = searcher.get_indentation(source_lines[pos])
        return all(source_lines[pos + i].startswith(match_indent + pattern_line)
                  for i, pattern_line in enumerate(pattern_lines)
                  if pattern_line.strip())

class ExactContentNoComments(SearchStrategy):
    """Exact content match ignoring indentation, comments, and empty lines."""
    def _strip_comments(self, line: str) -> str:
        """Remove comments from line."""
        if '#' in line:
            line = line.split('#')[0]
        if '//' in line:
            line = line.split('//')[0]
        return line.strip()

    def match(self, source_lines: List[str], pattern_lines: List[str], pos: int, searcher: 'Searcher') -> bool:
        if pos + len(pattern_lines) > len(source_lines):
            return False

        if searcher.debug_mode and LINE_OVER_LINE_DEBUG:
            print("\n[DEBUG] ExactContentNoComments trying to match at line", pos + 1)

        # Filter out comments and empty lines from pattern
        pattern_content = [self._strip_comments(line) for line in pattern_lines]
        pattern_content = [line for line in pattern_content if line]

        if searcher.debug_mode and LINE_OVER_LINE_DEBUG:
            print("[DEBUG] Pattern after processing:")
            for i, line in enumerate(pattern_content):
                print(f"[DEBUG]   {i+1}: '{line}'")

        # Match against source, ignoring comments and empty lines
        source_idx = pos
        pattern_idx = 0
        
        while pattern_idx < len(pattern_content) and source_idx < len(source_lines):
            source_line = self._strip_comments(source_lines[source_idx])
            if not source_line:
                source_idx += 1
                continue
                
            if searcher.debug_mode and LINE_OVER_LINE_DEBUG:
                print(f"[DEBUG] Line {source_idx + 1}: '{source_line}' vs '{pattern_content[pattern_idx]}'")
                
            if source_line != pattern_content[pattern_idx]:
                if searcher.debug_mode and LINE_OVER_LINE_DEBUG:
                    print("[DEBUG] Line mismatch")
                return False
                
            pattern_idx += 1
            source_idx += 1

        match_result = pattern_idx == len(pattern_content)
        if match_result and searcher.debug_mode:
            print("[DEBUG] Match found")
            return True
                
        return False

class Searcher:
    """Handles pattern searching in source code with configurable strategies."""
    
    def __init__(self, debug: bool = False):
        """Initialize searcher with debug mode."""
        self.debug_mode = debug

    @classmethod
    def set_debug(cls, enabled: bool):
        """Enable or disable debug mode - deprecated, use instance property instead"""
        # Remove the class-level debug setting as it's no longer needed
        raise DeprecationWarning("Class-level debug setting is deprecated. Use instance debug_mode property instead.")

    # Updated extension to strategy mapping to include ExactContentNoComments
    EXTENSION_STRATEGIES = {
        '.py': [ExactMatchStrategy(), IndentAwareStrategy(), ExactContentStrategy(), ExactContentNoComments()],
        '.java': [ExactMatchStrategy(), IndentAwareStrategy(), ExactContentStrategy(), ExactContentNoComments()],
        '.js': [ExactMatchStrategy(), IndentAwareStrategy(), ExactContentStrategy(), ExactContentNoComments()],
        '.ts': [ExactMatchStrategy(), IndentAwareStrategy(), ExactContentStrategy(), ExactContentNoComments()],
        '*': [ExactMatchStrategy(), ExactContentStrategy(), ExactContentNoComments()]  # updated default fallback
    }

    def get_strategies(self, file_ext: Optional[str]) -> List[SearchStrategy]:
        """Get search strategies for given file extension."""
        if not file_ext:
            return self.EXTENSION_STRATEGIES['*']
        return self.EXTENSION_STRATEGIES.get(file_ext.lower(), self.EXTENSION_STRATEGIES['*'])

    @staticmethod
    def get_indentation(line: str) -> str:
        """Get the leading whitespace of a line."""
        return re.match(r'^[ \t]*', line).group()

    @staticmethod
    def get_first_non_empty_line(text: str) -> tuple[str, int]:
        """Get first non-empty line and its index."""
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.strip():
                return line, i
        return '', 0

    @staticmethod
    def get_last_non_empty_line(text: str) -> tuple[str, int]:
        """Get last non-empty line and its index."""
        lines = text.splitlines()
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip():
                return lines[i], i
        return '', 0

    def _build_indent_map(self, text: str) -> dict[int, int]:
        """Build a map of line numbers to indentation levels."""
        indent_map = {}
        for i, line in enumerate(text.splitlines()):
            if line.strip():  # Only track non-empty lines
                indent_map[i] = len(self.get_indentation(line))
                if self.debug_mode:
                    print(f"[DEBUG] Line {i}: Indentation level {indent_map[i]}")
        return indent_map

    def normalize_pattern(self, pattern: str, base_indent: str = '') -> str:
        """Remove base indentation from pattern to help with matching."""
        lines = pattern.splitlines()
        first_line, start_idx = self.get_first_non_empty_line(pattern)
        last_line, end_idx = self.get_last_non_empty_line(pattern)
        
        # Calculate minimum indentation from first and last non-empty lines
        first_indent = len(self.get_indentation(first_line))
        last_indent = len(self.get_indentation(last_line))
        min_indent = min(first_indent, last_indent)

        if self.debug_mode:
            print(f"[DEBUG] First line indent: {first_indent}")
            print(f"[DEBUG] Last line indent: {last_indent}")
            print(f"[DEBUG] Using minimum indent: {min_indent}")

        normalized = []
        for i, line in enumerate(lines):
            if not line.strip():
                normalized.append('')
            else:
                line_indent = len(self.get_indentation(line))
                if line_indent < min_indent:
                    if self.debug_mode:
                        print(f"[DEBUG] Warning: Line {i} has less indentation ({line_indent}) than minimum ({min_indent})")
                    normalized.append(line)
                else:
                    normalized.append(line[min_indent:])
                    if self.debug_mode:
                        print(f"[DEBUG] Normalized line {i}: '{normalized[-1]}'")

        return '\n'.join(normalized)

    def _find_best_match_position(self, positions: List[int], source_lines: List[str], pattern_base_indent: int) -> Optional[int]:
        """Find the best matching position based on line number (earliest match)."""
        if self.debug_mode:
            print(f"[DEBUG] Finding best match among positions: {positions}")

        if not positions:
            return None

        best_pos = min(positions)  # Simply take the earliest match
        if self.debug_mode:
            print(f"[DEBUG] Selected match at line {best_pos + 1}")
        return best_pos

    def try_match_with_strategies(self, source_lines: List[str], pattern_lines: List[str], 
                                pos: int, strategies: List[SearchStrategy]) -> bool:
        """Try matching using multiple strategies in order."""
        if self.debug_mode and LINE_OVER_LINE_DEBUG:
            print(f"\n[DEBUG] Trying to match at line {pos + 1}")
            
        for strategy in strategies:
            if strategy.match(source_lines, pattern_lines, pos, self):
                if self.debug_mode:
                    print(f"[DEBUG] Match found with {strategy.__class__.__name__}")
                    print(f"[DEBUG] Stopping strategy chain at line {pos + 1}")
                return True
        return False

    def _find_matches(self, source_lines: List[str], pattern_lines: List[str], 
                     file_ext: Optional[str] = None) -> List[int]:
        """Find all matches using configured strategies."""
        strategies = self.get_strategies(file_ext)
        
        if self.debug_mode:
            print(f"\n[DEBUG] Starting search with {len(strategies)} strategies:")
            for i, strategy in enumerate(strategies):
                print(f"[DEBUG] {i+1}. {strategy.__class__.__name__}")

        # Try each strategy in order of preference
        for strategy in strategies:
            matches = []
            for i in range(len(source_lines)):
                if strategy.match(source_lines, pattern_lines, i, self):
                    matches.append(i)

            if matches:
                if self.debug_mode:
                    print(f"[DEBUG] Found {len(matches)} matches with {strategy.__class__.__name__}")
                return matches
                
        return []

    def exact_match(self, source: str, pattern: str) -> List[int]:
        """Perform exact line-by-line matching, preserving all whitespace except newlines."""
        source_lines = source.splitlines()
        pattern_lines = pattern.splitlines()
        pattern_len = len(pattern_lines)
        matches = []

        for i in range(len(source_lines) - pattern_len + 1):
            is_match = True
            for j in range(pattern_len):
                if source_lines[i + j] != pattern_lines[j]:
                    is_match = False
                    break

            if is_match:
                matches.append(i)

        if self.debug_mode and matches:
            print(f"[DEBUG] Found {len(matches)} exact matches")
            
        return matches