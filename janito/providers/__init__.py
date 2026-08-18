"""Per-provider configuration package.

The static provider registry is split into one ``config.py`` module per
provider under ``janito.providers.<name>``; each module exports
``PROVIDER_CONFIG`` -- that provider's config entry.  This package assembles
the per-provider entries into the internal ``_PROVIDER_CONFIGS`` dict and
exposes :func:`get_provider_config` for direct, model-scoped lookups.

Provider Info:
{
    "openai": {
        "default_model": "gpt-5.6-luna",
        "endpoint": None,  # Standard OpenAI - no base_url needed
        "models": {
            "gpt-5.6-luna": {
                "supported_api_types": ["Responses", "Completions"],
                "default_api_type": "Responses",
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

Provider-level fields:

  - "default_model": the model used when the user has not configured one.
    ``None`` means the provider has no sensible default and the user must
    set a model explicitly (e.g. the "custom" provider).  The name doubles
    as the key of the model's entry in ``models``.
  - "endpoint": the OpenAI-compatible base URL. ``None`` means the standard
    OpenAI API endpoint (no custom base URL needed); the special
    ``CUSTOM_ENDPOINT`` marker means the endpoint must come from config.
  - "endpoint_by_api_type" (optional): per-API-type base URLs, e.g. the
    native-SDK URL next to the OpenAI-compatible one.
  - "gemini_flavor" (optional): whether the provider's API uses the Gemini
    (Google) flavor of the OpenAI-compatible surface.  When ``True``, the
    ``enable_thinking`` extra-body flag is not sent (the field does not
    exist on Google's OpenAI-compatibility layer), because Gemini 3.x
    models reason by default; thinking depth is instead controlled through
    the resolved reasoning level, which the API maps to the model's
    ``thinking_level``.  Absent (or
    ``False``) means the provider follows the standard OpenAI-compatible
    behaviour.

Model-level fields (each entry of the ``models`` dict):

  - "supported_api_types": the API types the model supports
    ("Responses" and/or "Completions", plus native-SDK types such as
    "Anthropic"/"DashScope"). The effective type can be overridden per
    provider/model with ``--set api-type=...`` or per-call with
    ``--api-type``.
  - "default_api_type": the built-in default API type for the model
    (usually the first entry of its ``supported_api_types``, e.g.
    "Responses" for OpenAI's default model, so it uses the Responses API
    out of the box). The effective type can be overridden per provider/
    model with ``--set api-type=...`` or per-call with ``--api-type``.
  - "responses_in_server": whether the model's Responses API endpoint keeps
    the conversation state server-side (so turns can be chained with
    ``previous_response_id``). ``True`` for models that follow the OpenAI
    Responses API design (e.g. OpenAI); ``False`` for models whose
    ``/responses`` endpoint is **stateless** (e.g. DeepSeek), which cannot
    resolve a previous response id and require the client to track and
    re-send the entire conversation history on every request (like Chat
    Completions). Absent defaults to ``True`` (the Responses API design).
    Only meaningful when the model also supports "Responses".
  - "max_input_tokens": the maximum input-token (context window) limit used
    as the built-in default. Absent/``None`` means there is no built-in
    limit (the caller falls back to its own default).
  - "max_output_tokens": the maximum output-token limit (max_tokens /
    max_completion_tokens) used when the user has not configured one.
    Absent/``None`` means there is no built-in limit (the caller falls back
    to its own default).
  - "reasoning_level": the reasoning level/effort used by default for the
    model when it supports configurable reasoning depth. Absent means there
    is no built-in default.
  - "supported_reasoning_levels": the list of reasoning levels supported by
    the model, each with an ``effort`` key and a human-readable
    ``description``. Absent when the model has no configurable reasoning.
  - "thinking": the built-in default for thinking mode. May be a plain
    ``True`` flag -- sent as ``extra_body={'enable_thinking': True}`` --
    for models that reason by default (DeepSeek, Alibaba/Qwen), or a
    pass-through **dict** for models whose API takes a structured
    thinking parameter (MiniMax-M3: ``{'type': 'adaptive'}``, sent as
    ``extra_body={'thinking': {...}}``). Absent (or ``False``) means no
    built-in default. The CLI ``--thinking`` flag still forces it on
    explicitly. See :func:`janito.provider_accessors.apply_thinking_to_extra_body`.
  - "tools": the built-in (native) tools the model supports, e.g.
    ``[{"type": "code_interpreter"}, {"type": "web_search"},
    {"type": "web_extractor"}]`` for Alibaba/Qwen's flagship. These are
    **not** function tools: each ``type`` is enabled through request-body
    flags on the Completions API (``extra_body`` ``enable_code_interpreter``
    / ``enable_search``), entries in the ``tools`` array on the Responses
    API, and ``enable_code_interpreter`` / ``enable_search`` kwargs on the
    native DashScope API. ``code_interpreter`` only supports calls in
    thinking mode, so it also forces ``enable_thinking`` on. Absent (or
    ``None``) means the model has no built-in tools. See
    :func:`janito.provider_accessors.get_default_tools_from_provider`.
  - "tools_by_api_type": per-API-type overrides for the built-in tools
    (optional). When a model's endpoint does not accept every built-in tool
    (e.g. Alibaba's qwen3.8-max rejects ``code_interpreter`` on the
    Completions API with a 400 ``... does not support the code_interpreter
    tool``), declare the tools per API type and drop the plain ``tools``
    default: each API type in the map gets its own list, and API types
    absent from the map send no built-in tools. When the plain ``tools``
    default is present it applies to every API type not listed here. See
    :func:`janito.provider_accessors.get_default_tools_from_provider`.

For a fully commented reference of *every* CONFIG option (with example
values), see :mod:`janito.providers.template.config`.
"""

from .alibaba.config import PROVIDER_CONFIG as _ALIBABA_CONFIG
from .anthropic.config import PROVIDER_CONFIG as _ANTHROPIC_CONFIG
from .custom.config import CUSTOM_ENDPOINT_MARKER as CUSTOM_ENDPOINT_MARKER
from .custom.config import PROVIDER_CONFIG as _CUSTOM_CONFIG
from .deepseek.config import PROVIDER_CONFIG as _DEEPSEEK_CONFIG
from .google.config import PROVIDER_CONFIG as _GOOGLE_CONFIG
from .minimax.config import PROVIDER_CONFIG as _MINIMAX_CONFIG
from .moonshot.config import PROVIDER_CONFIG as _MOONSHOT_CONFIG
from .openai.config import PROVIDER_CONFIG as _OPENAI_CONFIG
from .xai.config import PROVIDER_CONFIG as _XAI_CONFIG
from .xiaomi.config import PROVIDER_CONFIG as _XIAOMI_CONFIG
from .zai.config import PROVIDER_CONFIG as _ZAI_CONFIG

# Per-provider built-in defaults, assembled from the per-provider ``config.py``
# modules above (each entry is the module's ``PROVIDER_CONFIG``, held by
# reference).  See the module docstring for the entry schema.
_PROVIDER_CONFIGS: dict[str, dict] = {
    # AI Providers with OpenAI-compatible APIs
    "openai": _OPENAI_CONFIG,
    "google": _GOOGLE_CONFIG,
    "minimax": _MINIMAX_CONFIG,
    "xiaomi": _XIAOMI_CONFIG,
    "moonshot": _MOONSHOT_CONFIG,
    "alibaba": _ALIBABA_CONFIG,
    "zai": _ZAI_CONFIG,
    "deepseek": _DEEPSEEK_CONFIG,
    "xai": _XAI_CONFIG,
    "anthropic": _ANTHROPIC_CONFIG,
    # Special case: requires an endpoint from config (--set endpoint) and has
    # no built-in default model (and therefore no built-in model entries).
    "custom": _CUSTOM_CONFIG,
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
# installed (see :func:`janito.provider_accessors.ensure_api_type_available`).
REQUIRES_BY_API_TYPE: dict[str, str] = {
    "Anthropic": "anthropic",
    "DashScope": "dashscope",
}


def get_provider_config(provider: str, model: str | None = None) -> dict | None:
    """Get the config entry for a provider, or for one of its models.

    Without ``model`` this returns the provider's full entry (the
    provider-level fields plus its ``models`` dict).  With ``model`` it
    returns just that model's entry *within* the provider (the
    ``models[model]`` dict with the model-level fields).

    Args:
        provider: The provider name (case-insensitive).
        model: The model name to return the config for. ``None`` returns the
            whole provider entry.

    Returns:
        The provider's info dict when ``model`` is ``None``; the model's
        entry when ``model`` is given; ``None`` when the provider is unknown
        or the model has no built-in entry.
    """
    if not provider:
        return None
    if provider in _PROVIDER_CONFIGS:
        entry = _PROVIDER_CONFIGS[provider]
    else:
        provider_lower = provider.lower()
        entry = next(
            (
                info
                for key, info in _PROVIDER_CONFIGS.items()
                if key.lower() == provider_lower
            ),
            None,
        )
    if entry is None:
        return None
    if model is None:
        return entry
    models = entry.get("models", {})
    if not isinstance(models, dict):
        return None
    return models.get(model)
