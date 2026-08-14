"""Web agent Anthropic API-type tests.

Split from ``test_web_api_types.py`` (system/tool conversion and the
accumulator for the Anthropic runner).
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
# Anthropic runner
# ---------------------------------------------------------------------------


def _cfg(thinking=False):
    class _Cfg:
        effective_thinking = thinking

    return _Cfg()


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
