"""
Built-in provider data for Janito CLI.

This module holds the static provider registry (``PROVIDER_INFO``), the
optional-package map for non-OpenAI API types (``REQUIRES_BY_API_TYPE``) and
the special ``CUSTOM_ENDPOINT`` marker.  It was extracted from
:mod:`janito.provider_config` (which re-exports these names and implements the
accessor functions over this data).

Provider Info:
{
    "openai": {
        "model": "gpt-4",
        "max_input_tokens": 128000,
        "max_output_tokens": 128000,
        "endpoint": None,  # Standard OpenAI - no base_url needed
    },
    # ... more providers
}
"""

# Marker for the special "custom" provider: its endpoint is not built in and
# must be supplied via config (--set endpoint).
CUSTOM_ENDPOINT_MARKER = "CUSTOM_ENDPOINT"


# Per-provider built-in defaults.
#
# Each entry describes a supported provider and carries more information than
# just the endpoint (the old ``PROVIDER_BASE_URLS`` only mapped a provider to
# its base URL). The fields are:
#
#   - "model": the model used when the user has not configured one.
#     ``None`` means the provider has no sensible default and the user must
#     set a model explicitly (e.g. the "custom" provider).
#   - "supported_api_types": the API types the provider supports
#     ("Responses" and/or "Completions"). The **first** entry is the built-in
#     default API type for the provider (e.g. OpenAI defaults to the
#     Responses API). The effective type can be overridden per-provider with
#     ``--set api-type=...`` or per-call with ``--api-type``.
#   - "responses_in_server": whether the provider's Responses API endpoint
#     keeps the conversation state server-side (so turns can be chained with
#     ``previous_response_id``). ``True`` for providers that follow the
#     OpenAI Responses API design (e.g. OpenAI); ``False`` for providers
#     whose ``/responses`` endpoint is **stateless** (e.g. DeepSeek), which
#     cannot resolve a previous response id and require the client to track
#     and re-send the entire conversation history on every request (like
#     Chat Completions). Absent defaults to ``True`` (the Responses API
#     design). Only meaningful when the provider also supports "Responses".
#   - "max_input_tokens": the maximum input-token (context window)
#     limit used as the built-in default. ``None`` means there is no built-in
#     limit (the caller falls back to its own default).
#   - "max_output_tokens": the maximum output-token limit (max_tokens
#     / max_completion_tokens) used when the user has not configured one.
#     ``None`` means there is no built-in limit (the caller falls back to its
#     own default).
#   - "reasoning_level": the reasoning level/effort used by default for
#     the provider's default model when it supports configurable reasoning
#     depth. ``None`` (or absent) means there is no built-in default.
#   - "supported_reasoning_levels": the list of reasoning levels supported by
#     the provider's default model, each with an ``effort`` key and a
#     human-readable ``description``. Absent when the model has no
#     configurable reasoning.
#   - "thinking": whether thinking mode (``extra_body=
#     {'enable_thinking': True}``) is enabled by default for the provider's
#     models. ``True`` for providers whose models reason by default (DeepSeek,
#     Alibaba/Qwen); absent (or ``False``) for the rest. The CLI ``--thinking``
#     flag still forces it on explicitly.
#   - "endpoint": the OpenAI-compatible base URL. ``None`` means the standard
#     OpenAI API endpoint (no custom base URL needed); the special
#     ``CUSTOM_ENDPOINT`` marker means the endpoint must come from config.
PROVIDER_INFO: dict[str, dict] = {
    # AI Providers with OpenAI-compatible APIs
    "openai": {
        "model": "gpt-5.6-luna",
        "supported_api_types": ["Responses", "Completions"],  # Responses is the default
        "responses_in_server": True,  # server-side conversation state (previous_response_id)
        "max_input_tokens": 1050000,
        "max_output_tokens": 128000,
        "endpoint": None,  # Standard OpenAI - no base_url needed
    },
    "minimax": {
        "model": "MiniMax-M3",
        "supported_api_types": ["Completions"],
        "max_input_tokens": 128000,
        "max_output_tokens": 511000,  # 512k
        "endpoint": "https://api.minimax.io/v1",
    },
    "xiaomi": {
        "model": "mimo-v2.5",
        "supported_api_types": ["Completions"],
        "max_input_tokens": 128000,
        "max_output_tokens": 120000,  # 128k
        "endpoint": "https://api.xiaomimimo.com/v1",
    },
    "moonshot": {
        "model": "kimi-k3-256k",
        "supported_api_types": ["Completions"],
        "max_input_tokens": 128000,
        "max_output_tokens": 250000,  # 256k
        "endpoint": "https://api.moonshot.ai/v1",
    },
    "alibaba": {
        "model": "qwen3.8-max",
        # Completions is the built-in default: DashScope's /responses endpoint
        # does not (yet) support qwen3.8-max (it rejects it with "Unsupported
        # model: 'qwen3.8-max'."), so the out-of-the-box provider must use the
        # Completions API where the default model works. The Responses API is
        # still supported for models that expose it (e.g. qwen3.7-max,
        # qwen3.6-plus, qwen3.5-plus, qwen-plus, qwen-flash) and can be
        # selected with --set api-type=Responses or --api-type responses. The
        # native DashScope SDK API type is selectable with
        # --set api-type=DashScope or --api-type DashScope (it requires the
        # optional `dashscope` package; see REQUIRES_BY_API_TYPE).
        "supported_api_types": ["Completions", "Responses", "DashScope"],
        "max_input_tokens": 1000000,  # 1M
        "max_output_tokens": 131072,
        "reasoning_level": "xhigh",
        "thinking": True,  # Qwen models reason by default
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
        "endpoint": "https://dashscope-intl.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1",
        # Per-API-type endpoints: the OpenAI-compatible Chat Completions /
        # Responses URL and the native DashScope SDK base URL (the SDK talks
        # to the DashScope native API, not the compatible-mode gateway).
        "endpoint_by_api_type": {
            "Completions": "https://dashscope-intl.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1",
            "Responses": "https://dashscope-intl.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1",
            "DashScope": "https://dashscope-intl.aliyuncs.com/api/v1",
        },
    },
    "zai": {
        "model": "glm-5.2",
        "supported_api_types": ["Completions"],
        "max_input_tokens": 128000,
        "max_output_tokens": 1000000,  # 1M
        "endpoint": "https://api.z.ai/api/paas/v4/",
    },
    "deepseek": {
        "model": "deepseek-v4-flash",
        "supported_api_types": ["Responses", "Completions", "Anthropic"],
        # DeepSeek's /responses endpoint is stateless: it cannot resolve a
        # previous_response_id, so the client must re-send the full history.
        "responses_in_server": False,
        "max_input_tokens": 1048576,  # 1M
        "max_output_tokens": 393216,  # 384k
        "thinking": True,  # DeepSeek models reason by default
        # Per the DeepSeek API reference, reasoning_effort accepts
        # low/high/max (default high; medium/xhigh map to high for
        # compatibility). deepseek-v4-pro currently supports only high/max
        # (low is treated as high, xhigh as max); deepseek-v4-flash supports
        # all three levels.
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
    },
    "xai": {
        "model": "grok-4",
        "supported_api_types": ["Completions"],
        "max_input_tokens": 128000,
        "max_output_tokens": 131072,
        "endpoint": "https://api.x.ai/v1",
    },
    "anthropic": {
        "model": "claude-sonnet-5",
        "supported_api_types": [
            "Completions",
            "Anthropic",  # native Anthropic SDK (requires the `anthropic` package)
        ],  # Completions is the built-in default: Anthropic's OpenAI-compatible
        # /v1/chat/completions. The native Anthropic SDK API type is selectable
        # with --set api-type=Anthropic / --api-type Anthropic (it requires the
        # optional `anthropic` package; see REQUIRES_BY_API_TYPE).
        "max_input_tokens": 200000,
        "max_output_tokens": 64000,
        "endpoint": "https://api.anthropic.com/v1/",
        # Per-API-type endpoints: the OpenAI-compatible Chat Completions URL
        # and the native Anthropic SDK base URL. A provider whose dict holds a
        # single entry uses that URL as the default for *any* API type (unless
        # a config endpoint is set); see get_endpoint_for_api_type.
        "endpoint_by_api_type": {
            "Completions": "https://api.anthropic.com/v1/",
            "Anthropic": "https://api.anthropic.com",
        },
    },
    # Special case: requires an endpoint from config (--set endpoint) and has
    # no built-in default model.
    "custom": {
        "model": None,
        "supported_api_types": ["Completions"],
        "max_input_tokens": None,
        "max_output_tokens": None,
        "endpoint": CUSTOM_ENDPOINT_MARKER,
    },
}

# Optional Python package required by each non-OpenAI API type.
#
# The two built-in API types (``"Responses"`` and ``"Completions"``) are
# served by the ``openai`` package, which is a hard dependency, so they never
# appear here. Any *other* API type listed in a provider's
# ``supported_api_types`` (e.g. ``"Anthropic"`` for the native Anthropic SDK)
# is backed by an optional package declared in this dict, keyed by the
# canonical API type.
#
# When the user attempts to set an API type whose required package is missing,
# the change is aborted with a message naming the package that must be
# installed (see :func:`ensure_api_type_available`).
REQUIRES_BY_API_TYPE: dict[str, str] = {
    "Anthropic": "anthropic",
    "DashScope": "dashscope",
}
