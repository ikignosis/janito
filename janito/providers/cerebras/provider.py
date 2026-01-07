"""Cerebras Inference provider implementation."""

from typing import Dict, Any
from janito.llm.provider import LLMProvider
from janito.llm.auth import LLMAuthManager
from janito.llm.driver_config import LLMDriverConfig
from janito.drivers.openai.driver import OpenAIModelDriver
from janito.tooling import get_local_tools_adapter
from janito.providers.registry import LLMProviderRegistry
from janito.providers.cerebras.model_info import MODEL_SPECS


class CerebrasProvider(LLMProvider):
    """Cerebras Inference API provider."""

    name = "cerebras"
    NAME = "cerebras"  # For backward compatibility
    DEFAULT_MODEL = "qwen-3-coder-480b"
    MAINTAINER = "João Pinto <janito@ikignosis.org>"
    MODEL_SPECS = MODEL_SPECS
    available = OpenAIModelDriver.available
    unavailable_reason = OpenAIModelDriver.unavailable_reason

    def __init__(
        self, auth_manager: LLMAuthManager = None, config: LLMDriverConfig = None
    ):
        """Initialize Cerebras provider with optional configuration."""
        self._tools_adapter = get_local_tools_adapter()
        
        # Call parent constructor to initialize base functionality
        super().__init__(auth_manager=auth_manager, config=config, tools_adapter=self._tools_adapter)
        
        # Initialize Cerebras-specific configuration
        if self.available:
            self._initialize_cerebras_config()

    def _initialize_cerebras_config(self):
        """Initialize Cerebras-specific configuration."""
        # Initialize API key
        api_key = self.auth_manager.get_credentials(self.name)
        if not api_key:
            from janito.llm.auth_utils import handle_missing_api_key
            handle_missing_api_key(self.name, "CEREBRAS_API_KEY")
        
        # Set API key in config
        if not self.config.api_key:
            self.config.api_key = api_key
        
        # Set Cerebras API endpoint
        self.config.base_url = "https://api.cerebras.ai/v1"

    def create_driver(self) -> OpenAIModelDriver:
        """
        Create and return a new OpenAIModelDriver instance for Cerebras.
        
        Returns:
            A new OpenAIModelDriver instance configured for Cerebras API
        """
        if not self.available:
            raise ImportError(f"CerebrasProvider unavailable: {self.unavailable_reason}")
        
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


LLMProviderRegistry.register(CerebrasProvider.name, CerebrasProvider)
