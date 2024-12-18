from typing import Optional, List
import os
from pathlib import Path

class ConfigManager:
    _instance = None

    def __init__(self):
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
        self.skipwork: bool = False

    @classmethod
    def get_instance(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_debug(self, enabled: bool) -> None:
        self.debug = enabled

    def set_verbose(self, enabled: bool) -> None:
        self.verbose = enabled

    def set_debug_line(self, line: Optional[int]) -> None:
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
        """Set raw output mode"""
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
        """Set auto apply mode"""
        self.auto_apply = enabled

    def set_tui(self, enabled: bool) -> None:
        """Set TUI mode"""
        self.tui = enabled

    def set_recursive(self, paths: Optional[List[Path]]) -> None:
        """Set paths to scan recursively

        Args:
            paths: List of directory paths to scan recursively, or None to disable recursive scanning
        """
        self.recursive = paths

    def set_skipwork(self, enabled: bool) -> None:
        """Set skipwork flag to skip scanning workspace_dir"""
        self.skipwork = enabled

# Create a singleton instance
config = ConfigManager.get_instance()