from janito.llm.provider import LLMProvider
from janito.llm.model import LLMModelInfo
from janito.llm.auth import LLMAuthManager
from janito.llm.driver_config import LLMDriverConfig
from janito.drivers.openai.driver import OpenAIModelDriver
from janito.tools.local import get_local_tools_adapter
from janito.providers.registry import LLMProviderRegistry
from janito.providers.mistral.model_info import MODEL_SPECS, DEFAULT_MODEL


class MistralProvider(LLMProvider):
    """Mistral AI LLM Provider implementation."""
    
    name = "mistral"
    NAME = "mistral"  # For backward compatibility
    MAINTAINER = "João Pinto <janito@ikignosis.org>"
    MODEL_SPECS = MODEL_SPECS
    DEFAULT_MODEL = DEFAULT_MODEL


    def __init__(
        self, auth_manager: LLMAuthManager = None, config: LLMDriverConfig = None
    ):
        self._tools_adapter = get_local_tools_adapter()
        
        # Call parent constructor to initialize base functionality
        super().__init__(auth_manager=auth_manager, config=config, tools_adapter=self._tools_adapter)
        
        # Initialize Mistral-specific configuration
        if self.available:
            self._initialize_mistral_config()

    def _initialize_mistral_config(self):
        """Initialize Mistral-specific configuration."""
        # Initialize API key
        api_key = self.auth_manager.get_credentials(self.name)
        if not api_key:
            from janito.llm.auth_utils import handle_missing_api_key
            handle_missing_api_key(self.name, "MISTRAL_API_KEY")
        
        # Set API key in config
        if not self.config.api_key:
            self.config.api_key = api_key
        
        # Set Mistral-specific base URL
        self.config.base_url = "https://api.mistral.ai/v1"

    def create_driver(self) -> OpenAIModelDriver:
        """
        Create and return a new OpenAIModelDriver instance for Mistral.
        
        Returns:
            A new OpenAIModelDriver instance configured for Mistral API
        """

        
        driver = OpenAIModelDriver(
            tools_adapter=self.tools_adapter, 
            provider_name=self.name
        )
        driver.config = self.config
        return driver

LLMProviderRegistry.register(MistralProvider.NAME, MistralProvider)
