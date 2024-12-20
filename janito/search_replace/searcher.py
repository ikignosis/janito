from typing import List, Optional, Dict, Type
from abc import ABC, abstractmethod
import re
from .strategy_result import StrategyResult

LINE_OVER_LINE_DEBUG = False

class SearchStrategy(ABC):
    """Base class for search strategies."""

    def __init__(self):
        """Initialize strategy with name derived from class name."""
        self.name = self.__class__.__name__.replace('Strategy', '')

    @abstractmethod
    def match(self, source_lines: List[str], pattern_lines: List[str], pos: int, searcher: 'Searcher') -> bool:
        """Check if pattern matches source at given position.
        
        Args:
            source_lines: List of source code lines to search in
            pattern_lines: List of pattern lines to match
            pos: Position in source_lines to start matching
            searcher: Searcher instance for utility methods
            
        Returns:
            bool: True if pattern matches at position, False otherwise
        """
        pass

class ExactMatchStrategy(SearchStrategy):
    """Strategy for exact match including indentation."""

    def match(self, source_lines: List[str], pattern_lines: List[str], pos: int, searcher: 'Searcher') -> bool:
        """Match pattern exactly with indentation.
        
        Args:
            source_lines: List of source code lines to search in
            pattern_lines: List of pattern lines to match
            pos: Position in source_lines to start matching
            searcher: Searcher instance for utility methods
            
        Returns:
            bool: True if pattern matches exactly at position, False otherwise
        """
        if pos + len(pattern_lines) > len(source_lines):
            return False
        return all(source_lines[pos + i] == pattern_line 
                  for i, pattern_line in enumerate(pattern_lines))

class ExactContentStrategy(SearchStrategy):
    """Exact content match ignoring all indentation."""

    def match(self, source_lines: List[str], pattern_lines: List[str], pos: int, searcher: 'Searcher') -> bool:
        """Match pattern exactly ignoring indentation.
        
        Args:
            source_lines: List of source code lines to search in
            pattern_lines: List of pattern lines to match
            pos: Position in source_lines to start matching
            searcher: Searcher instance for utility methods
            
        Returns:
            bool: True if pattern matches exactly at position, False otherwise
        """
        if pos + len(pattern_lines) > len(source_lines):
            return False
        return all(source_lines[pos + i].strip() == pattern_line.strip()
                  for i, pattern_line in enumerate(pattern_lines)
                  if pattern_line.strip())

class IndentAwareStrategy(SearchStrategy):
    """Indentation-aware matching preserving relative indentation."""

    def match(self, source_lines: List[str], pattern_lines: List[str], pos: int, searcher: 'Searcher') -> bool:
        """Match pattern preserving relative indentation.
        
        Args:
            source_lines: List of source code lines to search in
            pattern_lines: List of pattern lines to match
            pos: Position in source_lines to start matching
            searcher: Searcher instance for utility methods
            
        Returns:
            bool: True if pattern matches preserving indentation at position, False otherwise
        """
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
        """Match pattern ignoring comments and empty lines.
        
        Args:
            source_lines: List of source code lines to search in
            pattern_lines: List of pattern lines to match
            pos: Position in source_lines to start matching
            searcher: Searcher instance for utility methods
            
        Returns:
            bool: True if pattern matches ignoring comments at position, False otherwise
        """
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

class ExactContentNoCommentsFirstLinePartial(SearchStrategy):
    """Match first line partially, ignoring comments."""

    def _strip_comments(self, line: str) -> str:
        """Remove comments from line."""
        if '#' in line:
            line = line.split('#')[0]
        if '//' in line:
            line = line.split('//')[0]
        return line.strip()

    def match(self, source_lines: List[str], pattern_lines: List[str], pos: int, searcher: 'Searcher') -> bool:
        """Match first line of pattern partially ignoring comments.
        
        Args:
            source_lines: List of source code lines to search in
            pattern_lines: List of pattern lines to match
            pos: Position in source_lines to start matching
            searcher: Searcher instance for utility methods
            
        Returns:
            bool: True if first line of pattern matches partially at position, False otherwise
        """
        if pos >= len(source_lines):
            return False

        # Get first non-empty pattern line
        pattern_content = []
        for line in pattern_lines:
            stripped = self._strip_comments(line)
            if stripped:
                pattern_content.append(stripped)
                break

        if not pattern_content:
            return False

        # Get source line content
        source_line = self._strip_comments(source_lines[pos])
        if not source_line:
            return False

        # Check if pattern content is part of source line
        return pattern_content[0] in source_line

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
        '.py': [ExactMatchStrategy(), IndentAwareStrategy(), ExactContentStrategy(), ExactContentNoComments(), ExactContentNoCommentsFirstLinePartial()],
        '.java': [ExactMatchStrategy(), IndentAwareStrategy(), ExactContentStrategy(), ExactContentNoComments(), ExactContentNoCommentsFirstLinePartial()],
        '.js': [ExactMatchStrategy(), IndentAwareStrategy(), ExactContentStrategy(), ExactContentNoComments(), ExactContentNoCommentsFirstLinePartial()],
        '.ts': [ExactMatchStrategy(), IndentAwareStrategy(), ExactContentStrategy(), ExactContentNoComments(), ExactContentNoCommentsFirstLinePartial()],
        '*': [ExactMatchStrategy(), ExactContentStrategy(), ExactContentNoComments(), ExactContentNoCommentsFirstLinePartial()]  # updated default fallback
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
        """Build a map of line numbers to their indentation levels.
        
        Args:
            text: Source text to analyze
            
        Returns:
            dict[int, int]: Mapping of line numbers to indentation levels
        """
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

    def try_match_with_strategies(self, source_lines: List[str], pattern_lines: List[str],
                                pos: int, strategies: List[SearchStrategy]) -> StrategyResult:
        """Try matching using multiple strategies in sequence.
        
        Args:
            source_lines: List of source code lines
            pattern_lines: List of pattern lines to match
            pos: Position to start matching
            strategies: List of strategies to try
            
        Returns:
            StrategyResult: Result containing match success and strategy used
        """
        if self.debug_mode and LINE_OVER_LINE_DEBUG:
            print(f"\n[DEBUG] Trying to match at line {pos + 1}")

        for strategy in strategies:
            if strategy.match(source_lines, pattern_lines, pos, self):
                if self.debug_mode:
                    print(f"[DEBUG] Match found with {strategy.__class__.__name__}")
                    print(f"[DEBUG] Stopping strategy chain at line {pos + 1}")
                return StrategyResult(success=True, strategy_name=strategy.name, match_position=pos)
        return StrategyResult(success=False)

    def _find_matches(self, source_lines: List[str], pattern_lines: List[str],
                     file_ext: Optional[str] = None) -> List[int]:
        """Find first matching position using available strategies.
        
        Args:
            source_lines: List of source code lines
            pattern_lines: List of pattern lines to match
            file_ext: Optional file extension to determine strategies
            
        Returns:
            List[int]: List containing single match position or empty list if no match
        """
        strategies = self.get_strategies(file_ext)

        if self.debug_mode:
            print("\nTrying search strategies:")
            print("-" * 50)

        for strategy in strategies:
            strategy_name = strategy.__class__.__name__.replace('Strategy', '')

            if self.debug_mode:
                print(f"\n→ {strategy_name}...")

            for i in range(len(source_lines)):
                if strategy.match(source_lines, pattern_lines, i, self):
                    if self.debug_mode:
                        print(f"✓ Match found at line {i+1} using {strategy_name}")
                    return [i]  # Return immediately when first match is found

            if self.debug_mode and isinstance(strategy, (ExactMatchStrategy, IndentAwareStrategy)):
                print("No match found with precise strategy")

        return []  # Return empty list if no match found

    def _check_exact_match(self, source_lines: List[str], pattern_lines: List[str], pos: int) -> bool:
        """Check for exact line-by-line match at position.
        
        Args:
            source_lines: List of source code lines
            pattern_lines: List of pattern lines to match
            pos: Position to check for match
            
        Returns:
            bool: True if exact match found, False otherwise
        """
        if pos + len(pattern_lines) > len(source_lines):
            return False
        return all(source_lines[pos + j] == pattern_lines[j] for j in range(len(pattern_lines)))