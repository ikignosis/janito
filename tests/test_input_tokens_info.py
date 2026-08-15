"""
Tests for the input-tokens/max-tokens display (issue #31).

The token-usage summary shown at the end of each prompt should display the
output token count alongside the configured max output tokens using the
``output/max`` format, e.g. ``Out: 123/65.5k``.

These tests verify:
  - ``format_tokens()`` human-readable formatting.
  - The CLI usage summary string construction with and without a max-tokens
    value.
  - The web ``UsageEvent`` serialization includes ``max_tokens`` only when
    it is set.
  - The web ``StreamAccumulator.usage_event()`` passes ``max_tokens`` through.
  - The frontend usage strip renders the ``output/max`` pattern.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))
# The web frontend helpers live under tests/web.
sys.path.insert(0, str(Path(__file__).parent / "web"))

import pytest
from _frontend import render_index_html

if pytest is not None:
    from janito.openai_client.completions_api import format_tokens

    # ---- format_tokens unit tests ------------------------------------

    def test_format_tokens_plain_integer():
        assert format_tokens(150) == "150"

    def test_format_tokens_thousands():
        assert format_tokens(2000) == "2k"

    def test_format_tokens_thousands_fractional():
        assert format_tokens(12345) == "12.3k"

    def test_format_tokens_millions():
        assert format_tokens(4_000_000) == "4m"

    def test_format_tokens_none():
        assert format_tokens(None) is None

    # ---- CLI usage-line construction ---------------------------------

    def _build_parts(
        input_tokens,
        max_output_tokens,
        output_tokens=50,
        total_tokens=200,
        cached_tokens=None,
        max_input_tokens=None,
    ):
        """Replicate the parts-building logic from send_prompt."""
        parts = []
        if total_tokens is not None:
            parts.append(f"Total: {format_tokens(total_tokens)}")
        if input_tokens is not None:
            if max_input_tokens is not None:
                parts.append(
                    f"In: {format_tokens(input_tokens)}/{format_tokens(max_input_tokens)}"
                )
            else:
                parts.append(f"In: {format_tokens(input_tokens)}")
        if output_tokens is not None:
            if max_output_tokens is not None:
                parts.append(
                    f"Out: {format_tokens(output_tokens)}/{format_tokens(max_output_tokens)}"
                )
            else:
                parts.append(f"Out: {format_tokens(output_tokens)}")
        if cached_tokens is not None:
            parts.append(f"Cached: {format_tokens(cached_tokens)}")
        return parts

    def test_input_with_max_tokens():
        parts = _build_parts(1200, 65536, max_input_tokens=128000)
        assert "In: 1.2k/128k" in parts
        assert "Out: 50/65.5k" in parts

    def test_input_without_max_tokens():
        parts = _build_parts(1200, None)
        assert "In: 1.2k" in parts
        assert "Out: 50" in parts
        # No slash when max is not configured
        assert not any("/" in p for p in parts)

    def test_input_with_max_exact_values():
        parts = _build_parts(500, 1000, max_input_tokens=1000)
        assert "In: 500/1k" in parts
        assert "Out: 50/1k" in parts

    def test_input_zero_with_max():
        parts = _build_parts(0, 65536, max_input_tokens=128000)
        assert "In: 0/128k" in parts
        assert "Out: 50/65.5k" in parts

    def test_input_without_input_max_but_with_output_max():
        parts = _build_parts(1200, 65536)
        assert "In: 1.2k" in parts
        assert "Out: 50/65.5k" in parts

    # ---- Cost in the CLI usage line ----------------------------------

    def _display_usage_text(
        provider, model, usage, cached_details_attr="prompt_tokens_details"
    ):
        """Render the usage summary line through _display_usage."""
        from io import StringIO

        from rich.console import Console

        from janito.openai_client.client_support import _display_usage

        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        _display_usage(
            usage,
            None,
            None,
            1,
            console,
            provider=provider,
            model=model,
            cached_details_attr=cached_details_attr,
        )
        return buf.getvalue().strip()

    def _usage(input_tokens, output_tokens, cached_tokens):
        from types import SimpleNamespace

        return SimpleNamespace(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            prompt_tokens_details=SimpleNamespace(cached_tokens=cached_tokens),
        )

    def test_usage_line_cost_from_provider_cost_module():
        """The Cost part is computed via get_provider_cost for the provider."""
        # DeepSeek V4-Flash: $0.14 in (miss) + $0.28 out per 1M tokens.
        text = _display_usage_text(
            "deepseek", "deepseek-v4-flash", _usage(1_000_000, 1_000_000, 0)
        )
        assert "Cost: 0.420000$" in text

    def test_usage_line_cost_bills_cached_input_at_cache_hit():
        """Cached input tokens are billed at the provider's cache-hit rate."""
        # 500k of the 1M input tokens are cache hits ($0.0028 vs $0.14/1M).
        text = _display_usage_text(
            "deepseek", "deepseek-v4-flash", _usage(1_000_000, 1_000_000, 500_000)
        )
        assert "Cost: 0.351400$" in text

    def test_usage_line_cost_provider_without_cost_module_is_na():
        """Providers without a cost module fall back to Cost: N/A."""
        text = _display_usage_text(
            "openai", "gpt-5.6-luna", _usage(1_000_000, 1_000_000, 0)
        )
        assert "Cost: N/A" in text

    def test_usage_line_cost_without_provider_model_is_na():
        """No provider/model falls back to Cost: N/A."""
        text = _display_usage_text(None, None, _usage(1_000_000, 1_000_000, 0))
        assert "Cost: N/A" in text

    # ---- Web UsageEvent serialization --------------------------------

    def test_usage_event_to_dict_without_max():
        from janito.web.backend.events import UsageEvent

        ev = UsageEvent(total=100, input=80, output=20, cached=10)
        d = ev.to_dict()
        assert d == {
            "type": "usage",
            "total": 100,
            "input": 80,
            "output": 20,
            "cached": 10,
        }
        assert "max_tokens" not in d

    def test_usage_event_to_dict_with_max():
        from janito.web.backend.events import UsageEvent

        ev = UsageEvent(total=100, input=80, output=20, cached=0, max_tokens=65536)
        d = ev.to_dict()
        assert d["max_tokens"] == 65536

    # ---- StreamAccumulator.usage_event with max_tokens ---------------

    def test_stream_accumulator_usage_event_passes_max_tokens():
        from janito.web.backend.agent.call import StreamAccumulator

        class FakeUsage:
            total_tokens = 200
            prompt_tokens = 150
            completion_tokens = 50
            prompt_tokens_details = None

        acc = StreamAccumulator(usage=FakeUsage())
        ev = acc.usage_event(max_tokens=32768)
        assert ev is not None
        assert ev.max_tokens == 32768
        assert ev.to_dict()["max_tokens"] == 32768

    def test_stream_accumulator_usage_event_no_max():
        from janito.web.backend.agent.call import StreamAccumulator

        class FakeUsage:
            total_tokens = 200
            prompt_tokens = 150
            completion_tokens = 50
            prompt_tokens_details = None

        acc = StreamAccumulator(usage=FakeUsage())
        ev = acc.usage_event()
        assert ev is not None
        assert ev.max_tokens is None
        assert "max_tokens" not in ev.to_dict()

    # ---- Frontend wiring (static checks) -----------------------------

    def test_frontend_usage_strip_shows_output_max():
        """The usage-strip template must render ``output/max`` in the out chip."""
        html = render_index_html()
        # The out-chip must append max_tokens when available
        assert "msg.usage.max_tokens" in html
        assert "formatTokens(msg.usage.output) + (msg.usage.max_tokens" in html

    def test_frontend_status_bar_shows_output_max():
        """The status bar must render ``output/max`` in the tokens area."""
        html = render_index_html()
        assert "lastUsage.max_tokens" in html
        assert "formatTokens(lastUsage.output) + (lastUsage.max_tokens" in html

    def test_frontend_event_handler_captures_max_tokens():
        """chatEvents.js must store max_tokens from the usage event."""
        js = (
            Path(__file__).parent.parent
            / "janito"
            / "web"
            / "frontend"
            / "js"
            / "chatEvents.js"
        )
        src = js.read_text(encoding="utf-8")
        assert "max_tokens: c.event.max_tokens" in src

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                fn()
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
