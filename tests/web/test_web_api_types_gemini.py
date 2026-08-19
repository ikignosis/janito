"""Web agent Gemini API-type tests.

Split from ``test_web_api_types.py``: the native Gemini runner's
call-kwargs conversion (OpenAI history -> ``contents`` + function tool
schemas -> ``function_declarations``), stream accumulation (thought / text /
``function_call`` parts) and the sync-stream consumption off the event loop.
"""

import importlib.util
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

import janito.config_dir as config_dir_mod

try:
    import google.genai  # noqa: F401

    _HAS_GENAI = True
except ModuleNotFoundError:
    _HAS_GENAI = False

requires_genai = pytest.mark.skipif(
    not _HAS_GENAI, reason="google-genai package is not installed"
)

FRONTEND = Path(__file__).parent.parent.parent / "janito" / "web" / "frontend"


@pytest.fixture(scope="module", autouse=True)
def clean_config(request):
    """Isolate the config dir in a temp dir so tests never touch the real one."""
    prev_dir = config_dir_mod.get_config_dir()
    tmp = tempfile.mkdtemp(prefix="janito_web_api_types_gemini_tests_")
    config_dir_mod.set_config_dir(tmp)

    def restore():
        config_dir_mod.set_config_dir(str(prev_dir))

    request.addfinalizer(restore)


# ---------------------------------------------------------------------------
# Gemini runner
# ---------------------------------------------------------------------------


def _part(*, text=None, thought=False, thought_signature=None, function_call=None):
    return SimpleNamespace(
        text=text,
        thought=thought,
        thought_signature=thought_signature,
        function_call=function_call,
    )


def _function_call(call_id="", name="", args=None):
    return SimpleNamespace(id=call_id, name=name, args=args or {})


def _chunk(parts, finish_reason=None, usage=None):
    candidate = SimpleNamespace(
        content=SimpleNamespace(parts=parts), finish_reason=finish_reason
    )
    return SimpleNamespace(candidates=[candidate], usage_metadata=usage)


def _cfg(thinking=False):
    class _Cfg:
        effective_thinking = thinking

        def effective_tools_for(self, api_type):
            return None

    return _Cfg()


def test_gemini_build_call_kwargs_converts_history_and_tools():
    from janito.web.backend.agent import gemini

    messages = [
        {"role": "system", "content": "Be helpful."},
        {"role": "user", "content": "Hello"},
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "ReadFile",
                "description": "Read a file",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]
    kwargs = gemini.build_call_kwargs(
        "gemini-3.7-flash", messages, tools, _cfg(thinking=False), None, None, "high"
    )
    # The OpenAI chat shape is converted to Gemini contents; the leading
    # system message is folded into the top-level system_instruction.
    assert kwargs["model"] == "gemini-3.7-flash"
    assert kwargs["contents"] == [{"role": "user", "parts": [{"text": "Hello"}]}]
    assert kwargs["config"]["system_instruction"] == "Be helpful."
    assert kwargs["config"]["thinking_config"] == {"thinking_level": "high"}
    assert kwargs["config"]["tools"] == [
        {
            "function_declarations": [
                {
                    "name": "ReadFile",
                    "description": "Read a file",
                    "parameters": {"type": "object", "properties": {}},
                }
            ]
        }
    ]


def test_gemini_build_call_kwargs_omits_tools_when_none():
    from janito.web.backend.agent import gemini

    kwargs = gemini.build_call_kwargs(
        "gemini-3.7-flash",
        [{"role": "user", "content": "Hello"}],
        None,
        _cfg(thinking=False),
        None,
        None,
        None,
    )
    assert "tools" not in kwargs["config"]
    assert "thinking_config" not in kwargs["config"]


def test_gemini_accumulator_folds_chunks():
    from janito.web.backend.agent.gemini import GeminiTurnAccumulator

    acc = GeminiTurnAccumulator()
    chunks = [
        _chunk(
            [_part(text="think", thought=True, thought_signature="sig-1")],
            finish_reason=None,
        ),
        _chunk(
            [
                _part(text="Hi ", thought=False),
                _part(
                    function_call=_function_call(
                        "c1", "ReadFile", {"filepath": "/tmp/x"}
                    ),
                    thought_signature="sig-2",
                ),
            ],
            finish_reason=None,
        ),
        _chunk(
            [_part(text="there")],
            finish_reason=SimpleNamespace(name="STOP"),
            usage=SimpleNamespace(
                prompt_token_count=3, response_token_count=7, total_token_count=10
            ),
        ),
    ]
    deltas = [acc.handle(c) for c in chunks]
    assert acc.full_content() == "Hi there"
    assert acc.reasoning_content() == "think"
    assert acc.done is True
    assert acc.thought_parts == [{"text": "think", "thought_signature": "sig-1"}]
    assert acc.tool_calls_list() == [
        {
            "id": "c1",
            "type": "function",
            "function": {
                "name": "ReadFile",
                "arguments": '{"filepath": "/tmp/x"}',
            },
            "thought_signature": "sig-2",
        }
    ]
    usage = acc.usage_event()
    assert (usage.input, usage.output, usage.total) == (3, 7, 10)
    assert deltas[0] == ("think", None)
    assert deltas[1] == (None, "Hi ")


def test_gemini_accumulator_usage_event_none_without_usage():
    """No usage metadata -> no usage event."""
    from janito.web.backend.agent.gemini import GeminiTurnAccumulator

    acc = GeminiTurnAccumulator()
    acc.handle(_chunk([_part(text="hi")], finish_reason=None))
    assert acc.usage_event() is None


def test_gemini_create_client_aborts_without_google_genai(monkeypatch):
    """The web runner guards the optional `google-genai` package."""
    from janito.web.backend.agent import gemini

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    with pytest.raises(RuntimeError) as exc:
        gemini.create_client("https://generativelanguage.googleapis.com", "sk-test")
    assert "pip install google-genai" in str(exc.value)


@requires_genai
def test_gemini_create_client_builds_sdk_client():
    """With google-genai installed, create_client returns a genai.Client."""
    from janito.web.backend.agent import gemini

    client = gemini.create_client(
        "https://generativelanguage.googleapis.com", "sk-test"
    )
    assert client._api_client._http_options.base_url == (
        "https://generativelanguage.googleapis.com"
    )


def test_gemini_stream_turn_events_consumes_sync_stream(monkeypatch):
    """The web runner consumes the sync generate_content_stream off the
    event loop and yields reasoning/token events."""
    import asyncio

    from janito.web.backend.agent import gemini
    from janito.web.backend.events import ReasoningEvent, TokenEvent

    stop = _chunk([_part(text="done")], finish_reason=SimpleNamespace(name="STOP"))
    calls = []

    class _FakeModels:
        def generate_content_stream(self, **kwargs):
            calls.append(kwargs)
            return iter(
                [
                    _chunk(
                        [_part(text="hmm", thought=True)],
                        finish_reason=None,
                    ),
                    _chunk([_part(text="hey")], finish_reason=None),
                    stop,
                ]
            )

    class _FakeClient:
        def __init__(self):
            self.models = _FakeModels()

    handle = _FakeClient()
    kwargs = gemini.build_call_kwargs(
        "gemini-3.7-flash",
        [{"role": "user", "content": "hi"}],
        None,
        _cfg(thinking=False),
        None,
        None,
        None,
    )
    acc = gemini.accumulator()

    async def _run():
        events = []
        async for ev in gemini.stream_turn_events(handle, kwargs, acc):
            events.append(ev)
        return events

    events = asyncio.run(_run())
    assert [e.content for e in events] == ["hmm", "hey", "done"]
    assert isinstance(events[0], ReasoningEvent)
    assert isinstance(events[1], TokenEvent)
    assert acc.full_content() == "heydone"
    assert acc.reasoning_content() == "hmm"
    assert acc.done is True
    assert calls == [kwargs]
