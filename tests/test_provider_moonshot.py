import pytest
from janito.providers.registry import LLMProviderRegistry


def test_moonshot_provider_registered():
    provider_cls = LLMProviderRegistry.get("moonshot")
    assert provider_cls is not None, "Moonshot provider should be registered."
    provider = provider_cls()
    assert provider.name == "moonshot"
    assert provider.driver_config.base_url.startswith("https://api.moonshot.ai")
