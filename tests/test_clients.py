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
            "_resolve_model_settings": ("openai", "gpt-4", False, None),
            "_init_conversation_state": ("hi", "openai", "gpt-4"),
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
        state = c._init_conversation_state(
            "hi", "openai", "gpt-4", previous_messages=history
        )
        # The same list object is used and the user turn is appended to it.
        assert state is history
        assert state == [{"role": "user", "content": "hi"}]

    def test_completions_state_none_starts_fresh():
        from janito.openai_client.completions_api import CompletionsClient

        c = CompletionsClient()
        state = c._init_conversation_state(
            "hi", "openai", "gpt-4", previous_messages=None
        )
        assert state == [{"role": "user", "content": "hi"}]

    def test_anthropic_state_keeps_system_parameter():
        """The top-level system parameter is resolved from instructions and
        the in-place history keeps the system-role message."""
        from janito.openai_client.anthropic_api import AnthropicClient

        c = AnthropicClient()
        history = [{"role": "system", "content": "Be helpful"}]
        state = c._init_conversation_state(
            "hi",
            "anthropic",
            "claude-sonnet-5",
            previous_messages=history,
            instructions=None,
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
            "gpt-5.6-luna",
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
            "hi",
            "alibaba",
            "qwen3.8-max",
            previous_messages=None,
            instructions="be terse",
        )
        assert state == [
            {"role": "system", "content": "be terse"},
            {"role": "user", "content": "hi"},
        ]

    # ---- model-settings shape for the native-SDK clients ----------------

    def test_anthropic_model_settings_returns_4_tuple(monkeypatch):
        from janito.openai_client import anthropic_api

        monkeypatch.setattr(
            anthropic_api,
            "_resolve_max_output_tokens",
            lambda provider, model=None: 64000,
        )
        # No config override: the provider's built-in default applies.
        monkeypatch.setattr(
            anthropic_api, "load_max_input_tokens", lambda provider, model=None: None
        )
        monkeypatch.setattr(
            anthropic_api,
            "get_default_max_input_tokens_from_provider",
            lambda provider, model=None: 200000,
        )
        c = anthropic_api.AnthropicClient()
        thinking, max_out, max_in, reasoning = c._resolve_model_settings(
            "anthropic", "claude-sonnet-5", False, "high"
        )
        assert thinking is False
        assert max_out == 64000
        assert max_in == 200000
        # reasoning_level is accepted but not used by the native SDK.
        assert reasoning is None

    def test_anthropic_model_settings_config_override_wins(monkeypatch):
        from janito.openai_client import anthropic_api

        monkeypatch.setattr(
            anthropic_api,
            "_resolve_max_output_tokens",
            lambda provider, model=None: 64000,
        )
        # A configured max-input-tokens override beats the built-in default.
        monkeypatch.setattr(
            anthropic_api, "load_max_input_tokens", lambda provider, model=None: 4096
        )
        monkeypatch.setattr(
            anthropic_api,
            "get_default_max_input_tokens_from_provider",
            lambda provider, model=None: 200000,
        )
        c = anthropic_api.AnthropicClient()
        _, _, max_in, _ = c._resolve_model_settings(
            "anthropic", "claude-sonnet-5", False, "high"
        )
        assert max_in == 4096

    def test_dashscope_model_settings_returns_4_tuple(monkeypatch):
        import janito.dashscope_api as dsa

        monkeypatch.setattr(
            dsa,
            "_resolve_model_settings",
            lambda provider, model, thinking: (True, 8192, 128000),
        )
        c = dsa.DashScopeClient()
        thinking, max_out, max_in, reasoning = c._resolve_model_settings(
            "alibaba", "qwen3.8-max", True, "xhigh"
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
            return "hi", None, {}, None, {}

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
            lambda func, client, call_kwargs, tools_schemas: ("hi", None, {}, None, {}),
        )

        from janito.openai_client.completions_api import send_prompt

        assert send_prompt("hello", use_mcp=False) == "hi"

    # ---- verbose API call/response output -------------------------------

    def test_print_verbose_api_call_shows_messages_tail_only():
        """The request dump replaces the full messages list with its tail."""
        from io import StringIO

        from rich.console import Console

        from janito.openai_client.client_support import _print_verbose_api_call

        out = StringIO()
        console = Console(file=out, width=120, force_terminal=True)
        long_history = [
            {"role": "user", "content": "very early message, should not appear"},
            {"role": "assistant", "content": "early answer, should not appear"},
            {"role": "user", "content": "middle message, should not appear"},
            {"role": "user", "content": "fourth message, shown"},
            {"role": "user", "content": "penultimate message"},
            {"role": "assistant", "content": "tail message " + "x" * 1000},
        ]
        call_kwargs = {
            "model": "gpt-4",
            "messages": long_history,
            "temperature": 1.0,
            "max_completion_tokens": 8192,
        }
        _print_verbose_api_call(console, call_kwargs, tools_schemas=[])

        rendered = out.getvalue()
        # The summary notes the total count and that only the tail is shown.
        assert "6 items (showing last 3)" in rendered
        # The tail messages are present (truncated), the early ones are not.
        assert "tail message" in rendered
        assert "penultimate message" in rendered
        assert "fourth message" in rendered
        assert "very early message" not in rendered
        assert "early answer" not in rendered
        assert "middle message" not in rendered
        # Long content is truncated instead of dumped in full.
        assert "more chars" in rendered
        assert "x" * 1000 not in rendered
        # The scalar parameters survive untouched.
        assert '"max_completion_tokens": 8192' in rendered

    def test_print_verbose_api_call_summarizes_tools():
        from io import StringIO

        from rich.console import Console

        from janito.openai_client.client_support import _print_verbose_api_call

        out = StringIO()
        console = Console(file=out, width=120, force_terminal=True)
        call_kwargs = {"model": "gpt-4", "input": "hello"}
        _print_verbose_api_call(
            console,
            call_kwargs,
            tools_schemas=[
                {"type": "function", "function": {"name": "list_files"}},
                {"type": "function", "function": {"name": "read_file"}},
            ],
        )
        rendered = out.getvalue()
        assert '"2 tools"' in rendered
        assert '"list_files"' in rendered
        assert '"read_file"' in rendered

    def test_print_verbose_api_response_summary():
        from io import StringIO
        from types import SimpleNamespace

        from rich.console import Console

        from janito.openai_client.client_support import _print_verbose_api_response

        out = StringIO()
        console = Console(file=out, width=120, force_terminal=True)
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        _print_verbose_api_response(
            console,
            full_content="final answer " + "y" * 1000,
            reasoning_content="thinking step",
            tool_calls=[
                {"name": "list_files", "arguments": '{"path": "."}'},
                {"name": "read_file", "arguments": "{}"},
            ],
            usage_info=usage,
            response_id="resp_1",
            raw_attrs={
                "id": "chatcmpl-1",
                "model": "gpt-4o",
                "created": 1720000000,
                "system_fingerprint": "fp_abc",
                "finish_reason": "stop",
            },
        )
        rendered = out.getvalue()
        assert "Content:" in rendered
        assert "Reasoning:" in rendered
        assert "thinking step" in rendered
        assert "Tool calls: list_files(" in rendered
        assert "read_file(" in rendered
        assert "Usage:" in rendered
        assert "Response id: resp_1" in rendered
        # All raw top-level response attributes are enumerated.
        assert "Raw id: chatcmpl-1" in rendered
        assert "Raw model: gpt-4o" in rendered
        assert "Raw created: 1720000000" in rendered
        assert "Raw system_fingerprint: fp_abc" in rendered
        assert "Raw finish_reason: stop" in rendered
        # Long content is truncated (not the full 1000-char tail dumped).
        assert "more chars" in rendered
        assert "y" * 1000 not in rendered

    def test_verbose_wiring_in_send(monkeypatch):
        """verbose=True prints the API call params + response summary through
        the base Client.send; verbose=False prints neither."""
        import janito.openai_client.completions_api as ca

        calls = []

        def fake_run(func, client, call_kwargs, tools_schemas):
            return "hi", None, {}, None, {"id": "chatcmpl-1"}

        monkeypatch.setattr(
            ca,
            "resolve_runtime_config",
            lambda *a, **k: (None, "sk-test", "gpt-4"),
        )
        monkeypatch.setattr(ca, "_run_with_progress_bar", fake_run)
        monkeypatch.setattr(ca, "_load_mcp", lambda use_mcp: (None, []))

        client = ca.CompletionsClient(use_mcp=False)
        monkeypatch.setattr(
            client,
            "_print_verbose_api_call",
            lambda console, call_kwargs, tools_schemas: calls.append("call"),
        )
        monkeypatch.setattr(
            client,
            "_print_verbose_api_response",
            lambda console, content, reasoning, tool_calls, usage, state, raw_attrs=None: calls.append(
                "response"
            ),
        )

        client.send("hello", verbose=True, tools=[], thinking=False)
        assert calls == ["call", "response"]

        calls.clear()
        client.send("hello", verbose=False, tools=[], thinking=False)
        assert calls == []

    def test_verbose_responses_response_id_from_state(monkeypatch):
        """The Responses client's state dict carries the response id into the
        verbose response summary (server-side conversations chain by id)."""
        import janito.openai_client.conversations_api as ca

        captured = {}

        def fake_run(func, client, call_kwargs, tools_schemas):
            return (
                "hi",
                None,
                {},
                None,
                "resp_99",
                {"id": "resp_99", "status": "completed"},
            )

        monkeypatch.setattr(
            ca,
            "resolve_runtime_config",
            lambda *a, **k: (None, "sk-test", "gpt-4o"),
        )
        monkeypatch.setattr(ca, "_run_with_progress_bar", fake_run)
        monkeypatch.setattr(ca, "_load_mcp", lambda use_mcp: (None, []))
        monkeypatch.setattr(
            ca,
            "_init_conversation_state",
            lambda provider, model, previous_response_id, previous_items, instructions, prompt: (
                True,
                None,
                None,
                prompt,
                [],
            ),
        )
        monkeypatch.setattr(
            ca,
            "_build_call_kwargs",
            lambda *a, **k: {"model": "gpt-4o", "input": "hello"},
        )

        client = ca.ResponsesClient(use_mcp=False)
        monkeypatch.setattr(
            client,
            "_print_verbose_api_response",
            lambda console, content, reasoning, tool_calls, usage, state, raw_attrs=None: captured.setdefault(
                "state", state
            ),
        )

        result = client.send("hello", verbose=True, tools=[], thinking=False)
        assert result.response_id == "resp_99"
        # The base method extracts the response id from the Responses state.
        from io import StringIO

        from rich.console import Console

        from janito.openai_client.base_client import Client

        console = Console(file=StringIO(), width=120, force_terminal=True)
        calls = []
        monkeypatch.setattr(
            "janito.openai_client.base_client._print_verbose_api_response",
            lambda console, content, reasoning, tool_calls, usage, response_id, raw_attrs=None: calls.append(
                response_id
            ),
        )
        Client()._print_verbose_api_response(
            console, "hi", None, {}, None, {"response_id": "resp_99"}
        )
        Client()._print_verbose_api_response(console, "hi", None, {}, None, [])
        assert calls == ["resp_99", None]

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
