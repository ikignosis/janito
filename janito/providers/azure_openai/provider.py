from janito.llm.provider import LLMProvider
from janito.llm.model import LLMModelInfo
from janito.llm.auth import LLMAuthManager
from janito.llm.driver_config import LLMDriverConfig
from janito.tools import get_local_tools_adapter
from janito.providers.registry import LLMProviderRegistry

from .model_info import MODEL_SPECS

from janito.drivers.azure_openai.driver import AzureOpenAIModelDriver

available = AzureOpenAIModelDriver.available
unavailable_reason = AzureOpenAIModelDriver.unavailable_reason
maintainer = "João Pinto <janito@ikignosis.org>"


class AzureOpenAIProvider(LLMProvider):
    name = "azure_openai"
    NAME = "azure_openai"
    MAINTAINER = "João Pinto <janito@ikignosis.org>"
    MODEL_SPECS = MODEL_SPECS
    DEFAULT_MODEL = "azure_openai_deployment"

    def __init__(
        self, auth_manager: LLMAuthManager = None, config: LLMDriverConfig = None
    ):
        # Always create a tools adapter so that provider.execute_tool() works even when
        # the underlying driver is not available (e.g. OpenAI SDK not installed).
        self._tools_adapter = get_local_tools_adapter()
        if not self.available:
            self._driver = None
            return
        self._auth_manager = auth_manager or LLMAuthManager()
        self._api_key = self._auth_manager.get_credentials(type(self).NAME)
        if not self._api_key:
            from janito.llm.auth_utils import handle_missing_api_key

            handle_missing_api_key(self.name, "AZURE_OPENAI_API_KEY")

        self._tools_adapter = get_local_tools_adapter()
        self._driver_config = config or LLMDriverConfig(model=None)
        if not self._driver_config.model:
            self._driver_config.model = self.DEFAULT_MODEL
        if not self._driver_config.api_key:
            self._driver_config.api_key = self._api_key
        if not self._driver_config.extra.get("api_version"):
            self._driver_config.extra["api_version"] = "2023-05-15"
        # Inject azure_deployment_name from config if present
        from janito.config import config as global_config

        deployment_name = global_config.get("azure_deployment_name")
        if deployment_name:
            self._driver_config.extra["azure_deployment_name"] = deployment_name
        self.fill_missing_device_info(self._driver_config)
        self._driver = AzureOpenAIModelDriver(tools_adapter=self._tools_adapter)

    @property
    def driver(self):
        if not self.available:
            raise ImportError(
                f"AzureOpenAIProvider unavailable: {self.unavailable_reason}"
            )
        return self._driver

    @property
    def available(self):
        return available

    @property
    def unavailable_reason(self):
        return unavailable_reason

    def is_model_available(self, model_name):
        """
        Returns True for any model name, since Azure deployments are user-defined and not enumerable in advance.
        """
        return True

    def get_model_info(self, model_name=None):
        """
        For Azure OpenAI, accept any deployment name as a valid model name.
        If the model_name is not in MODEL_SPECS, return a generic info dict.
        """
        if model_name is None:
            # Return all known specs
            return {
                name: model_info.to_dict()
                for name, model_info in self.MODEL_SPECS.items()
            }
        if model_name in self.MODEL_SPECS:
            return self.MODEL_SPECS[model_name].to_dict()
        # Accept any deployment name as a valid model
        return {
            "name": model_name,
            "context": "N/A",
            "max_input": "N/A",
            "max_cot": "N/A",
            "max_response": "N/A",
            "thinking_supported": False,
            "default_temp": 0.2,
            "open": "azure_openai",
            "driver": "AzureOpenAIModelDriver",
        }

    def create_driver(self):
        """
        Creates and returns a new AzureOpenAIModelDriver instance with the provider's configuration and tools adapter.
        """
        driver = AzureOpenAIModelDriver(tools_adapter=self._tools_adapter)
        driver.config = self._driver_config
        # NOTE: The caller is responsible for calling driver.start() if background processing is needed.
        return driver

    def create_agent(self, tools_adapter=None, agent_name: str = None, **kwargs):
        from janito.llm.agent import LLMAgent
        from janito.drivers.azure_openai.driver import AzureOpenAIModelDriver

        # Always create a new driver with the passed-in tools_adapter
        driver = AzureOpenAIModelDriver(tools_adapter=tools_adapter)
        return LLMAgent(self, tools_adapter, agent_name=agent_name, **kwargs)

    @property
    def driver_config(self):
        """Public, read-only access to the provider's LLMDriverConfig object."""
        return self._driver_config

    def execute_tool(self, tool_name: str, event_bus, *args, **kwargs):
        # Use direct execution via adapter:
        self._tools_adapter.event_bus = event_bus
        return self._tools_adapter.execute_by_name(tool_name, *args, **kwargs)


LLMProviderRegistry.register(AzureOpenAIProvider.NAME, AzureOpenAIProvider)
