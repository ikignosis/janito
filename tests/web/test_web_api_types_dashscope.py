"""Web agent DashScope API-type tests.

Split from ``test_web_api_types.py`` (call-kwargs passthrough, accumulator
and endpoint-mismatch retry for the DashScope runner).
"""
import sys
import tempfile
from pathlib import Path

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
# DashScope runner
# ---------------------------------------------------------------------------


def _cfg(thinking=False):
    class _Cfg:
        effective_thinking = thinking

        def effective_tools_for(self, api_type):
            return None

    return _Cfg()


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


def test_dashscope_build_call_kwargs_passes_builtin_tools():
    """The effective model's built-in tools are sent as request-body enable_*
    kwargs on the native DashScope API (e.g. enable_code_interpreter /
    enable_search)."""
    from janito.web.backend.agent import dashscope

    class _Cfg:
        effective_thinking = True

        def effective_tools_for(self, api_type):
            return [
                {"type": "code_interpreter"},
                {"type": "web_search"},
                {"type": "web_extractor"},
            ]

    kwargs = dashscope.build_call_kwargs(
        "qwen3.8-max",
        [{"role": "user", "content": "Hello"}],
        None,
        _Cfg(),
        None,
        None,
        None,
    )
    assert kwargs["enable_code_interpreter"] is True
    assert kwargs["enable_thinking"] is True
    assert kwargs["enable_search"] is True


def test_dashscope_build_call_kwargs_omits_builtin_tools_when_none():
    """Models without built-in tools send no enable_* tool kwargs."""
    from janito.web.backend.agent import dashscope

    kwargs = dashscope.build_call_kwargs(
        "qwen3.8-max",
        [{"role": "user", "content": "Hello"}],
        None,
        _cfg(thinking=False),
        None,
        None,
        None,
    )
    assert "enable_code_interpreter" not in kwargs
    assert "enable_search" not in kwargs


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
