"""
Tests for the native Anthropic SDK client (``janito.openai_client.anthropic_api``).

The stream-assembly logic is tested with fake SDK event objects
(``SimpleNamespace``) and the package guard is pinned down: ``send_prompt`` /
``_create_client`` must refuse to run with an actionable install message when
the ``anthropic`` package is missing. The guard tests are skipped when the
optional ``anthropic`` package *is* installed (the guard can't be exercised),
and run when it is not.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from janito.openai_client import anthropic_api

try:
    import anthropic  # noqa: F401

    _HAS_ANTHROPIC = True
except ModuleNotFoundError:
    _HAS_ANTHROPIC = False

# The "aborts without the package" guard tests only apply when the optional
# `anthropic` package is missing; skip them when it is installed.
requires_no_anthropic = pytest.mark.skipif(
    _HAS_ANTHROPIC, reason="anthropic package is installed (guard not exercised)"
)


def _event(type_, **attrs):
    """Build a fake Anthropic SDK stream event."""
    return SimpleNamespace(type=type_, **attrs)


if pytest is not None:

    def test_convert_tools_to_anthropic_format():
        """Chat Completions schemas (function nested) become Anthropic tools
        (name/description/input_schema at the top level)."""
        schemas = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file",
                    "parameters": {
                        "type": "object",
                        "properties": {"filepath": {"type": "string"}},
                        "required": ["filepath"],
                    },
                },
            }
        ]
        converted = anthropic_api._convert_tools_to_anthropic_format(schemas)
        assert converted == [
            {
                "name": "read_file",
                "description": "Read a file",
                "input_schema": {
                    "type": "object",
                    "properties": {"filepath": {"type": "string"}},
                    "required": ["filepath"],
                },
            }
        ]

    def test_consume_stream_assembles_text_and_tool_use():
        """Text deltas and tool_use blocks (assembled from input_json deltas)
        are collected; usage is summed from message_start/message_delta."""
        events = [
            _event(
                "message_start",
                message=SimpleNamespace(usage=SimpleNamespace(input_tokens=10)),
            ),
            _event(
                "content_block_start",
                index=0,
                content_block=SimpleNamespace(type="text"),
            ),
            _event(
                "content_block_delta",
                index=0,
                delta=SimpleNamespace(type="text_delta", text="Hello "),
            ),
            _event(
                "content_block_delta",
                index=0,
                delta=SimpleNamespace(type="text_delta", text="world"),
            ),
            _event("content_block_stop", index=0),
            _event(
                "content_block_start",
                index=1,
                content_block=SimpleNamespace(
                    type="tool_use", id="toolu_1", name="read_file"
                ),
            ),
            _event(
                "content_block_delta",
                index=1,
                delta=SimpleNamespace(
                    type="input_json_delta", partial_json='{"filepath": "'
                ),
            ),
            _event(
                "content_block_delta",
                index=1,
                delta=SimpleNamespace(type="input_json_delta", partial_json='a.txt"}'),
            ),
            _event("content_block_stop", index=1),
            _event(
                "message_delta",
                usage=SimpleNamespace(output_tokens=20),
                delta=SimpleNamespace(stop_reason="tool_use"),
            ),
            _event("message_stop"),
        ]

        full, reasoning, tool_blocks, usage, raw_attrs = anthropic_api._consume_stream(
            events
        )
        assert full == "Hello world"
        assert reasoning is None
        assert tool_blocks == [
            {"id": "toolu_1", "name": "read_file", "input": {"filepath": "a.txt"}}
        ]
        assert usage.total_tokens == 30
        assert usage.input_tokens == 10
        assert usage.output_tokens == 20

    def test_consume_stream_collects_thinking_as_reasoning():
        """thinking_delta blocks are surfaced as reasoning content."""
        events = [
            _event(
                "message_start",
                message=SimpleNamespace(usage=SimpleNamespace(input_tokens=5)),
            ),
            _event(
                "content_block_start",
                index=0,
                content_block=SimpleNamespace(type="thinking"),
            ),
            _event(
                "content_block_delta",
                index=0,
                delta=SimpleNamespace(
                    type="thinking_delta", thinking="Let me think..."
                ),
            ),
            _event("content_block_stop", index=0),
            _event(
                "content_block_start",
                index=1,
                content_block=SimpleNamespace(type="text"),
            ),
            _event(
                "content_block_delta",
                index=1,
                delta=SimpleNamespace(type="text_delta", text="Answer"),
            ),
            _event("content_block_stop", index=1),
            _event("message_stop"),
        ]

        full, reasoning, tool_blocks, usage, raw_attrs = anthropic_api._consume_stream(
            events
        )
        assert full == "Answer"
        assert reasoning == "Let me think..."
        assert tool_blocks == []
        assert usage is not None

    def test_consume_stream_empty_raises():
        """A stream with zero events fails loudly (never an empty answer)."""
        with pytest.raises(RuntimeError, match="no stream events"):
            anthropic_api._consume_stream([])

    def test_consume_stream_error_event_raises():
        """An error event surfaces the API's message."""
        events = [_event("error", error=SimpleNamespace(message="boom"))]
        with pytest.raises(RuntimeError, match="boom"):
            anthropic_api._consume_stream(events)

    @requires_no_anthropic
    def test_create_client_aborts_without_anthropic_package():
        """The optional `anthropic` package is guarded with an actionable error."""
        with pytest.raises(RuntimeError) as exc:
            anthropic_api._create_client("https://api.anthropic.com", "sk-test")
        assert "pip install anthropic" in str(exc.value)

    @requires_no_anthropic
    def test_send_prompt_aborts_without_anthropic_package(monkeypatch):
        """send_prompt refuses to run when the `anthropic` package is missing,
        even when the rest of the runtime config resolves."""
        monkeypatch.setattr(
            anthropic_api,
            "resolve_runtime_config",
            lambda *a, **k: ("https://api.anthropic.com", "sk-test", "claude-sonnet-5"),
        )
        with pytest.raises(RuntimeError) as exc:
            anthropic_api.send_prompt("hello")
        assert "pip install anthropic" in str(exc.value)

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                fn()
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
