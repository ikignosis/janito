"""Built-in configuration for the DeepSeek provider.

``PROVIDER_CONFIG`` is the config entry for ``deepseek``.  See
:mod:`janito.providers.template.config` for the full reference of every
CONFIG option.
"""

#: The config entry for the ``deepseek`` provider.
PROVIDER_CONFIG: dict = {
    "default_model": "deepseek-v4-flash",
    "endpoint": "https://api.deepseek.com",
    # Per-API-type endpoints: the OpenAI-compatible base URL (Chat
    # Completions / Responses) and the Anthropic-compatible base URL for
    # the native Anthropic SDK API type. DeepSeek's Anthropic API lives at
    # https://api.deepseek.com/anthropic (see the DeepSeek API docs), so
    # the native-SDK API type is selectable with --set api-type=Anthropic
    # / --api-type Anthropic (it requires the optional `anthropic`
    # package; see REQUIRES_BY_API_TYPE).
    "endpoint_by_api_type": {
        "Completions": "https://api.deepseek.com",
        "Responses": "https://api.deepseek.com",
        "Anthropic": "https://api.deepseek.com/anthropic",
    },
    "models": {
        "deepseek-v4-flash": {
            "supported_api_types": ["Responses", "Completions", "Anthropic"],
            # DeepSeek's /responses endpoint is stateless: it cannot
            # resolve a previous_response_id, so the client must re-send
            # the full history.
            "responses_in_server": False,
            "max_input_tokens": 1048576,  # 1M
            "max_output_tokens": 393216,  # 384k
            "thinking": True,  # DeepSeek models reason by default
            # Per the DeepSeek API reference, reasoning_effort accepts
            # low/high/max (default high; medium/xhigh map to high for
            # compatibility). deepseek-v4-pro currently supports only
            # high/max (low is treated as high, xhigh as max);
            # deepseek-v4-flash supports all three levels.
            "supported_reasoning_levels": [
                {
                    "effort": "low",
                    "description": "Lighter reasoning for fast responses",
                },
                {
                    "effort": "high",
                    "description": "Standard reasoning depth (the API default)",
                },
                {
                    "effort": "max",
                    "description": "Maximum reasoning depth for complex problems",
                },
            ],
        },
    },
}
