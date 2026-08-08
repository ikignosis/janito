"""Web agent API-type support tests.

The web agentic loop (``janito.web.backend.agent.loop.stream_prompt``) used
to be hardcoded to the Chat Completions API.  It now resolves the API type
for the *effective provider* (``--api-type`` > the provider's configured
``api-type`` written by the Settings drawer > the provider's built-in
default) and dispatches to a per-type runner:

* ``Completions`` -> ``janito.web.backend.agent.call`` (the built-in path)
* ``Responses``   -> ``janito.web.backend.agent.responses``
* ``Anthropic``   -> ``janito.web.backend.agent.anthropic``
* ``DashScope``   -> ``janito.web.backend.agent.dashscope``

Each runner exposes the same interface (``create_client`` /
``build_call_kwargs`` / ``accumulator`` / ``stream_turn_events``) and keeps
the session history in the portable OpenAI chat format -- each API type
converts it to its own wire format when calling.

These tests pin down:

1. ``loop._runner_for`` dispatches each API type to its runner;
2. ``WebServerConfig`` carries ``--api-type`` (and reports it in CLI args);
3. the per-type call-kwargs builders (Responses input items + tool
   conversion, Anthropic system/tool conversion, DashScope passthrough);
4. the per-type accumulators fold streamed items into content / reasoning /
   tool calls (OpenAI wire format) / usage;
5. an end-to-end ``stream_prompt`` against a fake Responses client: the
   history stays OpenAI-format, tool-call rounds re-send the converted
   history, and a final ``DoneEvent`` is produced;
6. the status bar surfaces the effective API type for the selected provider.
"""

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

import janito.config_dir as config_dir_mod

try:
    import dashscope  # noqa: F401

    _HAS_DASHSCOPE = True
except ModuleNotFoundError:
    _HAS_DASHSCOPE = False

requires_dashscope = pytest.mark.skipif(
    not _HAS_DASHSCOPE, reason="dashscope package is not installed"
)

FRONTEND = Path(__file__).parent.parent.parent / "janito" / "web" / "frontend"


@pytest.fixture(scope="module", autouse=True)
def clean_config(request):
    """Isolate the config dir in a temp dir so tests never touch the real one."""
    prev_dir = config_dir_mod.get_config_dir()
    tmp = tempfile.mkdtemp(prefix="janito_web_api_types_tests_")
    config_dir_mod.set_config_dir(tmp)

    def restore():
        config_dir_mod.set_config_dir(str(prev_dir))

    request.addfinalizer(restore)


# ---------------------------------------------------------------------------
# Runner dispatch + config plumbing
# ---------------------------------------------------------------------------


def test_loop_dispatches_each_api_type_to_its_runner():
    from janito.web.backend.agent import loop

    assert loop._runner_for("Responses") is loop.responses_runner
    assert loop._runner_for("Anthropic") is loop.anthropic_runner
    assert loop._runner_for("DashScope") is loop.dashscope_runner
    # Completions is the built-in path (call.py) -- no runner module.
    assert loop._runner_for("Completions") is None


def test_web_server_config_carries_api_type():
    from janito.cli.parser import create_parser
    from janito.web.backend.config import WebServerConfig

    args = create_parser().parse_args(["--web", "--api-type", "Anthropic"])
    config = WebServerConfig.from_args(args)
    assert config.api_type == "Anthropic"
    assert config.cli_args["api_type"] == "Anthropic"

    args = create_parser().parse_args(["--web"])
    config = WebServerConfig.from_args(args)
    assert config.api_type is None  # follow the provider's configured default


# ---------------------------------------------------------------------------
# Shared usage helper
# ---------------------------------------------------------------------------


def test_usage_event_from_usage_handles_both_usage_shapes():
    from janito.web.backend.agent.call import usage_event_from_usage
    from janito.web.backend.events import UsageEvent

    # Chat Completions shape
    completions_usage = SimpleNamespace(
        total_tokens=10,
        prompt_tokens=6,
        completion_tokens=4,
        prompt_tokens_details=SimpleNamespace(cached_tokens=2),
    )
    ev = usage_event_from_usage(completions_usage, max_tokens=128)
    assert isinstance(ev, UsageEvent)
    assert (ev.total, ev.input, ev.output, ev.cached, ev.max_tokens) == (
        10,
        6,
        4,
        2,
        128,
    )

    # Responses / DashScope / Anthropic shape
    responses_usage = SimpleNamespace(
        total_tokens=10,
        input_tokens=6,
        output_tokens=4,
        input_tokens_details=SimpleNamespace(cached_tokens=3),
    )
    ev = usage_event_from_usage(responses_usage, max_tokens=64)
    assert (ev.total, ev.input, ev.output, ev.cached, ev.max_tokens) == (
        10,
        6,
        4,
        3,
        64,
    )

    assert usage_event_from_usage(None) is None


# ---------------------------------------------------------------------------
# Responses runner
# ---------------------------------------------------------------------------


def _cfg(thinking=False):
    class _Cfg:
        effective_thinking = thinking

    return _Cfg()


def test_responses_build_call_kwargs_converts_history_and_tools():
    from janito.web.backend.agent import responses

    messages = [
        {"role": "system", "content": "Be helpful."},
        {"role": "user", "content": "Hello"},
    ]
    tools = [
        {
            "type": "function",
            "function": {"name": "ReadFile", "description": "read", "parameters": {}},
        }
    ]
    kwargs = responses.build_call_kwargs(
        "gpt-4", messages, tools, _cfg(thinking=True), 1000, None, "high"
    )
    assert kwargs["model"] == "gpt-4"
    assert kwargs["max_output_tokens"] == 1000
    assert kwargs["reasoning"] == {"effort": "high"}
    assert kwargs["extra_body"]["enable_thinking"] is True
    assert kwargs["stream"] is True

    # The full history is re-sent as Responses input items.
    assert kwargs["input"] == [
        {
            "type": "message",
            "role": "system",
            "content": [{"type": "input_text", "text": "Be helpful."}],
        },
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Hello"}],
        },
    ]
    # Tools are converted to the Responses top-level shape.
    assert kwargs["tools"] == [
        {
            "type": "function",
            "name": "ReadFile",
            "description": "read",
            "parameters": {},
        }
    ]
    assert kwargs["tool_choice"] == "auto"


def test_responses_build_call_kwargs_omits_optional_fields():
    from janito.web.backend.agent import responses

    kwargs = responses.build_call_kwargs(
        "gpt-4",
        [{"role": "user", "content": "hi"}],
        None,
        _cfg(thinking=False),
        None,
        None,
        None,
    )
    assert "max_output_tokens" not in kwargs
    assert "reasoning" not in kwargs
    assert "extra_body" not in kwargs
    assert "tools" not in kwargs


def test_responses_accumulator_folds_stream_events():
    from janito.web.backend.agent.responses import ResponsesTurnAccumulator

    acc = ResponsesTurnAccumulator()
    events = [
        SimpleNamespace(type="response.created", response=SimpleNamespace(id="r1")),
        SimpleNamespace(type="response.reasoning_text.delta", delta="think"),
        SimpleNamespace(type="response.output_text.delta", delta="Hello"),
        SimpleNamespace(
            type="response.function_call_arguments.delta", item_id="fc1", delta='{"a"'
        ),
        SimpleNamespace(
            type="response.function_call_arguments.done",
            item_id="fc1",
            arguments='{"a":1}',
        ),
        SimpleNamespace(
            type="response.output_item.done",
            item=SimpleNamespace(
                type="function_call", call_id="call_1", name="ReadFile", id="fc1"
            ),
        ),
        SimpleNamespace(
            type="response.completed",
            response=SimpleNamespace(
                id="r1",
                usage=SimpleNamespace(total_tokens=9, input_tokens=5, output_tokens=4),
            ),
        ),
    ]
    deltas = [acc.handle(ev) for ev in events]
    assert acc.full_content() == "Hello"
    assert acc.reasoning_content() == "think"
    assert acc.tool_calls_list() == [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "ReadFile", "arguments": '{"a":1}'},
        }
    ]
    usage = acc.usage_event(max_tokens=100)
    assert (usage.input, usage.output, usage.total, usage.max_tokens) == (5, 4, 9, 100)
    # Reasoning/text deltas are surfaced live for the browser.
    assert deltas[1] == ("think", None)
    assert deltas[2] == (None, "Hello")


def test_responses_accumulator_raises_failed_error():
    from janito.web.backend.agent.responses import ResponsesTurnAccumulator

    acc = ResponsesTurnAccumulator()
    with pytest.raises(RuntimeError, match="boom"):
        acc.handle(
            SimpleNamespace(
                type="response.failed",
                response=SimpleNamespace(error=SimpleNamespace(message="boom")),
            )
        )


# ---------------------------------------------------------------------------
# Anthropic runner
# ---------------------------------------------------------------------------


def test_anthropic_build_call_kwargs_extracts_system_and_converts_tools():
    from janito.web.backend.agent import anthropic

    messages = [
        {"role": "system", "content": "Be helpful."},
        {"role": "user", "content": "Hello"},
    ]
    tools = [
        {
            "type": "function",
            "function": {"name": "ReadFile", "description": "read", "parameters": {}},
        }
    ]
    kwargs = anthropic.build_call_kwargs(
        "claude", messages, tools, _cfg(thinking=False), None, None, None
    )
    assert kwargs["model"] == "claude"
    assert kwargs["system"] == "Be helpful."
    assert kwargs["max_tokens"] == 100000  # the Messages API requires max_tokens
    assert kwargs["messages"] == [{"role": "user", "content": "Hello"}]
    assert kwargs["tools"] == [
        {"name": "ReadFile", "description": "read", "input_schema": {}}
    ]
    assert kwargs["stream"] is True


def test_anthropic_conversion_merges_consecutive_tool_messages():
    from janito.web.backend.agent.anthropic import _to_anthropic

    messages = [
        {"role": "user", "content": "do it"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "c1",
                    "type": "function",
                    "function": {"name": "ReadFile", "arguments": '{"a":1}'},
                },
                {
                    "id": "c2",
                    "type": "function",
                    "function": {"name": "ListFiles", "arguments": "{}"},
                },
            ],
        },
        {"role": "tool", "tool_call_id": "c1", "name": "ReadFile", "content": "one"},
        {"role": "tool", "tool_call_id": "c2", "name": "ListFiles", "content": "two"},
        {"role": "assistant", "content": "done"},
    ]
    converted, system = _to_anthropic(messages)
    assert system is None
    assert converted[0] == {"role": "user", "content": "do it"}
    # tool_calls -> tool_use blocks (with parsed input)
    assert converted[1] == {
        "role": "assistant",
        "content": [
            {"type": "tool_use", "id": "c1", "name": "ReadFile", "input": {"a": 1}},
            {"type": "tool_use", "id": "c2", "name": "ListFiles", "input": {}},
        ],
    }
    # consecutive tool messages merge into ONE user message of tool_results
    assert converted[2] == {
        "role": "user",
        "content": [
            {"type": "tool_result", "tool_use_id": "c1", "content": "one"},
            {"type": "tool_result", "tool_use_id": "c2", "content": "two"},
        ],
    }
    assert converted[3] == {"role": "assistant", "content": "done"}


def test_anthropic_accumulator_folds_stream_events():
    from janito.web.backend.agent.anthropic import AnthropicTurnAccumulator

    acc = AnthropicTurnAccumulator()
    events = [
        SimpleNamespace(
            type="message_start",
            message=SimpleNamespace(usage=SimpleNamespace(input_tokens=5)),
        ),
        SimpleNamespace(
            type="content_block_start",
            index=0,
            content_block=SimpleNamespace(type="text"),
        ),
        SimpleNamespace(
            type="content_block_delta",
            index=0,
            delta=SimpleNamespace(type="text_delta", text="Hi "),
        ),
        SimpleNamespace(
            type="content_block_delta",
            index=0,
            delta=SimpleNamespace(type="text_delta", text="there"),
        ),
        SimpleNamespace(type="content_block_stop", index=0),
        SimpleNamespace(
            type="content_block_start",
            index=1,
            content_block=SimpleNamespace(type="tool_use", id="tu1", name="ReadFile"),
        ),
        SimpleNamespace(
            type="content_block_delta",
            index=1,
            delta=SimpleNamespace(type="input_json_delta", partial_json='{"filepath"'),
        ),
        SimpleNamespace(
            type="content_block_delta",
            index=1,
            delta=SimpleNamespace(type="input_json_delta", partial_json=':"/tmp/x"}'),
        ),
        SimpleNamespace(type="content_block_stop", index=1),
        SimpleNamespace(type="message_delta", usage=SimpleNamespace(output_tokens=3)),
        SimpleNamespace(type="message_stop"),
    ]
    deltas = [acc.handle(ev) for ev in events]
    assert acc.full_content() == "Hi there"
    assert acc.done is True
    assert acc.tool_calls_list() == [
        {
            "id": "tu1",
            "type": "function",
            "function": {"name": "ReadFile", "arguments": '{"filepath": "/tmp/x"}'},
        }
    ]
    usage = acc.usage_event()
    assert (usage.input, usage.output, usage.total) == (5, 3, 8)
    assert deltas[2] == (None, "Hi ")
    assert deltas[3] == (None, "there")


# ---------------------------------------------------------------------------
# DashScope runner
# ---------------------------------------------------------------------------


def test_dashscope_build_call_kwargs_passes_history_and_thinking():
    from janito.web.backend.agent import dashscope

    messages = [
        {"role": "system", "content": "Be helpful."},
        {"role": "user", "content": "Hello"},
    ]
    tools = [{"type": "function", "function": {"name": "ReadFile", "parameters": {}}}]
    kwargs = dashscope.build_call_kwargs(
        "qwen3.8-max", messages, tools, _cfg(thinking=True), None, None, None
    )
    # The OpenAI chat shape is accepted natively -- sent as-is.
    assert kwargs["messages"] == messages
    assert kwargs["tools"] == tools
    assert kwargs["max_tokens"] == 100000
    assert kwargs["result_format"] == "message"
    assert kwargs["stream"] is True
    assert kwargs["incremental_output"] is True
    assert kwargs["enable_thinking"] is True


def test_dashscope_accumulator_folds_chunks():
    from janito.web.backend.agent.dashscope import DashScopeTurnAccumulator

    acc = DashScopeTurnAccumulator()
    chunks = [
        {
            "status_code": 200,
            "output": {
                "choices": [
                    {"message": {"reasoning_content": "think"}, "finish_reason": None}
                ]
            },
            "usage": {"input_tokens": 3},
        },
        {
            "status_code": 200,
            "output": {
                "choices": [
                    {
                        "message": {
                            "content": "Hi",
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "c1",
                                    "function": {
                                        "name": "ReadFile",
                                        "arguments": '{"filepath"',
                                    },
                                }
                            ],
                        },
                        "finish_reason": None,
                    }
                ]
            },
            "usage": {},
        },
        {
            "status_code": 200,
            "output": {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {"index": 0, "function": {"arguments": ':"/tmp/x"}'}}
                            ]
                        },
                        "finish_reason": "stop",
                    }
                ]
            },
            "usage": {"output_tokens": 7, "total_tokens": 10},
        },
    ]
    deltas = [acc.handle(c) for c in chunks]
    assert acc.full_content() == "Hi"
    assert acc.reasoning_content() == "think"
    assert acc.done is True
    assert acc.tool_calls_list() == [
        {
            "id": "c1",
            "type": "function",
            "function": {"name": "ReadFile", "arguments": '{"filepath":"/tmp/x"}'},
        }
    ]
    usage = acc.usage_event()
    assert (usage.input, usage.output, usage.total) == (3, 7, 10)
    assert deltas[0] == ("think", None)
    assert deltas[1] == (None, "Hi")


@requires_dashscope
def test_dashscope_stream_retries_on_endpoint_mismatch(monkeypatch):
    """The DashScope runner consumes the sync stream off the event loop and
    retries once on the other generation endpoint when the API rejects the
    model with a model/endpoint mismatch."""
    import asyncio

    import dashscope as dashscope_mod
    from dashscope import Generation, MultiModalConversation

    from janito.openai_client.dashscope_stream import _ModelEndpointMismatch
    from janito.web.backend.agent import dashscope as ds
    from janito.web.backend.events import TokenEvent

    calls = []

    def fake_generation_call(**kwargs):
        calls.append("Generation")

        def gen():
            raise _ModelEndpointMismatch("url error, please check url")
            yield  # pragma: no cover - makes this a generator

        return gen()

    def fake_multimodal_call(**kwargs):
        calls.append("MultiModal")
        # The multimodal endpoint requires list-of-modality-item content.
        assert all(isinstance(m["content"], list) for m in kwargs["messages"])

        def gen():
            yield {
                "status_code": 200,
                "output": {
                    "choices": [
                        {
                            "message": {"content": [{"text": "retried ok"}]},
                            "finish_reason": "stop",
                        }
                    ]
                },
                "usage": {},
            }

        return gen()

    monkeypatch.setattr(Generation, "call", staticmethod(fake_generation_call))
    monkeypatch.setattr(
        MultiModalConversation, "call", staticmethod(fake_multimodal_call)
    )
    # create_client sets the module-level base URL; restore it on teardown.
    monkeypatch.setattr(
        dashscope_mod,
        "base_http_api_url",
        getattr(dashscope_mod, "base_http_api_url", None),
        raising=False,
    )

    handle = ds.create_client("https://dashscope-intl.aliyuncs.com/api/v1", "sk-test")
    kwargs = ds.build_call_kwargs(
        "qwen-flash",
        [{"role": "user", "content": "hey"}],
        None,
        _cfg(thinking=False),
        None,
        None,
        None,
    )
    acc = ds.accumulator()

    async def _run():
        events = []
        async for ev in ds.stream_turn_events(handle, kwargs, acc):
            events.append(ev)
        return events

    events = asyncio.run(_run())
    assert calls == ["Generation", "MultiModal"]
    assert [e.content for e in events] == ["retried ok"]
    assert isinstance(events[0], TokenEvent)
    assert acc.full_content() == "retried ok"
    assert acc.done is True


# ---------------------------------------------------------------------------
# End-to-end: stream_prompt against a fake Responses client
# ---------------------------------------------------------------------------


class _FakeStream:
    """An async iterable of fake SDK events/chunks."""

    def __init__(self, items):
        self._items = list(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return self._items.pop(0)
        except IndexError:
            raise StopAsyncIteration


class _FakeResponsesApi:
    def __init__(self, owner):
        self._owner = owner

    async def create(self, **kwargs):
        self._owner.calls.append(kwargs)
        return _FakeStream(self._owner.streams.pop(0))


class _FakeClient:
    """Fake SDK client recording each call and replaying the given streams."""

    def __init__(self, streams):
        self.streams = list(streams)
        self.calls = []
        self.responses = _FakeResponsesApi(self)


def test_stream_prompt_responses_round_trip(monkeypatch):
    """The loop dispatches to the Responses runner, keeps the history in
    OpenAI format, and re-sends the converted history after a tool round."""
    import asyncio

    from janito.web.backend.agent import loop
    from janito.web.backend.config import WebServerConfig
    from janito.web.backend.events import DoneEvent, TokenEvent, WaitingEvent

    monkeypatch.setattr(
        loop,
        "resolve_runtime_config",
        lambda *a, **k: (None, "sk-test", "gpt-4"),
    )

    fake_client = _FakeClient(
        [
            # First round: a tool call (no final text yet).
            [
                SimpleNamespace(
                    type="response.output_text.delta", delta="Let me check."
                ),
                SimpleNamespace(
                    type="response.function_call_arguments.done",
                    item_id="fc1",
                    arguments='{"filepath": "/tmp/a"}',
                ),
                SimpleNamespace(
                    type="response.output_item.done",
                    item=SimpleNamespace(
                        type="function_call",
                        call_id="call_1",
                        name="ReadFile",
                        id="fc1",
                    ),
                ),
                SimpleNamespace(
                    type="response.completed", response=SimpleNamespace(id="r1")
                ),
            ],
            # Second round: the final answer.
            [
                SimpleNamespace(type="response.output_text.delta", delta="Done!"),
                SimpleNamespace(
                    type="response.completed",
                    response=SimpleNamespace(
                        id="r2",
                        usage=SimpleNamespace(
                            total_tokens=8, input_tokens=5, output_tokens=3
                        ),
                    ),
                ),
            ],
        ]
    )
    monkeypatch.setattr(
        "janito.web.backend.agent.responses.create_client",
        lambda base_url, api_key: fake_client,
    )

    async def _fake_run_tool_turn(tool_calls_list, full_content, messages, use_mcp):
        # Mirror run_tool_turn's OpenAI-format appends without executing tools.
        messages.append(
            {
                "role": "assistant",
                "content": full_content or None,
                "tool_calls": tool_calls_list,
            }
        )
        for tc in tool_calls_list:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": tc["function"]["name"],
                    "content": "{}",
                }
            )
        return
        yield  # pragma: no cover - makes this an async generator

    monkeypatch.setattr(loop, "run_tool_turn", _fake_run_tool_turn)

    config = WebServerConfig(provider="openai", no_tools=True, verbose=False)
    messages: list[dict] = []

    async def _run():
        events = []
        async for ev in loop.stream_prompt(
            "hi", messages, config, tools=[], use_mcp=False
        ):
            events.append(ev)
        return events

    events = asyncio.run(_run())
    client = fake_client

    # The history stays in the portable OpenAI chat format.
    assert messages == [
        {"role": "user", "content": "hi"},
        {
            "role": "assistant",
            "content": "Let me check.",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "ReadFile",
                        "arguments": '{"filepath": "/tmp/a"}',
                    },
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "name": "ReadFile", "content": "{}"},
        {"role": "assistant", "content": "Done!"},
    ]

    # Two API rounds: the first carries the user prompt, the second re-sends
    # the whole history including the function_call + function_call_output
    # items produced by the tool round.
    assert len(client.calls) == 2
    first_input = client.calls[0]["input"]
    assert first_input == [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "hi"}],
        }
    ]
    second_input = client.calls[1]["input"]
    # The second round re-sends the whole (converted) history as it stood
    # when the request was made: user prompt, the assistant's tool-call turn
    # (text + function_call), and the tool result.
    assert second_input == [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "hi"}],
        },
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Let me check."}],
        },
        {
            "type": "function_call",
            "call_id": "call_1",
            "name": "ReadFile",
            "arguments": '{"filepath": "/tmp/a"}',
        },
        {
            "type": "function_call_output",
            "call_id": "call_1",
            "output": "{}",
        },
    ]

    # Event flow: waiting -> token -> tool turn (no events) -> waiting ->
    # token -> usage -> done.
    assert isinstance(events[0], WaitingEvent)
    assert isinstance(events[1], TokenEvent) and events[1].content == "Let me check."
    assert isinstance(events[2], WaitingEvent)
    assert isinstance(events[3], TokenEvent) and events[3].content == "Done!"
    usage = next(e for e in events if getattr(e, "type", "") == "usage")
    assert (usage.input, usage.output, usage.total) == (5, 3, 8)
    done = next(e for e in events if isinstance(e, DoneEvent))
    assert done.full_content == "Done!"
    assert done.message_count == len(messages)


# ---------------------------------------------------------------------------
# Frontend wiring (static checks)
# ---------------------------------------------------------------------------


def test_status_bar_shows_effective_api_type():
    """The status bar renders an API badge resolved like the backend."""
    js = (FRONTEND / "js" / "statusBar.js").read_text(encoding="utf-8")
    assert "get apiType()" in js
    # Resolution mirrors resolve_api_type: configured override, then default.
    assert "p.api_type ||" in js
    assert "p.default_api_type" in js

    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert "<strong>API:</strong>" in html
    assert 'x-text="apiType"' in html
