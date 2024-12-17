from typing import List, Optional
import re

class Searcher:
    """Handles pattern searching in source code with indentation awareness."""
    debug_mode = True

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
        """Find the best matching position based on indentation similarity."""
        if self.debug_mode:
            print(f"[DEBUG] Finding best match among positions: {positions}")
            print(f"[DEBUG] Pattern base indentation: {pattern_base_indent}")

        if not positions:
            return None

        # Calculate indentation difference scores
        scores = []
        for pos in positions:
            indent_level = len(self.get_indentation(source_lines[pos]))
            indent_diff = abs(indent_level - pattern_base_indent)
            scores.append((indent_diff, pos))
            if self.debug_mode:
                print(f"[DEBUG] Position {pos}: indent_level={indent_level}, diff={indent_diff}")

        # Sort by indentation difference (smaller is better)
        scores.sort()
        if self.debug_mode:
            print(f"[DEBUG] Selected best match at position: {scores[0][1]}")
        return scores[0][1]

    def exact_match(self, source: str, pattern: str) -> List[int]:
        """Perform exact line-by-line matching, preserving all whitespace except newlines."""
        if self.debug_mode:
            print(f"[DEBUG] Starting exact match")
            print(f"[DEBUG] Pattern:\n{pattern}")

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
                if self.debug_mode:
                    print(f"[DEBUG] Found exact match at line {i}")
                matches.append(i)

        if self.debug_mode:
            print(f"[DEBUG] Found {len(matches)} exact matches")
            
        return matches