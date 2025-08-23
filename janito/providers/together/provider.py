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


class TogetherProvider(LLMProvider):
    name = 'together'
    NAME = 'together'
    MAINTAINER = 'Janito Team'
    MODEL_SPECS = MODEL_SPECS
    DEFAULT_MODEL = 'allenai/OLMo-2-0325-32B-Instruct'

    def __init__(
        self, auth_manager: LLMAuthManager = None, config: LLMDriverConfig = None
    ):
        self._tools_adapter = get_local_tools_adapter()
        self._driver = None

        if not self.available:
            return

        self._initialize_config(auth_manager, config)
        self._setup_model_config()

    def _initialize_config(self, auth_manager, config):
        self.auth_manager = auth_manager or LLMAuthManager()
        self._api_key = self.auth_manager.get_credentials(type(self).NAME)
        if not self._api_key:
            from janito.llm.auth_utils import handle_missing_api_key
            handle_missing_api_key(self.name, 'TOGETHER_API_KEY')

        self._driver_config = config or LLMDriverConfig(model=None)
        if not self._driver_config.model:
            self._driver_config.model = self.DEFAULT_MODEL
        if not self._driver_config.api_key:
            self._driver_config.api_key = self._api_key

        self._driver_config.base_url = 'https://api.together.xyz/v1'

    def _setup_model_config(self):
        model_name = self._driver_config.model
        model_spec = self.MODEL_SPECS.get(model_name)

        if hasattr(self._driver_config, 'max_tokens'):
            self._driver_config.max_tokens = None
        if hasattr(self._driver_config, 'max_completion_tokens'):
            self._driver_config.max_completion_tokens = None

        if model_spec:
            max_tokens = getattr(model_spec, 'max_tokens', None)
            if max_tokens and max_tokens != 'N/A':
                self._driver_config.max_tokens = int(max_tokens)

        self.fill_missing_device_info(self._driver_config)

    @property
    def driver(self) -> OpenAIModelDriver:
        if not self.available:
            raise ImportError(f'TogetherProvider unavailable: {self.unavailable_reason}')
        return self._driver

    @property
    def available(self):
        return available

    @property
    def unavailable_reason(self):
        return unavailable_reason

    def create_driver(self):
        driver = OpenAIModelDriver(
            tools_adapter=self._tools_adapter, provider_name=self.NAME
        )
        driver.config = self._driver_config
        return driver

    def create_agent(self, tools_adapter=None, agent_name: str = None, **kwargs):
        from janito.llm.agent import LLMAgent
        if tools_adapter is None:
            tools_adapter = get_local_tools_adapter()
        raise NotImplementedError(
            'create_agent must be constructed via new factory using input/output queues and config.'
        )

    @property
    def model_name(self):
        return self._driver_config.model

    @property
    def driver_config(self):
        return self._driver_config

    def execute_tool(self, tool_name: str, event_bus, *args, **kwargs):
        self._tools_adapter.event_bus = event_bus
        return self._tools_adapter.execute_by_name(tool_name, *args, **kwargs)


LLMProviderRegistry.register(TogetherProvider.NAME, TogetherProvider)

