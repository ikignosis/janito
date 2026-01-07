from janito.llm.provider import LLMProvider
from janito.llm.model import LLMModelInfo
from janito.llm.auth import LLMAuthManager
from janito.llm.driver_config import LLMDriverConfig
from janito.drivers.openai.driver import OpenAIModelDriver
from janito.tooling import get_local_tools_adapter
from janito.providers.registry import LLMProviderRegistry
from janito.providers.alibaba.model_info import MODEL_SPECS


available = OpenAIModelDriver.available
unavailable_reason = OpenAIModelDriver.unavailable_reason


class AlibabaProvider(LLMProvider):
    """Alibaba Qwen LLM Provider implementation."""
    
    name = "alibaba"
    NAME = "alibaba"  # For backward compatibility
    MAINTAINER = "João Pinto <janito@ikignosis.org>"
    MODEL_SPECS = MODEL_SPECS
    DEFAULT_MODEL = "qwen3-max"  # 256k context, Qwen3 Max Preview standard model
    available = OpenAIModelDriver.available
    unavailable_reason = OpenAIModelDriver.unavailable_reason

    def __init__(
        self, auth_manager: LLMAuthManager = None, config: LLMDriverConfig = None
    ):
        self._tools_adapter = get_local_tools_adapter()
        
        # Call parent constructor to initialize base functionality
        super().__init__(auth_manager=auth_manager, config=config, tools_adapter=self._tools_adapter)
        
        # Initialize Alibaba-specific configuration
        if self.available:
            self._initialize_alibaba_config()

    def _initialize_alibaba_config(self):
        """Initialize Alibaba-specific configuration."""
        # Initialize API key
        api_key = self.auth_manager.get_credentials(self.name)
        if not api_key:
            from janito.llm.auth_utils import handle_missing_api_key
            handle_missing_api_key(self.name, "ALIBABA_API_KEY")
        
        # Set API key in config
        if not self.config.api_key:
            self.config.api_key = api_key
        
        # Set Alibaba international endpoint as default base_url if not provided
        if not getattr(self.config, "base_url", None):
            self.config.base_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
            self.fill_missing_device_info(self.config)
            self._driver = None  # to be provided by factory/agent

    def create_driver(self) -> OpenAIModelDriver:
        """
        Create and return a new OpenAIModelDriver instance for Alibaba.
        
        Returns:
            A new OpenAIModelDriver instance configured for Alibaba API
        """
        if not self.available:
            raise ImportError(f"AlibabaProvider unavailable: {self.unavailable_reason}")
        
        driver = OpenAIModelDriver(
            tools_adapter=self.tools_adapter, 
            provider_name=self.name
        )
        driver.config = self.config
        return driver

    def execute_tool(self, tool_name: str, event_bus, *args, **kwargs):
        """Execute a tool by name."""
        self.tools_adapter.event_bus = event_bus
        return self.tools_adapter.execute_by_name(tool_name, *args, **kwargs)

    @property
    def driver_config(self):
        """Public, read-only access to the provider's LLMDriverConfig object."""
        return self.config

    def execute_tool(self, tool_name: str, event_bus, *args, **kwargs):
        self._tools_adapter.event_bus = event_bus
        return self._tools_adapter.execute_by_name(tool_name, *args, **kwargs)


LLMProviderRegistry.register(AlibabaProvider.NAME, AlibabaProvider)
