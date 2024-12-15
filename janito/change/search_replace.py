class PatternNotFoundException(Exception):
    """Raised when the search pattern is not found in the source code."""
    pass

def smart_search_replace(source_code: str, search_pattern: str, replacement: str) -> str:
    """
    Perform a search and replace operation that's aware of indentation.
    
    Args:
        source_code (str): The original source code with indentation
        search_pattern (str): The pattern to search for (may or may not have indentation)
        replacement (str): The text to replace matches with. If the first line has indentation,
                         the replacement is used as-is. Otherwise, the indentation from the
                         matched pattern is applied.
        
    Returns:
        str: The modified source code with replacements made
        
    Raises:
        PatternNotFoundException: If the search pattern is not found in the source code
    """
    def normalize_indentation(text: str) -> tuple[str, list[str]]:
        """
        Removes indentation from text while preserving the indentation pattern.
        Returns the normalized text and list of indentation strings.
        """
        text = text.strip()
        lines = text.splitlines()
        indentations = []
        normalized_lines = []
        
        for line in lines:
            # Find leading whitespace
            indent = ''
            for char in line:
                if char in ' \t':
                    indent += char
                else:
                    break
            indentations.append(indent)
            normalized_lines.append(line.lstrip())
            
        return '\n'.join(normalized_lines), indentations

    def apply_indentation(text: str, indentations: list[str]) -> str:
        """
        If the first line has indentation, returns the text as-is.
        Otherwise, applies the stored indentation pattern to the text.
        """
        text = text.rstrip()
        lines = text.splitlines()
        
        # Check if first line has indentation
        if lines and (lines[0].startswith(' ') or lines[0].startswith('\t')):
            return text
            
        # Apply indentation pattern as before
        if len(lines) != len(indentations):
            indentations = [indentations[0]] * len(lines)
        
        indented_lines = [indent + line 
                         for indent, line in zip(indentations, lines)]
        return '\n'.join(indented_lines)

    # Normalize inputs (only strip trailing whitespace from replacement)
    source_code = source_code.strip()
    search_pattern = search_pattern.strip()
    replacement = replacement.rstrip()
    
    # Normalize the search pattern (remove indentation but store it)
    normalized_pattern, pattern_indents = normalize_indentation(search_pattern)
    
    # Split source code into lines for processing
    source_lines = source_code.splitlines()
    result_lines = []
    i = 0
    pattern_found = False
    
    while i < len(source_lines):
        # Try to match the normalized pattern at current position
        matched = True
        match_indents = []
        pattern_lines = normalized_pattern.splitlines()
        
        if i + len(pattern_lines) <= len(source_lines):
            for j, pattern_line in enumerate(pattern_lines):
                current_line = source_lines[i + j]
                indent = ''
                for char in current_line:
                    if char in ' \t':
                        indent += char
                    else:
                        break
                
                if current_line.lstrip() != pattern_line:
                    matched = False
                    break
                    
                match_indents.append(indent)
        else:
            matched = False
        
        if matched:
            pattern_found = True
            # Apply the matched indentation to the replacement
            indented_replacement = apply_indentation(replacement, match_indents)
            result_lines.extend(indented_replacement.splitlines())
            i += len(pattern_lines)
        else:
            result_lines.append(source_lines[i])
            i += 1
    
    if not pattern_found:
        raise PatternNotFoundException("The specified search pattern was not found in the source code")
        
    return '\n'.join(result_lines)


# Example usage with error handling
if __name__ == "__main__":
    print("Example 1: Successful replacement")
    try:
        source = """def example():
    if condition:
        print("Hello")
        print("World")
    return True"""

        search = """if condition:
    print("Hello")
    print("World")"""

        replacement = """for i in range(3):
    print(f"Hello {i}")"""

        result = smart_search_replace(source, search, replacement)
        print("\nOriginal code:")
        print(source)
        print("\nResult:")
        print(result)
        
    except PatternNotFoundException as e:
        print(f"Error: {e}")

    print("\nExample 2: Pattern not found")
    try:
        source = """def example():
    print("Hello")
    return True"""

        search = """if condition:
    print("Hello")"""

        replacement = """for i in range(3):
    print(i)"""

        result = smart_search_replace(source, search, replacement)
        print("\nOriginal code:")
        print(source)
        print("\nResult:")
        print(result)
        
    except PatternNotFoundException as e:
        print(f"Error: {e}")