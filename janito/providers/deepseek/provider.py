from janito.llm.provider import LLMProvider
from janito.llm.model import LLMModelInfo
from janito.llm.auth import LLMAuthManager
from janito.llm.driver_config import LLMDriverConfig
from janito.drivers.openai.driver import OpenAIModelDriver
from janito.tools import get_local_tools_adapter
from janito.providers.registry import LLMProviderRegistry
from .model_info import MODEL_SPECS
from queue import Queue

available = OpenAIModelDriver.available
unavailable_reason = OpenAIModelDriver.unavailable_reason


class DeepSeekProvider(LLMProvider):
    name = "deepseek"
    NAME = "deepseek"
    MAINTAINER = "João Pinto <janito@ikignosis.org>"
    MODEL_SPECS = MODEL_SPECS
    DEFAULT_MODEL = "deepseek-chat"  # Options: deepseek-chat, deepseek-reasoner, deepseek-v3.1, deepseek-v3.1-base, deepseek-r1

    def __init__(
        self, auth_manager: LLMAuthManager = None, config: LLMDriverConfig = None
    ):
        # Always set a tools adapter so that even if the driver is unavailable,
        # generic code paths that expect provider.execute_tool() continue to work.
        self._tools_adapter = get_local_tools_adapter()
        if not self.available:
            self._driver = None
        else:
            self.auth_manager = auth_manager or LLMAuthManager()
            self._api_key = self.auth_manager.get_credentials(type(self).NAME)
            if not self._api_key:
                from janito.llm.auth_utils import handle_missing_api_key

                handle_missing_api_key(self.name, "DEEPSEEK_API_KEY")

            self._tools_adapter = get_local_tools_adapter()
            self._driver_config = config or LLMDriverConfig(model=None)
            if not self._driver_config.model:
                self._driver_config.model = self.DEFAULT_MODEL
            if not self._driver_config.api_key:
                self._driver_config.api_key = self._api_key
            # Set DeepSeek public endpoint as default base_url if not provided
            if not getattr(self._driver_config, "base_url", None):
                self._driver_config.base_url = "https://api.deepseek.com/v1"
            self.fill_missing_device_info(self._driver_config)
            self._driver = None  # to be provided by factory/agent

    @property
    def driver(self) -> OpenAIModelDriver:
        if not self.available:
            raise ImportError(f"OpenAIProvider unavailable: {self.unavailable_reason}")
        return self._driver

    @property
    def available(self):
        return available

    @property
    def unavailable_reason(self):
        return unavailable_reason

    def create_driver(self):
        """
        Creates and returns a new OpenAIModelDriver instance with input/output queues.
        """
        driver = OpenAIModelDriver(
            tools_adapter=self._tools_adapter, provider_name=self.name
        )
        driver.config = self._driver_config
        # NOTE: The caller is responsible for calling driver.start() if background processing is needed.
        return driver

    def create_agent(self, tools_adapter=None, agent_name: str = None, **kwargs):
        from janito.llm.agent import LLMAgent

        # Always create a new driver with the passed-in tools_adapter
        if tools_adapter is None:
            tools_adapter = get_local_tools_adapter()
        # Should use new-style driver construction via queues/factory (handled elsewhere)
        raise NotImplementedError(
            "create_agent must be constructed via new factory using input/output queues and config."
        )

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


LLMProviderRegistry.register(DeepSeekProvider.NAME, DeepSeekProvider)
