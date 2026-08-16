"""Built-in configuration for the Alibaba (DashScope) provider.

``PROVIDER_CONFIG`` is the config entry for ``alibaba``.  See
:mod:`janito.providers.template.config` for the full reference of every
CONFIG option.
"""

#: The config entry for the ``alibaba`` provider.
PROVIDER_CONFIG: dict = {
    "default_model": "qwen3.8-max",
    "endpoint": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    # Per-API-type endpoints: the OpenAI-compatible Chat Completions /
    # Responses base URL (DashScope's plain compatible-mode gateway, the
    # same URL the OpenAI SDK appends /chat/completions and /responses
    # to) and the native DashScope SDK base URL (the SDK talks to the
    # DashScope native API, not the compatible-mode gateway). The
    # "apps-protocol" compatible-mode URL
    # (dashscope-intl.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1)
    # only serves Model Studio *applications* and rejects ordinary
    # DashScope API keys with "Not support", so it must not be used here.
    "endpoint_by_api_type": {
        "Completions": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "Responses": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "DashScope": "https://dashscope-intl.aliyuncs.com/api/v1",
    },
    "models": {
        "qwen3.8-max": {
            # Completions is the built-in default: DashScope's /responses
            # endpoint does not (yet) support qwen3.8-max (it rejects it
            # with "Unsupported model: 'qwen3.8-max'."), so the
            # out-of-the-box provider must use the Completions API where
            # the default model works. The Responses API is still
            # supported for models that expose it (e.g. qwen3.7-max,
            # qwen3.6-plus, qwen3.5-plus, qwen-plus, qwen-flash) and can
            # be selected with --set api-type=Responses or --api-type
            # responses. The native DashScope SDK API type is selectable
            # with --set api-type=DashScope or --api-type DashScope (it
            # requires the optional `dashscope` package; see
            # REQUIRES_BY_API_TYPE).
            "supported_api_types": ["Completions", "Responses", "DashScope"],
            "max_input_tokens": 1000000,  # 1M
            "max_output_tokens": 131072,
            "reasoning_level": "xhigh",
            "thinking": True,  # Qwen models reason by default
            # Built-in (native) tools, enabled per API type.  These are
            # *not* function tools: on the Responses API they are entries in
            # the ``tools`` array, on the Completions API they are extra_body
            # ``enable_code_interpreter`` / ``enable_search`` flags, and on
            # the native DashScope API they are ``enable_code_interpreter`` /
            # ``enable_search`` kwargs.  ``code_interpreter`` only supports
            # calls in thinking mode, so it also forces ``enable_thinking``
            # on.
            #
            # Only the Responses API is enabled: the qwen3.8-max deployment
            # rejects the built-in tools on the Completions API with ``400
            # InternalError.Algo.InvalidParameter: The current model does not
            # support the code_interpreter tool.``, and the DashScope native
            # endpoint is left off for the same reason until confirmed.
            # Re-enable per API type once the endpoint accepts them.
            "tools_by_api_type": {
                "Responses": [
                    {"type": "code_interpreter"},
                    {"type": "web_search"},
                    {"type": "web_extractor"},
                ],
            },
            "supported_reasoning_levels": [
                {
                    "effort": "low",
                    "description": "Fast responses with lighter reasoning",
                },
                {
                    "effort": "medium",
                    "description": "Greater reasoning depth for complex problems",
                },
                {
                    "effort": "xhigh",
                    "description": "Extra high reasoning depth for complex problems",
                },
            ],
        },
    },
}
