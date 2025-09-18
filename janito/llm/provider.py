from abc import ABC, abstractmethod
import importlib
from typing import Optional, Dict, Any, Type
from janito.llm.driver import LLMDriver
from janito.llm.driver_config import LLMDriverConfig
from janito.llm.auth import LLMAuthManager
from janito.llm.model import LLMModelInfo


class LLMProvider(ABC):
    """
    Abstract base class for Large Language Model (LLM) providers.
    
    Following a similar pattern to LLMDriver, this class provides:
    - Provider lifecycle management
    - Configuration validation and management
    - Driver factory methods
    - Model specification handling
    - Authentication management
    
    Subclasses must implement the core interface for interacting with LLM APIs
    and define required class attributes.
    """
    
    # Required class attributes (similar to LLMDriver pattern)
    name: str = None  # Must be set on subclasses
    DEFAULT_MODEL: str = None  # Should be set by subclasses
    MAINTAINER: str = "Unknown Maintainer"
    
    # Optional attributes
    MODEL_SPECS: Optional[Dict[str, LLMModelInfo]] = None
    available: bool = True
    unavailable_reason: Optional[str] = None
    
    def __init_subclass__(cls, **kwargs):
        """Validate that subclasses define required attributes."""
        super().__init_subclass__(**kwargs)
        
        # Validate required attributes
        if not cls.name or not isinstance(cls.name, str):
            raise TypeError(f"Class {cls.__name__} must define a class attribute 'name' (non-empty str)")
        
        if not cls.DEFAULT_MODEL:
            raise TypeError(f"Class {cls.__name__} must define a class attribute 'DEFAULT_MODEL' (non-empty str)")
    
    def __init__(self, 
                 auth_manager: Optional[LLMAuthManager] = None,
                 config: Optional[LLMDriverConfig] = None,
                 tools_adapter=None):
        """
        Initialize the provider with authentication and configuration.
        
        Args:
            auth_manager: Authentication manager for handling credentials
            config: Driver configuration object
            tools_adapter: Tools adapter for tool execution
        """
        self.auth_manager = auth_manager or LLMAuthManager()
        self.config = config or LLMDriverConfig()
        self.tools_adapter = tools_adapter
        self._driver_class: Optional[Type[LLMDriver]] = None
        
        # Initialize configuration
        self._initialize_provider_config()
        
        # Validate provider availability
        if not self.available:
            self._handle_unavailable_provider()



    # Configuration management methods
    def fill_missing_device_info(self, config):
        """
        Fill missing LLMDriverConfig fields (max_tokens, temperature, etc) from MODEL_SPECS for the chosen model.
        Mutates the config in place.
        """
        if not hasattr(self, "MODEL_SPECS"):
            return
        model_name = getattr(config, "model", None) or getattr(
            self, "DEFAULT_MODEL", None
        )
        model_info = self.MODEL_SPECS.get(model_name)
        if not model_info:
            return
        # Handle common fields from model_info
        spec_dict = (
            model_info.to_dict() if hasattr(model_info, "to_dict") else dict(model_info)
        )
        if (
            hasattr(config, "max_tokens")
            and getattr(config, "max_tokens", None) is None
        ):
            val = spec_dict.get("max_tokens") or spec_dict.get("max_response")
            if val is not None:
                try:
                    config.max_tokens = int(val)
                except Exception:
                    pass
        if (
            hasattr(config, "temperature")
            and getattr(config, "temperature", None) is None
        ):
            val = spec_dict.get("temperature")
            if val is None:
                val = spec_dict.get("default_temp")
            if val is not None:
                try:
                    config.temperature = float(val)
                except Exception:
                    pass

    # Properties
    @property
    def model_name(self) -> str:
        """Get the current model name."""
        return self.config.model or self.DEFAULT_MODEL
    
    @property
    def driver_config(self) -> LLMDriverConfig:
        """Get the driver configuration."""
        return self.config
    
    @property
    def is_available(self) -> bool:
        """Check if the provider is available."""
        return self.available

    # Model information methods
    def is_model_available(self, model_name):
        """
        Returns True if the given model is available for this provider.
        Default implementation checks MODEL_SPECS; override for dynamic providers.
        """
        if not hasattr(self, "MODEL_SPECS"):
            return False
        return model_name in self.MODEL_SPECS

    # Driver resolution methods
    def get_model_info(self, model_name=None):
        """
        Return the info dict for a given model (driver, params, etc). If model_name is None, return all model info dicts.
        MODEL_SPECS must be dict[str, LLMModelInfo].
        """
        if not hasattr(self, "MODEL_SPECS"):
            raise NotImplementedError(
                "This provider does not have a MODEL_SPECS attribute."
            )
        if model_name is None:
            return {
                name: model_info.to_dict()
                for name, model_info in self.MODEL_SPECS.items()
            }
        if model_name in self.MODEL_SPECS:
            return self.MODEL_SPECS[model_name].to_dict()
        return None

    def _validate_model_specs(self) -> None:
        if not hasattr(self, "MODEL_SPECS"):
            raise NotImplementedError(
                "This provider does not have a MODEL_SPECS attribute."
            )

    def _get_model_name_from_config(self, config) -> Optional[str]:
        return (config or {}).get("model_name", getattr(self, "DEFAULT_MODEL", None))

    def _get_model_spec_entry(self, model_name) -> LLMModelInfo:
        spec = self.MODEL_SPECS.get(model_name, None)
        if spec is None:
            raise ValueError(f"Model '{model_name}' not found in MODEL_SPECS.")
        return spec

    def _get_driver_name_from_spec(self, spec) -> Optional[str]:
        driver_name = None
        if hasattr(spec, "driver") and spec.driver:
            driver_name = spec.driver
        elif hasattr(spec, "other") and isinstance(spec.other, dict):
            driver_name = spec.other.get("driver", None)
        return driver_name

    def _resolve_driver_class_by_name(self, driver_name: str) -> Type[LLMDriver]:
        if not driver_name:
            raise NotImplementedError(
                "No driver class found or specified for this MODEL_SPECS entry."
            )
        module_root = "janito.drivers"
        probable_path = None
        mapping = {
            "OpenAIResponsesModelDriver": "openai_responses.driver",
            "OpenAIModelDriver": "openai.driver",
            "AzureOpenAIModelDriver": "azure_openai.driver",
            "GoogleGenaiModelDriver": "google_genai.driver",
        }
        if driver_name in mapping:
            probable_path = mapping[driver_name]
            module_path = f"{module_root}.{probable_path}"
            mod = importlib.import_module(module_path)
            return getattr(mod, driver_name)
        # Attempt dynamic fallback based on convention
        if driver_name.endswith("ModelDriver"):
            base = driver_name[: -len("ModelDriver")]
            mod_name = base.replace("_", "").lower()
            module_path = f"{module_root}.{mod_name}.driver"
            try:
                mod = importlib.import_module(module_path)
                return getattr(mod, driver_name)
            except Exception:
                pass
        raise NotImplementedError(
            "No driver class found for driver_name: {}".format(driver_name)
        )

    def _validate_required_config(self, driver_class, config, driver_name) -> None:
        required = getattr(driver_class, "required_config", None)
        if required:
            missing = [
                k
                for k in required
                if not config or k not in config or config.get(k) in (None, "")
            ]
            if missing:
                raise ValueError(
                    f"Missing required config for {driver_name}: {', '.join(missing)}"
                )

    # Abstract methods that subclasses must implement
    @abstractmethod
    def create_driver(self) -> LLMDriver:
        """
        Create and return a new driver instance for this provider.
        
        Returns:
            A new LLMDriver instance configured for this provider
        """
        pass
    
    # Lifecycle methods
    def _initialize_provider_config(self):
        """Initialize provider-specific configuration."""
        # Set default model if not specified
        if not self.config.model:
            self.config.model = self.DEFAULT_MODEL
        
        # Fill missing configuration from model specs
        self.fill_missing_device_info(self.config)
        
        # Resolve driver class
        self._resolve_driver_class()
    
    def _handle_unavailable_provider(self):
        """Handle provider unavailability."""
        # This can be overridden by subclasses for custom handling
        pass
    
    def _resolve_driver_class(self):
        """Resolve the driver class for this provider."""
        if not hasattr(self, 'MODEL_SPECS') or not self.MODEL_SPECS:
            return
        
        model_name = self.config.model or self.DEFAULT_MODEL
        model_spec = self.MODEL_SPECS.get(model_name)
        
        if model_spec and hasattr(model_spec, 'driver') and model_spec.driver:
            driver_name = model_spec.driver
            try:
                self._driver_class = self._resolve_driver_class_by_name(driver_name)
            except Exception as e:
                # Fallback to default resolution
                self._driver_class = None
    
    def _resolve_driver_class_by_name(self, driver_name: str) -> Type[LLMDriver]:
        """
        Resolve a driver class by name using importlib.
        
        Args:
            driver_name: Name of the driver class
            
        Returns:
            The driver class
            
        Raises:
            ImportError: If the driver class cannot be found
        """
        # Common driver mappings
        driver_mappings = {
            "OpenAIModelDriver": "janito.drivers.openai.driver",
            "AzureOpenAIModelDriver": "janito.drivers.azure_openai.driver",
            "GoogleGenaiModelDriver": "janito.drivers.google_genai.driver",
            "AnthropicModelDriver": "janito.drivers.anthropic.driver",
        }
        
        if driver_name in driver_mappings:
            module_path = driver_mappings[driver_name]
        else:
            # Try to resolve by convention
            if driver_name.endswith("ModelDriver"):
                base_name = driver_name[:-len("ModelDriver")].lower().replace("_", "")
                module_path = f"janito.drivers.{base_name}.driver"
            else:
                raise ImportError(f"Cannot resolve driver class: {driver_name}")
        
        try:
            module = importlib.import_module(module_path)
            driver_class = getattr(module, driver_name)
            if not issubclass(driver_class, LLMDriver):
                raise ImportError(f"Driver {driver_name} is not a subclass of LLMDriver")
            return driver_class
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Failed to import driver {driver_name} from {module_path}: {e}")
            raise ImportError(f"Failed to import driver {driver_name} from {module_path}: {e}")

    # Agent creation methods
    def create_agent(self, tools_adapter=None, agent_name: str = None, **kwargs):
        from janito.llm.agent import LLMAgent

        # Dynamically create driver if supported, else fallback to existing.
        driver = self.driver
        return LLMAgent(self, tools_adapter, agent_name=agent_name, **kwargs)
