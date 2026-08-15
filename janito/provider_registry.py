"""
Provider registry and variant-name helpers.

Defines :class:`ProviderRegistry` (case-insensitive lookup over
:data:`janito.providers._PROVIDER_CONFIGS`, including registered provider
variants) plus the ``parse_variant_name`` / ``is_variant_style_name``
helpers it relies on.  Part of the split provider-config module family (see
:mod:`janito.provider_accessors`).
"""

from .provider_models import Provider
from .providers import _PROVIDER_CONFIGS, REQUIRES_BY_API_TYPE


def parse_variant_name(name: str) -> tuple[str, str] | None:
    """Split a variant-style name into its ``(base_provider, word)`` parts.

    A variant name follows the syntax ``<provider>-<word>``; the split
    happens on the **first** hyphen, so the word may itself contain hyphens
    (e.g. ``alibaba-token-plan`` -> ``("alibaba", "token-plan")``).

    Args:
        name: The raw name.

    Returns:
        A ``(base, word)`` tuple with both parts non-empty (stripped), or
        ``None`` when the name is not in ``<provider>-<word>`` form.
    """
    if not name:
        return None
    parts = str(name).split("-", 1)
    if len(parts) != 2:
        return None
    base, word = parts[0].strip(), parts[1].strip()
    if not base or not word:
        return None
    return base, word


def is_variant_style_name(name: str) -> bool:
    """Whether ``name`` looks like a provider variant (``<provider>-<word>``).

    This only checks the shape; the variant need not be registered (use
    :func:`is_registered_provider_variant` for that).

    Args:
        name: The provider name.

    Returns:
        True if the name matches the ``<provider>-<word>`` syntax.
    """
    return parse_variant_name(name) is not None


class ProviderRegistry:
    """Registry over :data:`janito.providers._PROVIDER_CONFIGS` with case-insensitive lookup.

    The registry holds a *reference* to the data dict (never a copy), and
    constructs :class:`Provider` instances on demand, so runtime mutations to
    the config registry (e.g. tests injecting a fake provider) are reflected
    in every lookup.

    Besides the built-in providers, the registry also resolves **registered
    provider variants** (``<provider>-<word>``, created with
    ``janito --create-variant``): a variant is looked up case-insensitively
    and yields a :class:`Provider` over the *base* provider's info entry,
    keeping the variant name as the provider name.
    """

    def __init__(self, data: dict | None = None, requires: dict | None = None):
        """Create a registry over ``data`` (defaults to ``_PROVIDER_CONFIGS``).

        Args:
            data: The provider config dict to read from. Defaults to the
                module-level :data:`janito.providers._PROVIDER_CONFIGS`.
            requires: The optional-package map keyed by API type. Defaults to
                :data:`janito.providers.REQUIRES_BY_API_TYPE`.
        """
        self._data = _PROVIDER_CONFIGS if data is None else data
        self._requires = REQUIRES_BY_API_TYPE if requires is None else requires

    @property
    def requires(self) -> dict:
        """The optional-package map (API type -> required package)."""
        return self._requires

    @staticmethod
    def _variant_base(name: str) -> str | None:
        """Return the canonical base provider of a registered variant.

        A variant is a ``<provider>-<word>`` name registered via
        ``janito --create-variant`` (stored as a ``providers`` entry in
        config.json).  The base is the provider prefix (before the first
        ``-``), which must be a supported provider (a config entry in
        :data:`janito.providers._PROVIDER_CONFIGS`) and the variant
        itself must be registered.

        Args:
            name: The provider name to check.

        Returns:
            The canonical base provider name if ``name`` is a registered
            variant, otherwise ``None``.
        """
        from .config_variants import is_registered_variant

        parsed = parse_variant_name(name)
        if parsed is None:
            return None
        base, _ = parsed
        base_lower = base.strip().lower()
        if not base_lower:
            return None
        for key in _PROVIDER_CONFIGS:
            if key.lower() == base_lower:
                return key if is_registered_variant(name) else None
        return None

    def canonical_name(self, provider: str) -> str | None:
        """Return the canonical (correctly cased) name for a provider.

        Supports both the built-in providers in
        :data:`janito.providers._PROVIDER_CONFIGS` and registered provider
        variants (``<provider>-<word>``).  Variants are matched
        case-insensitively and returned in their canonical (lowercased) form.

        Args:
            provider: The provider name (case-insensitive, surrounding
                whitespace ignored).

        Returns:
            The canonical provider name as used in ``_PROVIDER_CONFIGS`` if
            the provider is supported, the lowercased variant name if it is a
            registered variant, otherwise ``None``.
        """
        if not provider:
            return None

        provider_lower = provider.strip().lower()
        if not provider_lower:
            return None

        for key in self._data:
            if key.lower() == provider_lower:
                return key

        # Registered provider variant (<provider>-<word>): the base must be a
        # supported provider and the variant must be registered.
        if self._variant_base(provider) is not None:
            return provider_lower
        return None

    def get(self, name: str) -> Provider | None:
        """Look up a provider by name (case-insensitive, no whitespace strip).

        Mirrors the historical :func:`get_provider_config` semantics: an exact
        match wins, then a case-insensitive match.  Registered provider
        variants resolve to a :class:`Provider` over the base provider's info.
        Surrounding whitespace is *not* stripped here (use
        :meth:`canonical_name` for that).

        Args:
            name: The provider name.

        Returns:
            A :class:`Provider`, or ``None`` when unknown/empty.
        """
        if not name:
            return None

        # Try exact match first, then case-insensitive.
        if name in self._data:
            return Provider(name, self._data)

        name_lower = name.lower()
        for key in self._data:
            if key.lower() == name_lower:
                return Provider(key, self._data)

        # Registered provider variant: build a Provider over the base
        # provider's info, keeping the variant name as the provider name.
        base = self._variant_base(name)
        if base is not None:
            return Provider(name.strip().lower(), self._data, variant_of=base)

        return None

    def require(self, name: str) -> Provider:
        """Return the provider, raising ``ValueError`` when unsupported.

        Args:
            name: The provider name to validate (case-insensitive).  May be
                a supported provider or a registered variant.

        Returns:
            A :class:`Provider` for the canonical provider name.

        Raises:
            ValueError: If the provider is not supported. The message
                enumerates the supported providers and, when the name looks
                like an unregistered variant, hints at ``--create-variant``.
        """
        canonical = self.canonical_name(name)
        if canonical is None:
            supported = ", ".join(sorted(self._data.keys()))
            hint = ""
            if parse_variant_name(name) is not None:
                hint = (
                    f" Note: '{name}' looks like a provider variant "
                    f"(<provider>-<word>) but is not registered; create it "
                    f"with: janito --create-variant {name.strip()}"
                )
            raise ValueError(
                f"Unknown provider '{name}'. Supported providers: {supported}.{hint}"
            )
        if canonical in self._data:
            return Provider(canonical, self._data)
        base = self._variant_base(canonical)
        if base is None:  # pragma: no cover - canonical implies a match
            supported = ", ".join(sorted(self._data.keys()))
            raise ValueError(
                f"Unknown provider '{name}'. Supported providers: {supported}"
            )
        return Provider(canonical, self._data, variant_of=base)

    def names(self) -> list:
        """List all supported provider names."""
        return list(self._data.keys())


# Module-level singleton registry backing the functions below.
_registry = ProviderRegistry()
