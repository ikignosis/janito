"""
Configuration module for Janito.
Provides a singleton Config class to access configuration values.
"""
import os
from pathlib import Path
from typing import Optional
import typer

class Config:
    """Singleton configuration class for Janito."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._workspace_dir = os.getcwd()
        return cls._instance
    
    @property
    def workspace_dir(self) -> str:
        """Get the current workspace directory."""
        return self._workspace_dir
    
    @workspace_dir.setter
    def workspace_dir(self, path: str) -> None:
        """Set the workspace directory."""
        # Convert to absolute path if not already
        if not os.path.isabs(path):
            path = os.path.normpath(os.path.abspath(path))
        else:
            # Ensure Windows paths are properly formatted
            path = os.path.normpath(path)
        
        # Check if the directory exists
        if not os.path.isdir(path):
            create_dir = typer.confirm(f"Workspace directory does not exist: {path}\nDo you want to create it?")
            if create_dir:
                try:
                    os.makedirs(path, exist_ok=True)
                    print(f"Created workspace directory: {path}")
                except Exception as e:
                    raise ValueError(f"Failed to create workspace directory: {str(e)}")
            else:
                raise ValueError(f"Workspace directory does not exist: {path}")
        
        self._workspace_dir = path

# Convenience function to get the config instance
def get_config() -> Config:
    """Get the singleton Config instance."""
    return Config()
