import pytest
from janito.providers.registry import LLMProviderRegistry


def test_alibaba_qwen3_max_thinking_model():
    """Test that the new Qwen3-Max-Thinking model is properly registered and configured."""
    provider_cls = LLMProviderRegistry.get("alibaba")
    assert provider_cls is not None, "Alibaba provider should be registered."
    
    provider = provider_cls()
    model_info = provider.get_model_info("qwen3-max-2026-01-23")
    
    assert model_info is not None, "Qwen3-Max-Thinking model should be available."
    assert model_info.name == "qwen3-max-2026-01-23"
    assert model_info.context == 262144
    assert model_info.max_response == 65536
    assert model_info.thinking is True
    assert model_info.thinking_supported is True
    assert "Qwen3-Max-Thinking" in model_info.category