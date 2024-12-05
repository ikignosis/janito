from typing import Optional
import os

class ConfigManager:
    _instance = None
    
    def __init__(self):
        self.debug = False
        self.verbose = False
        self.debug_line = None
        self.test_cmd = os.getenv('JANITO_TEST_CMD')
        
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

# Create a singleton instance
config = ConfigManager.get_instance()