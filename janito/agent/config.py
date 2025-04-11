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


CONFIG_OPTIONS = {
    "api_key": "API key for OpenAI-compatible service (required)",
    "model": "Model name to use (e.g., 'openrouter/optimus-alpha')",
    "base_url": "API base URL (OpenAI-compatible endpoint)",
    "role": "Role description for the system prompt (e.g., 'software engineer')",
    "system_prompt": "Override the entire system prompt text",
    "temperature": "Sampling temperature (float, e.g., 0.0 - 2.0)",
    "max_tokens": "Maximum tokens for model response (int)"
}

class EffectiveConfig:
    """Read-only merged view of local and global configs"""
    def __init__(self, local_cfg, global_cfg):
        self.local_cfg = local_cfg
        self.global_cfg = global_cfg

    def get(self, key, default=None):
        for cfg in (self.local_cfg, self.global_cfg):
            val = cfg.get(key)
            if val is not None:
                return val
        return default

    def all(self):
        merged = {}
        # Start with global, override with local
        for cfg in (self.global_cfg, self.local_cfg):
            merged.update(cfg.all())
        return merged


# Singleton instances

local_config = FileConfig(Path('.janito/config.json'))
global_config = FileConfig(Path.home() / '.janito/config.json')

effective_config = EffectiveConfig(local_config, global_config)

def get_api_key():
    """Retrieve API key from environment or config files."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        return api_key
    api_key = effective_config.get("api_key")
    if api_key:
        return api_key
    raise ValueError("API key not found. Please set the OPENROUTER_API_KEY environment variable or configure 'api_key' in your config.")
