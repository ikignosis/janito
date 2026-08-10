#!/usr/bin/env python3
"""
Tests for the pluggable prompt handler (janito/tooling/prompting.py).

``BaseTool.prompt_user`` reads from stdin by default; when the web backend
installs a prompt handler through the ``prompting`` context variable, the
tool delegates to it instead (web mode presents the question as a browser
modal and returns the typed answer).

Verifies that:
- The handler defaults to ``None`` and can be set/restored.
- ``AskUser`` delegates to the installed handler instead of stdin.
- The handler's answer is whitespace-stripped, like the stdin path.
- A handler exception surfaces as a failed tool result (never crashes).
"""

from unittest.mock import patch

from janito.tooling.prompting import get_prompt_handler, set_prompt_handler
from janito.tools.system.ask_user import AskUser


class TestPromptHandlerContextVar:
    """The context variable accessors behave like the report handler."""

    def test_default_is_none(self):
        """No handler installed by default (CLI stdin fallback applies)."""
        assert get_prompt_handler() is None

    def test_set_and_get(self):
        """set_prompt_handler installs a handler, get returns it."""

        def handler(question):
            return "answer"

        set_prompt_handler(handler)
        try:
            assert get_prompt_handler() is handler
        finally:
            set_prompt_handler(None)

    def test_set_none_restores_default(self):
        """Passing None restores the default (console) behaviour."""

        def handler(question):
            return "answer"

        set_prompt_handler(handler)
        set_prompt_handler(None)
        assert get_prompt_handler() is None


class TestAskUserDelegatesToHandler:
    """AskUser uses the installed handler instead of stdin in web mode."""

    def test_ask_user_uses_handler_not_stdin(self):
        """With a handler installed, input() is never called."""
        captured = {}

        def handler(question):
            captured["question"] = question
            return "Paris"

        set_prompt_handler(handler)
        try:
            with patch(
                "builtins.input",
                side_effect=AssertionError("input() must not be called"),
            ):
                result = AskUser().run(question="What is the capital of France?")
        finally:
            set_prompt_handler(None)

        assert captured["question"] == "What is the capital of France?"
        assert result["success"] is True
        assert result["answer"] == "Paris"

    def test_ask_user_strips_handler_answer(self):
        """The handler's answer is stripped, mirroring the stdin path."""

        def handler(question):
            return "  hello  "

        set_prompt_handler(handler)
        try:
            result = AskUser().run(question="Say hello")
        finally:
            set_prompt_handler(None)

        assert result["success"] is True
        assert result["answer"] == "hello"

    def test_handler_exception_becomes_failed_result(self):
        """A raising handler never crashes the loop: AskUser returns
        success=False, matching the tool's error contract."""

        def handler(question):
            raise RuntimeError("browser disconnected")

        set_prompt_handler(handler)
        try:
            result = AskUser().run(question="Are you there?")
        finally:
            set_prompt_handler(None)

        assert result["success"] is False
        assert "browser disconnected" in result["error"]

    def test_handler_unset_falls_back_to_stdin(self):
        """Without a handler the CLI stdin path still works."""
        with patch("builtins.input", return_value="console"):
            result = AskUser().run(question="From the console?")

        assert result["success"] is True
        assert result["answer"] == "console"
