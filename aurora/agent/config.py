import json
import os
from pathlib import Path
from threading import Lock


class SingletonMeta(type):
    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class BaseConfig(metaclass=SingletonMeta):
    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def all(self):
        return self._data


class RuntimeConfig(BaseConfig):
    """In-memory only config, reset on restart"""
    pass


class FileConfig(BaseConfig):
    def __init__(self, path):
        super().__init__()
        self.path = Path(path).expanduser()
        self.load()

    def load(self):
        if self.path.exists():
            try:
                with open(self.path, 'r') as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}
        else:
            self._data = {}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, 'w') as f:
            json.dump(self._data, f, indent=2)


# Singleton instances
runtime_config = RuntimeConfig()
local_config = FileConfig(Path('.aurora/config.json'))
global_config = FileConfig(Path.home() / '.aurora/config.json')
