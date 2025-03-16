"""
Configuration module for Janito.
Provides a singleton Config class to access configuration values.
"""
import os
import json
from pathlib import Path
import typer
from typing import Dict, Any, Optional

class Config:
    """Singleton configuration class for Janito."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._workspace_dir = os.getcwd()
            cls._instance._verbose = False
            cls._instance._history_context_count = 5
            cls._instance._ask_mode = False
            cls._instance._load_config()
        return cls._instance
        
    def _load_config(self) -> None:
        """Load configuration from file."""
        config_path = Path(self._workspace_dir) / ".janito" / "config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    if "history_context_count" in config_data:
                        self._history_context_count = config_data["history_context_count"]
                    if "debug_mode" in config_data:
                        self._verbose = config_data["debug_mode"]
                    if "ask_mode" in config_data:
                        self._ask_mode = config_data["ask_mode"]
            except Exception as e:
                print(f"Warning: Failed to load configuration: {str(e)}")
                
    def _save_config(self) -> None:
        """Save configuration to file."""
        config_dir = Path(self._workspace_dir) / ".janito"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.json"
        
        config_data = {
            "history_context_count": self._history_context_count,
            "verbose": self._verbose,
            "ask_mode": self._ask_mode
        }
        
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save configuration: {str(e)}")
    
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
                    raise ValueError(f"Failed to create workspace directory: {str(e)}") from e
            else:
                raise ValueError(f"Workspace directory does not exist: {path}")
        
        self._workspace_dir = path
    
    @property
    def verbose(self) -> bool:
        """Get the verbose mode status."""
        return self._verbose
    
    @verbose.setter
    def verbose(self, value: bool) -> None:
        """Set the verbose mode status."""
        self._verbose = value
    
    # For backward compatibility
    @property
    def debug_mode(self) -> bool:
        """Get the debug mode status (alias for verbose)."""
        return self._verbose
    
    @debug_mode.setter
    def debug_mode(self, value: bool) -> None:
        """Set the debug mode status (alias for verbose)."""
        self._verbose = value

    @property
    def history_context_count(self) -> int:
        """Get the number of previous conversations to include in context."""
        return self._history_context_count
        
    @history_context_count.setter
    def history_context_count(self, count: int) -> None:
        """Set the number of previous conversations to include in context."""
        if count < 0:
            raise ValueError("History context count must be a non-negative integer")
        self._history_context_count = count
        self._save_config()
        
    @property
    def ask_mode(self) -> bool:
        """Get the ask mode status."""
        return self._ask_mode
        
    @ask_mode.setter
    def ask_mode(self, value: bool) -> None:
        """Set the ask mode status."""
        self._ask_mode = value
        self._save_config()

# Convenience function to get the config instance
def get_config() -> Config:
    """Get the singleton Config instance."""
    return Config()
