"""
Tests for the StreamConsumer classes (janito.openai_client.*_stream).

The four stream modules implement their assembly logic in consumer
classes with instance-attribute state:

- ``ResponsesStreamConsumer`` (responses_stream)
- ``CompletionsStreamConsumer`` (completions_stream)
- ``AnthropicStreamConsumer`` (anthropic_stream)
- ``DashScopeStreamConsumer`` (dashscope_stream)

The module-level ``_consume_*`` functions delegate to them; behavioural
equivalence is covered by the client tests (``test_conversations_api`` /
``test_anthropic_api`` / ``test_dashscope_api``), which call the module
functions.  These tests pin the class-only behaviours those client tests
do not reach: raw top-level attribute capture (used by the verbose API
dump), the cancel-event short-circuit, and the Completions-specific
error/usage-only/tool-call-delta handling (including Gemini's
``extra_content`` replay).
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

    def test_responses_consumer_captures_raw_attrs():
        """The Response object's scalar top-level attributes are kept raw."""
        from janito.openai_client.responses_stream import ResponsesStreamConsumer

        c = ResponsesStreamConsumer()
        c.handle_event(
            _Event(
                "response.created",
                response=SimpleNamespace(
                    id="r1", model="gpt-4o", created_at=1720000000, status="in_progress"
                ),
            )
        )
        c.handle_event(
            _Event(
                "response.completed",
                response=SimpleNamespace(
                    id="r1",
                    model="gpt-4o",
                    created_at=1720000000,
                    status="completed",
                    usage=None,
                ),
            )
        )
        # status from the completed event wins; output/usage are not captured.
        assert c.raw_attrs["id"] == "r1"
        assert c.raw_attrs["model"] == "gpt-4o"
        assert c.raw_attrs["created_at"] == 1720000000
        assert c.raw_attrs["status"] == "completed"
        assert "output" not in c.raw_attrs
        assert "usage" not in c.raw_attrs

    def test_responses_consumer_consume_cancel_short_circuits():
        from janito.openai_client.responses_stream import ResponsesStreamConsumer

        cancel = threading.Event()
        cancel.set()

        def events():
            if False:
                yield None  # pragma: no cover - keeps this a generator

        c = ResponsesStreamConsumer()
        content, reasoning, tools, usage, response_id, raw_attrs = c.consume(
            events(), cancel_event=cancel
        )
        # Cancel short-circuit must not raise the empty-stream error.
        assert content == ""
        assert tools == []
        assert response_id is None
        assert raw_attrs == {}

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

    def test_completions_consumer_captures_raw_attrs():
        """Top-level chunk metadata + finish_reason are kept raw."""
        from janito.openai_client.completions_stream import CompletionsStreamConsumer

        class _Delta:
            def __init__(self, content=None):
                self.content = content
                self.reasoning_content = None
                self.tool_calls = None

        class _Chunk:
            def __init__(self, delta, finish_reason=None, **attrs):
                self.choices = [
                    SimpleNamespace(delta=delta, finish_reason=finish_reason)
                ]
                self.usage = None
                for name, value in attrs.items():
                    setattr(self, name, value)

        c = CompletionsStreamConsumer()
        c.handle(
            _Chunk(
                _Delta(content="hi"),
                id="chatcmpl-1",
                model="gpt-4o",
                created=1720000000,
                system_fingerprint="fp_abc",
            )
        )
        c.handle(_Chunk(_Delta(content=" world"), finish_reason="stop"))
        # Scalar top-level attributes are captured; choices/usage are not.
        assert c.raw_attrs["id"] == "chatcmpl-1"
        assert c.raw_attrs["model"] == "gpt-4o"
        assert c.raw_attrs["created"] == 1720000000
        assert c.raw_attrs["system_fingerprint"] == "fp_abc"
        assert c.raw_attrs["finish_reason"] == "stop"
        assert "choices" not in c.raw_attrs
        assert "usage" not in c.raw_attrs

    def test_completions_consumer_surfaces_api_error_chunks():
        """A chunk with no choices but code/message must raise, not be silent.

        Some OpenAI-compatible providers (e.g. Alibaba DashScope) reject a
        request in-band: a single ChatCompletionChunk with empty ``choices``
        carrying ``code``/``message`` instead of an HTTP error.  Without the
        guard the turn would end with an empty response and no error output.
        """
        from janito.openai_client.completions_stream import CompletionsStreamConsumer

        class _ErrorChunk:
            choices = []
            usage = None
            code = "Not Found"
            message = "Not support"

        c = CompletionsStreamConsumer()
        with pytest.raises(RuntimeError, match="Not Found: Not support"):
            c.handle(_ErrorChunk())

    def test_completions_consumer_skips_usage_only_chunks():
        """A usage-only final chunk (no choices, no error) is not an error."""
        from janito.openai_client.completions_stream import CompletionsStreamConsumer

        class _UsageChunk:
            choices = []
            usage = SimpleNamespace(total_tokens=42)

        c = CompletionsStreamConsumer()
        c.handle(_UsageChunk())
        assert c.usage_info.total_tokens == 42
        assert c.full_content == ""

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

    def test_completions_consumer_preserves_extra_content():
        """Provider extras (Gemini thought_signature) survive the fold + list.

        Gemini 3.x attaches the thought signature to each function call as
        ``extra_content.google.thought_signature``; the accumulator must keep
        it and replay it on ``tool_calls_list`` so the follow-up request is
        not rejected with a 400 "missing thought_signature" error.
        """
        from janito.openai_client.completions_stream import CompletionsStreamConsumer

        c = CompletionsStreamConsumer()
        extra = {"google": {"thought_signature": "SIG-12345"}}

        class _Fn:
            name = "FindFiles"
            arguments = '{"paths": "."}'

        class _TC:
            index = 2
            id = "call_1"
            function = _Fn()
            extra_content = extra

        c.handle_tool_call_delta(_TC())
        assert c.tool_calls[2]["extra_content"] == extra
        assert c.tool_calls_list() == [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "FindFiles", "arguments": '{"paths": "."}'},
                "extra_content": extra,
            }
        ]

    def test_completions_consumer_list_omits_extra_content_when_absent():
        """Tool calls without provider extras keep the plain OpenAI shape."""
        from janito.openai_client.completions_stream import CompletionsStreamConsumer

        c = CompletionsStreamConsumer()

        class _Fn:
            name = "FindFiles"
            arguments = "{}"

        class _TC:
            index = 0
            id = "call_1"
            function = _Fn()

        c.handle_tool_call_delta(_TC())
        assert c.tool_calls_list() == [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "FindFiles", "arguments": "{}"},
            }
        ]

    # ---- AnthropicStreamConsumer --------------------------------------

    def test_anthropic_consumer_captures_raw_attrs():
        """Message metadata (id/model/role) + stop_reason are kept raw."""
        from janito.openai_client.anthropic_stream import AnthropicStreamConsumer

        c = AnthropicStreamConsumer()
        c.handle_event(
            _Event(
                "message_start",
                message=SimpleNamespace(
                    id="msg_1",
                    model="claude-3-5-sonnet",
                    role="assistant",
                    usage=SimpleNamespace(input_tokens=10),
                ),
            )
        )
        c.handle_event(
            _Event(
                "message_delta",
                usage=SimpleNamespace(output_tokens=20),
                delta=SimpleNamespace(stop_reason="end_turn"),
            )
        )
        # Scalar message metadata is captured; content/usage are not.
        assert c.raw_attrs["id"] == "msg_1"
        assert c.raw_attrs["model"] == "claude-3-5-sonnet"
        assert c.raw_attrs["role"] == "assistant"
        assert c.raw_attrs["stop_reason"] == "end_turn"
        assert "content" not in c.raw_attrs
        assert "usage" not in c.raw_attrs

    # ---- DashScopeStreamConsumer --------------------------------------

    def test_dashscope_consumer_captures_raw_attrs():
        """Top-level chunk metadata (request_id/status_code) + finish_reason kept raw."""
        from janito.openai_client.dashscope_stream import DashScopeStreamConsumer

        message = SimpleNamespace(content="hi", reasoning_content="", tool_calls=[])
        choice = SimpleNamespace(finish_reason="stop", message=message)
        chunk = SimpleNamespace(
            status_code=200,
            request_id="req_123",
            output=SimpleNamespace(choices=[choice]),
            usage=None,
        )
        c = DashScopeStreamConsumer()
        c.handle_chunk(chunk)
        assert c.raw_attrs["request_id"] == "req_123"
        assert c.raw_attrs["status_code"] == 200
        assert c.raw_attrs["finish_reason"] == "stop"
        assert "output" not in c.raw_attrs
        assert "usage" not in c.raw_attrs
