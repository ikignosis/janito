"""
Tests for the interactive shell status bar (bottom toolbar).

The toolbar shows the active model and provider. The provider must reflect the
one in effect for the current session (e.g. from ``--provider``) rather than
only the configured default, so that ``janito --provider deepseek`` shows
``provider: deepseek`` even when config.json still names another provider.
"""

from unittest.mock import patch

import pytest

from janito.shell import InteractiveShell


def _toolbar_text(shell):
    """Return the flattened text of the shell's bottom toolbar tokens."""
    return "".join(text for _, text in shell._get_bottom_toolbar())


@pytest.mark.parametrize("session_provider", [None, "deepseek"])
def test_toolbar_reports_session_provider(session_provider):
    """A session provider passed to the shell wins over the configured default."""
    shell = InteractiveShell(
        model="deepseek-v4-flash",
        no_history=True,
        provider=session_provider,
    )
    with patch("janito.general_config.get_active_provider", return_value="alibaba"):
        text = _toolbar_text(shell)
    assert "deepseek-v4-flash" in text  # model is always shown
    expected = session_provider if session_provider else "alibaba"
    assert f"provider: {expected}" in text
    # The other provider must never appear.
    other = "alibaba" if session_provider else "openai"
    assert f"provider: {other}" not in text


def test_toolbar_falls_back_to_active_provider_when_no_session_provider():
    """Without a session provider the toolbar reports the configured default."""
    shell = InteractiveShell(model="test-model", no_history=True, provider=None)
    with patch("janito.general_config.get_active_provider", return_value="openai"):
        text = _toolbar_text(shell)
    assert "provider: openai" in text
