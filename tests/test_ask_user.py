#!/usr/bin/env python3
"""
Tests for the AskUser tool (janito/tools/system/ask_user.py).

Verifies that:
- The tool returns success with the user's answer.
- The tool echoes back the question.
- The tool handles EOF gracefully (empty answer).
- The tool handles exceptions gracefully (success=False).
"""

from contextlib import redirect_stderr
from io import StringIO
from unittest.mock import patch

from janito.tools.system.ask_user import AskUser


class TestAskUser:
    """Tests for the AskUser tool."""

    def test_basic_answer(self):
        """Tool returns success and the user's answer."""
        with patch("builtins.input", return_value="Paris"):
            result = AskUser().run(question="What is the capital of France?")

        assert result["success"] is True
        assert result["question"] == "What is the capital of France?"
        assert result["answer"] == "Paris"

    def test_answer_is_stripped(self):
        """Leading/trailing whitespace in the answer is stripped."""
        with patch("builtins.input", return_value="  hello  "):
            result = AskUser().run(question="Say hello")

        assert result["success"] is True
        assert result["answer"] == "hello"

    def test_empty_answer(self):
        """An empty answer is returned as an empty string."""
        with patch("builtins.input", return_value=""):
            result = AskUser().run(question="Anything to add?")

        assert result["success"] is True
        assert result["answer"] == ""

    def test_eof_returns_empty_answer(self):
        """EOFError (e.g. piped input) results in an empty answer, not a crash."""
        with patch("builtins.input", side_effect=EOFError):
            result = AskUser().run(question="Are you there?")

        assert result["success"] is True
        assert result["answer"] == ""

    def test_keyboard_interrupt_returns_empty_answer(self):
        """KeyboardInterrupt results in an empty answer, not a crash."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = AskUser().run(question="Are you there?")

        assert result["success"] is True
        assert result["answer"] == ""

    def test_question_echoed_back(self):
        """The question is always echoed in the result."""
        with patch("builtins.input", return_value="42"):
            result = AskUser().run(question="Meaning of life?")

        assert result["question"] == "Meaning of life?"

    def test_question_printed_inside_rich_table(self):
        """The question is rendered by rich inside a table on stderr."""
        question = "What is the capital of France?"
        buffer = StringIO()

        with patch("builtins.input", return_value="Paris"), redirect_stderr(buffer):
            AskUser().run(question=question)

        output = buffer.getvalue()
        assert question in output
        # rich table frame characters (header row + question row + borders)
        assert "Question" in output
        assert "│" in output  # vertical border
        assert "─" in output  # horizontal border

    def test_question_inside_table_does_not_interpret_markup(self):
        """Markup-like text in the question is shown literally, not styled."""
        question = "Pick [bold]one[/bold] option"
        buffer = StringIO()

        with patch("builtins.input", return_value="A"), redirect_stderr(buffer):
            AskUser().run(question=question)

        output = buffer.getvalue()
        assert "[bold]one[/bold]" in output

    def test_success_key_always_present(self):
        """The 'success' key is always present in the returned dict."""
        with patch("builtins.input", return_value="yes"):
            result = AskUser().run(question="ok?")

        assert "success" in result
