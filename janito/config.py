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
        self.workdir = Path.cwd()
        self.raw = False
        self.include: List[Path] = []
        self.auto_apply: bool = False
        self.tui: bool = False
        
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

    def set_workdir(self, path: Optional[Path]) -> None:
        """Set the working directory"""
        self.workdir = path if path is not None else Path.cwd()

    def set_raw(self, enabled: bool) -> None:
        """Set raw output mode"""
        self.raw = enabled

    def set_include(self, paths: Optional[List[Path]]) -> None:
        """Set additional paths to include"""
        self.include = paths if paths is not None else []

    def set_auto_apply(self, enabled: bool) -> None:
        """Set auto apply mode"""
        self.auto_apply = enabled

    def set_tui(self, enabled: bool) -> None:
        """Set TUI mode"""
        self.tui = enabled

# Create a singleton instance
config = ConfigManager.get_instance()