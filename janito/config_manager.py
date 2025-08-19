import json
from pathlib import Path
from threading import Lock


class ConfigManager:
    """
    Unified configuration manager supporting:
      - Defaults
      - File-based configuration
      - Runtime overrides (e.g., CLI args)
    """

    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(
        self, config_path=None, defaults=None, runtime_overrides=None, config_name=None
    ):
        # Lazy single-init
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        if config_name:
            self.config_path = (
                Path.home() / ".janito" / "configs" / f"{config_name}.json"
            )
        else:
            self.config_path = Path(
                config_path or Path.home() / ".janito" / "config.json"
            )
        self.defaults = dict(defaults) if defaults else {}
        self.file_config = {}
        self.runtime_overrides = dict(runtime_overrides) if runtime_overrides else {}
        self._load_file_config()
        self._apply_tool_permissions_on_startup()

    def _apply_tool_permissions_on_startup(self):
        # On startup, read tool_permissions from config and set global permissions
        perm_str = self.file_config.get("tool_permissions")
        if perm_str:
            try:
                from janito.tools.permissions_parse import parse_permissions_string
                from janito.tools.permissions import set_global_allowed_permissions

                perms = parse_permissions_string(perm_str)
                set_global_allowed_permissions(perms)
            except Exception as e:
                print(f"Warning: Failed to apply tool_permissions from config: {e}")

        # Load plugins from config
        plugins_config = self.file_config.get("plugins", {})
        if plugins_config:
            try:
                from janito.plugins.manager import PluginManager

                plugin_manager = PluginManager()
                plugin_manager.load_plugins_from_config({"plugins": plugins_config})
            except Exception as e:
                print(f"Warning: Failed to load plugins from config: {e}")
        else:
            # Try loading from user config directory
            try:
                from janito.plugins.manager import PluginManager

                plugin_manager = PluginManager()
                plugin_manager.load_plugins_from_user_config()
            except Exception as e:
                print(f"Warning: Failed to load plugins from user config: {e}")

        # Load disabled tools from config - skip during startup to avoid circular imports
        # This will be handled by the CLI when needed

    def _load_file_config(self):
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                try:
                    self.file_config = json.load(f)
                except Exception:
                    self.file_config = {}
        else:
            self.file_config = {}

    def save(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.file_config, f, indent=2)
            f.write("\n")

    def get(self, key, default=None):
        # Precedence: runtime_overrides > file_config > defaults
        for layer in (self.runtime_overrides, self.file_config, self.defaults):
            if key in layer and layer[key] is not None:
                return layer[key]
        return default

    def runtime_set(self, key, value):
        self.runtime_overrides[key] = value

    def file_set(self, key, value):
        # Always reload, update, and persist
        self._load_file_config()
        self.file_config[key] = value
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.file_config, f, indent=2)
            f.write("\n")

    def all(self, layered=False):
        merged = dict(self.defaults)
        merged.update(self.file_config)
        merged.update(self.runtime_overrides)
        if layered:
            # Only file+runtime, i.e., what is saved to disk
            d = dict(self.file_config)
            d.update(self.runtime_overrides)
            return d
        return merged

    # Namespaced provider/model config
    def get_provider_config(self, provider, default=None):
        providers = self.file_config.get("providers") or {}
        return providers.get(provider) or (default or {})

    def set_provider_config(self, provider, key, value):
        if "providers" not in self.file_config:
            self.file_config["providers"] = {}
        if provider not in self.file_config["providers"]:
            self.file_config["providers"][provider] = {}
        self.file_config["providers"][provider][key] = value

    def get_provider_model_config(self, provider, model, default=None):
        return (
            self.file_config.get("providers")
            or {}.get(provider, {}).get("models", {}).get(model)
            or (default or {})
        )

    def set_provider_model_config(self, provider, model, key, value):
        if "providers" not in self.file_config:
            self.file_config["providers"] = {}
        if provider not in self.file_config["providers"]:
            self.file_config["providers"][provider] = {}
        if "models" not in self.file_config["providers"][provider]:
            self.file_config["providers"][provider]["models"] = {}
        if model not in self.file_config["providers"][provider]["models"]:
            self.file_config["providers"][provider]["models"][model] = {}
        self.file_config["providers"][provider]["models"][model][key] = value

    # Support loading runtime overrides after init (e.g. after parsing CLI args)
    def apply_runtime_overrides(self, overrides_dict):
        self.runtime_overrides.update(overrides_dict)
