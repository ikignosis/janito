"""Built-in configuration for the OpenRouter provider.

``PROVIDER_CONFIG`` is the config entry for ``openrouter``.  OpenRouter is an
aggregator: it proxies models from many providers behind a single
OpenAI-compatible endpoint, so it has no single sensible default model.
Like the ``custom`` provider it therefore requires the user to pick a model
explicitly (``--model`` or ``providers.openrouter.model`` in config.json).

Unlike ``custom``, it ships a built-in endpoint and a placeholder
``custom`` model entry that only carries built-in defaults (the default API
type), so API-type resolution still works before a model is configured.
The placeholder default model is not a real model name: runtime model
resolution treats it as "no model configured" and informs the user (see
``janito.provider_accessors.requires_explicit_model`` and
``janito.openai_client.completions_api.resolve_runtime_config``).

See :mod:`janito.providers.template.config` for the full reference of every
CONFIG option.
"""

#: The config entry for the ``openrouter`` provider.
PROVIDER_CONFIG: dict = {
    # The "custom" placeholder: not a real model name.  It marks that the
    # provider has no usable default model -- the user must supply one
    # (--model or providers.openrouter.model) -- while its ``models`` entry
    # below carries the built-in defaults (the default API type).
    "default_model": "custom",
    "endpoint": "https://openrouter.ai/api/v1",
    "models": {
        "custom": {
            "supported_api_types": ["Completions"],
            "default_api_type": "Completions",
        },
    },
}
