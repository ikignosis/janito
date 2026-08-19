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
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

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

    def test_usage_line_cost_from_provider_cost_module(monkeypatch):
        """The Cost part is computed via get_provider_cost for the provider."""
        # Pin the request time to off-peak (12:00 UTC) so the estimate is
        # deterministic: DeepSeek V4-Flash is $0.22 in (miss) + $0.66 out per
        # 1M tokens off-peak.
        monkeypatch.setattr(
            "janito.providers.deepseek.cost._utcnow",
            lambda: datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc),
        )
        text = _display_usage_text(
            "deepseek", "deepseek-v4-flash", _usage(1_000_000, 1_000_000, 0)
        )
        assert "Cost: 0.880000$ (off-peak)" in text

    def test_usage_line_cost_bills_cached_input_at_cache_hit(monkeypatch):
        """Cached input tokens are billed at the provider's cache-hit rate."""
        # Pin the request time to off-peak (12:00 UTC); 500k of the 1M input
        # tokens are cache hits ($0.007 vs $0.22/1M).
        monkeypatch.setattr(
            "janito.providers.deepseek.cost._utcnow",
            lambda: datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc),
        )
        text = _display_usage_text(
            "deepseek", "deepseek-v4-flash", _usage(1_000_000, 1_000_000, 500_000)
        )
        assert "Cost: 0.773500$ (off-peak)" in text

    def test_usage_line_cost_google_provider():
        """Google Gemini usage calculates cost using google.cost module."""
        text = _display_usage_text(
            "google", "gemini-3.7-flash", _usage(1_000_000, 1_000_000, 0)
        )
        assert "Cost: 4.500000$" in text

    def test_usage_line_cost_minimax_provider():
        """MiniMax usage calculates cost using minimax.cost module."""
        text = _display_usage_text("minimax", "MiniMax-M3", _usage(100_000, 100_000, 0))
        assert "Cost: 0.150000$" in text

    def test_usage_line_cost_openai_provider():
        """OpenAI GPT-5.6 Luna usage calculates cost using openai.cost module."""
        # 100k input tokens (<= 272K threshold): standard rates
        # (100k * $0.20 + 1M * $1.20) / 1M = 1.22.
        text = _display_usage_text(
            "openai", "gpt-5.6-luna", _usage(100_000, 1_000_000, 0)
        )
        assert "Cost: 1.220000$" in text

    def test_usage_line_cost_openai_high_context():
        """High-context OpenAI requests (> 272K input tokens) bill at 2x/1.5x."""
        text = _display_usage_text(
            "openai", "gpt-5.6-luna", _usage(300_000, 1_000_000, 0)
        )
        assert "Cost: 1.920000$" in text

    def test_usage_line_cost_anthropic_provider():
        """Anthropic usage calculates cost using anthropic.cost module."""
        # 1M input (cache miss) at $2 + 1M output at $10 per 1M tokens.
        text = _display_usage_text(
            "anthropic", "claude-sonnet-5", _usage(1_000_000, 1_000_000, 0)
        )
        assert "Cost: 12.000000$" in text

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

else:  # pragma: no cover - fallback runner without pytest

    def _main():
        for name, fn in sorted(globals().items()):
            if name.startswith("test_") and callable(fn):
                fn()
                print(f"OK {name}")

    if __name__ == "__main__":
        _main()
