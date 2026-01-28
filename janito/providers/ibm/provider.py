"""IBM WatsonX AI Provider implementation."""

from janito.llm.provider import LLMProvider
from janito.llm.auth import LLMAuthManager
from janito.llm.driver_config import LLMDriverConfig
from janito.tools.local import get_local_tools_adapter
from janito.providers.registry import LLMProviderRegistry
from janito.providers.ibm.model_info import MODEL_SPECS, DEFAULT_MODEL

from janito.drivers.openai.driver import OpenAIModelDriver


class IBMProvider(LLMProvider):
    """IBM WatsonX AI Provider for accessing IBM's AI services."""

    name = "ibm"
    NAME = "ibm"  # For backward compatibility
    MAINTAINER = "João Pinto <janito@ikignosis.org>"
    MODEL_SPECS = MODEL_SPECS
    DEFAULT_MODEL = DEFAULT_MODEL


    def __init__(
        self, auth_manager: LLMAuthManager = None, config: LLMDriverConfig = None
    ):
        self._tools_adapter = get_local_tools_adapter()
        
        # Call parent constructor to initialize base functionality
        super().__init__(auth_manager=auth_manager, config=config, tools_adapter=self._tools_adapter)
        
        # Initialize IBM-specific configuration
        self._initialize_ibm_config()

    def _initialize_ibm_config(self):
        """Initialize IBM-specific configuration."""
        # IBM WatsonX uses multiple credentials
        api_key = self.auth_manager.get_credentials(self.name)
        if not api_key:
            from janito.llm.auth_utils import handle_missing_api_key
            handle_missing_api_key(self.name, "WATSONX_API_KEY")

        # Get project ID for WatsonX
        project_id = self.auth_manager.get_credentials(f"{self.name}_project_id")
        if not project_id:
            from janito.llm.auth_utils import handle_missing_api_key
            handle_missing_api_key(self.name, "WATSONX_PROJECT_ID")
        
        # Get region/space ID
        space_id = self.auth_manager.get_credentials(f"{self.name}_space_id")
        
        # Set API key in config
        if not self.config.api_key:
            self.config.api_key = api_key

        # Store additional IBM-specific credentials in config extra
        self.config.extra.update({
            "project_id": project_id,
            "space_id": space_id
        })

        # Set IBM WatsonX specific parameters
        self.config.base_url = "https://us-south.ml.cloud.ibm.com"

    def create_driver(self) -> OpenAIModelDriver:
        """
        Create and return a new OpenAIModelDriver instance for IBM WatsonX.
        
        Returns:
            A new OpenAIModelDriver instance configured for IBM WatsonX API
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
        return self.tools_adapter.execute_by_name(tool_name, *args, **kwargs)

    @property
    def model_name(self):
        return self.config.model

    @property
    def driver_config(self):
        """Public, read-only access to the provider's LLMDriverConfig object."""
        return self.config

    def execute_tool(self, tool_name: str, event_bus, *args, **kwargs):
        self._tools_adapter.event_bus = event_bus
        return self._tools_adapter.execute_by_name(tool_name, *args, **kwargs)


LLMProviderRegistry.register(IBMProvider.NAME, IBMProvider)
