from typing import Tuple, List, Optional
import re
import sys
from pathlib import Path

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
        self.pattern_found = False
        self.allow_partial = allow_partial
        # Build indent map on initialization
        self.source_indent_map = self._build_indent_map(self.source_code)
        self.pattern_base_indent = len(self.get_indentation(self.search_pattern.splitlines()[0])) if self.search_pattern else 0
    
    def _build_indent_map(self, text: str) -> dict[int, int]:
        """Build a map of line numbers to indentation levels."""
        indent_map = {}
        for i, line in enumerate(text.splitlines()):
            if line.strip():  # Only track non-empty lines
                indent_map[i] = len(self.get_indentation(line))
        return indent_map

    def _find_best_match_position(self, positions: List[int], source_lines: List[str]) -> Optional[int]:
        """Find the best matching position based on indentation similarity."""
        if not positions:
            return None
            
        # Calculate indentation difference scores
        scores = []
        for pos in positions:
            indent_level = len(self.get_indentation(source_lines[pos]))
            indent_diff = abs(indent_level - self.pattern_base_indent)
            scores.append((indent_diff, pos))
            
        # Sort by indentation difference (smaller is better)
        scores.sort()
        return scores[0][1]

    @staticmethod
    def get_indentation(line: str) -> str:
        """Get the leading whitespace of a line."""
        return re.match(r'^[ \t]*', line).group()
    
    @staticmethod
    def get_first_non_empty_line(text: str) -> Tuple[str, int]:
        """Get first non-empty line and its index."""
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.strip():
                return line, i
        return '', 0
    
    def normalize_pattern(self, pattern: str, base_indent: str) -> str:
        """Remove base indentation from pattern to help with matching."""
        lines = pattern.splitlines()
        _, start_idx = self.get_first_non_empty_line(pattern)
        normalized = []
        
        for i, line in enumerate(lines):
            if i < start_idx or not line.strip():
                normalized.append('')
            else:
                normalized.append(line[len(base_indent):])
        
        return '\n'.join(normalized)
    
    def create_indented_replacement(self, match_indent: str) -> List[str]:
        """Create properly indented replacement lines."""
        search_first, search_start_idx = self.get_first_non_empty_line(self.search_pattern)
        replace_first, replace_start_idx = self.get_first_non_empty_line(self.replacement)
        
        search_indent = self.get_indentation(search_first)
        replace_indent = self.get_indentation(replace_first)
        
        replace_lines = self.replacement.splitlines()
        indented_replacement = []
        
        # Calculate indentation shifts
        context_shift = len(match_indent) - len(search_indent)
        pattern_shift = len(replace_indent) - len(search_indent)
        
        for i, line in enumerate(replace_lines):
            if i < replace_start_idx or not line.strip():
                indented_replacement.append('')
            else:
                line_indent = self.get_indentation(line)
                rel_indent = len(line_indent) - len(replace_indent)
                final_indent = ' ' * (len(match_indent) + rel_indent)
                indented_replacement.append(final_indent + line.lstrip())
        
        return indented_replacement
    
    def find_pattern(self) -> bool:
        """Search for pattern with indentation awareness, falling back to partial matches."""
        try:
            search_first, _ = self.get_first_non_empty_line(self.search_pattern)
            search_indent = self.get_indentation(search_first)
            
            normalized_pattern = self.normalize_pattern(self.search_pattern, search_indent)
            source_lines = self.source_code.splitlines()
            
            # Try exact matches first
            matches = []
            for i in range(len(source_lines)):
                if self._try_match_at_position(i, source_lines, normalized_pattern):
                    matches.append(i)
                    
            # If no exact matches, try partial matches
            if not matches:
                pattern_lines = normalized_pattern.splitlines()
                matches = self._find_partial_matches(source_lines, pattern_lines)
                
            return bool(self._find_best_match_position(matches, source_lines))
            
        except Exception:
            return False

    def replace(self) -> str:
        """Perform the search and replace operation, falling back to partial matches."""
        if self.replacement is None:
            if not self.find_pattern():
                raise PatternNotFoundException(
                    "The specified search pattern was not found in the source code"
                )
            return self.source_code
            
        search_first, _ = self.get_first_non_empty_line(self.search_pattern)
        search_indent = self.get_indentation(search_first)
        
        normalized_pattern = self.normalize_pattern(self.search_pattern, search_indent)
        source_lines = self.source_code.splitlines()
        result_lines = []
        
        # Try exact matches first
        matches = []
        pos = 0
        while pos < len(source_lines):
            if self._try_match_at_position(pos, source_lines, normalized_pattern):
                matches.append(pos)
            pos += 1
            
        # If no exact matches, try partial matches
        if not matches:
            pattern_lines = normalized_pattern.splitlines()
            matches = self._find_partial_matches(source_lines, pattern_lines)
            
        best_pos = self._find_best_match_position(matches, source_lines)
        if best_pos is None:
            raise PatternNotFoundException(
                "The specified search pattern was not found in the source code"
            )
            
        # Apply replacement
        i = 0
        while i < len(source_lines):
            if i == best_pos:
                self.pattern_found = True
                match_indent = self.get_indentation(source_lines[i])
                indented_replacement = self.create_indented_replacement(match_indent)
                result_lines.extend(indented_replacement)
                # For partial matches, only skip the matched line
                i += 1 if not matches else len(normalized_pattern.splitlines())
            else:
                result_lines.append(source_lines[i])
                i += 1
                
        return '\n'.join(result_lines)
    
    def _try_match_at_position(self, pos: int, source_lines: List[str], 
                             normalized_pattern: str) -> bool:
        """Try to match the pattern at the given position."""
        pattern_lines = normalized_pattern.splitlines()
        
        if pos + len(pattern_lines) > len(source_lines):
            return False
            
        pattern_first_line = next((l for l in pattern_lines if l.strip()), '')
        if not pattern_first_line:
            return False
            
        match_indent = self.get_indentation(source_lines[pos])
        current_indent = match_indent
        
        if self.allow_partial:
            # For partial matches, check if any non-empty pattern line is contained in the source
            return any(
                p.strip() in source_lines[pos + j].strip()
                for j, p in enumerate(pattern_lines)
                if p.strip() and pos + j < len(source_lines)
            )
        
        # Original exact matching logic
        for j, pattern_line in enumerate(pattern_lines):
            source_line = source_lines[pos + j]
            if not pattern_line and not source_line.strip():
                continue
                
            # Update current indentation if source line has different indentation
            source_indent = self.get_indentation(source_line)
            if len(source_indent) < len(current_indent):
                current_indent = source_indent
                
            if not source_line.startswith(current_indent + pattern_line):
                return False
                
        return True

    def _find_partial_matches(self, source_lines: List[str], pattern_lines: List[str]) -> List[int]:
        """Find positions of partial matches when no exact match is found."""
        matches = []
        pattern_core_lines = [l.strip() for l in pattern_lines if l.strip()]
        
        for i, line in enumerate(source_lines):
            if any(p in line.strip() for p in pattern_core_lines):
                matches.append(i)
        return matches

    def _handle_match(self, pos: int, source_lines: List[str], 
                     normalized_pattern: str, result_lines: List[str]) -> int:
        """Handle a successful pattern match."""
        self.pattern_found = True
        match_indent = self.get_indentation(source_lines[pos])
        indented_replacement = self.create_indented_replacement(match_indent)
        result_lines.extend(indented_replacement)
        return pos + len(normalized_pattern.splitlines())

    def debug_indentation(self, source: str, pattern: str):
        """Debug indentation issues between source and pattern"""
        def get_indent_info(text: str) -> str:
            indent = re.match(r'^[ \t]*', text).group()
            return ''.join('S' if c == ' ' else 'T' if c == '\t' else 'X' for c in indent)

        # Get base indentation levels
        source_first, _ = self.get_first_non_empty_line(source)
        pattern_first, _ = self.get_first_non_empty_line(pattern)
        source_base = self.get_indentation(source_first)
        pattern_base = self.get_indentation(pattern_first)

        print(f"Base indentation levels:")
        print(f"Source : {len(source_base)} chars ({get_indent_info(source_base)})")
        print(f"Pattern: {len(pattern_base)} chars ({get_indent_info(pattern_base)})")
        
        print("\nSource indentation map:")
        for i, line in enumerate(source.splitlines(), 1):
            indent = get_indent_info(line)
            print(f"{i:3d} | {indent:20} |{line}")

        print("\nPattern indentation map:")
        for i, line in enumerate(pattern.splitlines(), 1):
            indent = get_indent_info(line)
            print(f"{i:3d} | {indent:20} |{line}")

        # Try to find closest matches
        normalized = self.normalize_pattern(pattern, pattern_base)
        print("\nClosest partial matches:")
        source_lines = source.splitlines()
        for i in range(len(source_lines)):
            line = source_lines[i]
            if any(p.strip() in line.strip() for p in pattern.splitlines() if p.strip()):
                print(f"Line {i+1}: {line}")

def smart_search_replace(source_code: str, search_pattern: str, replacement: str) -> str:
    """Convenience function wrapper for SearchReplacer class."""
    replacer = SearchReplacer(source_code, search_pattern, replacement)
    return replacer.replace()


def parse_test_file(filepath: Path) -> List[dict]:
    """Parse a test file containing test cases. Replacement section is optional."""
    test_cases = []
    current_test = {}
    current_section = None
    current_content = []
    
    try:
        content = filepath.read_text()
        lines = content.splitlines()
        
        for line in lines:
            if line.startswith("Test: "):
                if current_test:
                    if current_section and current_content:
                        current_test[current_section] = "\n".join(current_content)
                    test_cases.append(current_test)
                current_test = {"name": line[6:].strip(), "expect_success": True}
                current_section = None
                current_content = []
            elif line.startswith("Original:"):
                if current_section and current_content:
                    current_test[current_section] = "\n".join(current_content)
                current_section = "source"
                current_content = []
            elif line.startswith("Search pattern:"):
                if current_section and current_content:
                    current_test[current_section] = "\n".join(current_content)
                current_section = "search"
                current_content = []
            elif line.startswith("Replacement:"):
                if current_section and current_content:
                    current_test[current_section] = "\n".join(current_content)
                current_section = "replacement"
                current_content = []
            elif not line.startswith("="):  # Skip separator lines
                if current_section:
                    current_content.append(line)
                    
        # Add last test case
        if current_test:
            if current_section and current_content:
                current_test[current_section] = "\n".join(current_content)
            test_cases.append(current_test)
            
        return test_cases
    except Exception as e:
        print(f"Error parsing test file: {e}")
        return []

def _run_tests(test_file: Optional[Path] = None) -> None:
    """Run test cases from file or use built-in examples"""
    if test_file:
        test_cases = parse_test_file(test_file)
        if not test_cases:
            print("No valid test cases found in file, using built-in tests")
            test_cases = [
                {
                    "name": "Different search/replace indentation",
                    "source": """def example():
    if condition:
        print("Hello")
        print("World")
    return True""",
                    "search": """    if condition:
        print("Hello")
        print("World")""",
                    "replacement": """if True:
    print("Different")
    print("Indent")""",
                    "expect_success": True
                },
                {
                    "name": "Fix broken indentation with different base indent",
                    "source": """def process_data(items):
    for item in items:
    if item.valid:
    process_item(item)
        validate(item)
            cleanup(item)
    return True""",
                    "search": """    for item in items:
    if item.valid:
    process_item(item)
        validate(item)
            cleanup(item)""",
                    "replacement": """for item in items:
    if item.valid:
        process_item(item)
        validate(item)
        cleanup(item)""",
                    "expect_success": True
                },
                {
                    "name": "Increased base indentation",
                    "source": """if True:
    if nested:
        do_something()""",
                    "search": """    if nested:
        do_something()""",
                    "replacement": """while nested:
    do_something_else()
    continue""",
                    "expect_success": True
                }
            ]
    else:
        test_cases = [
            {
                "name": "Different search/replace indentation",
                "source": """def example():
    if condition:
        print("Hello")
        print("World")
    return True""",
                "search": """    if condition:
        print("Hello")
        print("World")""",
                "replacement": """if True:
    print("Different")
    print("Indent")""",
                "expect_success": True
            },
            {
                "name": "Fix broken indentation with different base indent",
                "source": """def process_data(items):
    for item in items:
    if item.valid:
    process_item(item)
        validate(item)
            cleanup(item)
    return True""",
                "search": """    for item in items:
    if item.valid:
    process_item(item)
        validate(item)
            cleanup(item)""",
                "replacement": """for item in items:
    if item.valid:
        process_item(item)
        validate(item)
        cleanup(item)""",
                "expect_success": True
            },
            {
                "name": "Increased base indentation",
                "source": """if True:
    if nested:
        do_something()""",
                "search": """    if nested:
        do_something()""",
                "replacement": """while nested:
    do_something_else()
    continue""",
                "expect_success": True
            }
        ]

    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print("=" * 40)
        print("Original:")
        print(test['source'])
        print("\nSearch pattern:")
        print(test['search'])
        
        replacer = SearchReplacer(
            test['source'], 
            test['search'],
            test.get('replacement')  # May be None for search-only tests
        )
        
        try:
            if 'replacement' in test:
                result = replacer.replace()
                if test['expect_success']:
                    print("\nResult:")
                    print(result)
                else:
                    print("\nUnexpected success! Should have raised an error")
            else:
                # Search-only test case
                found = replacer.find_pattern()
                print("\nSearch result:", "Pattern found!" if found else "Pattern not found.")
        except PatternNotFoundException as e:
            if not test['expect_success']:
                print(f"\nExpected error: {e}")
            else:
                print(f"\nUnexpected error: {e}")
        except Exception as e:
            print(f"\nUnexpected error: {type(e).__name__}: {e}")
        print("=" * 40)

if __name__ == "__main__":
    test_file = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if test_file and not test_file.exists():
        print(f"Test file not found: {test_file}")
        sys.exit(1)
    _run_tests(test_file)