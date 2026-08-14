"""
Tests for reasoning-level support in the OpenAI-compatible API calls.

Covers:
- ``send_prompt`` resolving the reasoning level (CLI arg > per-provider config
  > built-in ``PROVIDER_INFO`` default) and sending it as ``reasoning_effort``.
- The web agent's ``build_call_kwargs`` forwarding ``reasoning_effort``.
- The CLI ``--reasoning-level`` flag parsing.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import janito.config_dir as config_dir_mod
import janito.openai_client.completions_api as client_mod
from janito.web.backend.agent.call import build_call_kwargs


@pytest.fixture(autouse=True)
def _isolate_config_dir(monkeypatch, tmp_path):
    """Point the config directory at a temp dir for every test.

    ``send_prompt`` resolves the reasoning level from the per-provider config
    (``<provider>.reasoning-level``), which lives in the real ``~/.janito`` by
    default. Without this fixture tests would read/write the developer's actual
    config, making them order- and environment-dependent.
    """
    monkeypatch.setattr(config_dir_mod, "_config_dir", tmp_path)


def _fake_run_returns(content, reasoning=None, tool_calls=None, usage=None):
    """Capture the call kwargs and return a canned streaming result."""

    def fake_run(func, client, call_kwargs, tools_schemas):
        fake_run.captured_kwargs = call_kwargs
        return content, reasoning, tool_calls or {}, usage

    fake_run.captured_kwargs = None
    return fake_run


if pytest is not None:

    def test_send_prompt_passes_builtin_default_reasoning_effort(monkeypatch):
        """Alibaba's built-in default (xhigh) is sent as reasoning_effort."""
        fake_run = _fake_run_returns("hi")
        monkeypatch.setattr(
            client_mod,
            "resolve_runtime_config",
            lambda *a, **k: (None, "sk-test", "qwen3.8-max"),
        )
        monkeypatch.setattr(client_mod, "_run_with_progress_bar", fake_run)
        result = client_mod.send_prompt("hello", use_mcp=False, cli_provider="alibaba")
        assert result == "hi"
        assert fake_run.captured_kwargs["reasoning_effort"] == "xhigh"

    def test_send_prompt_cli_reasoning_level_overrides_default(monkeypatch):
        """--reasoning-level low wins over the built-in xhigh default."""
        fake_run = _fake_run_returns("hi")
        monkeypatch.setattr(
            client_mod,
            "resolve_runtime_config",
            lambda *a, **k: (None, "sk-test", "qwen3.8-max"),
        )
        monkeypatch.setattr(client_mod, "_run_with_progress_bar", fake_run)
        client_mod.send_prompt(
            "hello", use_mcp=False, cli_provider="alibaba", reasoning_level="low"
        )
        assert fake_run.captured_kwargs["reasoning_effort"] == "low"

    def test_send_prompt_config_reasoning_level_used(monkeypatch, tmp_path):
        """A per-provider config value is used when no CLI arg is given."""
        from janito.config_cli import set_config_from_cli

        set_config_from_cli("reasoning-level=medium", "alibaba")
        fake_run = _fake_run_returns("hi")
        monkeypatch.setattr(
            client_mod,
            "resolve_runtime_config",
            lambda *a, **k: (None, "sk-test", "qwen3.8-max"),
        )
        monkeypatch.setattr(client_mod, "_run_with_progress_bar", fake_run)
        client_mod.send_prompt("hello", use_mcp=False, cli_provider="alibaba")
        assert fake_run.captured_kwargs["reasoning_effort"] == "medium"

    def test_send_prompt_no_reasoning_level_omits_effort(monkeypatch):
        """No reasoning_effort is sent when nothing resolves (e.g. openai)."""
        fake_run = _fake_run_returns("hi")
        monkeypatch.setattr(
            client_mod,
            "resolve_runtime_config",
            lambda *a, **k: (None, "sk-test", "gpt-4"),
        )
        monkeypatch.setattr(client_mod, "_run_with_progress_bar", fake_run)
        client_mod.send_prompt("hello", use_mcp=False, cli_provider="openai")
        assert "reasoning_effort" not in fake_run.captured_kwargs

    def test_send_prompt_thinking_defaults_on_for_deepseek(monkeypatch):
        """DeepSeek reasons by default: enable_thinking is sent without -t."""
        fake_run = _fake_run_returns("hi")
        monkeypatch.setattr(
            client_mod,
            "resolve_runtime_config",
            lambda *a, **k: (None, "sk-test", "deepseek-v4-flash"),
        )
        monkeypatch.setattr(client_mod, "_run_with_progress_bar", fake_run)
        client_mod.send_prompt("hello", use_mcp=False, cli_provider="deepseek")
        assert fake_run.captured_kwargs["extra_body"]["enable_thinking"] is True

    def test_send_prompt_thinking_defaults_on_for_alibaba(monkeypatch):
        """Alibaba/Qwen reasons by default: enable_thinking is sent without -t."""
        fake_run = _fake_run_returns("hi")
        monkeypatch.setattr(
            client_mod,
            "resolve_runtime_config",
            lambda *a, **k: (None, "sk-test", "qwen3.8-max"),
        )
        monkeypatch.setattr(client_mod, "_run_with_progress_bar", fake_run)
        client_mod.send_prompt("hello", use_mcp=False, cli_provider="alibaba")
        assert fake_run.captured_kwargs["extra_body"]["enable_thinking"] is True

    def test_send_prompt_thinking_off_by_default_for_openai(monkeypatch):
        """OpenAI has no default thinking: enable_thinking is not sent."""
        fake_run = _fake_run_returns("hi")
        monkeypatch.setattr(
            client_mod,
            "resolve_runtime_config",
            lambda *a, **k: (None, "sk-test", "gpt-4"),
        )
        monkeypatch.setattr(client_mod, "_run_with_progress_bar", fake_run)
        client_mod.send_prompt("hello", use_mcp=False, cli_provider="openai")
        assert "extra_body" not in fake_run.captured_kwargs

    def test_send_prompt_explicit_thinking_flag_still_wins(monkeypatch):
        """-t forces enable_thinking even for providers without a default."""
        fake_run = _fake_run_returns("hi")
        monkeypatch.setattr(
            client_mod,
            "resolve_runtime_config",
            lambda *a, **k: (None, "sk-test", "gpt-4"),
        )
        monkeypatch.setattr(client_mod, "_run_with_progress_bar", fake_run)
        client_mod.send_prompt(
            "hello", use_mcp=False, cli_provider="openai", thinking=True
        )
        assert fake_run.captured_kwargs["extra_body"]["enable_thinking"] is True

    def test_build_call_kwargs_forwards_reasoning_effort():
        class _Cfg:
            effective_thinking = False

        kwargs = build_call_kwargs("qwen3.8-max", _Cfg(), 1000, None, "xhigh")
        assert kwargs["reasoning_effort"] == "xhigh"
        assert kwargs["model"] == "qwen3.8-max"
        assert kwargs["stream"] is True

    def test_build_call_kwargs_omits_reasoning_effort_when_none():
        class _Cfg:
            effective_thinking = False

        kwargs = build_call_kwargs("gpt-4", _Cfg(), 1000, None, None)
        assert "reasoning_effort" not in kwargs

    def test_build_call_kwargs_enables_thinking_when_effective():
        """Web agent sends enable_thinking when the effective state is on
        (runtime toggle, --thinking flag, or provider default)."""

        class _Cfg:
            effective_thinking = True

        kwargs = build_call_kwargs("deepseek-v4-flash", _Cfg(), 1000, None, None)
        assert kwargs["extra_body"]["enable_thinking"] is True

    def test_build_call_kwargs_omits_thinking_when_off():
        """Web agent omits enable_thinking when the effective state is off."""

        class _Cfg:
            effective_thinking = False

        kwargs = build_call_kwargs("gpt-4", _Cfg(), 1000, None, None)
        assert "extra_body" not in kwargs

    def test_cli_parser_accepts_reasoning_level_choices():
        from janito.cli.parser import create_parser

        for level in ("low", "medium", "high", "xhigh", "none", "minimal", "max"):
            args = create_parser().parse_args(["--reasoning-level", level, "prompt"])
            assert args.reasoning_level == level

    def test_cli_parser_rejects_invalid_reasoning_level():
        from janito.cli.parser import create_parser

        with pytest.raises(SystemExit):
            create_parser().parse_args(["--reasoning-level", "turbo", "prompt"])

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                try:
                    fn()
                except TypeError:
                    # Skip tests that require monkeypatch/tmp_path fixtures.
                    continue
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
