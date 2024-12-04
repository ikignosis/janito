from typing import Optional
import os

class ConfigManager:
    _instance = None
    
    def __init__(self):
        self.debug = False
        self.verbose = False
        self.debug_line = None  # Add this line
        
    @classmethod
    def get_instance(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def set_debug(self, enabled: bool) -> None:
        self.debug = enabled

    def set_verbose(self, enabled: bool) -> None:
        self.verbose = enabled
        
    def set_debug_line(self, line: Optional[int]) -> None:  # Add this method
        self.debug_line = line
        
    def should_debug_line(self, line: int) -> bool:  # Add this method
        """Return True if we should show debug for this line number"""
        return self.debug and (self.debug_line is None or self.debug_line == line)

# Create a singleton instance
config = ConfigManager.get_instance()