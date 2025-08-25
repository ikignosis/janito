class BaseTool:
    """
    Base class for all tools.
    
    Parameters:
        path (str): Target file path for file operations
        content (str): File content to write or process
        overwrite (bool): Whether to overwrite existing files (default: False)
        sources (str): Source file(s) to copy from
        target (str): Destination path for copy operations
        recursive (bool): Whether to process directories recursively
        from_line (int): Starting line number for file reading
        to_line (int): Ending line number for file reading
        search_text (str): Text to search for in files
        replacement_text (str): Text to replace search matches with
        use_regex (bool): Whether to treat search as regex pattern
        case_sensitive (bool): Whether search should be case sensitive
        max_depth (int): Maximum directory depth to search
        include_gitignored (bool): Whether to include .gitignored files
        timeout (int): Timeout in seconds for operations
        require_confirmation (bool): Whether to require user confirmation
        data (dict): Chart data for visualization tools
        title (str): Chart title
        width (int): Chart width in pixels
        height (int): Chart height in pixels
        query (str): Search query for text search
        paths (str): Directory or file paths to search in
        src_path (str): Source path for move operations
        dest_path (str): Destination path for move operations
        code (str): Python code to execute
        pattern (str): File pattern to match (e.g., '*.py')
    """

    tool_name: str = ""

    def __init__(self):
        if not self.tool_name:
            self.tool_name = self.__class__.__name__.lower()

    def run(self, *args, **kwargs) -> str:
        """Execute the tool."""
        raise NotImplementedError
