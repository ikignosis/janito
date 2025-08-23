"""
Module for guessing the provider based on model names.
"""

from janito.providers.registry import LLMProviderRegistry


def guess_provider_from_model(model_name: str) -> str:
    """
    Guess the provider based on the model name.

    Args:
        model_name: The name of the model to guess the provider for

    Returns:
        The provider name if a match is found, None otherwise
    """
    if not model_name:
        return None

    model_name = model_name.lower()

    # Check each provider's models
    return _find_provider_for_model(model_name)


def _find_provider_for_model(model_name: str) -> str:
    """Find provider for given model name."""
    for provider_name in LLMProviderRegistry.list_providers():
        provider_class = LLMProviderRegistry.get(provider_name)
        if not provider_class:
            continue

        if _check_provider_models(provider_name, provider_class, model_name):
            return provider_name

    return None


def _check_provider_models(provider_name: str, provider_class, model_name: str) -> bool:
    """Check if provider has matching model."""
    try:
        if hasattr(provider_class, "MODEL_SPECS"):
            model_specs = provider_class.MODEL_SPECS
            for spec_model_name in model_specs.keys():
                if spec_model_name.lower() == model_name:
                    return True

        # Handle special cases like moonshot
        if provider_name == "moonshot":
            return _check_moonshot_models(model_name)

    except Exception:
        # Skip providers that have issues accessing model specs
        pass

    return False


def _check_moonshot_models(model_name: str) -> bool:
    """Check moonshot models specifically."""
    try:
        from janito.providers.moonshot.model_info import MOONSHOT_MODEL_SPECS

        for spec_model_name in MOONSHOT_MODEL_SPECS.keys():
            if spec_model_name.lower() == model_name:
                return True
    except ImportError:
        pass
    return False
