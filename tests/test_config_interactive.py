"""Tests for the interactive ``--config`` provider selection (questionary)."""

from unittest.mock import patch

import pytest

from janito.cli.handlers.config import _prompt_provider


class _FakeQuestionary:
    """A stand-in for ``questionary.select(...).ask()``."""

    def __init__(self, result):
        self._result = result
        self.select_kwargs = None

    def select(self, *args, **kwargs):
        self.select_kwargs = (args, kwargs)
        return self

    def ask(self):
        if isinstance(self._result, BaseException):
            raise self._result
        return self._result


def _select_kwargs(fake):
    """Return the kwargs passed to questionary.select by _prompt_provider."""
    return fake.select_kwargs[1]


def test_prompt_provider_uses_questionary_select(monkeypatch, capsys):
    fake = _FakeQuestionary("deepseek")
    monkeypatch.setattr("janito.cli.handlers.config.questionary", fake)

    result = _prompt_provider(existing_provider=None)

    assert result == "deepseek"
    args, kwargs = fake.select_kwargs
    assert args[0] == "Select a provider"
    assert kwargs["choices"] == [
        "alibaba",
        "anthropic",
        "custom",
        "deepseek",
        "minimax",
        "moonshot",
        "openai",
        "xai",
        "xiaomi",
        "zai",
    ]
    # No pre-selection when there is no existing provider.
    assert kwargs["default"] is None
    out = capsys.readouterr().out
    assert "Using provider: deepseek" in out


def test_prompt_provider_preselects_existing_provider(monkeypatch):
    fake = _FakeQuestionary("openai")
    monkeypatch.setattr("janito.cli.handlers.config.questionary", fake)

    result = _prompt_provider(existing_provider="openai")

    assert result == "openai"
    kwargs = _select_kwargs(fake)
    assert kwargs["default"] == "openai"


def test_prompt_provider_unknown_existing_provider_has_no_default(monkeypatch):
    fake = _FakeQuestionary("openai")
    monkeypatch.setattr("janito.cli.handlers.config.questionary", fake)

    _prompt_provider(existing_provider="not-a-provider")

    kwargs = _select_kwargs(fake)
    assert kwargs["default"] is None


def test_prompt_provider_none_selection_returns_none(monkeypatch, capsys):
    fake = _FakeQuestionary(None)
    monkeypatch.setattr("janito.cli.handlers.config.questionary", fake)

    result = _prompt_provider(existing_provider=None)

    assert result is None
    err = capsys.readouterr().err
    assert "Provider name is required" in err


def test_prompt_provider_keyboard_interrupt_exits(capsys):
    fake = _FakeQuestionary(KeyboardInterrupt())
    with (
        patch("janito.cli.handlers.config.questionary", fake),
        pytest.raises(SystemExit) as exc_info,
    ):
        _prompt_provider(existing_provider=None)

    assert exc_info.value.code == 0
    assert "Configuration cancelled." in capsys.readouterr().out
