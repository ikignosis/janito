from typing import List
from .searcher import Searcher

class Replacer:
    """Handles replacement operations with proper indentation."""

    def __init__(self):
        self.searcher = Searcher()

    def create_indented_replacement(self, match_indent: str, search_pattern: str, replacement: str) -> List[str]:
        """Create properly indented replacement lines."""
        search_first, search_start_idx = self.searcher.get_first_non_empty_line(search_pattern)
        replace_first, replace_start_idx = self.searcher.get_first_non_empty_line(replacement)

        search_indent = self.searcher.get_indentation(search_first)
        replace_indent = self.searcher.get_indentation(replace_first)

        replace_lines = replacement.splitlines()
        indented_replacement = []

        # Calculate indentation shifts
        context_shift = len(match_indent) - len(search_indent)
        pattern_shift = len(replace_indent) - len(search_indent)

        for i, line in enumerate(replace_lines):
            if i < replace_start_idx or not line.strip():
                indented_replacement.append('')
            else:
                line_indent = self.searcher.get_indentation(line)
                rel_indent = len(line_indent) - len(replace_indent)
                final_indent = ' ' * (len(match_indent) + rel_indent)
                indented_replacement.append(final_indent + line.lstrip())

        return indented_replacement