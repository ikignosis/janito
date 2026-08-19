"""
Tests for the native Gemini SDK client (``janito.gemini_api``).

The stream-assembly logic is tested with fake SDK chunk objects
(``SimpleNamespace`` mirroring ``GenerateContentResponse`` /
``Candidate`` / ``Part``) and the package guard is pinned down:
``send_prompt`` / ``_create_client`` must refuse to run with an actionable
install message when the ``google-genai`` package is missing.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from janito import gemini_api

try:
    import google.genai  # noqa: F401

    _HAS_GENAI = True
except ModuleNotFoundError:
    _HAS_GENAI = False

requires_genai = pytest.mark.skipif(
    not _HAS_GENAI, reason="google-genai package is not installed"
)


def _part(*, text=None, thought=False, thought_signature=None, function_call=None):
    """Build a fake Gemini ``Part``."""
    return SimpleNamespace(
        text=text,
        thought=thought,
        thought_signature=thought_signature,
        function_call=function_call,
    )


def _function_call(call_id="", name="", args=None, will_continue=False):
    """Build a fake Gemini ``FunctionCall``."""
    return SimpleNamespace(
        id=call_id, name=name, args=args or {}, will_continue=will_continue
    )


def _chunk(parts, finish_reason=None, usage=None, model_version=None):
    """Build a fake Gemini ``GenerateContentResponse`` stream chunk."""
    candidate = SimpleNamespace(
        content=SimpleNamespace(parts=parts), finish_reason=finish_reason
    )
    return SimpleNamespace(
        candidates=[candidate],
        usage_metadata=usage,
        model_version=model_version,
    )


if pytest is not None:

    def test_consume_stream_assembles_text_and_usage():
        """Text deltas accumulate; usage is read from the final chunk."""
        chunks = [
            _chunk([_part(text="Hello ")], finish_reason=None),
            _chunk(
                [_part(text="world")],
                finish_reason=SimpleNamespace(name="STOP"),
                usage=SimpleNamespace(
                    prompt_token_count=10, response_token_count=20, total_token_count=30
                ),
            ),
        ]
        (
            full,
            reasoning,
            tool_calls,
            usage,
            raw_attrs,
            thought_parts,
        ) = gemini_api._consume_stream(chunks)
        assert full == "Hello world"
        assert reasoning is None
        assert tool_calls == []
        assert thought_parts == []
        assert usage.total_tokens == 30
        assert usage.input_tokens == 10
        assert usage.output_tokens == 20
        assert raw_attrs["finish_reason"] == "STOP"

    def test_consume_stream_collects_thought_parts():
        """Thought parts are surfaced as reasoning text and kept verbatim."""
        chunks = [
            _chunk(
                [_part(text="Let me think", thought=True, thought_signature="sig-1")],
                finish_reason=None,
            ),
            _chunk([_part(text="Answer")], finish_reason=SimpleNamespace(name="STOP")),
        ]
        (
            full,
            reasoning,
            tool_calls,
            usage,
            raw_attrs,
            thought_parts,
        ) = gemini_api._consume_stream(chunks)
        assert full == "Answer"
        assert reasoning == "Let me think"
        assert thought_parts == [{"text": "Let me think", "thought_signature": "sig-1"}]

    def test_consume_stream_thought_parts_do_not_leak_into_content():
        """Thought text is displayed as reasoning, never as answer content."""
        chunks = [
            _chunk([_part(text="Hidden", thought=True)], finish_reason=None),
            _chunk([_part(text="Visible")], finish_reason=SimpleNamespace(name="STOP")),
        ]
        (
            full,
            reasoning,
            tool_calls,
            usage,
            raw_attrs,
            thought_parts,
        ) = gemini_api._consume_stream(chunks)
        assert full == "Visible"
        assert reasoning == "Hidden"

    def test_consume_stream_collects_function_calls():
        """function_call parts surface as id/name/arguments (+ signature)."""
        chunks = [
            _chunk(
                [
                    _part(
                        function_call=_function_call(
                            "fc_1", "read_file", {"filepath": "a.txt"}
                        ),
                        thought_signature="sig-2",
                    )
                ],
                finish_reason=None,
            ),
            _chunk(
                [_part(text="Final answer")],
                finish_reason=SimpleNamespace(name="STOP"),
            ),
        ]
        (
            full,
            reasoning,
            tool_calls,
            usage,
            raw_attrs,
            thought_parts,
        ) = gemini_api._consume_stream(chunks)
        assert full == "Final answer"
        assert tool_calls == [
            {
                "id": "fc_1",
                "name": "read_file",
                "arguments": '{"filepath": "a.txt"}',
                "thought_signature": "sig-2",
            }
        ]

    def test_consume_stream_accumulates_partial_args_dicts():
        """Function-call args split across chunks are merged per call id."""
        chunks = [
            _chunk(
                [
                    _part(
                        function_call=_function_call(
                            "fc_1", "get_weather", {"city": "Lisbon"}
                        )
                    )
                ],
                finish_reason=None,
            ),
            _chunk(
                [
                    _part(
                        function_call=_function_call(
                            "fc_1", "get_weather", {"unit": "C"}
                        )
                    )
                ],
                finish_reason=SimpleNamespace(name="STOP"),
            ),
        ]
        (
            full,
            reasoning,
            tool_calls,
            usage,
            raw_attrs,
            thought_parts,
        ) = gemini_api._consume_stream(chunks)
        assert tool_calls == [
            {
                "id": "fc_1",
                "name": "get_weather",
                "arguments": '{"city": "Lisbon", "unit": "C"}',
            }
        ]

    def test_consume_stream_empty_raises():
        """A stream with zero chunks fails loudly (never an empty answer)."""
        with pytest.raises(RuntimeError, match="no stream chunks"):
            gemini_api._consume_stream([])

    def test_create_client_aborts_without_google_genai_package(monkeypatch):
        """The optional `google-genai` package is guarded with an actionable
        error (find_spec patched to simulate a missing package)."""
        import importlib.util

        monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
        with pytest.raises(RuntimeError) as exc:
            gemini_api._create_client(
                "https://generativelanguage.googleapis.com", "sk-test"
            )
        assert "pip install google-genai" in str(exc.value)

    def test_send_prompt_aborts_without_google_genai_package(monkeypatch):
        """send_prompt refuses to run when the `google-genai` package is
        missing, even when the rest of the runtime config resolves."""
        import importlib.util

        monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
        monkeypatch.setattr(
            gemini_api,
            "resolve_runtime_config",
            lambda *a, **k: (
                "https://generativelanguage.googleapis.com",
                "sk-test",
                "gemini-3.7-flash",
            ),
        )
        with pytest.raises(RuntimeError) as exc:
            gemini_api.send_prompt("hello")
        assert "pip install google-genai" in str(exc.value)

    @requires_genai
    def test_create_client_builds_sdk_client_with_base_url():
        """With google-genai installed, _create_client returns a genai.Client
        carrying the resolved base URL and API key."""
        client = gemini_api._create_client(
            "https://generativelanguage.googleapis.com", "sk-test"
        )
        assert client._api_client._http_options.base_url == (
            "https://generativelanguage.googleapis.com"
        )

    def test_gemini_client_resolves_native_api_type(monkeypatch):
        """The Gemini client resolves the runtime config with the native
        "Gemini" API type so the endpoint_by_api_type map is honored."""
        calls = {}

        def fake_resolve(cli_model, cli_provider, cli_api_type=None):
            calls["api_type"] = cli_api_type
            return (
                "https://generativelanguage.googleapis.com",
                "sk-test",
                "gemini-3.7-flash",
            )

        monkeypatch.setattr(gemini_api, "resolve_runtime_config", fake_resolve)
        client = gemini_api.GeminiClient(cli_model=None, cli_provider="google")
        base_url, api_key, model = client._resolve_runtime_config()
        assert calls["api_type"] == "Gemini"
        assert base_url == "https://generativelanguage.googleapis.com"
        assert model == "gemini-3.7-flash"

    def test_gemini_helpers_build_call_kwargs_sends_config():
        """The CLI Gemini path sends system_instruction, max_output_tokens,
        thinking_config.thinking_level and function_declarations."""
        from janito.gemini_helpers import _build_call_kwargs

        schemas = [
            {
                "type": "function",
                "function": {
                    "name": "ReadFile",
                    "description": "Read a file",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        kwargs = _build_call_kwargs(
            "gemini-3.7-flash",
            [{"role": "user", "content": "hi"}],
            65536,
            "Be terse",
            "high",
            schemas,
        )
        assert kwargs["model"] == "gemini-3.7-flash"
        assert kwargs["contents"] == [{"role": "user", "parts": [{"text": "hi"}]}]
        config = kwargs["config"]
        assert config["system_instruction"] == "Be terse"
        assert config["max_output_tokens"] == 65536
        assert config["thinking_config"] == {"thinking_level": "high"}
        assert config["tools"] == [
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

    def test_gemini_helpers_build_call_kwargs_omits_tools_when_none():
        """No tools -> the request carries no tools key."""
        from janito.gemini_helpers import _build_call_kwargs

        kwargs = _build_call_kwargs(
            "gemini-3.7-flash",
            [{"role": "user", "content": "hi"}],
            1000,
            None,
            None,
            None,
        )
        assert "tools" not in kwargs["config"]
        assert "thinking_config" not in kwargs["config"]
        assert "system_instruction" not in kwargs["config"]

    def test_gemini_helpers_builtin_tools_are_not_function_tools():
        """Built-in (native) tools (code_interpreter / web_search) are not
        converted to function_declarations -- they are model capabilities,
        not function tools."""
        from janito.gemini_helpers import _convert_tools_to_gemini_format

        assert (
            _convert_tools_to_gemini_format(
                [{"type": "code_interpreter"}, {"type": "web_search"}]
            )
            is None
        )

    def test_gemini_helpers_messages_to_contents_roundtrip():
        """OpenAI-format history converts to Gemini contents, keeping the
        model's thought blocks and per-call signatures verbatim."""
        from janito.gemini_helpers import _messages_to_contents

        messages = [
            {"role": "system", "content": "Be terse"},
            {"role": "user", "content": "hi"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "f", "arguments": '{"x":1}'},
                        "thought_signature": "sig-3",
                    }
                ],
                "thought_parts": [{"text": "thinking", "thought_signature": "sig-3"}],
            },
            {
                "role": "tool",
                "tool_call_id": "c1",
                "name": "f",
                "content": '{"ok": true}',
            },
            {"role": "assistant", "content": "done"},
        ]
        contents = _messages_to_contents(messages)
        assert contents == [
            {"role": "user", "parts": [{"text": "hi"}]},
            {
                "role": "model",
                "parts": [
                    {"text": "thinking", "thought_signature": "sig-3"},
                    {
                        "function_call": {"id": "c1", "name": "f", "args": {"x": 1}},
                        "thought_signature": "sig-3",
                    },
                ],
            },
            {
                "role": "user",
                "parts": [
                    {
                        "function_response": {
                            "id": "c1",
                            "name": "f",
                            "response": {"ok": True},
                        }
                    }
                ],
            },
            {"role": "model", "parts": [{"text": "done"}]},
        ]

    def test_gemini_helpers_messages_to_contents_wraps_non_json_tool_results():
        """Plain-text / non-object tool results are wrapped under a ``result``
        key: Gemini's ``function_response.response`` must be a JSON object and
        the google-genai SDK rejects raw strings (e.g. the ``extra_forbidden``
        ``Part.role``/``Part.parts`` validation error)."""
        from janito.gemini_helpers import _messages_to_contents

        messages = [
            {"role": "user", "content": "get details for library-skills"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {
                            "name": "load_skill",
                            "arguments": '{"skill_name": "library-skills"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "c1",
                "name": "load_skill",
                "content": "# library-skills\n\n---\nsome markdown",
            },
            {"role": "tool", "tool_call_id": "c2", "name": "f", "content": "[1, 2, 3]"},
            {"role": "tool", "tool_call_id": "c3", "name": "f", "content": "hello"},
        ]
        contents = _messages_to_contents(messages)
        responses = [
            p["function_response"]["response"]
            for c in contents
            if c["role"] == "user"
            for p in c["parts"]
            if "function_response" in p
        ]
        # Plain text (markdown / free-form) and JSON lists are wrapped so the
        # SDK's FunctionResponse.response (a JSON object) validates.
        assert responses == [
            {"result": "# library-skills\n\n---\nsome markdown"},
            {"result": [1, 2, 3]},
            {"result": "hello"},
        ]

    def test_gemini_helpers_messages_to_contents_keeps_object_tool_results():
        """JSON-object tool results stay structured (not wrapped)."""
        from janito.gemini_helpers import _messages_to_contents

        messages = [
            {
                "role": "tool",
                "tool_call_id": "c1",
                "name": "f",
                "content": '{"ok": true, "value": 1}',
            },
        ]
        contents = _messages_to_contents(messages)
        assert contents[0]["parts"][0]["function_response"]["response"] == {
            "ok": True,
            "value": 1,
        }

    def test_gemini_helpers_handle_tool_parts_records_history():
        """Tool calls are recorded with their signatures and the results are
        appended as tool-role messages."""
        from janito.gemini_helpers import _handle_tool_parts

        calls = []

        class _Executor:
            def execute_tool_call(self, adapted_call):
                calls.append(adapted_call)
                return {"content": '{"ok": true}'}

        messages = [{"role": "user", "content": "hi"}]
        _handle_tool_parts(
            [
                {
                    "id": "fc_1",
                    "name": "read_file",
                    "arguments": '{"filepath": "a.txt"}',
                    "thought_signature": "sig-4",
                }
            ],
            "",
            "thinking",
            [{"text": "thinking", "thought_signature": "sig-4"}],
            messages,
            _Executor(),
        )
        assert messages[1] == {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "fc_1",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": '{"filepath": "a.txt"}',
                    },
                    "thought_signature": "sig-4",
                }
            ],
            "reasoning_content": "thinking",
            "thought_parts": [{"text": "thinking", "thought_signature": "sig-4"}],
        }
        assert messages[2] == {
            "role": "tool",
            "content": '{"ok": true}',
            "tool_call_id": "fc_1",
            "name": "read_file",
            "thought_signature": "sig-4",
        }
        assert calls[0]["function"]["name"] == "read_file"

    def test_stream_response_drives_generate_content_stream(monkeypatch):
        """_stream_response opens generate_content_stream and assembles the
        response parts from the streamed chunks."""
        stop = _chunk([_part(text="hello")], finish_reason=SimpleNamespace(name="STOP"))
        calls = []

        class _FakeModels:
            def generate_content_stream(self, **kwargs):
                calls.append(kwargs)
                return iter([stop])

        class _FakeClient:
            def __init__(self):
                self.models = _FakeModels()

        client = _FakeClient()
        call_kwargs = {
            "model": "gemini-3.7-flash",
            "contents": [{"role": "user", "parts": [{"text": "hi"}]}],
            "config": {"max_output_tokens": 1000},
        }
        (
            full,
            reasoning,
            tool_calls,
            usage,
            raw_attrs,
            thought_parts,
        ) = gemini_api._stream_response(client, call_kwargs, [])
        assert full == "hello"
        assert calls == [call_kwargs]

    def test_stream_response_attaches_function_tools(monkeypatch):
        """_stream_response appends the resolved function-declaration tools to
        config.tools: without them the Gemini API receives no function
        declarations and the model emits MALFORMED_FUNCTION_CALL (empty
        answer)."""
        stop = _chunk(
            [
                _part(
                    function_call=_function_call("c1", "ListFiles", {"directory": "."})
                )
            ],
            finish_reason=SimpleNamespace(name="STOP"),
        )
        calls = []

        class _FakeModels:
            def generate_content_stream(self, **kwargs):
                calls.append(kwargs)
                return iter([stop])

        class _FakeClient:
            def __init__(self):
                self.models = _FakeModels()

        client = _FakeClient()
        call_kwargs = {
            "model": "gemini-3.7-flash",
            "contents": [{"role": "user", "parts": [{"text": "list files"}]}],
            "config": {"max_output_tokens": 1000},
        }
        tools_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "ListFiles",
                    "description": "List files",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        (
            full,
            reasoning,
            tool_calls,
            usage,
            raw_attrs,
            thought_parts,
        ) = gemini_api._stream_response(client, call_kwargs, tools_schemas)
        assert tool_calls[0]["name"] == "ListFiles"
        assert len(calls) == 1
        sent = calls[0]
        assert sent["config"]["tools"] == [
            {
                "function_declarations": [
                    {
                        "name": "ListFiles",
                        "description": "List files",
                        "parameters": {"type": "object", "properties": {}},
                    }
                ]
            }
        ]
        # The caller's dict is not mutated.
        assert "tools" not in call_kwargs["config"]

    def test_stream_response_does_not_duplicate_existing_tools(monkeypatch):
        """When config.tools already declares function_declarations (the web
        agent's build_call_kwargs converts them up front), _stream_response
        does not append them a second time."""
        stop = _chunk([_part(text="done")], finish_reason=SimpleNamespace(name="STOP"))
        calls = []

        class _FakeModels:
            def generate_content_stream(self, **kwargs):
                calls.append(kwargs)
                return iter([stop])

        class _FakeClient:
            def __init__(self):
                self.models = _FakeModels()

        client = _FakeClient()
        existing = [
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
        call_kwargs = {
            "model": "gemini-3.7-flash",
            "contents": [{"role": "user", "parts": [{"text": "hi"}]}],
            "config": {"max_output_tokens": 1000, "tools": existing},
        }
        gemini_api._stream_response(client, call_kwargs, existing)
        assert calls[0]["config"]["tools"] == existing

    def test_stream_response_merges_native_and_function_tools(monkeypatch):
        """Provider native tools (e.g. google_search) already in config.tools
        are kept and the function declarations are appended alongside them."""
        stop = _chunk([_part(text="done")], finish_reason=SimpleNamespace(name="STOP"))
        calls = []

        class _FakeModels:
            def generate_content_stream(self, **kwargs):
                calls.append(kwargs)
                return iter([stop])

        class _FakeClient:
            def __init__(self):
                self.models = _FakeModels()

        client = _FakeClient()
        call_kwargs = {
            "model": "gemini-3.7-flash",
            "contents": [{"role": "user", "parts": [{"text": "hi"}]}],
            "config": {"max_output_tokens": 1000, "tools": [{"google_search": {}}]},
        }
        tools_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "ReadFile",
                    "description": "Read a file",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
        gemini_api._stream_response(client, call_kwargs, tools_schemas)
        sent = calls[0]["config"]["tools"]
        assert sent[0] == {"google_search": {}}
        assert sent[1]["function_declarations"][0]["name"] == "ReadFile"

    def test_stream_response_ignores_empty_candidate_chunks():
        """Chunks without candidates are folded without error."""
        empty = SimpleNamespace(candidates=None, usage_metadata=None)
        (
            full,
            reasoning,
            tool_calls,
            usage,
            raw_attrs,
            thought_parts,
        ) = gemini_api._consume_stream([empty, _chunk([_part(text="hi")], None)])
        assert full == "hi"

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                fn()
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
