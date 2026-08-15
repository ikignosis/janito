"""Template provider configuration -- reference for every CONFIG option.

This module is **not** a real provider: it is never imported into
:data:`janito.providers._PROVIDER_CONFIGS` and its ``PROVIDER_CONFIG`` is
only a documentation skeleton.  It is the template for writing a new
provider's ``config.py``: every possible CONFIG option is shown below,
fully commented, in one ``PROVIDER_CONFIG`` dict.

To add a provider, copy this file to ``janito/providers/<name>/config.py``,
fill in the real values, and register the entry in
:data:`janito.providers._PROVIDER_CONFIGS` (inside ``janito/providers/
__init__.py``).

See also:

  - :mod:`janito.providers` -- how the per-provider entries are assembled
    into the registry (including the ``REQUIRES_BY_API_TYPE`` optional-
    package map that native-SDK API types must be added to).
  - :mod:`janito.provider_accessors` -- how each CONFIG option is read and
    applied at runtime.
"""

#: The config entry for the ``<name>`` provider.
#:
#: The entry has two levels.  The *provider level* holds what is intrinsic
#: to the provider; everything that depends on the model lives under the
#: per-provider ``models`` dict, keyed by model name.
PROVIDER_CONFIG: dict = {
    # ------------------------------------------------------------------
    # Provider-level fields
    # ------------------------------------------------------------------
    #: The model used when the user has not configured one.  ``None`` means
    #: the provider has no sensible default and the user must set a model
    #: explicitly (e.g. the "custom" provider).  The name doubles as the
    #: key of the model's entry in ``models``.
    "default_model": "my-default-model",
    #: The OpenAI-compatible base URL.  ``None`` means the standard OpenAI
    #: API endpoint (no custom base URL needed); the special
    #: ``CUSTOM_ENDPOINT`` marker (see ``janito/providers/custom/config.py``)
    #: means the endpoint must come from config (only the "custom" provider
    #: uses it).
    "endpoint": "https://api.example.com/v1",
    #: Per-API-type base URLs (optional).  Lets a provider declare a
    #: different URL per API type, e.g. the native-SDK URL next to the
    #: OpenAI-compatible one.  A dict holding a single entry uses that URL
    #: as the default for *any* API type (unless a config endpoint is set);
    #: with multiple entries, each API type maps to its own URL and an API
    #: type absent from the map falls back to the single ``endpoint``
    #: above.  Omit the key entirely when every API type shares
    #: ``endpoint``.
    "endpoint_by_api_type": {
        "Completions": "https://api.example.com/v1",
        "Responses": "https://api.example.com/v1",
        # Native-SDK API types (e.g. "Anthropic", "DashScope") go here too.
        "Anthropic": "https://api.example.com/anthropic",
    },
    # ------------------------------------------------------------------
    # Model-level fields (one entry per model, keyed by model name)
    # ------------------------------------------------------------------
    "models": {
        "my-default-model": {
            #: The API types the model supports: "Responses" and/or
            #: "Completions" (both served by the `openai` package), plus
            #: native-SDK types such as "Anthropic"/"DashScope".  The
            #: **first** entry is the built-in default API type for the
            #: model.  The effective type can be overridden per
            #: provider/model with ``--set api-type=...`` or per-call with
            #: ``--api-type``.  Native-SDK API types must also be declared
            #: in ``REQUIRES_BY_API_TYPE`` (see :mod:`janito.providers`).
            "supported_api_types": ["Responses", "Completions"],
            #: Whether the model's Responses API endpoint keeps the
            #: conversation state server-side (so turns can be chained with
            #: ``previous_response_id``).  ``True`` for models that follow
            #: the OpenAI Responses API design; ``False`` for models whose
            #: ``/responses`` endpoint is **stateless** (e.g. DeepSeek),
            #: which cannot resolve a previous response id and require the
            #: client to track and re-send the entire conversation history
            #: on every request (like Chat Completions).  Absent defaults
            #: to ``True``.  Only meaningful when the model also supports
            #: "Responses".
            "responses_in_server": True,
            #: The maximum input-token (context window) limit used as the
            #: built-in default.  Absent/``None`` means there is no
            #: built-in limit (the caller falls back to its own default).
            "max_input_tokens": 128000,
            #: The maximum output-token limit (max_tokens /
            #: max_completion_tokens) used when the user has not configured
            #: one.  Absent/``None`` means there is no built-in limit (the
            #: caller falls back to its own default).
            "max_output_tokens": 32768,
            #: The reasoning level/effort used by default for the model
            #: when it supports configurable reasoning depth.  Must be one
            #: of the ``effort`` values declared in
            #: ``supported_reasoning_levels``.  Absent means there is no
            #: built-in default.
            "reasoning_level": "high",
            #: The list of reasoning levels supported by the model, each
            #: with an ``effort`` key and a human-readable ``description``.
            #: Absent when the model has no configurable reasoning.
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
                    "description": "Maximum reasoning depth for complex problems",
                },
            ],
            #: The built-in default for thinking mode.  May be a plain
            #: ``True`` flag -- sent as ``extra_body={'enable_thinking':
            #: True}`` -- for models that reason by default (DeepSeek,
            #: Alibaba/Qwen), or a pass-through **dict** for models whose
            #: API takes a structured thinking parameter (MiniMax-M3:
            #: ``{'type': 'adaptive'}``, sent as ``extra_body={'thinking':
            #: {...}}``).  Absent (or ``False``) means no built-in default.
            #: The CLI ``--thinking`` flag still forces it on explicitly.
            "thinking": True,
        },
    },
}
