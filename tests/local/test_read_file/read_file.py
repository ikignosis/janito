def read_file(paths, from_line=None, to_line=None):
    """
    Unified file reading function that wraps view_file and read_files.

    Args:
        paths: str or list - single file path or list of file paths
        from_line: int - starting line number (1-based, for single file only)
        to_line: int - ending line number (1-based, for single file only)

    Returns:
        str: File content(s) with appropriate headers
    """
    import os

    # Handle single file with line range
    if isinstance(paths, str) and (from_line is not None or to_line is not None):
        return view_file(paths, from_line, to_line)

    # Handle multiple files or single file without line range
    if isinstance(paths, str):
        paths = [paths]

    # Use read_files for multiple files
    return read_files(paths)


def view_file(path, from_line=None, to_line=None):
    """Original view_file implementation - kept for backward compatibility"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total_lines = len(lines)

        if from_line is None:
            from_line = 1
        if to_line is None:
            to_line = total_lines

        # Convert to 0-based indexing
        from_idx = max(0, from_line - 1)
        to_idx = min(total_lines, to_line)

        selected_lines = lines[from_idx:to_idx]

        if from_line == 1 and to_line == total_lines:
            header = f"--- File: {path} | All lines (total: {total_lines}) ---"
        else:
            header = f"--- File: {path} | Lines: {from_line}-{min(to_line, total_lines)} (of {total_lines}) ---"

        return header + "\n" + "".join(selected_lines)

    except Exception as e:
        return f"Error reading file: {str(e)}"


def read_files(paths):
    """Original read_files implementation - kept for backward compatibility"""
    result = []

    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                result.append(f"--- File: {path} ---\n{content}")
        except Exception as e:
            result.append(f"Error reading file {path}: {str(e)}")

    return "\n\n".join(result)
