"""
Tests for the Responses API client (:mod:`janito.openai_client.conversations_api`).

``conversations_api.send_prompt`` mirrors ``completions_api.send_prompt`` but
targets the Responses API (``client.responses.create``) with server-side
conversation state: the client never stores or updates a ``messages`` list,
and turns are chained with ``previous_response_id``.

These tests verify:
  - ``_consume_response_stream`` text / reasoning / tool-call assembly.
  - ``response.failed`` is turned into a raised error.
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
    (
        content,
        reasoning,
        tools,
        usage,
        response_id,
        raw_attrs,
    ) = api._consume_response_stream(events)
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
    (
        content,
        reasoning,
        tools,
        usage,
        response_id,
        raw_attrs,
    ) = api._consume_response_stream(events)
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
    _, _, tools, _, response_id, _ = api._consume_response_stream(events)
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
        "janito.openai_client.responses_helpers.get_all_tool_schemas",
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


def _mock_send_prompt_for_model(monkeypatch, model, builtin_tools, create_side_effect):
    """Like ``_mock_send_prompt`` but for a specific model, with the model's
    built-in (native) tools resolved via the provider accessor."""
    client_inst = mock.Mock()
    client_inst.responses.create.side_effect = create_side_effect
    monkeypatch.setattr(api, "OpenAI", mock.Mock(return_value=client_inst))
    monkeypatch.setattr(
        api,
        "resolve_runtime_config",
        lambda *a, **k: ("https://api.example.com", "sk-test", model),
    )
    monkeypatch.setattr(
        "janito.openai_client.responses_helpers.get_all_tool_schemas",
        lambda: [{"type": "function", "function": {"name": "list_files"}}],
    )
    monkeypatch.setattr(
        "janito.provider_accessors.get_default_tools_from_provider",
        lambda p, m=None, api_type=None: builtin_tools,
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
    monkeypatch.setattr(
        "janito.openai_client.responses_state.get_responses_in_server_from_provider",
        lambda p, m=None: False,
    )
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
    monkeypatch.setattr(
        "janito.openai_client.responses_state.get_responses_in_server_from_provider",
        lambda p, m=None: False,
    )
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
        # "usage" is no longer a valid include value: usage arrives on the
        # final response.completed event by default (part of the Response
        # object), so no include parameter is sent.
        assert "include" not in kwargs
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


def test_send_prompt_server_side_resends_pending_items_with_completed_id(
    monkeypatch,
):
    """Server-side Responses: after an Enter-cancel the next turn re-sends the
    cancelled message as input items chained from the last *completed*
    response id (the aborted response id is discarded by the provider and
    never used, so no previous_response_not_found)."""
    seen = []

    def create(**kwargs):
        seen.append(kwargs)
        assert kwargs["previous_response_id"] == "resp_prev"
        assert kwargs["input"] == [
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "cancelled prompt"}],
            },
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "follow up"}],
            },
        ]
        return _stream(
            [
                _Event("response.created", response=_Response("resp_n")),
                _Event("response.output_text.delta", delta="ok"),
                _Event("response.completed", response=_Response("resp_n")),
            ]
        )

    _mock_send_prompt(monkeypatch, create)

    result = api.send_prompt(
        "follow up",
        previous_response_id="resp_prev",
        previous_items=[
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "cancelled prompt"}],
            }
        ],
        instructions="Be helpful",
        tools=[],
        use_mcp=False,
    )
    assert result.response_id == "resp_n"
    # Server-side success: the pending items are folded into the server
    # conversation; no client-side items are carried forward.
    assert result.input_items is None


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


def test_send_prompt_server_side_turn_items_mirror_tool_round(monkeypatch):
    """Server-side Responses: the completed turn's display-only mirror
    (``turn_items``) records the user prompt, the tool-call round
    (function_call + function_call_output) and the final assistant text, so
    the shell can render /history even though the real conversation lives on
    the server (no client-side ``input_items`` are carried)."""
    seen = []

    def create(**kwargs):
        seen.append(kwargs)
        round_no = len(seen)
        if round_no == 1:
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
    result = api.send_prompt("List files", tools=None, use_mcp=False)

    assert result.content == "Here are the files"
    assert result.response_id == "resp_b"
    assert result.message_count == 2
    # Server-side conversation: no client-side items history to carry.
    assert result.input_items is None
    # The display-only mirror holds the full turn for /history.
    assert result.turn_items == [
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
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Here are the files"}],
        },
    ]


def test_send_prompt_server_side_turn_items_plain_response(monkeypatch):
    """Server-side Responses: a plain (no-tool) turn's display-only mirror
    holds just the user prompt and the assistant text."""
    seen = []

    def create(**kwargs):
        seen.append(kwargs)
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

    assert result.input_items is None
    assert result.turn_items == [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Hello"}],
        },
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Hi there"}],
        },
    ]


def test_send_prompt_appends_builtin_tools_without_function_tools(monkeypatch):
    """An empty function-tools list (the ``--no-tools`` case): the effective
    model's built-in (native) tools are still enabled on the CLI Responses
    path.  They are model capabilities, not function tools -- mirroring the
    web agent (and the Responses ``image_generation`` tool)."""
    seen = []

    def create(**kwargs):
        seen.append(kwargs)
        return _stream(
            [
                _Event("response.created", response=_Response("resp_a")),
                _Event("response.output_text.delta", delta="done"),
                _Event("response.completed", response=_Response("resp_a")),
            ]
        )

    _mock_send_prompt_for_model(
        monkeypatch,
        "qwen3.8-max",
        [
            {"type": "code_interpreter"},
            {"type": "web_search"},
            {"type": "web_extractor"},
        ],
        create,
    )
    api.send_prompt("Hello", tools=[], use_mcp=False, cli_provider="alibaba")
    assert seen[-1]["tools"] == [
        {"type": "code_interpreter"},
        {"type": "web_search"},
        {"type": "web_extractor"},
    ]
    assert seen[-1]["tool_choice"] == "auto"


def test_send_prompt_merges_builtin_tools_with_function_tools(monkeypatch):
    """Function-tool schemas (converted to the Responses shape) come first,
    followed by the model's built-in (native) tools."""
    seen = []

    def create(**kwargs):
        seen.append(kwargs)
        return _stream(
            [
                _Event("response.created", response=_Response("resp_a")),
                _Event("response.output_text.delta", delta="done"),
                _Event("response.completed", response=_Response("resp_a")),
            ]
        )

    _mock_send_prompt_for_model(
        monkeypatch,
        "qwen3.8-max",
        [
            {"type": "code_interpreter"},
            {"type": "web_search"},
            {"type": "web_extractor"},
        ],
        create,
    )
    api.send_prompt("Hello", tools=None, use_mcp=False, cli_provider="alibaba")
    assert seen[-1]["tools"] == [
        {
            "type": "function",
            "name": "list_files",
            "description": "",
            "parameters": {},
        },
        {"type": "code_interpreter"},
        {"type": "web_search"},
        {"type": "web_extractor"},
    ]
    assert seen[-1]["tool_choice"] == "auto"


def test_send_prompt_no_builtin_tools_for_openai_responses(monkeypatch):
    """Models without built-in tools get no native entries appended."""
    seen = []

    def create(**kwargs):
        seen.append(kwargs)
        return _stream(
            [
                _Event("response.created", response=_Response("resp_a")),
                _Event("response.output_text.delta", delta="done"),
                _Event("response.completed", response=_Response("resp_a")),
            ]
        )

    _mock_send_prompt_for_model(monkeypatch, "gpt-4o", None, create)
    api.send_prompt("Hello", tools=None, use_mcp=False, cli_provider="openai")
    # Only the converted function tools; no code_interpreter / web_search.
    assert seen[-1]["tools"] == [
        {
            "type": "function",
            "name": "list_files",
            "description": "",
            "parameters": {},
        }
    ]
    assert seen[-1]["tool_choice"] == "auto"


def test_conversation_result_defaults():
    result = api.ConversationResult(content="text", response_id="resp_1")
    assert result.message_count == 1


def test_module_reexports_completions_api_helpers():
    # Shared helpers are re-exported so callers can import everything from a
    # single module.
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


# ---- send_factory (real-time /provider switch) -----------------------------


def test_send_factory_honors_cli_model_for_startup_provider(monkeypatch):
    """The factory keeps ``--model`` for the provider it was given for."""
    import janito.cli.chat as chat_mod
    import janito.openai_client.conversations_api as conv_api

    captured = {}

    def capturer(*a, **kw):
        captured.update(kw)
        return "ok"

    # openai/gpt-5.6-luna resolves to Responses -> the wrapper calls the
    # conversations client; patch it (Completions path patched for safety).
    monkeypatch.setattr(conv_api, "send_prompt", capturer)
    monkeypatch.setattr(chat_mod, "send_prompt", capturer)

    factory = chat_mod._make_send_factory(
        cli_api_type=None,
        cli_model="gpt-5.6-luna",
        cli_provider="openai",
        cli_reasoning_level=None,
    )
    send = factory("openai")
    send("hello", previous_messages=[])
    assert captured["cli_model"] == "gpt-5.6-luna"
    assert captured["cli_provider"] == "openai"


def test_send_factory_resolves_new_provider_model_and_api_type(monkeypatch):
    """After a /provider switch the new provider's own model and API type are
    resolved (the startup ``--model`` does not leak into it)."""
    import janito.cli.chat as chat_mod

    factory = chat_mod._make_send_factory(
        cli_api_type=None,
        cli_model="gpt-5.6-luna",  # startup --model, belongs to openai
        cli_provider="openai",
        cli_reasoning_level=None,
    )
    send = factory("moonshot")  # switched provider

    captured = {}
    monkeypatch.setattr(
        chat_mod,
        "send_prompt",
        lambda *a, **kw: captured.update(kw) or "ok",
    )
    send("hello", previous_messages=[])
    # The new provider's built-in default model is used, not the startup one.
    assert captured["cli_model"] == "kimi-k3"
    assert captured["cli_provider"] == "moonshot"


def test_send_factory_resolves_configured_model_for_new_provider(monkeypatch, tmp_path):
    """A configured model for the switched-to provider is picked up."""
    import janito.cli.chat as chat_mod
    import janito.config_dir as config_dir_mod
    import janito.openai_client.conversations_api as conv_api

    # Point the config directory at a temp dir and set a provider model.
    config_path = tmp_path / ".janito" / "config.json"
    monkeypatch.setattr(config_dir_mod, "_config_dir", config_path.parent)
    from janito.config_store import set_config_value

    set_config_value("deepseek.model", "deepseek-v4-pro")

    captured = {}

    def capturer(*a, **kw):
        captured.update(kw)
        return "ok"

    # deepseek/deepseek-v4-pro resolves to Responses -> conversations client.
    monkeypatch.setattr(conv_api, "send_prompt", capturer)
    monkeypatch.setattr(chat_mod, "send_prompt", capturer)

    factory = chat_mod._make_send_factory(
        cli_api_type=None,
        cli_model=None,
        cli_provider="openai",
        cli_reasoning_level=None,
    )
    send = factory("deepseek")
    send("hello", previous_messages=[])
    assert captured["cli_model"] == "deepseek-v4-pro"
    assert captured["cli_provider"] == "deepseek"


def test_send_factory_resolves_api_type_per_new_provider(monkeypatch):
    """The API type is re-resolved for the switched-to provider: moonshot's
    only supported type is Completions, openai's default is Responses."""
    import janito.cli.chat as chat_mod

    # Capture the api_type passed to _make_send_prompt_func.
    captured = {}

    def fake_make(api_type, **kwargs):
        captured["api_type"] = api_type
        captured["cli_model"] = kwargs["cli_model"]
        captured["cli_provider"] = kwargs["cli_provider"]
        return lambda **kw: "ok"

    monkeypatch.setattr(chat_mod, "_make_send_prompt_func", fake_make)

    factory = chat_mod._make_send_factory(
        cli_api_type=None,
        cli_model=None,
        cli_provider="openai",
        cli_reasoning_level=None,
    )
    factory("moonshot")
    assert captured["api_type"] == "Completions"
    assert captured["cli_model"] == "kimi-k3"
    assert captured["cli_provider"] == "moonshot"

    factory("openai")
    assert captured["api_type"] == "Responses"
    assert captured["cli_model"] is None  # openai default model resolved in-client


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


def test_shell_rollback_server_side_repoints_previous_response_id():
    """/rollback on a server-side Responses conversation (e.g. OpenAI) undoes
    the last completed turn by chaining the next turn (previous_response_id)
    from the response that preceded it, instead of resetting the whole
    server-side conversation to None."""
    from janito.shell.cmds.rollback import RollbackCmdHandler

    shell = RollbackCmdHandler.__new__(RollbackCmdHandler)
    # Two completed turns: r1 then r2 (chained from r1). The checkpoint is
    # before the second turn.
    shell.messages_history = [{"role": "system", "content": "sys"}]
    shell.history_checkpoint = 1
    shell.previous_response_id = "r2"
    shell.conversation_items = None
    shell.response_chain = ["r1", "r2"]
    shell.response_checkpoint = 1

    handler = RollbackCmdHandler()
    handler._do_rollback(shell)

    # The chain is truncated back to the checkpoint and the next turn chains
    # from the response before the rolled-back exchange.
    assert shell.response_chain == ["r1"]
    assert shell.previous_response_id == "r1"


def test_shell_rollback_server_side_single_turn_resets_to_fresh(capsys):
    """/rollback on a server-side Responses conversation with a single
    completed turn returns to a fresh server conversation (previous_response_id
    None), the same end state as the previous full reset for that case."""
    from janito.shell.cmds.rollback import RollbackCmdHandler

    shell = RollbackCmdHandler.__new__(RollbackCmdHandler)
    shell.messages_history = [{"role": "system", "content": "sys"}]
    shell.history_checkpoint = 1
    shell.previous_response_id = "r1"
    shell.conversation_items = None
    shell.response_chain = ["r1"]
    shell.response_checkpoint = 0

    handler = RollbackCmdHandler()
    handler._do_rollback(shell)

    assert shell.response_chain == []
    assert shell.previous_response_id is None
    assert "fresh conversation" in capsys.readouterr().out


def test_shell_rollback_server_side_at_checkpoint_reports_nothing(capsys):
    """A second consecutive /rollback on a server-side conversation (already at
    the checkpoint) reports nothing to roll back and keeps the conversation
    instead of resetting it."""
    from janito.shell.cmds.rollback import RollbackCmdHandler

    shell = RollbackCmdHandler.__new__(RollbackCmdHandler)
    shell.messages_history = [{"role": "system", "content": "sys"}]
    shell.history_checkpoint = 1
    shell.previous_response_id = "r1"
    shell.conversation_items = None
    shell.response_chain = ["r1"]
    shell.response_checkpoint = 1

    handler = RollbackCmdHandler()
    handler._do_rollback(shell)

    # State is preserved: no truncation, no reset.
    assert shell.response_chain == ["r1"]
    assert shell.previous_response_id == "r1"
    assert "Nothing to rollback" in capsys.readouterr().out


def test_shell_rollback_server_side_without_chain_falls_back_to_reset(capsys):
    """/rollback on a server-side conversation with no tracked chain (e.g. a
    manually seeded previous_response_id) keeps the legacy full-reset
    behaviour."""
    from janito.shell.cmds.rollback import RollbackCmdHandler

    shell = RollbackCmdHandler.__new__(RollbackCmdHandler)
    shell.messages_history = [{"role": "system", "content": "sys"}]
    shell.history_checkpoint = 1
    shell.previous_response_id = "r1"
    shell.conversation_items = None
    shell.response_chain = []
    shell.response_checkpoint = 0

    handler = RollbackCmdHandler()
    handler._do_rollback(shell)

    assert shell.previous_response_id is None
    assert "server-side conversation reset" in capsys.readouterr().out


def test_shell_send_prompt_records_server_side_response_chain():
    """Each completed server-side Responses turn appends its final response id
    to the shell's response_chain, so /rollback has a rollback target (and a
    second turn appends the next id, keeping the chain in turn order)."""
    from janito.openai_client.conversations_api import ConversationResult
    from janito.shell import InteractiveShell

    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt="sys")
    calls = {"n": 0}

    def send_prompt_func(user_input, **kwargs):
        calls["n"] += 1
        return ConversationResult(
            content="hi", response_id=f"r{calls['n']}", input_items=None
        )

    shell.send_prompt_func = send_prompt_func
    shell.verbose = False
    shell.no_tools = True
    shell.thinking = False

    shell._send_prompt("first")
    assert shell.response_chain == ["r1"]
    assert shell.previous_response_id == "r1"

    # The second turn is chained from the first response and appends its own.
    shell._send_prompt("second")
    assert shell.response_chain == ["r1", "r2"]
    assert shell.previous_response_id == "r2"


def test_shell_send_prompt_mirrors_server_side_turns_for_history():
    """Each completed server-side Responses turn appends its display-only
    mirror (user prompt + assistant text, Responses input items) to the
    shell's mirrored_history, so /history can render the conversation even
    though the real history lives on the server."""
    from janito.openai_client.conversations_api import ConversationResult
    from janito.shell import InteractiveShell

    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt="sys")
    calls = {"n": 0}

    def send_prompt_func(user_input, **kwargs):
        calls["n"] += 1
        return ConversationResult(
            content=f"reply {calls['n']}",
            response_id=f"r{calls['n']}",
            input_items=None,
            turn_items=[
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_input}],
                },
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": f"reply {calls['n']}"}],
                },
            ],
        )

    shell.send_prompt_func = send_prompt_func
    shell.verbose = False
    shell.no_tools = True
    shell.thinking = False

    shell._send_prompt("first")
    assert len(shell.mirrored_history) == 2
    assert shell.mirrored_history[0]["content"][0]["text"] == "first"
    assert shell.mirrored_history[1]["content"][0]["text"] == "reply 1"

    # A second turn appends its own mirror items, in turn order.
    shell._send_prompt("second")
    assert len(shell.mirrored_history) == 4
    assert shell.mirrored_history[2]["content"][0]["text"] == "second"
    assert shell.mirrored_history[3]["content"][0]["text"] == "reply 2"


def test_shell_send_prompt_stateless_does_not_mirror():
    """Stateless Responses (e.g. DeepSeek) mirrors through
    conversation_items, so the /history display mirror stays empty."""
    from janito.openai_client.conversations_api import ConversationResult
    from janito.shell import InteractiveShell

    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt="sys")

    def send_prompt_func(user_input, **kwargs):
        return ConversationResult(
            content="ok",
            response_id=None,
            input_items=[
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_input}],
                },
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "ok"}],
                },
            ],
            turn_items=[],
        )

    shell.send_prompt_func = send_prompt_func
    shell.verbose = False
    shell.no_tools = True
    shell.thinking = False

    shell._send_prompt("hello")
    assert shell.mirrored_history == []
    assert len(shell.conversation_items) == 2
    assert shell.previous_response_id is None


def test_shell_rollback_server_side_truncates_mirrored_history():
    """/rollback on a server-side Responses conversation also truncates the
    display-only /history mirror back to its checkpoint, so /history no
    longer shows the rolled-back exchange."""
    from janito.shell.cmds.rollback import RollbackCmdHandler

    shell = RollbackCmdHandler.__new__(RollbackCmdHandler)
    shell.messages_history = [{"role": "system", "content": "sys"}]
    shell.history_checkpoint = 1
    shell.previous_response_id = "r2"
    shell.conversation_items = None
    shell.response_chain = ["r1", "r2"]
    shell.response_checkpoint = 1
    shell.mirrored_history = [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "one"}],
        },
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "reply 1"}],
        },
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "two"}],
        },
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "reply 2"}],
        },
    ]
    shell.mirrored_checkpoint = 2

    handler = RollbackCmdHandler()
    handler._do_rollback(shell)

    assert shell.response_chain == ["r1"]
    assert shell.previous_response_id == "r1"
    assert shell.mirrored_history == [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "one"}],
        },
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "reply 1"}],
        },
    ]


def test_shell_send_prompt_keeps_chain_on_enter_cancel():
    """An Enter-cancelled server-side turn (RequestCancelled) appends nothing
    to the response_chain: the shell keeps chaining from the last completed
    response."""
    from janito.openai_client import RequestCancelled
    from janito.shell import InteractiveShell

    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt="sys")
    shell.response_chain = ["r1"]
    shell.response_checkpoint = 1
    shell.previous_response_id = "r1"

    def send_prompt_func(user_input, **kwargs):
        raise RequestCancelled("cancelled by Enter")

    shell.send_prompt_func = send_prompt_func
    shell.verbose = False
    shell.no_tools = True
    shell.thinking = False

    shell._send_prompt("hello")

    # No completed turn: the chain and checkpoint are unchanged.
    assert shell.response_chain == ["r1"]
    assert shell.previous_response_id == "r1"


def test_shell_initialize_history_resets_response_chain():
    """A fresh conversation (F2 / restart / provider switch) also clears the
    tracked server-side response chain so the next turn starts a new server
    conversation."""
    from janito.shell import InteractiveShell

    shell = InteractiveShell(model="test-model", no_history=True)
    shell.initialize_history(system_prompt="sys")
    shell.response_chain = ["r1", "r2"]
    shell.response_checkpoint = 1

    shell.initialize_history(system_prompt="sys")
    assert shell.response_chain == []
    assert shell.response_checkpoint == 0


def test_run_stream_round_recovers_response_id_on_cancel(monkeypatch):
    """Enter-cancel (RequestCancelled) carries the conversation state so the
    shell can continue without losing the user's message: server-side
    conversations hand back the pending user messages (the aborted response
    id is discarded by the provider and must NOT be chained from), stateless
    conversations pass back the full client-side items (which include the
    cancelled message)."""
    from janito.openai_client import RequestCancelled

    client = api.ResponsesClient()

    # Server-side: the pending user messages are handed back for the caller
    # to re-send chained from the last completed response id; the aborted
    # response id from the partial stream is never attached.
    pending = [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "List files"}],
        }
    ]
    exc = RequestCancelled("cancelled")
    exc.partial_result = ("", None, [], None, "resp_aborted")
    monkeypatch.setattr(api, "_run_with_progress_bar", mock.Mock(side_effect=exc))

    with pytest.raises(RequestCancelled) as excinfo:
        client._run_stream_round(
            mock.Mock(),
            {},
            [],
            {
                "responses_in_server": True,
                "response_id": "r1",
                "input_items": "List files",
                "pending_items": pending,
            },
            base_url="https://api.example.com",
            api_key="sk-test",  # pragma: allowlist secret
            model="gpt-4o",
            console=None,
        )
    # No aborted response id: the next turn keeps chaining from the last
    # completed response ("r1").
    assert getattr(excinfo.value, "response_id", None) is None
    # The pending user messages are handed back so they are re-sent.
    assert excinfo.value.conversation_items == pending

    # Server-side without explicit pending items: a string prompt is wrapped
    # into a user message item so the shell can re-send it.
    exc3 = RequestCancelled("cancelled")
    exc3.partial_result = ("", None, [], None, "resp_aborted")
    monkeypatch.setattr(api, "_run_with_progress_bar", mock.Mock(side_effect=exc3))

    with pytest.raises(RequestCancelled) as excinfo3:
        client._run_stream_round(
            mock.Mock(),
            {},
            [],
            {
                "responses_in_server": True,
                "response_id": None,
                "input_items": "List files",
            },
            base_url="https://api.example.com",
            api_key="sk-test",  # pragma: allowlist secret
            model="gpt-4o",
            console=None,
        )
    assert getattr(excinfo3.value, "response_id", None) is None
    assert excinfo3.value.conversation_items == pending

    # Stateless: the full client-side items (system + cancelled message) are
    # handed back so the next turn re-sends them; no id to chain with.
    items = [
        {
            "type": "message",
            "role": "system",
            "content": [{"type": "input_text", "text": "Sys"}],
        },
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "List files"}],
        },
    ]
    exc2 = RequestCancelled("cancelled")
    exc2.partial_result = ("", None, [], None, "resp_x")
    monkeypatch.setattr(api, "_run_with_progress_bar", mock.Mock(side_effect=exc2))

    with pytest.raises(RequestCancelled) as excinfo2:
        client._run_stream_round(
            mock.Mock(),
            {},
            [],
            {
                "responses_in_server": False,
                "response_id": None,
                "input_items": items,
            },
            base_url="https://api.example.com",
            api_key="sk-test",  # pragma: allowlist secret
            model="gpt-4o",
            console=None,
        )
    assert getattr(excinfo2.value, "response_id", None) is None
    assert excinfo2.value.conversation_items == items
