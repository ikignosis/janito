
def adjust_indentation(original: str, replacement: str) -> str:
    """Adjust replacement text indentation based on original text"""
    if not original or not replacement:
        return replacement
        
    # Get first non-empty lines to compare indentation
    orig_lines = original.splitlines()
    repl_lines = replacement.splitlines()
    
    orig_first = next((l for l in orig_lines if l.strip()), '')
    repl_first = next((l for l in repl_lines if l.strip()), '')
    
    # Calculate indentation difference
    orig_indent = len(orig_first) - len(orig_first.lstrip())
    repl_indent = len(repl_first) - len(repl_first.lstrip())
    indent_delta = orig_indent - repl_indent
    
    if indent_delta == 0:
        return replacement
        
    # Adjust indentation for all lines
    adjusted_lines = []
    for line in repl_lines:
        if not line.strip():  # Preserve empty lines
            adjusted_lines.append(line)
            continue
        
        current_indent = len(line) - len(line.lstrip())
        new_indent = max(0, current_indent + indent_delta)
        adjusted_lines.append(' ' * new_indent + line.lstrip())
    
    return '\n'.join(adjusted_lines)