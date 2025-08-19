from janito.llm.provider import LLMProvider
from janito.llm.model import LLMModelInfo
from janito.llm.auth import LLMAuthManager
from janito.llm.driver_config import LLMDriverConfig
from janito.tools import get_local_tools_adapter
from janito.providers.registry import LLMProviderRegistry
from .model_info import MODEL_SPECS
from janito.drivers.openai.driver import OpenAIModelDriver


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    NAME = "anthropic"
    MAINTAINER = "Alberto Minetti <alberto.minetti@gmail.com>"
    MODEL_SPECS = MODEL_SPECS
    DEFAULT_MODEL = "claude-3-7-sonnet-20250219"

    def __init__(
        self, auth_manager: LLMAuthManager = None, config: LLMDriverConfig = None
    ):
        self._tools_adapter = get_local_tools_adapter()
        self.auth_manager = auth_manager or LLMAuthManager()
        self._api_key = self.auth_manager.get_credentials(type(self).NAME)
        if not self._api_key:
            from janito.llm.auth_utils import handle_missing_api_key

            handle_missing_api_key(self.name, "ANTHROPIC_API_KEY")

        self._tools_adapter = get_local_tools_adapter()
        self._driver_config = config or LLMDriverConfig(model=None)
        if not getattr(self._driver_config, "model", None):
            self._driver_config.model = self.DEFAULT_MODEL
        if not self._driver_config.api_key:
            self._driver_config.api_key = self._api_key
        # Set the Anthropic OpenAI-compatible API endpoint
        self._driver_config.base_url = "https://api.anthropic.com/v1/"
        self.fill_missing_device_info(self._driver_config)
        self._driver = None  # to be provided by factory/agent

    @property
    def driver(self) -> OpenAIModelDriver:
        if not self.available:
            raise ImportError(
                f"AnthropicProvider unavailable: {self.unavailable_reason}"
            )
        return self._driver

    @property
    def available(self):
        return OpenAIModelDriver.available

    @property
    def unavailable_reason(self):
        return OpenAIModelDriver.unavailable_reason

    def create_driver(self):
        """
        Creates and returns a new OpenAIModelDriver instance configured for Anthropic API.
        """
        driver = OpenAIModelDriver(
            tools_adapter=self._tools_adapter, provider_name=self.name
        )
        driver.config = self._driver_config
        return driver

    @property
    def model_name(self):
        return self._driver_config.model

    @property
    def driver_config(self):
        """Public, read-only access to the provider's LLMDriverConfig object."""
        return self._driver_config

    def execute_tool(self, tool_name: str, event_bus, *args, **kwargs):
        self._tools_adapter.event_bus = event_bus
        return self._tools_adapter.execute_by_name(tool_name, *args, **kwargs)


LLMProviderRegistry.register(AnthropicProvider.NAME, AnthropicProvider)
