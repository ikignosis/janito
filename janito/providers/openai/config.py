"""Built-in configuration for the OpenAI provider.

``PROVIDER_CONFIG`` is the config entry for ``openai``.  See
:mod:`janito.providers.template.config` for the full reference of every
CONFIG option.
"""

#: The config entry for the ``openai`` provider.
PROVIDER_CONFIG: dict = {
    "default_model": "gpt-5.6-luna",
    "endpoint": None,  # Standard OpenAI - no base_url needed
    "models": {
        "gpt-5.6-sol": {
            "supported_api_types": [
                "Responses",
                "Completions",
            ],
            "default_api_type": "Responses",  # built-in default (Responses is the default)
            "responses_in_server": True,  # server-side conversation state (previous_response_id)
            "max_input_tokens": 1050000,
            "max_output_tokens": 128000,
        },
        "gpt-5.6-terra": {
            "supported_api_types": [
                "Responses",
                "Completions",
            ],
            "default_api_type": "Responses",  # built-in default (Responses is the default)
            "responses_in_server": True,  # server-side conversation state (previous_response_id)
            "max_input_tokens": 1050000,
            "max_output_tokens": 128000,
        },
        "gpt-5.6-luna": {
            "supported_api_types": [
                "Responses",
                "Completions",
            ],
            "default_api_type": "Responses",  # built-in default (Responses is the default)
            "responses_in_server": True,  # server-side conversation state (previous_response_id)
            "max_input_tokens": 1050000,
            "max_output_tokens": 128000,
        },
    },
}
