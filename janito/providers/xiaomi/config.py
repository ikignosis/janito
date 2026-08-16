"""Built-in configuration for the Xiaomi provider.

``PROVIDER_CONFIG`` is the config entry for ``xiaomi``.  See
:mod:`janito.providers.template.config` for the full reference of every
CONFIG option.
"""

#: The config entry for the ``xiaomi`` provider.
PROVIDER_CONFIG: dict = {
    "default_model": "mimo-v2.5",
    "endpoint": "https://api.xiaomimimo.com/v1",
    "models": {
        "mimo-v2.5": {
            "supported_api_types": ["Completions"],
            "default_api_type": "Completions",  # built-in default (the first supported type)
            "max_input_tokens": 128000,
            "max_output_tokens": 120000,  # 128k
        },
    },
}
