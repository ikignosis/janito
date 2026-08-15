"""Built-in configuration for the Zhipu (z.ai) provider.

``PROVIDER_CONFIG`` is the config entry for ``zai``.  See
:mod:`janito.providers.template.config` for the full reference of every
CONFIG option.
"""

#: The config entry for the ``zai`` provider.
PROVIDER_CONFIG: dict = {
    "default_model": "glm-5.2",
    "endpoint": "https://api.z.ai/api/paas/v4/",
    "models": {
        "glm-5.2": {
            "supported_api_types": ["Completions"],
            "max_input_tokens": 128000,
            "max_output_tokens": 1000000,  # 1M
        },
    },
}
