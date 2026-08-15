"""Built-in configuration for the xAI (Grok) provider.

``PROVIDER_CONFIG`` is the config entry for ``xai``.  See
:mod:`janito.providers.template.config` for the full reference of every
CONFIG option.
"""

#: The config entry for the ``xai`` provider.
PROVIDER_CONFIG: dict = {
    "default_model": "grok-4",
    "endpoint": "https://api.x.ai/v1",
    "models": {
        "grok-4": {
            "supported_api_types": ["Completions"],
            "max_input_tokens": 128000,
            "max_output_tokens": 131072,
        },
    },
}
