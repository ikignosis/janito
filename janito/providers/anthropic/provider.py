from janito.llm.provider import LLMProvider
from janito.llm.model import LLMModelInfo
from janito.llm.auth import LLMAuthManager
from janito.llm.driver_config import LLMDriverConfig
from janito.tools import get_local_tools_adapter
from janito.providers.registry import LLMProviderRegistry
from janito.providers.anthropic.model_info import MODEL_SPECS
from janito.drivers.openai.driver import OpenAIModelDriver


class AnthropicProvider(LLMProvider):
    """Anthropic LLM Provider implementation."""

    name = "anthropic"
    NAME = "anthropic"  # For backward compatibility
    MAINTAINER = "Alberto Minetti <alberto.minetti@gmail.com>"
    MODEL_SPECS = MODEL_SPECS
    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
    available = OpenAIModelDriver.available
    unavailable_reason = OpenAIModelDriver.unavailable_reason

    def __init__(
        self, auth_manager: LLMAuthManager = None, config: LLMDriverConfig = None
    ):
        self._tools_adapter = get_local_tools_adapter()

        # Call parent constructor to initialize base functionality
        super().__init__(
            auth_manager=auth_manager, config=config, tools_adapter=self._tools_adapter
        )

        # Initialize API key and configure Anthropic-specific settings
        if self.available:
            self._initialize_anthropic_config()

    def _initialize_anthropic_config(self):
        """Initialize Anthropic-specific configuration."""
        # Initialize API key
        api_key = self.auth_manager.get_credentials(self.name)
        if not api_key:
            from janito.llm.auth_utils import handle_missing_api_key

            handle_missing_api_key(self.name, "ANTHROPIC_API_KEY")

        # Set API key in config
        if not self.config.api_key:
            self.config.api_key = api_key

        # Set the Anthropic OpenAI-compatible API endpoint
        self.config.base_url = "https://api.anthropic.com/v1/"

    def create_driver(self) -> OpenAIModelDriver:
        """
        Create and return a new OpenAIModelDriver instance for Anthropic.

        Returns:
            A new OpenAIModelDriver instance configured for Anthropic API
        """
        if not self.available:
            raise ImportError(
                f"AnthropicProvider unavailable: {self.unavailable_reason}"
            )

        driver = OpenAIModelDriver(
            tools_adapter=self.tools_adapter, provider_name=self.name
        )
        driver.config = self.config
        return driver

    def execute_tool(self, tool_name: str, event_bus, *args, **kwargs):
        """Execute a tool by name."""
        self.tools_adapter.event_bus = event_bus
        return self.tools_adapter.execute_by_name(tool_name, *args, **kwargs)


LLMProviderRegistry.register(AnthropicProvider.NAME, AnthropicProvider)
