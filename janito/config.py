from typing import Optional, List
import os
from pathlib import Path

class ConfigManager:
    """Singleton configuration manager for the application."""

    _instance = None

    def __init__(self):
        """Initialize configuration with default values."""
        self.debug = False
        self.verbose = False
        self.debug_line = None
        self.test_cmd = os.getenv('JANITO_TEST_CMD')
        self.workspace_dir = Path.cwd()
        self.raw = False
        self.include: List[Path] = []
        self.recursive: List[Path] = []
        self.auto_apply: bool = False
        self.tui: bool = False
        self.skip_work: bool = False

    @classmethod
    def get_instance(cls) -> "ConfigManager":
        """Return the singleton instance of ConfigManager.
        
        Returns:
            ConfigManager: The singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_debug(self, enabled: bool) -> None:
        """Set debug mode.
        
        Args:
            enabled: True to enable debug mode, False to disable
        """
        self.debug = enabled

    def set_verbose(self, enabled: bool) -> None:
        """Set verbose output mode.
        
        Args:
            enabled: True to enable verbose output, False to disable
        """
        self.verbose = enabled

    def set_debug_line(self, line: Optional[int]) -> None:
        """Set specific line number for debug output.
        
        Args:
            line: Line number to debug, or None for all lines
        """
        self.debug_line = line

    def should_debug_line(self, line: int) -> bool:
        """Return True if we should show debug for this line number"""
        return self.debug and (self.debug_line is None or self.debug_line == line)

    def set_test_cmd(self, cmd: Optional[str]) -> None:
        """Set the test command, overriding environment variable"""
        self.test_cmd = cmd if cmd is not None else os.getenv('JANITO_TEST_CMD')

    def set_workspace_dir(self, path: Optional[Path]) -> None:
        """Set the workspace directory"""
        self.workspace_dir = path if path is not None else Path.cwd()

    def set_raw(self, enabled: bool) -> None:
        """Set raw output mode.
        
        Args:
            enabled: True to enable raw output mode, False to disable
        """
        self.raw = enabled

    def set_include(self, paths: Optional[List[Path]]) -> None:
        """
        Set additional paths to include.

        Args:
            paths: List of paths to include

        Raises:
            ValueError: If duplicate paths are provided
        """
        if paths is None:
            self.include = []
            return

        # Convert paths to absolute and resolve symlinks
        resolved_paths = [p.absolute().resolve() for p in paths]

        # Check for duplicates
        seen_paths = set()
        unique_paths = []

        for path in resolved_paths:
            if path in seen_paths:
                raise ValueError(f"Duplicate path provided: {path}")
            seen_paths.add(path)
            unique_paths.append(path)

        self.include = unique_paths

    def set_auto_apply(self, enabled: bool) -> None:
        """Set auto apply mode for changes.
        
        Args:
            enabled: True to enable auto apply mode, False to disable
        """
        self.auto_apply = enabled

    def set_tui(self, enabled: bool) -> None:
        """Set Text User Interface mode.
        
        Args:
            enabled: True to enable TUI mode, False to disable
        """
        self.tui = enabled

    def set_recursive(self, paths: Optional[List[Path]]) -> None:
        """Set paths to scan recursively

        Args:
            paths: List of directory paths to scan recursively, or None to disable recursive scanning
        """
        self.recursive = paths

    def set_skip_work(self, enabled: bool) -> None:
        """Set whether to skip scanning the workspace directory.
        
        Args:
            enabled: True to skip workspace directory, False to include it
        """
        self.skip_work = enabled

# Create a singleton instance
config = ConfigManager.get_instance()