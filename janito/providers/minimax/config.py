"""Built-in configuration for the MiniMax provider.

``PROVIDER_CONFIG`` is the config entry for ``minimax``.  See
:mod:`janito.providers.template.config` for the full reference of every
CONFIG option.
"""

#: The config entry for the ``minimax`` provider.
PROVIDER_CONFIG: dict = {
    "default_model": "MiniMax-M3",
    "endpoint": "https://api.minimax.io/v1",
    # Per-API-type endpoints: the OpenAI-compatible base URL (Chat
    # Completions / Responses) and the Anthropic-compatible base URL for
    # the native Anthropic SDK API type. MiniMax's Anthropic-compatible
    # API lives at https://api.minimax.io/anthropic, so the native-SDK
    # API type is selectable with --set api-type=Anthropic /
    # --api-type Anthropic (it requires the optional `anthropic` package;
    # see REQUIRES_BY_API_TYPE).
    "endpoint_by_api_type": {
        "Completions": "https://api.minimax.io/v1",
        "Responses": "https://api.minimax.io/v1",
        "Anthropic": "https://api.minimax.io/anthropic",
    },
    "models": {
        "MiniMax-M3": {
            "supported_api_types": ["Completions", "Anthropic"],
            "max_input_tokens": 1000000,  # 1M
            "max_output_tokens": 511000,  # 512k
            # MiniMax-M3 reasons by default. Its OpenAI-compatible API
            # controls thinking with a `thinking` object (type can be
            # "disabled" or "adaptive"; adaptive == thinking on), so the
            # built-in default is a pass-through dict instead of a plain
            # True flag (see apply_thinking_to_extra_body).
            "thinking": {"type": "adaptive"},
        },
    },
}
