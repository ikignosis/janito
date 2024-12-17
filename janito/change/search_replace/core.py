from typing import Optional
from pathlib import Path
from .searcher import Searcher
from .replacer import Replacer
from .parser import parse_test_file

class PatternNotFoundException(Exception):
    """Raised when the search pattern is not found in the source code."""
    pass

class SearchReplacer:
    """Handles indentation-aware search and replace operations on Python source code."""

    def __init__(self, source_code: str, search_pattern: str, replacement: Optional[str] = None, allow_partial: bool = True):
        """Initialize with source code and patterns."""
        self.source_code = source_code.rstrip()
        self.search_pattern = search_pattern.rstrip()
        self.replacement = replacement.rstrip() if replacement else None
        self.allow_partial = allow_partial
        self.pattern_found = False
        self.searcher = Searcher()
        self.replacer = Replacer()

        # Initialize pattern base indent
        first_line, _ = self.searcher.get_first_non_empty_line(self.search_pattern)
        self.pattern_base_indent = len(self.searcher.get_indentation(first_line)) if first_line else 0

    def find_pattern(self) -> bool:
        """Search for pattern with indentation awareness."""
        try:
            # Try exact matching first
            exact_matches = self.searcher.exact_match(self.source_code, self.search_pattern)
            if exact_matches:
                if self.searcher.debug_mode:
                    print("[DEBUG] Found pattern using exact match")
                return True

            # Fall back to flexible matching
            if self.searcher.debug_mode:
                print("[DEBUG] No exact match found, trying flexible matching")
            search_first, _ = self.searcher.get_first_non_empty_line(self.search_pattern)
            search_indent = self.searcher.get_indentation(search_first)
            normalized_pattern = self.searcher.normalize_pattern(self.search_pattern, search_indent)

            source_lines = self.source_code.splitlines()
            matches = self._find_matches(source_lines, normalized_pattern)

            return bool(self.searcher._find_best_match_position(matches, source_lines, self.pattern_base_indent))
        except Exception:
            return False

    def replace(self) -> str:
        """Perform the search and replace operation."""
        if self.replacement is None:
            if not self.find_pattern():
                raise PatternNotFoundException("Pattern not found")
            return self.source_code

        source_lines = self.source_code.splitlines()
        search_first, _ = self.searcher.get_first_non_empty_line(self.search_pattern)
        search_indent = self.searcher.get_indentation(search_first)
        normalized_pattern = self.searcher.normalize_pattern(self.search_pattern, search_indent)

        matches = self._find_matches(source_lines, normalized_pattern)
        best_pos = self.searcher._find_best_match_position(matches, source_lines, self.pattern_base_indent)

        if best_pos is None:
            raise PatternNotFoundException("Pattern not found")

        return self._apply_replacement(source_lines, best_pos, normalized_pattern)

    def _find_matches(self, source_lines, normalized_pattern):
        """Find all possible matches in source."""
        # Try exact matching first
        exact_matches = self.searcher.exact_match('\n'.join(source_lines), self.search_pattern)
        if exact_matches:
            if self.searcher.debug_mode:
                print("[DEBUG] Using exact matches for replacement")
            return exact_matches

        # Fall back to flexible matching
        if self.searcher.debug_mode:
            print("[DEBUG] Falling back to flexible matching")
        matches = []
        for i in range(len(source_lines)):
            if self._try_match_at_position(i, source_lines, normalized_pattern):
                matches.append(i)
        return matches

    def _apply_replacement(self, source_lines, match_pos, normalized_pattern):
        """Apply replacement at the matched position."""
        result_lines = []
        i = 0
        while i < len(source_lines):
            if i == match_pos:
                self.pattern_found = True
                match_indent = self.searcher.get_indentation(source_lines[i])
                replacement_lines = self.replacer.create_indented_replacement(
                    match_indent, self.search_pattern, self.replacement
                )
                result_lines.extend(replacement_lines)
                i += len(normalized_pattern.splitlines())
            else:
                result_lines.append(source_lines[i])
                i += 1
        return '\n'.join(result_lines)

    def _try_match_at_position(self, pos, source_lines, normalized_pattern):
        """Check if pattern matches at given position."""
        pattern_lines = normalized_pattern.splitlines()
        if pos + len(pattern_lines) > len(source_lines):
            return False

        if self.allow_partial:
            return any(
                p.strip() in source_lines[pos + j].strip()
                for j, p in enumerate(pattern_lines)
                if p.strip() and pos + j < len(source_lines)
            )

        match_indent = self.searcher.get_indentation(source_lines[pos])
        for j, pattern_line in enumerate(pattern_lines):
            if not pattern_line and not source_lines[pos + j].strip():
                continue
            if not source_lines[pos + j].startswith(match_indent + pattern_line):
                return False
        return True