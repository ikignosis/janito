from .config import BaseConfig, effective_config


class RuntimeConfig(BaseConfig):
    """In-memory only config, reset on restart"""

    pass


runtime_config = RuntimeConfig()


class UnifiedConfig:
    """
    Config lookup order:
    1. runtime_config (in-memory, highest priority)
    2. effective_config (local/global, read-only)
    """

    def __init__(self, runtime_cfg, effective_cfg):
        self.runtime_cfg = runtime_cfg
        self.effective_cfg = effective_cfg

    def get(self, key, default=None):
        val = self.runtime_cfg.get(key)
        if val is not None:
            return val
        return self.effective_cfg.get(key, default)

    def all(self):
        merged = dict(self.effective_cfg.all())
        merged.update(self.runtime_cfg.all())
        return merged


unified_config = UnifiedConfig(runtime_config, effective_config)
