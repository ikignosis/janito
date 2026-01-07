from janito.llm.provider import LLMProvider
from janito.llm.auth import LLMAuthManager
from janito.llm.driver_config import LLMDriverConfig
from janito.drivers.openai.driver import OpenAIModelDriver
from janito.tooling import get_local_tools_adapter
from janito.providers.registry import LLMProviderRegistry
from janito.providers.moonshot.model_info import MOONSHOT_MODEL_SPECS, DEFAULT_MODEL


class MoonshotProvider(LLMProvider):
    """Moonshot AI LLM Provider implementation."""
    
    name = "moonshot"
    NAME = "moonshot"  # For backward compatibility
    MAINTAINER = "João Pinto <janito@ikignosis.org>"
    MODEL_SPECS = MOONSHOT_MODEL_SPECS
    DEFAULT_MODEL = DEFAULT_MODEL
    available = OpenAIModelDriver.available
    unavailable_reason = OpenAIModelDriver.unavailable_reason

    def __init__(
        self, auth_manager: LLMAuthManager = None, config: LLMDriverConfig = None
    ):
        self._tools_adapter = get_local_tools_adapter()
        
        # Call parent constructor to initialize base functionality
        super().__init__(auth_manager=auth_manager, config=config, tools_adapter=self._tools_adapter)
        
        # Initialize Moonshot-specific configuration
        if self.available:
            self._initialize_moonshot_config()

    def _initialize_moonshot_config(self):
        """Initialize Moonshot-specific configuration."""
        # Initialize API key
        api_key = self.auth_manager.get_credentials(self.name)
        if not api_key:
            from janito.llm.auth_utils import handle_missing_api_key
            handle_missing_api_key(self.name, "MOONSHOT_API_KEY")
        
        # Set API key in config
        if not self.config.api_key:
            self.config.api_key = api_key
        
        # Set Moonshot API endpoint
        self.config.base_url = "https://api.moonshot.ai/v1"

    def create_driver(self) -> OpenAIModelDriver:
        """
        Create and return a new OpenAIModelDriver instance for Moonshot.
        
        Returns:
            A new OpenAIModelDriver instance configured for Moonshot API
        """
        if not self.available:
            raise ImportError(f"MoonshotProvider unavailable: {self.unavailable_reason}")
        
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




LLMProviderRegistry.register(MoonshotProvider.NAME, MoonshotProvider)
