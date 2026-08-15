"""
Built-in provider data for Janito CLI.

This module holds the static provider registry (``PROVIDER_INFO``), the
optional-package map for non-OpenAI API types (``REQUIRES_BY_API_TYPE``) and
the special ``CUSTOM_ENDPOINT`` marker.  It was extracted from
:mod:`janito.provider_accessors` (which implements the accessor functions
over this data).

Provider Info:
{
    "openai": {
        "default_model": "gpt-5.6-luna",
        "endpoint": None,  # Standard OpenAI - no base_url needed
        "models": {
            "gpt-5.6-luna": {
                "supported_api_types": ["Responses", "Completions"],
                "max_input_tokens": 1050000,
                "max_output_tokens": 128000,
                "responses_in_server": True,
            },
        },
    },
    # ... more providers
}

Configuration is organized at two levels: the *provider level* holds what is
intrinsic to the provider (``default_model``, ``endpoint``,
``endpoint_by_api_type``), while everything that depends on the model lives
under the per-provider ``models`` dict, keyed by model name.
"""

# Marker for the special "custom" provider: its endpoint is not built in and
# must be supplied via config (--set endpoint).
CUSTOM_ENDPOINT_MARKER = "CUSTOM_ENDPOINT"


# Per-provider built-in defaults.
#
# Each entry describes a supported provider.  The fields are split between
# the **provider level** (what is intrinsic to the provider) and the **model
# level** (per-model capabilities and defaults, under ``models``):
#
# Provider-level fields:
#
#   - "default_model": the model used when the user has not configured one.
#     ``None`` means the provider has no sensible default and the user must
#     set a model explicitly (e.g. the "custom" provider).  The name doubles
#     as the key of the model's entry in ``models``.
#   - "endpoint": the OpenAI-compatible base URL. ``None`` means the standard
#     OpenAI API endpoint (no custom base URL needed); the special
#     ``CUSTOM_ENDPOINT`` marker means the endpoint must come from config.
#   - "endpoint_by_api_type" (optional): per-API-type base URLs, e.g. the
#     native-SDK URL next to the OpenAI-compatible one.
#
# Model-level fields (each entry of the ``models`` dict):
#
#   - "supported_api_types": the API types the model supports
#     ("Responses" and/or "Completions", plus native-SDK types such as
#     "Anthropic"/"DashScope"). The **first** entry is the built-in default
#     API type for the model (e.g. OpenAI's default model uses the Responses
#     API). The effective type can be overridden per provider/model with
#     ``--set api-type=...`` or per-call with ``--api-type``.
#   - "responses_in_server": whether the model's Responses API endpoint keeps
#     the conversation state server-side (so turns can be chained with
#     ``previous_response_id``). ``True`` for models that follow the OpenAI
#     Responses API design (e.g. OpenAI); ``False`` for models whose
#     ``/responses`` endpoint is **stateless** (e.g. DeepSeek), which cannot
#     resolve a previous response id and require the client to track and
#     re-send the entire conversation history on every request (like Chat
#     Completions). Absent defaults to ``True`` (the Responses API design).
#     Only meaningful when the model also supports "Responses".
#   - "max_input_tokens": the maximum input-token (context window) limit used
#     as the built-in default. Absent/``None`` means there is no built-in
#     limit (the caller falls back to its own default).
#   - "max_output_tokens": the maximum output-token limit (max_tokens /
#     max_completion_tokens) used when the user has not configured one.
#     Absent/``None`` means there is no built-in limit (the caller falls back
#     to its own default).
#   - "reasoning_level": the reasoning level/effort used by default for the
#     model when it supports configurable reasoning depth. Absent means there
#     is no built-in default.
#   - "supported_reasoning_levels": the list of reasoning levels supported by
#     the model, each with an ``effort`` key and a human-readable
#     ``description``. Absent when the model has no configurable reasoning.
#   - "thinking": whether thinking mode (``extra_body=
#     {'enable_thinking': True}``) is enabled by default for the model.
#     ``True`` for models that reason by default (DeepSeek, Alibaba/Qwen);
#     absent (or ``False``) for the rest. The CLI ``--thinking`` flag still
#     forces it on explicitly.
PROVIDER_INFO: dict[str, dict] = {
    # AI Providers with OpenAI-compatible APIs
    "openai": {
        "default_model": "gpt-5.6-luna",
        "endpoint": None,  # Standard OpenAI - no base_url needed
        "models": {
            "gpt-5.6-luna": {
                "supported_api_types": [
                    "Responses",
                    "Completions",
                ],  # Responses is the default
                "responses_in_server": True,  # server-side conversation state (previous_response_id)
                "max_input_tokens": 1050000,
                "max_output_tokens": 128000,
            },
        },
    },
    "minimax": {
        "default_model": "MiniMax-M3",
        "endpoint": "https://api.minimax.io/v1",
        "models": {
            "MiniMax-M3": {
                "supported_api_types": ["Completions"],
                "max_input_tokens": 128000,
                "max_output_tokens": 511000,  # 512k
            },
        },
    },
    "xiaomi": {
        "default_model": "mimo-v2.5",
        "endpoint": "https://api.xiaomimimo.com/v1",
        "models": {
            "mimo-v2.5": {
                "supported_api_types": ["Completions"],
                "max_input_tokens": 128000,
                "max_output_tokens": 120000,  # 128k
            },
        },
    },
    "moonshot": {
        "default_model": "kimi-k3-256k",
        "endpoint": "https://api.moonshot.ai/v1",
        "models": {
            "kimi-k3-256k": {
                "supported_api_types": ["Completions"],
                "max_input_tokens": 128000,
                "max_output_tokens": 250000,  # 256k
                # Per the Moonshot/Kimi API reference, reasoning_effort accepts
                # low/high/max (default max). Kimi K3 models always reason.
                "reasoning_level": "max",
                "supported_reasoning_levels": [
                    {
                        "effort": "low",
                        "description": "Lighter reasoning for fast responses",
                    },
                    {
                        "effort": "high",
                        "description": "Standard reasoning depth",
                    },
                    {
                        "effort": "max",
                        "description": "Maximum reasoning depth (the API default)",
                    },
                ],
            },
        },
    },
    "alibaba": {
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
    },
    "zai": {
        "default_model": "glm-5.3",
        "endpoint": "https://api.z.ai/api/paas/v4/",
        "models": {
            "glm-5.3": {
                "supported_api_types": ["Completions"],
                "max_input_tokens": 128000,
                "max_output_tokens": 1000000,  # 1M
            },
            "glm-5.2": {
                "supported_api_types": ["Completions"],
                "max_input_tokens": 128000,
                "max_output_tokens": 1000000,  # 1M
            },
        },
    },
    "deepseek": {
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
    },
    "xai": {
        "default_model": "grok-4",
        "endpoint": "https://api.x.ai/v1",
        "models": {
            "grok-4": {
                "supported_api_types": ["Completions"],
                "max_input_tokens": 128000,
                "max_output_tokens": 131072,
            },
        },
    },
    "anthropic": {
        "default_model": "claude-sonnet-5",
        "endpoint": "https://api.anthropic.com/v1/",
        # Per-API-type endpoints: the OpenAI-compatible Chat Completions URL
        # and the native Anthropic SDK base URL. A provider whose dict holds a
        # single entry uses that URL as the default for *any* API type (unless
        # a config endpoint is set); see get_endpoint_for_api_type.
        "endpoint_by_api_type": {
            "Completions": "https://api.anthropic.com/v1/",
            "Anthropic": "https://api.anthropic.com",
        },
        "models": {
            "claude-sonnet-5": {
                "supported_api_types": [
                    "Completions",
                    "Anthropic",  # native Anthropic SDK (requires the `anthropic` package)
                ],  # Completions is the built-in default: Anthropic's
                # OpenAI-compatible /v1/chat/completions. The native Anthropic
                # SDK API type is selectable with --set api-type=Anthropic /
                # --api-type Anthropic (it requires the optional `anthropic`
                # package; see REQUIRES_BY_API_TYPE).
                "max_input_tokens": 200000,
                "max_output_tokens": 64000,
            },
        },
    },
    # Special case: requires an endpoint from config (--set endpoint) and has
    # no built-in default model (and therefore no built-in model entries).
    "custom": {
        "default_model": None,
        "endpoint": CUSTOM_ENDPOINT_MARKER,
        "models": {},
    },
}

# Optional Python package required by each non-OpenAI API type.
#
# The two built-in API types (``"Responses"`` and ``"Completions"``) are
# served by the ``openai`` package, which is a hard dependency, so they never
# appear here. Any *other* API type listed in a model's
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
