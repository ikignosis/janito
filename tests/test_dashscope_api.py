"""
Tests for the native DashScope SDK client (``janito.dashscope_api``).

The ``dashscope`` package is **not** installed in the test environment, so the
stream-assembly logic is tested with fake SDK chunk objects (``SimpleNamespace``)
and the package guard is pinned down: ``send_prompt`` / ``_create_client`` must
refuse to run with an actionable install message when the package is missing.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from janito import dashscope_api


def _chunk(
    status_code=200,
    content="",
    reasoning="",
    tool_calls=None,
    finish_reason=None,
    usage=None,
    code="",
    message="",
):
    """Build a fake DashScope SDK streaming chunk.

    Mirrors the shape of the SDK's ``GenerationResponse``: a ``status_code``,
    an ``output`` with ``choices[0].message`` (content / reasoning_content /
    tool_calls) and ``finish_reason``, plus an optional ``usage``.
    """
    message_obj = SimpleNamespace(
        content=content,
        reasoning_content=reasoning,
        tool_calls=tool_calls or [],
    )
    choice = SimpleNamespace(
        finish_reason=finish_reason,
        message=message_obj,
    )
    return SimpleNamespace(
        status_code=status_code,
        output=SimpleNamespace(choices=[choice]),
        usage=usage,
        code=code,
        message=message,
        request_id="req-123",
    )


if pytest is not None:

    def test_consume_stream_assembles_text_and_usage():
        """Content deltas accumulate; usage is read from the chunks."""
        chunks = [
            _chunk(content="Hello ", finish_reason=None),
            _chunk(
                content="world",
                finish_reason="stop",
                usage=SimpleNamespace(
                    input_tokens=10, output_tokens=20, total_tokens=30
                ),
            ),
        ]
        full, reasoning, tool_blocks, usage = dashscope_api._consume_stream(chunks)
        assert full == "Hello world"
        assert reasoning is None
        assert tool_blocks == []
        assert usage.total_tokens == 30
        assert usage.input_tokens == 10
        assert usage.output_tokens == 20

    def test_consume_stream_collects_reasoning_content():
        """reasoning_content deltas are surfaced as reasoning text."""
        chunks = [
            _chunk(content="", reasoning="Let me think...", finish_reason=None),
            _chunk(content="", reasoning=" more.", finish_reason=None),
            _chunk(content="Answer", finish_reason="stop"),
        ]
        full, reasoning, tool_blocks, usage = dashscope_api._consume_stream(chunks)
        assert full == "Answer"
        assert reasoning == "Let me think... more."
        assert tool_blocks == []

    def test_consume_stream_collects_tool_calls():
        """tool_calls carried by a chunk are surfaced as id/name/arguments."""
        tool_calls = [
            {
                "id": "call_1",
                "function": {
                    "name": "read_file",
                    "arguments": '{"filepath": "a.txt"}',
                },
            }
        ]
        chunks = [
            _chunk(content="", tool_calls=tool_calls, finish_reason="tool_calls"),
            _chunk(content="Final answer", finish_reason="stop"),
        ]
        full, reasoning, tool_blocks, usage = dashscope_api._consume_stream(chunks)
        assert full == "Final answer"
        assert tool_blocks == [
            {"id": "call_1", "name": "read_file", "arguments": '{"filepath": "a.txt"}'}
        ]

    def test_consume_stream_error_chunk_raises():
        """A non-200 chunk surfaces the API's code/message."""
        chunks = [_chunk(status_code=400, code="InvalidParameter", message="boom")]
        with pytest.raises(RuntimeError, match="boom"):
            dashscope_api._consume_stream(chunks)

    def test_consume_stream_empty_raises():
        """A stream with zero chunks fails loudly (never an empty answer)."""
        with pytest.raises(RuntimeError, match="no stream chunks"):
            dashscope_api._consume_stream([])

    def test_consume_stream_cancel_short_circuits():
        """An Enter-to-cancel stop is not treated as an empty stream."""
        import threading

        cancel = threading.Event()
        cancel.set()
        chunks = [_chunk(content="partial")]
        full, reasoning, tool_blocks, usage = dashscope_api._consume_stream(
            chunks, cancel_event=cancel
        )
        assert full == ""
        assert tool_blocks == []
        # Cancel short-circuit must not raise the empty-stream error.

    def test_get_handles_dict_and_attribute_access():
        """_get reads both plain dicts and DictMixin-style objects."""
        assert dashscope_api._get({"a": 1}, "a") == 1
        assert dashscope_api._get(SimpleNamespace(a=1), "a") == 1
        assert dashscope_api._get(None, "a", "fallback") == "fallback"
        assert dashscope_api._get({"a": 1}, "missing") is None

    def test_create_client_aborts_without_dashscope_package(monkeypatch):
        """The optional `dashscope` package is guarded with an actionable error.

        ``find_spec`` is patched to simulate a missing package so the guard
        is exercised in environments where ``dashscope`` is installed too.
        """
        import importlib.util

        monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
        with pytest.raises(RuntimeError) as exc:
            dashscope_api._create_client(
                "https://dashscope-intl.aliyuncs.com/api/v1", "sk-test"
            )
        assert "pip install dashscope" in str(exc.value)

    def test_send_prompt_aborts_without_dashscope_package(monkeypatch):
        """send_prompt refuses to run when the `dashscope` package is missing,
        even when the rest of the runtime config resolves."""
        import importlib.util

        monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
        monkeypatch.setattr(
            dashscope_api,
            "resolve_runtime_config",
            lambda *a, **k: (
                "https://dashscope-intl.aliyuncs.com/api/v1",
                "sk-test",
                "qwen-plus",
            ),
        )
        with pytest.raises(RuntimeError) as exc:
            dashscope_api.send_prompt("hello")
        assert "pip install dashscope" in str(exc.value)

    def test_consume_stream_joins_multimodal_content():
        """Multimodal content (list of {"text": ...} items) is joined as text."""
        chunks = [
            _chunk(content=[{"text": "Hello "}], finish_reason=None),
            _chunk(content=[{"text": "world"}], finish_reason="stop"),
        ]
        full, reasoning, tool_blocks, usage = dashscope_api._consume_stream(chunks)
        assert full == "Hello world"

    def test_consume_stream_accumulates_tool_call_arguments():
        """Tool-call arguments split across chunks are accumulated by index."""
        chunks = [
            _chunk(
                content="",
                tool_calls=[
                    {
                        "index": 0,
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "get_weather", "arguments": '{"city": '},
                    }
                ],
                finish_reason=None,
            ),
            _chunk(
                content="",
                tool_calls=[
                    {
                        "index": 0,
                        "id": "",
                        "type": "function",
                        "function": {"arguments": '"Lisbon"}'},
                    }
                ],
                finish_reason="tool_calls",
            ),
            _chunk(content="Final", finish_reason="stop"),
        ]
        full, reasoning, tool_blocks, usage = dashscope_api._consume_stream(chunks)
        assert full == "Final"
        assert tool_blocks == [
            {"id": "call_1", "name": "get_weather", "arguments": '{"city": "Lisbon"}'}
        ]

    def test_consume_stream_url_error_raises_endpoint_mismatch():
        """A url-error chunk (model/endpoint mismatch) raises _ModelEndpointMismatch."""
        chunks = [
            _chunk(
                status_code=400,
                code="InvalidParameter",
                message="url error, please check url!",
            )
        ]
        with pytest.raises(dashscope_api._ModelEndpointMismatch):
            dashscope_api._consume_stream(chunks)

    def test_is_multimodal_model():
        """Multimodal models are detected; plain-text models are not."""
        assert dashscope_api._is_multimodal_model("qwen3.8-max")
        assert dashscope_api._is_multimodal_model("qwen3.6-plus")
        assert dashscope_api._is_multimodal_model("qwen3.7-plus")
        assert dashscope_api._is_multimodal_model("qwen3-vl-plus")
        assert dashscope_api._is_multimodal_model("qwen-omni-turbo")
        assert not dashscope_api._is_multimodal_model("qwen3.7-max")
        assert not dashscope_api._is_multimodal_model("qwen3-max")
        assert not dashscope_api._is_multimodal_model("qwen-plus")
        assert not dashscope_api._is_multimodal_model("qwen-flash")
        assert not dashscope_api._is_multimodal_model("")

    def test_to_multimodal_messages_wraps_string_content():
        """String content is wrapped into [{"text": ...}] for the multimodal API."""
        messages = [
            {"role": "system", "content": "be terse"},
            {"role": "user", "content": "hi"},
            {"role": "tool", "content": "ok", "tool_call_id": "call_1"},
        ]
        converted = dashscope_api._to_multimodal_messages(messages)
        assert converted == [
            {"role": "system", "content": [{"text": "be terse"}]},
            {"role": "user", "content": [{"text": "hi"}]},
            {"role": "tool", "content": [{"text": "ok"}], "tool_call_id": "call_1"},
        ]
        # The original messages are not mutated.
        assert messages[0]["content"] == "be terse"

    def _install_fake_dashscope(monkeypatch, streams):
        """Install a fake ``dashscope`` module and record call kwargs.

        ``streams`` maps API class name ("Generation" / "MultiModalConversation")
        to the stream (or callable returning one) its ``call`` should return.
        Returns the list of ``(class_name, kwargs)`` calls.
        """
        fake = type(sys)("dashscope")
        calls = []

        def make_call(name):
            target = streams[name]

            def call(**kwargs):
                calls.append((name, kwargs))
                if callable(target) and not isinstance(target, (list, tuple)):
                    return target(**kwargs)
                return target

            return staticmethod(call)

        fake.Generation = type("Generation", (), {"call": make_call("Generation")})
        fake.MultiModalConversation = type(
            "MultiModalConversation",
            (),
            {"call": make_call("MultiModalConversation")},
        )
        monkeypatch.setitem(sys.modules, "dashscope", fake)
        return calls

    def test_stream_response_routes_multimodal_model(monkeypatch):
        """A multimodal model goes to MultiModalConversation with wrapped content."""
        stop = _chunk(content=[{"text": "hi"}], finish_reason="stop")
        calls = _install_fake_dashscope(
            monkeypatch,
            {"Generation": [], "MultiModalConversation": [stop]},
        )
        client = SimpleNamespace(api_key="sk-test")
        call_kwargs = {
            "model": "qwen3.8-max",
            "messages": [{"role": "user", "content": "hi"}],
        }
        full, reasoning, tool_blocks, usage = dashscope_api._stream_response(
            client, call_kwargs, []
        )
        assert full == "hi"
        assert [name for name, _ in calls] == ["MultiModalConversation"]
        assert calls[0][1]["messages"] == [
            {"role": "user", "content": [{"text": "hi"}]}
        ]

    def test_stream_response_text_model_uses_generation(monkeypatch):
        """A plain-text model goes to Generation with untouched messages."""
        stop = _chunk(content="hello", finish_reason="stop")
        calls = _install_fake_dashscope(
            monkeypatch,
            {"Generation": [stop], "MultiModalConversation": []},
        )
        client = SimpleNamespace(api_key="sk-test")
        call_kwargs = {
            "model": "qwen-plus",
            "messages": [{"role": "user", "content": "hi"}],
        }
        full, reasoning, tool_blocks, usage = dashscope_api._stream_response(
            client, call_kwargs, []
        )
        assert full == "hello"
        assert [name for name, _ in calls] == ["Generation"]
        assert calls[0][1]["messages"] == [{"role": "user", "content": "hi"}]

    def test_stream_response_retries_other_endpoint_on_url_error(monkeypatch):
        """A url-error rejection retries once on the other generation endpoint."""
        err = _chunk(
            status_code=400,
            code="InvalidParameter",
            message="url error, please check url!",
        )
        ok = _chunk(content=[{"text": "recovered"}], finish_reason="stop")
        calls = _install_fake_dashscope(
            monkeypatch,
            {"Generation": [err], "MultiModalConversation": [ok]},
        )
        client = SimpleNamespace(api_key="sk-test")
        # qwen-plus is classified as text -> Generation is tried first and
        # rejected, then the call is retried on MultiModalConversation.
        call_kwargs = {
            "model": "qwen-plus",
            "messages": [{"role": "user", "content": "hi"}],
        }
        full, reasoning, tool_blocks, usage = dashscope_api._stream_response(
            client, call_kwargs, []
        )
        assert full == "recovered"
        assert [name for name, _ in calls] == ["Generation", "MultiModalConversation"]

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                fn()
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
