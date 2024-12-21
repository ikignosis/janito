def find_function_for_line(source: str, target_line: int) -> Optional[Tuple[str, int, int, List[str]]]:
    """
    Find which function/method contains a specific line of code, including nested functions and class methods.
    
    Args:
        source: Either a file path or a string containing Python code
        target_line: Line number to look for
        
    Returns:
        Tuple of (symbol_path, start_line, end_line, scope_types) if found, None otherwise
        symbol_path is the full path (e.g., "MyClass.my_method.inner_func")
        scope_types is a list of scope types (e.g., ["class", "method", "function"])
    """
    try:
        if os.path.isfile(source):
            with open(source, 'r') as file:
                code = file.read()
        else:
            code = source
            
        tree = ast.parse(code)
    except Exception as e:
        raise ValueError(f"Failed to parse Python code: {str(e)}")

    def find_last_line(node):
        """Find the last line number in a node by traversing all children."""
        max_line = node.lineno
        
        # For nodes that have end_lineno, use it
        if hasattr(node, 'end_lineno') and node.end_lineno is not None:
            max_line = max(max_line, node.end_lineno)
            
        # Recursively check all child nodes
        for child in ast.iter_child_nodes(node):
            if hasattr(child, 'lineno'):
                child_last = find_last_line(child)
                max_line = max(max_line, child_last)
                
        return max_line

    class ScopeInfo:
        def __init__(self, path: List[str], types: List[str], node: Union[ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef]):
            self.path = path
            self.types = types
            self.node = node
            self.start = node.lineno
            self.end = find_last_line(node)

    def find_scopes(node, parent_path=None, scope_types=None) -> List[ScopeInfo]:
        """Find all scopes in the code and their ranges."""
        if parent_path is None:
            parent_path = []
        if scope_types is None:
            scope_types = []
            
        scopes = []
        current_scope = None
        current_name = None
        
        if isinstance(node, ast.ClassDef):
            current_scope = "class"
            current_name = node.name
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if scope_types and scope_types[-1] == "class":
                current_scope = "method"
            else:
                current_scope = "function"
            current_name = node.name
            
        if current_name and current_scope:
            current_path = parent_path + [current_name]
            current_types = scope_types + [current_scope]
            scopes.append(ScopeInfo(current_path, current_types, node))
            
            # Process children with updated path
            for child in ast.iter_child_nodes(node):
                scopes.extend(find_scopes(child, current_path, current_types))
        else:
            # Process children with same path
            for child in ast.iter_child_nodes(node):
                scopes.extend(find_scopes(child, parent_path, scope_types))
                
        return scopes

    # Find all scopes
    all_scopes = find_scopes(tree)
    
    # Find the innermost scope containing the target line
    matching_scopes = [
        scope for scope in all_scopes 
        if scope.start <= target_line <= scope.end
    ]
    
    # Sort by scope depth (most nested first) and start line (latest first)
    matching_scopes.sort(key=lambda s: (-len(s.path), -s.start))
    
    if matching_scopes:
        innermost = matching_scopes[0]
        return ('.'.join(innermost.path), innermost.start, innermost.end, innermost.types)
    
    return None