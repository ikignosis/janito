"""
Tests for the shared Client base class and its four concrete subclasses.

The module-level ``send_prompt`` functions of ``completions_api``,
``conversations_api``, ``anthropic_api`` and ``dashscope_api`` now delegate to
``*Client`` subclasses of ``janito.openai_client.base_client.Client``.  These
tests pin the new class contract:

- The base class raises ``NotImplementedError`` for unimplemented hooks.
- Each subclass declares the right ``api_type`` / ``backend_default``.
- The per-turn hooks preserve the historical behaviour (e.g. the "is not
  None" empty-list semantics of ``previous_messages``, the Responses state
  dict, and the 4-tuple model-settings shape for the native-SDK clients).

The behavioural equivalence of the four ``send_prompt`` functions is covered
by the existing client tests (``test_conversations_api``,
``test_anthropic_api``, ``test_dashscope_api``, ``test_reasoning_level``),
which monkeypatch the module globals that the subclasses forward to.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from janito.openai_client.base_client import Client

if pytest is not None:
    # ---- base class contract -------------------------------------------

    def test_base_hooks_raise_not_implemented():
        c = Client()
        # (hook, args) -- each hook must raise NotImplementedError when the
        # base implementation is reached (before any argument validation).
        hooks = {
            "_resolve_runtime_config": (),
            "_create_sdk_client": ("http://example.test", "dummy-key"),
            "_create_tool_executor": (None,),
            "_resolve_tools": (None, []),
            "_resolve_model_settings": ("openai", False, None),
            "_init_conversation_state": ("hi", "openai"),
            "_build_call_kwargs": ("m", {}, 1000, None, None, False),
            "_run_stream_round": (
                None,
                {},
                [],
                {},
            ),
            "_handle_tool_calls": ({}, "", None, {}, None),
            "_finalize": ("", None, {}, None, None, None, None),
        }
        # _run_stream_round has keyword-only params after ``state``.
        with pytest.raises(NotImplementedError):
            c._run_stream_round(
                None,
                {},
                [],
                {},
                base_url=None,
                api_key="dummy-key",  # pragma: allowlist secret
                model="m",
                console=None,
            )
        del hooks["_run_stream_round"]
        for hook, args in hooks.items():
            with pytest.raises(NotImplementedError):
                getattr(c, hook)(*args)

    def test_base_defaults():
        c = Client()
        assert c.api_type == "Completions"
        assert c.backend_default == "api.openai.com"
        assert c.cli_model is None
        assert c.cli_provider is None
        assert c.use_mcp is True

    def test_base_send_requires_runtime_config():
        """send() without a concrete subclass fails at the first hook."""
        with pytest.raises(NotImplementedError):
            Client().send("hello")

    # ---- concrete subclasses: identity ----------------------------------

    def test_subclass_identities():
        from janito.dashscope_api import DashScopeClient
        from janito.openai_client.anthropic_api import AnthropicClient
        from janito.openai_client.completions_api import CompletionsClient
        from janito.openai_client.conversations_api import ResponsesClient

        assert issubclass(CompletionsClient, Client)
        assert issubclass(ResponsesClient, Client)
        assert issubclass(AnthropicClient, Client)
        assert issubclass(DashScopeClient, Client)

        assert CompletionsClient().api_type == "Completions"
        assert ResponsesClient().api_type == "Responses"
        assert AnthropicClient().api_type == "Anthropic"
        assert DashScopeClient().api_type == "DashScope"

        assert AnthropicClient().backend_default == "https://api.anthropic.com"
        assert (
            DashScopeClient().backend_default
            == "https://dashscope-intl.aliyuncs.com/api/v1"
        )

    # ---- conversation-state semantics -----------------------------------

    def test_completions_state_preserves_empty_list():
        """An empty caller-owned history must be kept (not replaced)."""
        from janito.openai_client.completions_api import CompletionsClient

        c = CompletionsClient()
        history: list = []
        state = c._init_conversation_state("hi", "openai", previous_messages=history)
        # The same list object is used and the user turn is appended to it.
        assert state is history
        assert state == [{"role": "user", "content": "hi"}]

    def test_completions_state_none_starts_fresh():
        from janito.openai_client.completions_api import CompletionsClient

        c = CompletionsClient()
        state = c._init_conversation_state("hi", "openai", previous_messages=None)
        assert state == [{"role": "user", "content": "hi"}]

    def test_anthropic_state_keeps_system_parameter():
        """The top-level system parameter is resolved from instructions and
        the in-place history keeps the system-role message."""
        from janito.openai_client.anthropic_api import AnthropicClient

        c = AnthropicClient()
        history = [{"role": "system", "content": "Be helpful"}]
        state = c._init_conversation_state(
            "hi", "anthropic", previous_messages=history, instructions=None
        )
        assert state["messages"] is history
        assert state["messages"][-1] == {"role": "user", "content": "hi"}
        # The system message is preserved in the client-side history and
        # surfaced as the top-level system parameter.
        assert state["messages"][0] == {"role": "system", "content": "Be helpful"}
        assert state["system"] == "Be helpful"

    def test_responses_state_dict_shape():
        from janito.openai_client.conversations_api import ResponsesClient

        c = ResponsesClient()
        state = c._init_conversation_state(
            "hi",
            "openai",
            previous_response_id=None,
            previous_items=None,
            instructions="Be helpful",
        )
        assert state["responses_in_server"] is True
        assert state["response_id"] is None
        assert state["conversation_items"] is None
        assert state["input_items"] == "hi"
        assert state["instructions"] == "Be helpful"
        assert state["message_count"] == 1

    def test_dashscope_state_prepends_instructions():
        from janito.dashscope_api import DashScopeClient

        c = DashScopeClient()
        state = c._init_conversation_state(
            "hi", "alibaba", previous_messages=None, instructions="be terse"
        )
        assert state == [
            {"role": "system", "content": "be terse"},
            {"role": "user", "content": "hi"},
        ]

    # ---- model-settings shape for the native-SDK clients ----------------

    def test_anthropic_model_settings_returns_4_tuple(monkeypatch):
        from janito.openai_client import anthropic_api

        monkeypatch.setattr(
            anthropic_api, "_resolve_max_output_tokens", lambda provider: 64000
        )
        monkeypatch.setattr(
            anthropic_api,
            "get_default_max_input_tokens_from_provider",
            lambda provider: 200000,
        )
        c = anthropic_api.AnthropicClient()
        thinking, max_out, max_in, reasoning = c._resolve_model_settings(
            "anthropic", False, "high"
        )
        assert thinking is False
        assert max_out == 64000
        assert max_in == 200000
        # reasoning_level is accepted but not used by the native SDK.
        assert reasoning is None

    def test_dashscope_model_settings_returns_4_tuple(monkeypatch):
        import janito.dashscope_api as dsa

        monkeypatch.setattr(
            dsa,
            "_resolve_model_settings",
            lambda provider, thinking: (True, 8192, 128000),
        )
        c = dsa.DashScopeClient()
        thinking, max_out, max_in, reasoning = c._resolve_model_settings(
            "alibaba", True, "xhigh"
        )
        assert (thinking, max_out, max_in) == (True, 8192, 128000)
        # reasoning_level is dropped (not used by the native SDK).
        assert reasoning is None

    # ---- pipeline wiring through module globals -------------------------

    def test_completions_client_send_wires_module_globals(monkeypatch):
        """CompletionsClient.send resolves the monkeypatched module globals
        (resolve_runtime_config / _run_with_progress_bar), proving the
        subclasses forward through their module namespace."""
        import janito.openai_client.completions_api as ca

        captured = {}

        def fake_run(func, client, call_kwargs, tools_schemas):
            captured["call_kwargs"] = call_kwargs
            return "hi", None, {}, None

        monkeypatch.setattr(
            ca,
            "resolve_runtime_config",
            lambda *a, **k: (None, "sk-test", "gpt-4"),
        )
        monkeypatch.setattr(ca, "_run_with_progress_bar", fake_run)
        monkeypatch.setattr(ca, "_load_mcp", lambda use_mcp: (None, []))

        result = ca.CompletionsClient(use_mcp=False).send(
            "hello", tools=[], thinking=False
        )
        assert result == "hi"
        assert captured["call_kwargs"]["model"] == "gpt-4"

    def test_send_prompt_returns_shared_client_behaviour(monkeypatch):
        """The module-level send_prompt now returns exactly what the client
        class produces (regression guard for the delegation)."""
        import janito.openai_client.completions_api as ca

        monkeypatch.setattr(
            ca,
            "resolve_runtime_config",
            lambda *a, **k: (None, "sk-test", "gpt-4"),
        )
        monkeypatch.setattr(
            ca,
            "_run_with_progress_bar",
            lambda func, client, call_kwargs, tools_schemas: ("hi", None, {}, None),
        )

        from janito.openai_client.completions_api import send_prompt

        assert send_prompt("hello", use_mcp=False) == "hi"

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        import tempfile

        class _MP:
            def __init__(self):
                self._undo = []

            def setattr(self, obj, name, value):
                self._undo.append((obj, name, getattr(obj, name)))
                setattr(obj, name, value)

            def restore(self):
                for obj, name, value in reversed(self._undo):
                    setattr(obj, name, value)

        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                mp = _MP()
                try:
                    import inspect

                    params = inspect.signature(fn).parameters
                    with tempfile.TemporaryDirectory():
                        if "monkeypatch" in params:
                            fn(mp)
                        else:
                            fn()
                finally:
                    mp.restore()
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
