"""
Tests for the StreamConsumer classes (janito.openai_client.*_stream).

The four stream modules now implement their assembly logic in consumer
classes with instance-attribute state:

- ``ResponsesStreamConsumer`` (responses_stream)
- ``CompletionsStreamConsumer`` (completions_stream)
- ``AnthropicStreamConsumer`` (anthropic_stream)
- ``DashScopeStreamConsumer`` (dashscope_stream)

The module-level ``_consume_*`` functions delegate to them; behavioural
equivalence is already covered by the existing client tests (which call the
module functions).  These tests pin the new class contract: the result
properties, the ``consume``/``handle_*`` API and the legacy ``state``-dict
bridges.
"""

import sys
import threading
from pathlib import Path
from types import SimpleNamespace

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class _Event:
    """Fake stream event with a ``type`` plus arbitrary attributes."""

    def __init__(self, type, **attrs):
        self.type = type
        for name, value in attrs.items():
            setattr(self, name, value)


def _stream(events):
    yield from events


if pytest is not None:
    # ---- ResponsesStreamConsumer --------------------------------------

    def test_responses_consumer_assembles_text_and_usage():
        from janito.openai_client.responses_stream import ResponsesStreamConsumer

        c = ResponsesStreamConsumer()
        c.handle_event(_Event("response.created", response=SimpleNamespace(id="r1")))
        c.handle_event(_Event("response.output_text.delta", delta="Hello"))
        c.handle_event(_Event("response.output_text.delta", delta=" world"))
        c.handle_event(
            _Event(
                "response.completed",
                response=SimpleNamespace(
                    id="r1", usage=SimpleNamespace(total_tokens=100)
                ),
            )
        )
        assert c.full_content == "Hello world"
        assert c.reasoning_content is None
        assert c.response_id == "r1"
        assert c.usage_info.total_tokens == 100

    def test_responses_consumer_properties():
        from janito.openai_client.responses_stream import ResponsesStreamConsumer

        c = ResponsesStreamConsumer()
        assert c.full_content == ""
        assert c.reasoning_content is None
        c.reasoning.append("thinking")
        assert c.reasoning_content == "thinking"

    def test_responses_consumer_consume_cancel_short_circuits():
        from janito.openai_client.responses_stream import ResponsesStreamConsumer

        cancel = threading.Event()
        cancel.set()

        def events():
            if False:
                yield None  # pragma: no cover - keeps this a generator

        c = ResponsesStreamConsumer()
        content, reasoning, tools, usage, response_id = c.consume(
            events(), cancel_event=cancel
        )
        # Cancel short-circuit must not raise the empty-stream error.
        assert content == ""
        assert tools == []
        assert response_id is None

    def test_responses_consumer_empty_stream_raises():
        from janito.openai_client.responses_stream import ResponsesStreamConsumer

        with pytest.raises(RuntimeError, match="empty response"):
            ResponsesStreamConsumer().consume(_stream([]))

    def test_responses_legacy_handle_bridge_writes_back():
        """The re-exported _handle_* functions keep working with a state dict."""
        from janito.openai_client import responses_stream as rs

        state = {
            "content": [],
            "reasoning": [],
            "tool_calls": [],
            "partial_arguments": {},
            "usage_info": None,
            "response_id": None,
        }
        rs._handle_stream_event(
            _Event("response.created", response=SimpleNamespace(id="r_b")),
            state,
        )
        rs._handle_text_delta(_Event("response.output_text.delta", delta="hi"), state)
        assert state["response_id"] == "r_b"
        assert state["content"] == ["hi"]

    # ---- CompletionsStreamConsumer ------------------------------------

    def test_completions_consumer_assembles_chunks():
        from janito.openai_client.completions_stream import CompletionsStreamConsumer

        c = CompletionsStreamConsumer()

        class _Delta:
            def __init__(self, content=None, reasoning=None, tool_calls=None):
                self.content = content
                self.reasoning_content = reasoning
                self.tool_calls = tool_calls

        class _Chunk:
            def __init__(self, delta, usage=None, choices=True):
                self.choices = [SimpleNamespace(delta=delta)] if choices else []
                self.usage = usage

        c.handle_chunk(_Chunk(_Delta(content="Hello ")).choices[0].delta)
        c.handle_chunk(
            _Chunk(_Delta(content="world", reasoning="think")).choices[0].delta
        )
        assert c.full_content == "Hello world"
        assert c.reasoning_content == "think"
        c.consume(
            _stream([_Chunk(_Delta(content=" final"), usage=SimpleNamespace(total=5))])
        )
        assert c.usage_info.total == 5

    def test_completions_consumer_accumulates_tool_call_deltas():
        from janito.openai_client.completions_stream import CompletionsStreamConsumer

        c = CompletionsStreamConsumer()

        class _Fn:
            name = "read_file"
            arguments = '{"filepath": "'

        class _TC:
            index = 0
            id = "call_1"
            function = _Fn()

        class _Fn2:
            name = None
            arguments = 'a.txt"}'

        class _TC2:
            index = 0
            id = None
            function = _Fn2()

        c.handle_tool_call_delta(_TC())
        c.handle_tool_call_delta(_TC2())
        assert c.tool_calls == {
            0: {
                "id": "call_1",
                "name": "read_file",
                "arguments": '{"filepath": "a.txt"}',
            }
        }

    def test_completions_legacy_chunk_bridge_mutates_in_place():
        from janito.openai_client.completions_stream import _consume_chunk

        content, reasoning, tool_calls = [], [], {}
        _consume_chunk(
            SimpleNamespace(content="x", reasoning_content=None, tool_calls=None),
            content,
            reasoning,
            tool_calls,
        )
        assert content == ["x"]

    # ---- AnthropicStreamConsumer --------------------------------------

    def test_anthropic_consumer_assembles_text_and_tool_use():
        from janito.openai_client.anthropic_stream import AnthropicStreamConsumer

        c = AnthropicStreamConsumer()
        c.handle_event(
            _Event(
                "message_start",
                message=SimpleNamespace(usage=SimpleNamespace(input_tokens=10)),
            )
        )
        c.handle_event(
            _Event(
                "content_block_start",
                index=0,
                content_block=SimpleNamespace(type="text"),
            )
        )
        c.handle_event(
            _Event(
                "content_block_delta",
                index=0,
                delta=SimpleNamespace(type="text_delta", text="Hello"),
            )
        )
        c.handle_event(_Event("content_block_stop", index=0))
        assert c.full_content == "Hello"
        assert c.reasoning_content is None
        # usage_info is a SimpleNamespace built from the token counters.
        assert c.usage_info.input_tokens == 10
        assert c.usage_info.output_tokens is None
        assert c.usage_info.total_tokens == 10

    def test_anthropic_consumer_message_stop_completes():
        from janito.openai_client.anthropic_stream import AnthropicStreamConsumer

        c = AnthropicStreamConsumer()
        assert c.handle_event(_Event("message_stop")) is True
        assert c.handle_event(_Event("content_block_start", index=0)) is False

    def test_anthropic_consumer_usage_none_when_no_tokens():
        from janito.openai_client.anthropic_stream import AnthropicStreamConsumer

        assert AnthropicStreamConsumer().usage_info is None

    def test_anthropic_legacy_handle_bridge_returns_complete():
        from janito.openai_client import anthropic_stream as ast

        state = {
            "content": [],
            "reasoning": [],
            "tool_use_blocks": [],
            "blocks": {},
            "input_tokens": None,
            "output_tokens": None,
        }
        complete = ast._handle_anthropic_event(_Event("message_stop"), state)
        assert complete is True

    # ---- DashScopeStreamConsumer --------------------------------------

    def _dashscope_chunk(
        content="", reasoning="", tool_calls=None, finish=None, usage=None
    ):
        message = SimpleNamespace(
            content=content,
            reasoning_content=reasoning,
            tool_calls=tool_calls or [],
        )
        choice = SimpleNamespace(finish_reason=finish, message=message)
        return SimpleNamespace(
            status_code=200,
            output=SimpleNamespace(choices=[choice]),
            usage=usage,
        )

    def test_dashscope_consumer_joins_multimodal_content_and_usage():
        from janito.openai_client.dashscope_stream import DashScopeStreamConsumer

        c = DashScopeStreamConsumer()
        c.handle_chunk(_dashscope_chunk(content=[{"text": "Hello "}]))
        c.handle_chunk(
            _dashscope_chunk(
                content=[{"text": "world"}],
                finish="stop",
                usage=SimpleNamespace(
                    input_tokens=10, output_tokens=20, total_tokens=30
                ),
            )
        )
        assert c.full_content == "Hello world"
        assert c.finish is True
        assert c.usage_state == {
            "input_tokens": 10,
            "output_tokens": 20,
            "total_tokens": 30,
        }

    def test_dashscope_consumer_accumulates_tool_calls():
        from janito.openai_client.dashscope_stream import DashScopeStreamConsumer

        c = DashScopeStreamConsumer()
        c.handle_message(
            SimpleNamespace(
                content="",
                reasoning_content="",
                tool_calls=[
                    {
                        "index": 0,
                        "id": "call_1",
                        "function": {"name": "get_weather", "arguments": '{"city": '},
                    }
                ],
            )
        )
        c.handle_message(
            SimpleNamespace(
                content="",
                reasoning_content="",
                tool_calls=[
                    {"index": 0, "id": "", "function": {"arguments": '"Lisbon"}'}}
                ],
            )
        )
        assert c.tool_calls == {
            0: {
                "id": "call_1",
                "name": "get_weather",
                "arguments": '{"city": "Lisbon"}',
            }
        }

    def test_dashscope_consumer_empty_stream_raises():
        from janito.openai_client.dashscope_stream import DashScopeStreamConsumer

        with pytest.raises(RuntimeError, match="no stream chunks"):
            DashScopeStreamConsumer().consume(_stream([]))

    def test_dashscope_legacy_chunk_bridge():
        from janito.openai_client import dashscope_stream as ds

        state = {
            "content": [],
            "reasoning": [],
            "tool_calls": {},
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "finish": False,
        }
        ds._consume_dashscope_chunk(
            _dashscope_chunk(content="hi", finish="stop"), state
        )
        assert state["content"] == ["hi"]
        assert state["finish"] is True

    # ---- module-level _consume_* delegate to the consumers ------------

    def test_module_consume_functions_delegate():
        """The tested module functions return what the consumers produce."""
        from janito.openai_client import anthropic_stream as ast
        from janito.openai_client import dashscope_stream as dst
        from janito.openai_client import responses_stream as rs

        events = [
            _Event("response.created", response=SimpleNamespace(id="r1")),
            _Event("response.output_text.delta", delta="via consumer"),
            _Event(
                "response.completed",
                response=SimpleNamespace(id="r1", usage=None),
            ),
        ]
        direct = rs.ResponsesStreamConsumer().consume(_stream(events))
        delegated = rs._consume_response_stream(_stream(events))
        assert delegated == direct

        anth_events = [_Event("message_stop")]
        assert ast._consume_stream(_stream(anth_events)) == (
            ast.AnthropicStreamConsumer().consume(_stream(anth_events))
        )

        chunks = [_dashscope_chunk(content="x", finish="stop")]
        assert dst._consume_stream(_stream(chunks)) == (
            dst.DashScopeStreamConsumer().consume(_stream(chunks))
        )

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                fn()
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
