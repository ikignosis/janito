"""
Provider name validation helpers.

Module-level functions for validating provider names, checking variants and
listing supported providers.  Part of the split provider-config module
family.
"""

from .provider_registry import _registry


def canonical_provider_name(provider: str) -> str | None:
    """
    Return the canonical (correctly cased) name for a supported provider.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        The canonical provider name as used in the provider registry
        (``janito.providers._PROVIDER_CONFIGS``) if the provider is supported,
        otherwise ``None``.
    """
    return _registry.canonical_name(provider)


def is_supported_provider(provider: str) -> bool:
    """
    Check if a provider name is a supported provider (i.e. it maps to an entry
    in :data:`janito.providers._PROVIDER_CONFIGS`).

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        True if the provider is supported, False otherwise
    """
    return _registry.canonical_name(provider) is not None


def is_registered_provider_variant(name: str) -> bool:
    """Whether ``name`` is a registered provider variant (not a base provider).

    Unlike :func:`is_supported_provider` (which also accepts built-in
    providers), this only returns True for registered variants.

    Args:
        name: The provider name.

    Returns:
        True if the name is a registered variant.
    """
    return _registry._variant_base(name) is not None


def list_variants() -> list:
    """List all registered provider variant names, sorted.

    Returns:
        Sorted list of registered variant names (e.g. ``["alibaba-tokenplan"]``).
    """
    from .config_variants import load_variants

    return sorted(load_variants().keys())


def is_custom_provider(provider: str) -> bool:
    """
    Check if a provider is the special "custom" provider.

    A provider variant of "custom" (e.g. ``custom-local``, created with
    ``--create-variant custom-local``) counts as custom too: it inherits the
    "custom" provider's built-in defaults.

    Args:
        provider: The provider name (case-insensitive)

    Returns:
        True if the provider is "custom" (or a variant of it), False otherwise
    """
    if not provider:
        return False
    if provider.strip().lower() == "custom":
        return True
    found = _registry.get(provider)
    return found.is_custom if found is not None else False


def validate_provider_name(provider: str) -> str:
    """
    Validate a provider name against the supported providers and return its
    canonical form.

    A provider is considered valid only if it maps to an entry in
    :data:`janito.providers._PROVIDER_CONFIGS`.

    Args:
        provider: The provider name to validate (case-insensitive)

    Returns:
        The canonical (correctly cased) provider name.

    Raises:
        ValueError: If the provider is not supported. The message enumerates
            the supported providers.
    """
    return _registry.require(provider).name


def list_supported_providers() -> list:
    """
    List all supported providers.

    Returns:
        List of provider names
    """
    return _registry.names()
