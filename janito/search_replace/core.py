from typing import Optional, List
from pathlib import Path
import os
from datetime import datetime
from .logger import log_match, log_failure
from .searcher import Searcher
from .replacer import Replacer

class PatternNotFoundException(Exception):
    """Raised when the search pattern is not found in the source code."""
    pass

class SearchReplacer:
    """Handles indentation-aware search and replace operations on Python source code."""

    def __init__(self, source_code: str, search_pattern: str, replacement: Optional[str] = None, 
                 file_ext: Optional[str] = None, debug: bool = False):
        """Initialize with source code and patterns."""
        self.source_code = source_code.rstrip()
        self.search_pattern = search_pattern.rstrip()
        self.replacement = replacement.rstrip() if replacement else None
        self.file_ext = file_ext.lower() if file_ext else None
        self.pattern_found = False
        self.searcher = Searcher(debug=debug)
        self.replacer = Replacer(debug=debug)

        # Initialize pattern base indent
        first_line, _ = self.searcher.get_first_non_empty_line(self.search_pattern)
        self.pattern_base_indent = len(self.searcher.get_indentation(first_line)) if first_line else 0

    def find_pattern(self) -> bool:
        """Search for pattern with indentation awareness."""
        try:
            source_lines = self.source_code.splitlines()
            search_first, _ = self.searcher.get_first_non_empty_line(self.search_pattern)
            search_indent = self.searcher.get_indentation(search_first)
            normalized_pattern = self.searcher.normalize_pattern(self.search_pattern, search_indent)
            matches = self._find_matches(source_lines, normalized_pattern)
            return bool(matches)  # Just check if we got any match
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
        if not matches:
            # Log failed match if not in debug mode
            if not self.searcher.debug_mode:
                log_failure(self.file_ext)
            raise PatternNotFoundException("Pattern not found")

        match_pos = matches[0]  # We know there's exactly one match if we get here

        if self.searcher.debug_mode:
            pattern_lines = len(normalized_pattern.splitlines())
            replacement_lines = len(self.replacement.splitlines()) if self.replacement else 0
            print(f"\n[DEBUG] Replacing {pattern_lines} lines with {replacement_lines} lines")
            context_start = max(0, match_pos - 2)
            context_end = min(len(source_lines), match_pos + len(normalized_pattern.splitlines()) + 2)
            print("\n[DEBUG] Context before replacement:")
            for i in range(context_start, context_end):
                prefix = ">>> " if context_start <= i < match_pos + len(normalized_pattern.splitlines()) else "    "
                print(f"[DEBUG] {prefix}Line {i + 1}: {source_lines[i]}")

        result = self._apply_replacement(source_lines, match_pos, normalized_pattern)

        if self.searcher.debug_mode:
            print("\n[DEBUG] Context after replacement:")
            result_lines = result.splitlines()
            for i in range(context_start, context_end):
                prefix = ">>> " if context_start <= i < match_pos + len(self.replacement.splitlines()) else "    "
                print(f"[DEBUG] {prefix}Line {i + 1}: {result_lines[i]}")

        return result

    def _find_matches(self, source_lines, normalized_pattern):
        """Find all possible matches in source."""
        pattern_lines = normalized_pattern.splitlines()
        return self.searcher._find_matches(source_lines, pattern_lines, self.file_ext)

    def _apply_replacement(self, source_lines, match_pos, normalized_pattern):
        """Apply replacement at the matched position."""
        result_lines = []
        i = 0
        while i < len(source_lines):
            if i == match_pos:
                self.pattern_found = True
                if not self.searcher.debug_mode:
                    log_match("Strategy", self.file_ext)
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

    # Remove _try_match_at_position method as it's redundant