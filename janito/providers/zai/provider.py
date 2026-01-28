from janito.llm.provider import LLMProvider
from janito.llm.model import LLMModelInfo
from janito.llm.auth import LLMAuthManager
from janito.llm.driver_config import LLMDriverConfig
from janito.drivers.openai.driver import OpenAIModelDriver
from janito.tools.local import get_local_tools_adapter
from janito.providers.registry import LLMProviderRegistry
from janito.providers.zai.model_info import MODEL_SPECS, DEFAULT_MODEL


class ZAIProvider(LLMProvider):
    """ZAI (Zhihu AI) LLM Provider implementation."""
    
    name = "zai"
    NAME = "zai"  # For backward compatibility
    MAINTAINER = "João Pinto <janito@ikignosis.org>"
    MODEL_SPECS = MODEL_SPECS
    DEFAULT_MODEL = DEFAULT_MODEL


    def __init__(
        self, auth_manager: LLMAuthManager = None, config: LLMDriverConfig = None
    ):
        self._tools_adapter = get_local_tools_adapter()
        
        # Call parent constructor to initialize base functionality
        super().__init__(auth_manager=auth_manager, config=config, tools_adapter=self._tools_adapter)
        
        # Initialize ZAI-specific configuration
        if self.available:
            self._initialize_zai_config()
        else:
            # Even when the ZAI driver is unavailable we still need a tools adapter
            # so that any generic logic that expects `execute_tool()` to work does not
            # crash with an AttributeError when it tries to access `self.tools_adapter`.
            pass

    def _initialize_zai_config(self):
        """Initialize ZAI-specific configuration."""
        # Initialize API key
        api_key = self.auth_manager.get_credentials(self.name)
        if not api_key:
            from janito.llm.auth_utils import handle_missing_api_key
            handle_missing_api_key(self.name, "ZAI_API_KEY")
        
        # Set API key in config
        if not self.config.api_key:
            self.config.api_key = api_key
        
        # Set Z.AI endpoint as default base_url if not provided
        if not getattr(self.config, "base_url", None):
            self.config.base_url = "https://api.z.ai/api/paas/v4/"
            self.fill_missing_device_info(self.config)
            self._driver = None  # to be provided by factory/agent

    def create_driver(self) -> OpenAIModelDriver:
        """
        Create and return a new OpenAIModelDriver instance for ZAI.
        
        Returns:
            A new OpenAIModelDriver instance configured for ZAI API
        """

        
        driver = OpenAIModelDriver(
            tools_adapter=self.tools_adapter, 
            provider_name=self.name
        )
        driver.config = self.config
        return driver

    def execute_tool(self, tool_name: str, event_bus, *args, **kwargs):
        """Execute a tool by name."""
        self.tools_adapter.event_bus = event_bus
LLMProviderRegistry.register(ZAIProvider.NAME, ZAIProvider)
