"""Built-in configuration for the Google (Gemini) provider.

``PROVIDER_CONFIG`` is the config entry for ``google``.  See
:mod:`janito.providers.template.config` for the full reference of every
CONFIG option.

The Gemini models are accessed through Google's OpenAI-compatibility layer
(see https://ai.google.dev/gemini-api/docs/openai): the OpenAI SDK is pointed
at ``https://generativelanguage.googleapis.com/v1beta/openai/`` with a Gemini
API key from Google AI Studio (``GEMINI_API_KEY``), so the provider talks to
Gemini through the standard Chat Completions API.
"""

#: The config entry for the ``google`` provider.
PROVIDER_CONFIG: dict = {
    "default_model": "gemini-3.7-flash",
    # Google's OpenAI-compatible base URL: the OpenAI SDK appends
    # /chat/completions to it.  Only the Chat Completions API is documented
    # by the OpenAI-compatibility layer, so the provider is Completions-only.
    "endpoint": "https://generativelanguage.googleapis.com/v1beta/openai/",
    # Gemini-flavored API: Google's OpenAI-compatibility layer has
    # provider-specific behaviours that differ from the standard
    # OpenAI-compatible surface.  In particular, the ``enable_thinking``
    # extra-body flag is **not** accepted (Gemini 3.x models reason by
    # default and the field does not exist); thinking depth is controlled
    # through the resolved reasoning level (``reasoning_effort``), which
    # the API maps to the model's ``thinking_level``.
    "gemini_flavor": True,
    "models": {
        "gemini-3.7-flash": {
            "supported_api_types": ["Completions"],
            "default_api_type": "Completions",  # built-in default (the first supported type)
            "max_input_tokens": 1048576,  # 1M
            "max_output_tokens": 65536,  # 64k
            # Gemini 3.x models reason by default and thinking cannot be
            # disabled for them.  Per the Gemini API OpenAI-compatibility
            # reference, reasoning_effort maps to the model's thinking_level,
            # which accepts minimal/low/medium/high.
            "supported_reasoning_levels": [
                {
                    "effort": "minimal",
                    "description": "Minimal thinking for fast responses",
                },
                {
                    "effort": "low",
                    "description": "Lighter reasoning for fast responses",
                },
                {
                    "effort": "medium",
                    "description": "Standard reasoning depth",
                },
                {
                    "effort": "high",
                    "description": "Deep reasoning for complex problems",
                },
            ],
        },
    },
}
