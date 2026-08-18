"""
Tests for the shell /price command handler.

``/price`` renders a table with one row per built-in model: the provider,
the model name and the estimated cost of a notional request of **1M input
tokens (cache miss) + 1M cached input tokens + 1M output tokens**.  The
cost column is computed by the provider's cost module via
:func:`janito.provider_accessors.get_provider_cost` with
``is_reference=True`` (so reference/peak rates apply and the string carries
no rate-band suffix); providers/models without a cost module show ``N/A``.
The command must not match non-``/price`` input (e.g. ``/prices``).
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

import janito.config_dir as config_dir_mod
from janito.provider_accessors import get_provider_cost
from janito.provider_registry import _registry
from janito.provider_validation import list_supported_providers
from janito.shell import InteractiveShell
from janito.shell.cmds.registry import get_registered_commands


def _use_temp_config(monkeypatch, tmp_path):
    """Point the config directory at a temporary directory."""
    config_path = tmp_path / ".janito" / "config.json"
    monkeypatch.setattr(config_dir_mod, "_config_dir", config_path.parent)
    return config_path


def _shell():
    """Build a fresh shell for testing."""
    return InteractiveShell(model="test-model", no_history=True)


def _price_handler():
    """Return the registered /price command handler."""
    return next(c for c in get_registered_commands() if c.name == "/price")


def _inject_fake_no_cost_provider():
    """Inject a provider with a model but no cost module.

    Every built-in provider with built-in models now ships a cost module, so
    the N/A fallback is exercised through a runtime-injected provider.  The
    registry holds a reference to ``janito.providers._PROVIDER_CONFIGS``, so
    the mutation is visible to the /price handler.

    Returns:
        A callable that restores ``_PROVIDER_CONFIGS`` to its original state.
    """
    import janito.providers as pvd

    original = dict(pvd._PROVIDER_CONFIGS)
    pvd._PROVIDER_CONFIGS["fake-no-cost"] = {
        "default_model": "fake-model",
        "endpoint": None,
        "models": {
            "fake-model": {
                "supported_api_types": ["Completions"],
                "max_input_tokens": None,
                "max_output_tokens": None,
            }
        },
    }

    def restore():
        pvd._PROVIDER_CONFIGS.clear()
        pvd._PROVIDER_CONFIGS.update(original)

    return restore


def test_price_command_is_registered():
    """The /price handler is registered with the shell command registry."""
    names = [cmd.name for cmd in get_registered_commands()]
    assert "/price" in names


def test_price_lists_providers_and_models(monkeypatch, tmp_path, capsys):
    """``/price`` lists every built-in provider and its built-in models."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell()
    assert _price_handler().handle(shell, "/price") is True

    out = capsys.readouterr().out
    for provider in list_supported_providers():
        found = _registry.get(provider)
        for model in found.model_names():
            assert provider in out
            assert model in out


def test_price_cost_column_matches_provider_cost(monkeypatch, tmp_path, capsys):
    """The cost column equals get_provider_cost(..., is_reference=True)."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell()
    assert _price_handler().handle(shell, "/price") is True

    out = capsys.readouterr().out
    for provider in list_supported_providers():
        found = _registry.get(provider)
        for model in found.model_names():
            expected = get_provider_cost(
                provider, model, 1_000_000, 1_000_000, 1_000_000, is_reference=True
            )
            assert expected in out


def test_price_applies_reference_rates(monkeypatch, tmp_path, capsys):
    """The price column uses the reference (peak) rates, e.g. DeepSeek's."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell()
    assert _price_handler().handle(shell, "/price") is True

    out = capsys.readouterr().out
    # 1M cache-hit input + 1M output at reference (peak) rates:
    #   alibaba qwen3.8-max        -> 0.25 + 6.0          = 6.250000$
    #   deepseek deepseek-v4-flash -> (0.007 + 0.66) * 2  = 1.334000$
    #   deepseek deepseek-v4-pro   -> (0.022 + 1.98) * 2  = 4.004000$
    #   google  gemini-3.7-flash   -> 0.1875 + 3.75       = 3.937500$
    #   minimax MiniMax-M3         -> 0.12 + 2.40         = 2.520000$
    #   zai     glm-5.2            -> 0.26 + 4.40         = 4.660000$
    assert "6.250000$" in out
    assert "4.660000$" in out
    assert "1.334000$" in out
    assert "4.004000$" in out
    assert "3.937500$" in out
    assert "2.520000$" in out
    # The reference annotation is not attached (no rate-band suffix).
    assert "off-peak" not in out
    assert "(peak)" not in out


def test_price_shows_na_for_models_without_cost_module(monkeypatch, tmp_path, capsys):
    """Models without a provider cost module are reported as N/A."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell()
    assert _price_handler().handle(shell, "/price") is True

    out = capsys.readouterr().out
    # The anthropic provider now ships a cost module, so its models show a
    # real cost, not N/A.  /price bills 1M cache-hit input + 1M output:
    # claude-sonnet-5 -> $0.20 + $10 = 10.200000$.
    assert "anthropic" in out
    assert "claude-sonnet-5" in out
    assert "10.200000$" in out
    # OpenAI ships a cost module, so its model shows a real cost, not N/A.
    assert "gpt-5.6-luna" in out
    assert "1.840000$" in out

    # A provider without a cost module is reported as N/A.
    restore = _inject_fake_no_cost_provider()
    try:
        assert _price_handler().handle(_shell(), "/price") is True
        out = capsys.readouterr().out
        assert "fake-no-cost" in out
        assert "fake-model" in out
        assert "N/A" in out
    finally:
        restore()


def test_non_price_input_is_not_handled(capsys):
    """``/prices`` (plural) must not match the /price command."""
    shell = _shell()
    assert _price_handler().handle(shell, "/prices") is False
    assert capsys.readouterr().out == ""


def test_price_sorted_by_cost_descending(monkeypatch, tmp_path, capsys):
    """``/price`` sorts rows by cost from max to min as floats, with N/A at the bottom."""
    _use_temp_config(monkeypatch, tmp_path)
    shell = _shell()
    assert _price_handler().handle(shell, "/price") is True

    out = capsys.readouterr().out
    pos_fable = out.find("claude-fable-5")
    pos_opus = out.find("claude-opus-5")
    pos_kimi = out.find("kimi-k3")
    pos_sonnet = out.find("claude-sonnet-5")
    pos_alibaba = out.find("qwen3.8-max")
    pos_zai = out.find("glm-5.2")
    pos_deepseek_pro = out.find("deepseek-v4-pro")
    pos_gemini = out.find("gemini-3.7-flash")
    pos_minimax = out.find("MiniMax-M3")
    pos_openai = out.find("gpt-5.6-luna")
    pos_deepseek_flash = out.find("deepseek-v4-flash")

    assert pos_fable != -1
    assert pos_opus != -1
    assert pos_kimi != -1
    assert pos_sonnet != -1
    assert pos_alibaba != -1
    assert pos_zai != -1
    assert pos_deepseek_pro != -1
    assert pos_gemini != -1
    assert pos_minimax != -1
    assert pos_openai != -1
    assert pos_deepseek_flash != -1

    # Claude Fable (51$) > Claude Opus (25.5$) > Moonshot Kimi (14.03$) >
    # Claude Sonnet (10.2$) > Alibaba (6.25$) > Z.ai (4.66$) >
    # DeepSeek Pro (4.004$) > Gemini Flash (3.9375$) > MiniMax M3 (2.52$) >
    # OpenAI Luna (1.84$) > DeepSeek Flash (1.334$).
    assert (
        pos_fable
        < pos_opus
        < pos_kimi
        < pos_sonnet
        < pos_alibaba
        < pos_zai
        < pos_deepseek_pro
        < pos_gemini
        < pos_minimax
        < pos_openai
        < pos_deepseek_flash
    )
    # N/A rows (no cost module) sort below every numeric cost.
    restore = _inject_fake_no_cost_provider()
    try:
        assert _price_handler().handle(_shell(), "/price") is True
        out = capsys.readouterr().out
        pos_fake = out.find("fake-model")
        assert pos_fake != -1
        assert pos_deepseek_flash < pos_fake
    finally:
        restore()


def test_parse_cost_helper():
    """_parse_cost correctly parses numeric costs and handles N/A / invalid strings."""
    from janito.shell.cmds.price import _parse_cost

    assert _parse_cost("6.250000$") == 6.25
    assert _parse_cost("0.880000$ (off-peak)") == 0.88
    assert _parse_cost("  3.937500$ ") == 3.9375
    assert _parse_cost("N/A") == float("-inf")
    assert _parse_cost("") == float("-inf")
    assert _parse_cost(None) == float("-inf")
