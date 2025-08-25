"""
Base classes for janito plugins.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Type

@dataclass
class PluginMetadata:
    name: str
    version: str
    description: str
    author: str
    license: str = "MIT"
    homepage: Optional[str] = None
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class PluginResource:
    name: str
    type: str
    description: str
    schema: Optional[Dict[str, Any]] = None

class Plugin(ABC):
    def __init__(self):
        self.metadata: PluginMetadata = self.get_metadata()

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        pass

    def get_tools(self):
        return []

    def get_commands(self):
        return {}

    def initialize(self):
        pass

    def cleanup(self):
        pass

    def get_config_schema(self):
        return {}

    def validate_config(self, config):
        return True

    def get_resources(self):
        return []
