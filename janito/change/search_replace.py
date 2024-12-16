from typing import Tuple, List, Optional
import re

class PatternNotFoundException(Exception):
    """Raised when the search pattern is not found in the source code."""
    pass

def smart_search_replace(source_code: str, search_pattern: str, replacement: str) -> str:
    """
    Perform an indentation-aware search and replace operation on Python source code.
    
    The function matches based on the indentation of the first line of the search pattern
    and applies the same relative indentation to the replacement, while handling differences
    between search and replacement base indentation levels.
    
    Args:
        source_code (str): The original source code to modify
        search_pattern (str): The code pattern to search for
        replacement (str): The code to insert
        
    Returns:
        str: Modified source code with the replacement applied
        
    Raises:
        PatternNotFoundException: If the search pattern isn't found in the source code
        
    Example:
        >>> source = '''def test():
        ...     if nested:
        ...         print("test")'''
        >>> pattern = '''if nested:
        ...         print("test")'''
        >>> replacement = '''while nested:
        ...     print("changed")'''
        >>> print(smart_search_replace(source, pattern, replacement))
        def test():
            while nested:
                print("changed")
    """
    def get_indentation(line: str) -> str:
        """Get the leading whitespace of a line."""
        return re.match(r'^[ \t]*', line).group()

    def get_first_non_empty_line(text: str) -> Tuple[str, int]:
        """Get first non-empty line and its index."""
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.strip():
                return line, i
        return '', 0

    # Normalize inputs
    source_code = source_code.rstrip()
    search_pattern = search_pattern.rstrip()
    replacement = replacement.rstrip()

    # Get first non-empty lines and their indentation
    search_first_line, search_start_idx = get_first_non_empty_line(search_pattern)
    replace_first_line, replace_start_idx = get_first_non_empty_line(replacement)
    search_indent = get_indentation(search_first_line)
    replace_indent = get_indentation(replace_first_line)

    # Prepare normalized pattern for searching
    pattern_lines = search_pattern.splitlines()
    normalized_pattern = []
    
    # Remove base indentation from pattern to help with matching
    for i, line in enumerate(pattern_lines):
        if i < search_start_idx or not line.strip():
            normalized_pattern.append('')
        else:
            line_indent = get_indentation(line)
            normalized_pattern.append(line[len(search_indent):])
    
    normalized_pattern = '\n'.join(normalized_pattern)
    
    # Process source code
    source_lines = source_code.splitlines()
    result_lines = []
    i = 0
    pattern_found = False
    
    while i < len(source_lines):
        # Try to match the normalized pattern
        matched = True
        match_indent = ''
        pattern_lines = normalized_pattern.splitlines()
        
        if i + len(pattern_lines) <= len(source_lines):
            # Get indentation from the first non-empty line at current position
            current_pos = i
            while current_pos < len(source_lines) and not source_lines[current_pos].strip():
                current_pos += 1
                
            if current_pos < len(source_lines):
                match_indent = get_indentation(source_lines[current_pos])
                
                # Check if pattern matches at current position
                for j, pattern_line in enumerate(pattern_lines):
                    if not pattern_line and not source_lines[i + j].strip():
                        continue
                    source_line = source_lines[i + j]
                    if not source_line.startswith(match_indent + pattern_line):
                        matched = False
                        break
        else:
            matched = False
        
        if matched:
            pattern_found = True
            # Prepare replacement with correct indentation
            replace_lines = replacement.splitlines()
            indented_replacement = []
            
            # Calculate both indentation shifts
            context_shift = len(match_indent) - len(search_indent)  # Found vs Search
            pattern_shift = len(replace_indent) - len(search_indent)  # Replace vs Search
            
            for j, line in enumerate(replace_lines):
                if j < replace_start_idx or not line.strip():
                    indented_replacement.append('')
                else:
                    # Get the line's indent relative to replacement's first line
                    line_indent = get_indentation(line)
                    rel_indent = len(line_indent) - len(replace_indent)
                    
                    # Apply both shifts to maintain relative structure
                    final_indent = ' ' * (len(match_indent) + rel_indent)
                    indented_replacement.append(final_indent + line.lstrip())
            
            result_lines.extend(indented_replacement)
            i += len(pattern_lines)
        else:
            result_lines.append(source_lines[i])
            i += 1
    
    if not pattern_found:
        raise PatternNotFoundException(
            "The specified search pattern was not found in the source code"
        )
        
    return '\n'.join(result_lines)


def _run_tests():
    """Run test cases."""
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
        print("\nReplacement:")
        print(test['replacement'])
        
        try:
            result = smart_search_replace(
                test['source'],
                test['search'],
                test['replacement']
            )
            if test['expect_success']:
                print("\nResult:")
                print(result)
            else:
                print("\nUnexpected success! Should have raised an error")
        except PatternNotFoundException as e:
            if not test['expect_success']:
                print(f"\nExpected error: {e}")
            else:
                print(f"\nUnexpected error: {e}")
        except Exception as e:
            print(f"\nUnexpected error: {type(e).__name__}: {e}")
        print("=" * 40)


if __name__ == "__main__":
    _run_tests()