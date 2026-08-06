"""
Tests for the Responses API client (:mod:`janito.openai_client.conversations_api`).

``conversations_api.send_prompt`` mirrors ``completions_api.send_prompt`` but
targets the Responses API (``client.responses.create``) with server-side
conversation state: the client never stores or updates a ``messages`` list,
and turns are chained with ``previous_response_id``.

These tests verify:
  - ``_consume_response_stream`` text / reasoning / tool-call assembly.
  - ``response.failed`` is turned into a raised error.
  - Enter-to-cancel short-circuits the stream and closes the connection.
  - ``send_prompt`` chains tool-call rounds via ``previous_response_id`` and
    returns a ``ConversationResult`` carrying the final server-side response
    id (no client-side history is kept or mutated).
  - ``instructions`` are only sent on the first turn of a conversation.
"""

import json
import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest import mock

import pytest

import janito.config_dir as config_dir_mod
import janito.tooling.used_files as used_files
from janito.openai_client import conversations_api as api


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Run each test in a temp CWD with a temp config dir and clean state.

    ``send_prompt`` resets the in-process used-files tracker and clears the
    ``./.janito/changes.jsonl`` log (relative to the CWD), so each test gets
    its own temp dirs and the in-memory tracker is reset before and after.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config_dir_mod, "_config_dir", tmp_path)
    used_files.reset_used_files()
    yield
    used_files.reset_used_files()


# ---- Minimal stand-ins for the SDK's typed stream events -----------------


class _Event:
    """Fake stream event; ``type`` plus arbitrary attributes."""

    def __init__(self, type, **attrs):
        self.type = type
        for name, value in attrs.items():
            setattr(self, name, value)


class _Response:
    def __init__(self, id, usage=None, error=None):
        self.id = id
        self.usage = usage
        self.error = error


class _FunctionCallItem:
    def __init__(self, id, call_id, name, arguments=None):
        self.id = id
        self.type = "function_call"
        self.call_id = call_id
        self.name = name
        self.arguments = arguments


class _Usage:
    total_tokens = 100
    input_tokens = 60
    output_tokens = 40
    input_tokens_details = type("Details", (), {"cached_tokens": 5})()


def _stream(events):
    yield from events


# ---- _consume_response_stream -------------------------------------------


def test_consume_stream_assembles_text_and_usage():
    events = _stream(
        [
            _Event("response.created", response=_Response("resp_1")),
            _Event("response.output_text.delta", delta="Hello"),
            _Event("response.output_text.delta", delta=" world"),
            _Event("response.completed", response=_Response("resp_1", usage=_Usage())),
        ]
    )
    content, reasoning, tools, usage, response_id = api._consume_response_stream(events)
    assert content == "Hello world"
    assert reasoning is None
    assert tools == []
    assert response_id == "resp_1"
    assert usage.total_tokens == 100
    assert usage.input_tokens_details.cached_tokens == 5


def test_consume_stream_assembles_split_tool_call_arguments():
    events = _stream(
        [
            _Event("response.created", response=_Response("resp_2")),
            _Event("response.reasoning_text.delta", delta="thinking..."),
            _Event(
                "response.function_call_arguments.delta",
                item_id="fc_1",
                delta='{"path":',
            ),
            _Event(
                "response.function_call_arguments.delta",
                item_id="fc_1",
                delta=' "/tmp/a"}',
            ),
            _Event(
                "response.output_item.done",
                item=_FunctionCallItem("fc_1", "call_1", "read_file"),
            ),
            _Event("response.output_text.delta", delta="Let me check"),
            _Event("response.completed", response=_Response("resp_2")),
        ]
    )
    content, reasoning, tools, usage, response_id = api._consume_response_stream(events)
    assert content == "Let me check"
    assert reasoning == "thinking..."
    assert tools == [
        {"call_id": "call_1", "name": "read_file", "arguments": '{"path": "/tmp/a"}'}
    ]
    assert response_id == "resp_2"


def test_consume_stream_prefers_full_arguments_from_done_event():
    events = _stream(
        [
            _Event("response.created", response=_Response("resp_3")),
            _Event(
                "response.function_call_arguments.done",
                item_id="fc_1",
                arguments='{"x": 1}',
            ),
            _Event(
                "response.output_item.done",
                item=_FunctionCallItem("fc_1", "call_9", "run_bash", '{"x": 1}'),
            ),
            _Event("response.completed", response=_Response("resp_3")),
        ]
    )
    _, _, tools, _, response_id = api._consume_response_stream(events)
    assert tools == [{"call_id": "call_9", "name": "run_bash", "arguments": '{"x": 1}'}]
    assert response_id == "resp_3"


def test_consume_stream_raises_on_failed_response():
    events = _stream(
        [
            _Event("response.created", response=_Response("resp_4")),
            _Event(
                "response.failed",
                response=_Response(
                    "resp_4", error=type("E", (), {"message": "boom"})()
                ),
            ),
        ]
    )
    with pytest.raises(RuntimeError, match="boom"):
        api._consume_response_stream(events)


def test_consume_stream_raises_on_untyped_error_event():
    """Some providers (e.g. Alibaba DashScope's /responses endpoint) stream
    API errors as SSE events the SDK cannot type: ``event.type`` is None but
    the payload carries the error as ``code``/``message`` attributes (e.g.
    ``code='InvalidParameter'``, ``message="Unsupported model:
    'qwen3.8-max'."``). These must raise instead of silently returning an
    empty response."""
    events = _stream(
        [
            _Event(
                None,
                code="InvalidParameter",
                message="Unsupported model: 'qwen3.8-max'.",
                request_id="req_1",
            )
        ]
    )
    with pytest.raises(RuntimeError, match="Unsupported model: 'qwen3.8-max'"):
        api._consume_response_stream(events)


def test_consume_stream_raises_on_empty_stream():
    """A stream that yields no events at all must raise rather than silently
    returning an empty response."""
    with pytest.raises(RuntimeError, match="empty response"):
        api._consume_response_stream(_stream([]))


def test_consume_stream_cancel_is_not_an_empty_stream():
    """An Enter-to-cancel short-circuit (no events consumed) must NOT be
    mistaken for an empty stream."""
    import threading

    cancel = threading.Event()
    cancel.set()

    def events():
        if False:
            yield None  # pragma: no cover - keeps this a generator

    content, _, tools, usage, response_id = api._consume_response_stream(
        events(), cancel_event=cancel
    )
    assert content == ""
    assert tools == []
    assert response_id is None


def test_consume_stream_cancel_short_circuits():
    import threading

    cancel = threading.Event()

    def events():
        yield _Event("response.created", response=_Response("resp_5"))
        yield _Event("response.output_text.delta", delta="partial")
        # User presses Enter while waiting: cancel is set before the next event.
        cancel.set()
        yield _Event("response.output_text.delta", delta="more")
        yield _Event("response.completed", response=_Response("resp_5"))

    content, _, tools, usage, response_id = api._consume_response_stream(
        events(), cancel_event=cancel
    )
    assert content == "partial"
    assert tools == []
    assert response_id == "resp_5"


def test_stream_response_closes_connection_on_cancel():
    import threading

    cancel = threading.Event()

    class FakeStream:
        def __init__(self, client):
            self.client = client

        def __iter__(self):
            yield _Event("response.created", response=_Response("r1"))
            yield _Event("response.output_text.delta", delta="hi")
            cancel.set()
            yield _Event("response.completed", response=_Response("r1"))

        def close(self):
            self.client.closed = True

    class FakeClient:
        def __init__(self):
            self.closed = False

        @property
        def responses(self):
            client = self

            class _Responses:
                def create(self, **kwargs):
                    return FakeStream(client)

            return _Responses()

    client = FakeClient()
    cancel.clear()
    content, _, _, _, _ = api._stream_response(
        client, {"model": "m", "input": "hi", "stream": True}, None, cancel_event=cancel
    )
    assert content == "hi"
    assert client.closed is True


# ---- _convert_tools_to_responses_format ----------------------------------


def test_convert_tools_to_responses_format_lifts_name_to_top_level():
    """Chat Completions schemas (name nested under 'function') are converted
    to the Responses API shape (name/description/parameters at the top level)."""
    completions_schemas = [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "svc_mcp_tool",
                "description": "[svc] MCP tool",
                "parameters": {
                    "type": "object",
                    "properties": {"x": {"type": "string"}},
                    "required": ["x"],
                },
            },
        },
    ]
    converted = api._convert_tools_to_responses_format(completions_schemas)
    assert converted == [
        {
            "type": "function",
            "name": "list_files",
            "description": "List files",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "type": "function",
            "name": "svc_mcp_tool",
            "description": "[svc] MCP tool",
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
            },
        },
    ]
    # Every converted tool carries the top-level 'name' the Responses API
    # requires (missing it caused "tools[0]: missing field 'name'").
    assert all("name" in tool for tool in converted)


def test_convert_tools_to_responses_format_handles_already_converted_and_empty():
    # A schema that already has top-level name (no nested 'function') is kept.
    already = {"type": "function", "name": "x", "parameters": {}}
    assert api._convert_tools_to_responses_format([already]) == [
        {"type": "function", "name": "x", "description": "", "parameters": {}}
    ]
    # An empty list stays empty.
    assert api._convert_tools_to_responses_format([]) == []


# ---- send_prompt (mocked network) ----------------------------------------


def _mock_send_prompt(monkeypatch, create_side_effect):
    """Patch config resolution, tool schemas, the executor and the client."""
    client_inst = mock.Mock()
    client_inst.responses.create.side_effect = create_side_effect
    monkeypatch.setattr(api, "OpenAI", mock.Mock(return_value=client_inst))
    monkeypatch.setattr(
        api,
        "resolve_runtime_config",
        lambda *a, **k: ("https://api.example.com", "sk-test", "gpt-4o"),
    )
    monkeypatch.setattr(
        api,
        "get_all_tool_schemas",
        lambda: [{"type": "function", "function": {"name": "list_files"}}],
    )
    executor_inst = mock.Mock()
    executor_inst.execute_tool_call.return_value = {
        "tool_call_id": "call_1",
        "role": "tool",
        "name": "list_files",
        "content": json.dumps({"success": True}),
    }
    monkeypatch.setattr(api, "ToolExecutor", mock.Mock(return_value=executor_inst))
    return client_inst


def test_send_prompt_stateless_replays_full_history(monkeypatch):
    """Stateless providers (responses_in_server False, e.g. DeepSeek) cannot
    resolve a previous_response_id: the client re-sends the full conversation
    as input items on every request and never chains with an id."""
    monkeypatch.setattr(api, "get_responses_in_server_from_provider", lambda p: False)
    seen = []

    def create(**kwargs):
        # Snapshot the input list: send_prompt appends to the same list in
        # place after the request, so re-checking kwargs later would see the
        # mutated history.
        seen.append(dict(kwargs, input=list(kwargs["input"])))
        round_no = len(seen)
        if round_no == 1:
            # First round: input is a fresh items list (system instructions
            # folded in, then the user prompt); no previous_response_id and no
            # instructions kwarg (already part of the items).
            assert "previous_response_id" not in kwargs
            assert "instructions" not in kwargs
            assert kwargs["input"] == [
                {
                    "type": "message",
                    "role": "system",
                    "content": [{"type": "input_text", "text": "Be helpful"}],
                },
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "List files"}],
                },
            ]
            return _stream(
                [
                    _Event("response.created", response=_Response("resp_a")),
                    _Event(
                        "response.output_item.done",
                        item=_FunctionCallItem("it1", "call_1", "list_files", "{}"),
                    ),
                    _Event("response.completed", response=_Response("resp_a")),
                ]
            )
        if round_no == 2:
            # Tool round: the full history (system + user + function_call +
            # function_call_output) is re-sent; never chained with an id.
            assert "previous_response_id" not in kwargs
            assert kwargs["input"] == [
                {
                    "type": "message",
                    "role": "system",
                    "content": [{"type": "input_text", "text": "Be helpful"}],
                },
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "List files"}],
                },
                {
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "list_files",
                    "arguments": "{}",
                },
                {
                    "type": "function_call_output",
                    "call_id": "call_1",
                    "output": json.dumps({"success": True}),
                },
            ]
            return _stream(
                [
                    _Event("response.created", response=_Response("resp_b")),
                    _Event("response.output_text.delta", delta="Here are the files"),
                    _Event(
                        "response.completed",
                        response=_Response("resp_b", usage=_Usage()),
                    ),
                ]
            )
        raise AssertionError(f"unexpected round {round_no}")

    _mock_send_prompt(monkeypatch, create)

    result = api.send_prompt(
        "List files", instructions="Be helpful", tools=None, use_mcp=False
    )

    assert result.content == "Here are the files"
    # Stateless: no server-side handle to chain with.
    assert result.response_id is None
    assert result.message_count == 2
    assert len(seen) == 2
    # The result carries the full client-side history for the next turn.
    assert result.input_items is not None
    assert result.input_items[-1] == {
        "type": "message",
        "role": "assistant",
        "content": [{"type": "output_text", "text": "Here are the files"}],
    }


def test_send_prompt_stateless_continues_with_previous_items(monkeypatch):
    """The next turn re-sends the previous turn's items plus the new prompt."""
    monkeypatch.setattr(api, "get_responses_in_server_from_provider", lambda p: False)
    seen = []

    def create(**kwargs):
        # Snapshot the input list (send_prompt mutates it in place later).
        seen.append(dict(kwargs, input=list(kwargs["input"])))
        assert "previous_response_id" not in kwargs
        return _stream(
            [
                _Event("response.created", response=_Response("resp_n")),
                _Event("response.output_text.delta", delta="ok"),
                _Event("response.completed", response=_Response("resp_n")),
            ]
        )

    _mock_send_prompt(monkeypatch, create)

    # First turn (fresh conversation).
    first = api.send_prompt("Hello", instructions="Sys", tools=[], use_mcp=False)
    assert seen[-1]["input"] == [
        {
            "type": "message",
            "role": "system",
            "content": [{"type": "input_text", "text": "Sys"}],
        },
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Hello"}],
        },
    ]

    # Second turn: the full history is re-sent with the new user prompt
    # appended; instructions are NOT folded again (already in the history).
    second = api.send_prompt(
        "Follow up",
        previous_items=first.input_items,
        instructions="Sys",
        tools=[],
        use_mcp=False,
    )
    assert seen[-1]["input"] == first.input_items + [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Follow up"}],
        }
    ]
    assert second.input_items == seen[-1]["input"] + [
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "ok"}],
        }
    ]


def test_send_prompt_plain_response(monkeypatch):
    seen = []

    def create(**kwargs):
        seen.append(kwargs)
        assert kwargs["input"] == "Hello"
        assert kwargs["include"] == ["usage"]
        assert "previous_response_id" not in kwargs
        return _stream(
            [
                _Event("response.created", response=_Response("resp_1")),
                _Event("response.output_text.delta", delta="Hi there"),
                _Event(
                    "response.completed", response=_Response("resp_1", usage=_Usage())
                ),
            ]
        )

    _mock_send_prompt(monkeypatch, create)
    result = api.send_prompt("Hello", tools=None, use_mcp=False)

    assert result.content == "Hi there"
    assert result.response_id == "resp_1"
    assert result.message_count == 1
    # Server-side conversation: no client-side items history to carry.
    assert result.input_items is None
    assert len(seen) == 1


def test_send_prompt_raises_on_untyped_error_event(monkeypatch):
    """A server-side provider that streams an untyped error event (e.g.
    DashScope rejecting qwen3.8-max on /responses) must raise a clear error
    instead of returning an empty ConversationResult."""

    def create(**kwargs):
        return _stream(
            [
                _Event(
                    None,
                    code="InvalidParameter",
                    message="Unsupported model: 'qwen3.8-max'.",
                )
            ]
        )

    _mock_send_prompt(monkeypatch, create)
    with pytest.raises(RuntimeError, match="Unsupported model: 'qwen3.8-max'"):
        api.send_prompt("Hello", tools=None, use_mcp=False)


def test_send_prompt_raises_on_empty_stream(monkeypatch):
    """A stream with no events at all raises instead of returning an empty
    result."""

    def create(**kwargs):
        return _stream([])

    _mock_send_prompt(monkeypatch, create)
    with pytest.raises(RuntimeError, match="empty response"):
        api.send_prompt("Hello", tools=None, use_mcp=False)


def test_send_prompt_raises_when_no_response_id_and_no_output(monkeypatch):
    """A server-side provider that reports no response id and produces neither
    content nor tool calls raises an error naming the model (safety net for
    providers whose failure never surfaces as a proper event)."""

    def create(**kwargs):
        return _stream(
            [
                _Event("response.in_progress", response=_Response("unused")),
            ]
        )

    _mock_send_prompt(monkeypatch, create)
    with pytest.raises(RuntimeError, match="gpt-4o"):
        api.send_prompt("Hello", tools=None, use_mcp=False)


def test_send_prompt_sends_instructions_only_on_first_turn(monkeypatch):
    seen = []

    def create(**kwargs):
        seen.append(kwargs)
        return _stream(
            [
                _Event("response.created", response=_Response("resp_n")),
                _Event("response.output_text.delta", delta="ok"),
                _Event("response.completed", response=_Response("resp_n")),
            ]
        )

    _mock_send_prompt(monkeypatch, create)

    # Fresh conversation: instructions are sent.
    api.send_prompt("First", instructions="Be helpful", tools=[], use_mcp=False)
    assert seen[-1]["instructions"] == "Be helpful"

    # Continuing a conversation: instructions are NOT re-sent; the turn is
    # chained via previous_response_id instead.
    api.send_prompt(
        "Follow up",
        previous_response_id="resp_prev",
        instructions="Be helpful",
        tools=[],
        use_mcp=False,
    )
    assert "instructions" not in seen[-1]
    assert seen[-1]["previous_response_id"] == "resp_prev"


def test_send_prompt_chains_tool_calls_without_client_history(monkeypatch):
    """The agent loop must chain tool rounds via previous_response_id and keep
    no client-side messages list (the caller-owned list is not touched)."""
    seen = []

    def create(**kwargs):
        seen.append(kwargs)
        round_no = len(seen)
        if round_no == 1:
            # First round: the model requests a tool call.
            assert kwargs["input"] == "List files"
            assert "previous_response_id" not in kwargs
            # Tools are converted from the Chat Completions shape (name nested
            # under "function") to the Responses API shape (top-level name).
            assert kwargs["tools"] == [
                {
                    "type": "function",
                    "name": "list_files",
                    "description": "",
                    "parameters": {},
                }
            ]
            return _stream(
                [
                    _Event("response.created", response=_Response("resp_a")),
                    _Event(
                        "response.output_item.done",
                        item=_FunctionCallItem("it1", "call_1", "list_files", "{}"),
                    ),
                    _Event("response.completed", response=_Response("resp_a")),
                ]
            )
        if round_no == 2:
            # Second round: tool outputs are chained to the previous response.
            assert kwargs["previous_response_id"] == "resp_a"
            assert kwargs["input"] == [
                {
                    "type": "function_call_output",
                    "call_id": "call_1",
                    "output": json.dumps({"success": True}),
                }
            ]
            assert kwargs["tools"] == [
                {
                    "type": "function",
                    "name": "list_files",
                    "description": "",
                    "parameters": {},
                }
            ]
            return _stream(
                [
                    _Event("response.created", response=_Response("resp_b")),
                    _Event("response.output_text.delta", delta="Here are the files"),
                    _Event(
                        "response.completed",
                        response=_Response("resp_b", usage=_Usage()),
                    ),
                ]
            )
        raise AssertionError(f"unexpected round {round_no}")

    _mock_send_prompt(monkeypatch, create)

    caller_history = [{"role": "system", "content": "seed"}]
    result = api.send_prompt("List files", tools=None, use_mcp=False)

    assert result.content == "Here are the files"
    assert result.response_id == "resp_b"
    assert result.message_count == 2
    # Server-side conversation: the history lives on the server, so the
    # result carries no client-side items.
    assert result.input_items is None
    assert len(seen) == 2
    # The caller-owned history must be untouched: no client-side messages list
    # is created, appended to or updated by the Responses implementation.
    assert caller_history == [{"role": "system", "content": "seed"}]


def test_conversation_result_defaults():
    result = api.ConversationResult(content="text", response_id="resp_1")
    assert result.message_count == 1


def test_module_reexports_completions_api_helpers():
    # Shared helpers are re-exported so callers can import everything from a
    # single module.
    assert api.RequestCancelled is not None
    assert api.resolve_runtime_config is not None
    assert api.get_env_config is not None


# ---- API-type selection (chat.py wrapper + shell state) -------------------


def test_make_send_prompt_func_responses_dispatch(monkeypatch):
    """In Responses mode the wrapper chains via previous_response_id and
    ignores previous_messages (no client-side history)."""
    import janito.cli.chat as chat_mod

    captured = {}

    def fake_send_responses(
        prompt,
        verbose=False,
        previous_response_id=None,
        previous_items=None,
        instructions=None,
        tools=None,
        thinking=False,
        cli_model=None,
        cli_provider=None,
        reasoning_level=None,
    ):
        captured["prompt"] = prompt
        captured["previous_response_id"] = previous_response_id
        captured["previous_items"] = previous_items
        captured["instructions"] = instructions
        captured["tools"] = tools
        captured["cli_model"] = cli_model
        captured["cli_provider"] = cli_provider
        return api.ConversationResult(content="hi", response_id="resp_z")

    # The wrapper imports send_prompt from conversations_api at call time, so
    # patching the module attribute is enough.
    monkeypatch.setattr(api, "send_prompt", fake_send_responses)

    func = chat_mod._make_send_prompt_func(
        "Responses", cli_model="gpt-4", cli_provider="openai"
    )
    result = func(
        "hello",
        previous_messages=[{"role": "system", "content": "x"}],
        previous_response_id="resp_y",
        previous_items=[{"type": "message", "role": "user", "content": []}],
        instructions="sys",
        tools=[],
        thinking=False,
    )

    assert isinstance(result, api.ConversationResult)
    assert result.response_id == "resp_z"
    assert captured["previous_response_id"] == "resp_y"
    assert captured["previous_items"] == [
        {"type": "message", "role": "user", "content": []}
    ]
    assert captured["instructions"] == "sys"
    assert captured["tools"] == []
    assert captured["cli_model"] == "gpt-4"
    assert captured["cli_provider"] == "openai"
    # previous_messages is deliberately not forwarded in Responses mode.
    assert "previous_messages" not in captured


def test_make_send_prompt_func_completions_dispatch(monkeypatch):
    """In Completions mode the wrapper keeps the previous behaviour: it
    forwards previous_messages and returns the assistant text."""
    import janito.cli.chat as chat_mod

    captured = {}

    def fake_send_completions(
        prompt,
        verbose=False,
        previous_messages=None,
        tools=None,
        thinking=False,
        cli_model=None,
        cli_provider=None,
        reasoning_level=None,
    ):
        captured["prompt"] = prompt
        captured["previous_messages"] = previous_messages
        captured["cli_provider"] = cli_provider
        return "completions answer"

    monkeypatch.setattr(chat_mod, "send_prompt", fake_send_completions)

    func = chat_mod._make_send_prompt_func(
        "Completions", cli_model="gpt-4", cli_provider="openai"
    )
    result = func(
        "hello",
        previous_messages=[{"role": "user", "content": "hello"}],
        previous_response_id="resp_y",
        instructions="sys",
        tools=None,
        thinking=False,
    )

    assert result == "completions answer"
    assert captured["previous_messages"] == [{"role": "user", "content": "hello"}]
    assert captured["cli_provider"] == "openai"


def test_shell_tracks_and_resets_previous_response_id():
    """The interactive shell keeps the server-side response id and resets it
    on a fresh conversation (initialize_history), so a restart never chains to
    the old server conversation."""
    from janito.shell import InteractiveShell

    shell = InteractiveShell(model="test-model", no_history=True)
    assert shell.previous_response_id is None
    assert shell.conversation_items is None

    # Simulate a completed Responses turn: the run loop stores the id.
    shell.previous_response_id = "resp_1"
    assert shell.previous_response_id == "resp_1"

    # F2 / "restart" call initialize_history -> fresh server conversation.
    shell.initialize_history(system_prompt="You are helpful")
    assert shell.previous_response_id is None
    assert shell.conversation_items is None


def test_shell_tracks_stateless_conversation_items():
    """For stateless Responses providers (responses_in_server False) the shell
    keeps the client-side input items (never an id) and resets them on a fresh
    conversation."""
    from janito.shell import InteractiveShell

    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt="You are helpful")

    items = [
        {"type": "message", "role": "system", "content": []},
        {"type": "message", "role": "user", "content": []},
        {"type": "message", "role": "assistant", "content": []},
    ]
    # Simulate a completed stateless turn: the run loop stores the items and
    # never keeps an id to chain with.
    shell.conversation_checkpoint = 0
    shell.conversation_items = items
    assert shell.conversation_items == items

    # F2 / "restart" call initialize_history -> fresh client-side history.
    shell.initialize_history(system_prompt="You are helpful")
    assert shell.conversation_items is None
    assert shell.conversation_checkpoint == 0


def test_shell_rollback_truncates_stateless_conversation_items():
    """/rollback truncates the client-side items back to the checkpoint for
    stateless Responses providers."""
    from janito.shell.cmds.rollback import RollbackCmdHandler

    shell = RollbackCmdHandler.__new__(RollbackCmdHandler)
    # Fresh conversation: system + user + assistant.
    shell.messages_history = [{"role": "system", "content": "sys"}]
    shell.history_checkpoint = 1
    shell.previous_response_id = None
    shell.conversation_checkpoint = 2
    shell.conversation_items = [
        {"type": "message", "role": "system", "content": []},
        {"type": "message", "role": "user", "content": []},
        {"type": "message", "role": "assistant", "content": []},
    ]

    handler = RollbackCmdHandler()
    handler._do_rollback(shell)

    # Rolled back to the checkpoint (system + user only).
    assert shell.conversation_items == [
        {"type": "message", "role": "system", "content": []},
        {"type": "message", "role": "user", "content": []},
    ]
