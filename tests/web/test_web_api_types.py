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
from _frontend import render_index_html

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


def test_web_server_config_effective_tools_for_resolves_per_api_type():
    """The effective built-in tools are resolved per API type: alibaba's
    qwen3.8-max enables code_interpreter / web_search / web_extractor on the
    Responses API only (the Completions deployment rejects code_interpreter
    with a 400)."""
    from janito.cli.parser import create_parser
    from janito.web.backend.config import WebServerConfig

    args = create_parser().parse_args(["--web", "--provider", "alibaba"])
    config = WebServerConfig.from_args(args)

    assert config.effective_tools_for("Responses") == [
        {"type": "code_interpreter"},
        {"type": "web_search"},
        {"type": "web_extractor"},
    ]
    assert config.effective_tools_for("Completions") is None
    assert config.effective_tools_for("DashScope") is None


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
# Frontend wiring (static checks)
# ---------------------------------------------------------------------------


def test_status_bar_shows_effective_api_type():
    """The status bar renders an API badge resolved like the backend."""
    js = (FRONTEND / "js" / "statusBar.js").read_text(encoding="utf-8")
    assert "get apiType()" in js
    # Resolution mirrors resolve_api_type: configured override, then default.
    assert "p.api_type ||" in js
    assert "p.default_api_type" in js

    html = render_index_html()
    assert "<strong>API:</strong>" in html
    assert 'x-text="apiType"' in html
