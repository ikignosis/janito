"""
Per-provider config loaders.

These helpers read provider-scoped values (``model``, ``endpoint``) and
model-scoped values (``max-output-tokens``, ``max-input-tokens``,
``reasoning-level``, ``api-type``, ``responses-in-server``) from
``~/.janito/config.json``.  They were extracted from
:mod:`janito.general_config` so the core config storage module stays focused
on read/write primitives.

Model-scoped settings are stored under
``providers.<provider>.models.<model>.<key>``; the loaders take an optional
``model`` argument (defaulting to the provider's configured model, else its
built-in default model) and read **only** the model-scoped path.

The class :class:`ProviderConfigLoader` centralizes the loaders (each used
to repeat the ``determine_provider`` -> guard -> ``get_config_value``
-> coerce dance); the module-level functions below are the public API and
delegate to a module-level loader instance.

``general_config`` imports this module's helpers at its top, so this module
imports ``general_config`` *lazily* inside the methods below
(``determine_provider``) rather than at module import time -- this keeps the
import graph acyclic regardless of which module is imported first.
"""

import logging

# Configure logger for this module
logger = logging.getLogger(__name__)


class ProviderConfigLoader:
    """Read provider/model-scoped values from ``~/.janito/config.json``.

    Each loader resolves the provider (``--provider`` CLI argument first, then
    the configured ``provider`` value) and reads its config key.  The
    model-scoped loaders additionally resolve the model (explicit ``model``
    argument first, then the provider's configured model, else its built-in
    default model) and read the ``providers.<provider>.models.<model>.<key>``
    path only.
    """

    @staticmethod
    def _resolve_provider(cli_provider: str | None) -> str | None:
        """Resolve the provider used for provider-scoped config lookups."""
        from .general_config import determine_provider

        return determine_provider(cli_provider)

    @staticmethod
    def _resolve_model(
        cli_provider: str | None, model: str | None = None
    ) -> str | None:
        """Resolve the model used for model-scoped config lookups.

        Priority: the explicit ``model`` argument, then the provider's
        configured model (``<provider>.model``), then the provider's
        built-in default model.
        """
        from .provider_accessors import get_default_model_from_provider

        if model:
            return model
        provider = ProviderConfigLoader._resolve_provider(cli_provider)
        if not provider:
            return None
        return load_model_from_config(provider) or get_default_model_from_provider(
            provider
        )

    def load_model(self, cli_provider: str | None = None) -> str | None:
        """Load the model name for the active provider from config.json.

        The model is stored under a provider-scoped key (``<provider>.model``)
        so that different providers can each have their own default model.

        Args:
            cli_provider: Provider passed via ``--provider`` (may be None). If
                not provided, the provider is read from config.json.

        Returns:
            str: Model name from config, or None if not found or provider unknown
        """
        from .config_keys import model_config_key
        from .config_store import get_config_value

        provider = self._resolve_provider(cli_provider)
        if not provider:
            return None
        return get_config_value(model_config_key(provider))

    def load_max_output_tokens(
        self, cli_provider: str | None = None, model: str | None = None
    ) -> int | None:
        """Load max output tokens from ~/.janito/config.json if it exists.

        This value is used as the maximum output-token limit (``max_tokens`` /
        ``max_completion_tokens``) for API calls. It is stored per
        provider/model under the nested providers structure (e.g.
        providers.openai.models.gpt-5.6-luna.max-output-tokens).

        Args:
            cli_provider: Provider passed via ``--provider`` (may be None). If
                not provided, the provider is read from config.json.
            model: The model the value belongs to. ``None`` resolves to the
                provider's configured model, else its built-in default model.

        Returns:
            int: Max output tokens from config, or None if not found
        """
        from .config_keys import model_scoped_config_key
        from .config_store import get_config_value

        provider = self._resolve_provider(cli_provider)
        if not provider:
            return None
        model = self._resolve_model(cli_provider, model)
        if not model:
            return None
        value = get_config_value(
            model_scoped_config_key(provider, model, "max-output-tokens")
        )
        if value is not None:
            return int(value)
        return None

    def load_max_input_tokens(
        self, cli_provider: str | None = None, model: str | None = None
    ) -> int | None:
        """Load max input tokens from ~/.janito/config.json if it exists.

        This value is the maximum input-token (context window) limit used for
        the usage summary display. It is stored per provider/model under the
        nested providers structure (e.g.
        providers.openai.models.gpt-5.6-luna.max-input-tokens).

        Args:
            cli_provider: Provider passed via ``--provider`` (may be None). If
                not provided, the provider is read from config.json.
            model: The model the value belongs to. ``None`` resolves to the
                provider's configured model, else its built-in default model.

        Returns:
            int: Max input tokens from config, or None if not found
        """
        from .config_keys import model_scoped_config_key
        from .config_store import get_config_value

        provider = self._resolve_provider(cli_provider)
        if not provider:
            return None
        model = self._resolve_model(cli_provider, model)
        if not model:
            return None
        value = get_config_value(
            model_scoped_config_key(provider, model, "max-input-tokens")
        )
        if value is not None:
            return int(value)
        return None

    def load_reasoning_level(
        self, cli_provider: str | None = None, model: str | None = None
    ) -> str | None:
        """Load the reasoning level for the active provider/model from config.json.

        The reasoning level is stored under a model-scoped key
        (``providers.<provider>.models.<model>.reasoning-level``) so that
        different provider/model pairs can each have their own reasoning
        depth (e.g. ``low``/``medium``/``xhigh`` for Qwen3.8-Max).

        Args:
            cli_provider: Provider passed via ``--provider`` (may be None). If
                not provided, the provider is read from config.json.
            model: The model the value belongs to. ``None`` resolves to the
                provider's configured model, else its built-in default model.

        Returns:
            str: The reasoning level from config, or None if not found
        """
        from .config_keys import model_scoped_config_key
        from .config_store import get_config_value

        provider = self._resolve_provider(cli_provider)
        if not provider:
            return None
        model = self._resolve_model(cli_provider, model)
        if not model:
            return None
        value = get_config_value(
            model_scoped_config_key(provider, model, "reasoning-level")
        )
        if value is not None:
            return str(value)
        return None

    def load_api_type(
        self, cli_provider: str | None = None, model: str | None = None
    ) -> str | None:
        """Load the API type for the active provider/model from config.json.

        The API type is stored under a model-scoped key
        (``providers.<provider>.models.<model>.api-type``) so that different
        provider/model pairs can each select which API they talk to
        (``"Responses"`` or ``"Completions"``).

        Args:
            cli_provider: Provider passed via ``--provider`` (may be None). If
                not provided, the provider is read from config.json.
            model: The model the value belongs to. ``None`` resolves to the
                provider's configured model, else its built-in default model.

        Returns:
            str: The API type from config, or None if not found
        """
        from .config_keys import model_scoped_config_key
        from .config_store import get_config_value

        provider = self._resolve_provider(cli_provider)
        if not provider:
            return None
        model = self._resolve_model(cli_provider, model)
        if not model:
            return None
        value = get_config_value(model_scoped_config_key(provider, model, "api-type"))
        if value is not None:
            return str(value)
        return None

    def load_responses_in_server(
        self, cli_provider: str | None = None, model: str | None = None
    ) -> bool | None:
        """Load the Responses-in-server override for a provider/model from config.json.

        The override is stored under a model-scoped key
        (``providers.<provider>.models.<model>.responses-in-server``) so that
        different provider/model pairs can each decide whether their
        Responses API keeps conversation state server-side.

        Args:
            cli_provider: Provider passed via ``--provider`` (may be None). If
                not provided, the provider is read from config.json.
            model: The model the value belongs to. ``None`` resolves to the
                provider's configured model, else its built-in default model.

        Returns:
            bool: The configured override (``True``/``False``), or ``None`` when
                no override is stored (the built-in default applies).
        """
        from .config_keys import model_scoped_config_key
        from .config_store import get_config_value

        provider = self._resolve_provider(cli_provider)
        if not provider:
            return None
        model = self._resolve_model(cli_provider, model)
        if not model:
            return None
        value = get_config_value(
            model_scoped_config_key(provider, model, "responses-in-server")
        )
        if value is None:
            return None
        # Tolerate string forms written by hand/older configs ("true"/"false").
        if isinstance(value, str):
            return value.strip().lower() in ("true", "1", "yes", "on")
        return bool(value)

    def load_endpoint(self, cli_provider: str | None = None) -> str | None:
        """Load custom endpoint URL from ~/.janito/config.json if it exists.

        This is used for the 'custom' provider or to override provider base URLs.

        The endpoint is stored under a provider-scoped key
        (``<provider>.endpoint``) so that different providers can each have their
        own endpoint. The provider is resolved from ``cli_provider`` first, then
        from the configured ``provider`` value.

        For backward compatibility, the legacy top-level ``endpoint`` key is still
        honored as a fallback when no provider-scoped endpoint is set.

        Args:
            cli_provider: Provider passed via ``--provider`` (may be None). If
                not provided, the provider is read from config.json.

        Returns:
            str: Endpoint URL from config, or None if not found or provider unknown
        """
        from .config_keys import endpoint_config_key
        from .config_store import get_config_value

        provider = self._resolve_provider(cli_provider)
        if provider:
            value = get_config_value(endpoint_config_key(provider))
            if value is not None:
                return value
        # Backward compatibility: legacy top-level 'endpoint' key
        return get_config_value("endpoint")


# Module-level singleton backing the backward-compatible functions below.
_loader = ProviderConfigLoader()


def load_model_from_config(cli_provider: str | None = None) -> str | None:
    """Load the model name for the active provider from ~/.janito/config.json.

    The model is stored under a provider-scoped key (``<provider>.model``) so
    that different providers can each have their own default model.

    Args:
        cli_provider: Provider passed via ``--provider`` (may be None). If not
            provided, the provider is read from config.json.

    Returns:
        str: Model name from config, or None if not found or provider unknown
    """
    return _loader.load_model(cli_provider)


def load_max_output_tokens(
    cli_provider: str | None = None, model: str | None = None
) -> int | None:
    """Load max output tokens from ~/.janito/config.json if it exists.

    This value is used as the maximum output-token limit (``max_tokens`` /
    ``max_completion_tokens``) for API calls. It is stored per provider/model
    under the nested providers structure (e.g.
    providers.openai.models.gpt-5.6-luna.max-output-tokens).

    Args:
        cli_provider: Provider passed via ``--provider`` (may be None). If not
            provided, the provider is read from config.json.
        model: The model the value belongs to. ``None`` resolves to the
            provider's configured model, else its built-in default model.

    Returns:
        int: Max output tokens from config, or None if not found
    """
    return _loader.load_max_output_tokens(cli_provider, model)


def load_max_input_tokens(
    cli_provider: str | None = None, model: str | None = None
) -> int | None:
    """Load max input tokens from ~/.janito/config.json if it exists.

    This value is the maximum input-token (context window) limit used for
    the usage summary display. It is stored per provider/model under the
    nested providers structure (e.g.
    providers.openai.models.gpt-5.6-luna.max-input-tokens).

    Args:
        cli_provider: Provider passed via ``--provider`` (may be None). If not
            provided, the provider is read from config.json.
        model: The model the value belongs to. ``None`` resolves to the
            provider's configured model, else its built-in default model.

    Returns:
        int: Max input tokens from config, or None if not found
    """
    return _loader.load_max_input_tokens(cli_provider, model)


def load_reasoning_level(
    cli_provider: str | None = None, model: str | None = None
) -> str | None:
    """Load the reasoning level for the active provider/model from config.json.

    The reasoning level is stored under a model-scoped key
    (``providers.<provider>.models.<model>.reasoning-level``) so that
    different provider/model pairs can each have their own reasoning depth
    (e.g. ``low``/``medium``/``xhigh`` for Qwen3.8-Max).

    Args:
        cli_provider: Provider passed via ``--provider`` (may be None). If not
            provided, the provider is read from config.json.
        model: The model the value belongs to. ``None`` resolves to the
            provider's configured model, else its built-in default model.

    Returns:
        str: The reasoning level from config, or None if not found
    """
    return _loader.load_reasoning_level(cli_provider, model)


def load_api_type(
    cli_provider: str | None = None, model: str | None = None
) -> str | None:
    """Load the API type for the active provider/model from config.json.

    The API type is stored under a model-scoped key
    (``providers.<provider>.models.<model>.api-type``) so that different
    provider/model pairs can each select which API they talk to
    (``"Responses"`` or ``"Completions"``).

    Args:
        cli_provider: Provider passed via ``--provider`` (may be None). If not
            provided, the provider is read from config.json.
        model: The model the value belongs to. ``None`` resolves to the
            provider's configured model, else its built-in default model.

    Returns:
        str: The API type from config, or None if not found
    """
    return _loader.load_api_type(cli_provider, model)


def load_responses_in_server_from_config(
    cli_provider: str | None = None,
    model: str | None = None,
) -> bool | None:
    """Load the Responses-in-server override for a provider/model from config.json.

    The override is stored under a model-scoped key
    (``providers.<provider>.models.<model>.responses-in-server``) so that
    different provider/model pairs can each decide whether their Responses
    API keeps conversation state server-side.

    Args:
        cli_provider: Provider passed via ``--provider`` (may be None). If not
            provided, the provider is read from config.json.
        model: The model the value belongs to. ``None`` resolves to the
            provider's configured model, else its built-in default model.

    Returns:
        bool: The configured override (``True``/``False``), or ``None`` when
            no override is stored (the built-in default applies).
    """
    return _loader.load_responses_in_server(cli_provider, model)


def load_endpoint_from_config(cli_provider: str | None = None) -> str | None:
    """Load custom endpoint URL from ~/.janito/config.json if it exists.

    This is used for the 'custom' provider or to override provider base URLs.

    The endpoint is stored under a provider-scoped key
    (``<provider>.endpoint``) so that different providers can each have their
    own endpoint. The provider is resolved from ``cli_provider`` first, then
    from the configured ``provider`` value.

    For backward compatibility, the legacy top-level ``endpoint`` key is still
    honored as a fallback when no provider-scoped endpoint is set.

    Args:
        cli_provider: Provider passed via ``--provider`` (may be None). If not
            provided, the provider is read from config.json.

    Returns:
        str: Endpoint URL from config, or None if not found or provider unknown
    """
    return _loader.load_endpoint(cli_provider)
