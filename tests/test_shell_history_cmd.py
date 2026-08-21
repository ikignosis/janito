"""
Tests for the /history shell command.

``/history`` renders the conversation history as a rich table.  Where that
history lives depends on the API type: Completions / Anthropic / DashScope
keep it in ``shell.messages_history`` (system + user + assistant), while the
Responses API keeps it elsewhere -- stateless providers (e.g. DeepSeek) hold
the full conversation client-side as Responses input items in
``shell.conversation_items`` (``messages_history`` then only ever holds the
system prompt), and server-side providers (e.g. OpenAI) keep it on the server
with a display-only mirror of the completed turns in
``shell.mirrored_history`` (plus any pending Enter-cancelled messages in
``conversation_items``).  These tests verify the command renders the right
source in each mode.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

from janito.shell import InteractiveShell
from janito.shell.cmds.registry import get_registered_commands


def _history_handler():
    """Return the registered /history command handler."""
    return next(c for c in get_registered_commands() if c.name == "/history")


def _shell():
    """Build a fresh shell for testing."""
    return InteractiveShell(model="test-model", no_history=True)


# ---------------------------------------------------------------------------
# Registry / dispatch
# ---------------------------------------------------------------------------


def test_history_command_is_registered():
    """The /history handler is registered with the shell command registry."""
    names = [cmd.name for cmd in get_registered_commands()]
    assert "/history" in names


def test_history_handles_exact_command_only():
    """/history only fires on the exact command, not sub-strings."""
    shell = _shell()
    handler = _history_handler()
    assert handler.handle(shell, "/history") is True
    assert handler.handle(shell, "/history foo") is False


# ---------------------------------------------------------------------------
# Completions / Anthropic / DashScope: messages_history
# ---------------------------------------------------------------------------


def test_history_renders_messages_history():
    """Completions-mode history is rendered from shell.messages_history."""
    shell = _shell()
    shell.messages_history = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    rows = _history_handler()._history_rows(shell)
    assert rows == [
        ("system", "sys"),
        ("user", "hello"),
        ("assistant", "hi"),
    ]


def test_history_empty():
    """No history prints an empty placeholder (no rows to render)."""
    shell = _shell()
    shell.messages_history = []
    assert _history_handler()._history_rows(shell) == []


# ---------------------------------------------------------------------------
# Stateless Responses (e.g. DeepSeek): conversation_items
# ---------------------------------------------------------------------------


def test_history_prefers_stateless_conversation_items():
    """For stateless Responses providers /history renders conversation_items
    (which include the folded-in system prompt) instead of the system-only
    messages_history."""
    shell = _shell()
    # messages_history only ever holds the system prompt in Responses mode.
    shell.messages_history = [{"role": "system", "content": "sys"}]
    shell.conversation_items = [
        {
            "type": "message",
            "role": "system",
            "content": [{"type": "input_text", "text": "sys"}],
        },
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "hello"}],
        },
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "hi"}],
        },
    ]
    rows = _history_handler()._history_rows(shell)
    assert rows == [
        ("system", "sys"),
        ("user", "hello"),
        ("assistant", "hi"),
    ]


def test_history_stateless_with_tool_rounds():
    """Stateless Responses tool-call rounds render as function_call /
    function_call_output rows."""
    shell = _shell()
    shell.messages_history = [{"role": "system", "content": "sys"}]
    shell.conversation_items = [
        {
            "type": "message",
            "role": "system",
            "content": [{"type": "input_text", "text": "sys"}],
        },
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "list files"}],
        },
        {
            "type": "function_call",
            "call_id": "call_1",
            "name": "ListFiles",
            "arguments": '{"directory": "."}',
        },
        {
            "type": "function_call_output",
            "call_id": "call_1",
            "output": '{"files": ["a.py"]}',
        },
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Here are the files."}],
        },
    ]
    rows = _history_handler()._history_rows(shell)
    assert rows == [
        ("system", "sys"),
        ("user", "list files"),
        ("function_call", 'ListFiles({"directory": "."})'),
        ("function_call_output", '{"files": ["a.py"]}'),
        ("assistant", "Here are the files."),
    ]


def test_history_stateless_without_system_prompt():
    """Stateless Responses without a system prompt still renders the full
    conversation (messages_history is empty, items start with the user)."""
    shell = _shell()
    shell.messages_history = []
    shell.conversation_items = [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "hello"}],
        },
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "hi"}],
        },
    ]
    rows = _history_handler()._history_rows(shell)
    assert rows == [
        ("user", "hello"),
        ("assistant", "hi"),
    ]


# ---------------------------------------------------------------------------
# Server-side Responses (e.g. OpenAI): system prompt + pending items
# ---------------------------------------------------------------------------


def test_history_server_side_with_pending_items():
    """Server-side Responses keeps history on the server; /history shows the
    system prompt from messages_history plus any pending (Enter-cancelled)
    user messages carried in conversation_items."""
    shell = _shell()
    shell.messages_history = [{"role": "system", "content": "sys"}]
    shell.previous_response_id = "resp_1"
    shell.conversation_items = [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "hello"}],
        },
    ]
    rows = _history_handler()._history_rows(shell)
    assert rows == [
        ("system", "sys"),
        ("user", "hello"),
    ]


def test_history_server_side_renders_mirrored_turns():
    """Server-side Responses (e.g. OpenAI) keeps the real conversation on the
    server; /history renders the display-only client-side mirror of the
    completed turns (user/assistant text + tool-call rounds), followed by any
    pending (Enter-cancelled) messages."""
    shell = _shell()
    shell.messages_history = [{"role": "system", "content": "sys"}]
    shell.previous_response_id = "resp_2"
    shell.mirrored_history = [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "list files"}],
        },
        {
            "type": "function_call",
            "call_id": "call_1",
            "name": "ListFiles",
            "arguments": '{"directory": "."}',
        },
        {
            "type": "function_call_output",
            "call_id": "call_1",
            "output": '{"files": ["a.py"]}',
        },
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Here are the files."}],
        },
    ]
    shell.conversation_items = [
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "cancelled prompt"}],
        },
    ]
    rows = _history_handler()._history_rows(shell)
    assert rows == [
        ("system", "sys"),
        ("user", "list files"),
        ("function_call", 'ListFiles({"directory": "."})'),
        ("function_call_output", '{"files": ["a.py"]}'),
        ("assistant", "Here are the files."),
        ("user", "cancelled prompt"),
    ]


# ---------------------------------------------------------------------------
# Checkpoint markers
# ---------------------------------------------------------------------------


def test_history_checkpoint_markers_positions():
    """Checkpoint values map to the row they precede (Completions mode),
    numbered by their order in the checkpoint list."""
    shell = _shell()
    shell.messages_history = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
        {"role": "user", "content": "again"},
        {"role": "assistant", "content": "ok"},
    ]
    shell.history_checkpoints = [1, 3]
    handler = _history_handler()
    markers = handler._checkpoint_markers(shell, len(shell.messages_history))
    assert markers == {1: [1], 3: [2]}


def test_history_checkpoint_markers_keep_individual_ordinals():
    """The marker mapping keeps each checkpoint's own ordinal even when
    several checkpoints sit at the same display position (defensive: the
    normal flow records strictly increasing positions, but a manually
    seeded list may contain duplicates)."""
    shell = _shell()
    shell.messages_history = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    shell.history_checkpoints = [1, 1, 1]
    handler = _history_handler()
    markers = handler._checkpoint_markers(shell, len(shell.messages_history))
    assert markers == {1: [1, 2, 3]}


def test_history_checkpoint_markers_ignore_out_of_range():
    """Checkpoints beyond the current history (e.g. after a rollback that
    kept stale values) are ignored by the display."""
    shell = _shell()
    shell.messages_history = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
    ]
    shell.history_checkpoints = [1, 5]
    markers = _history_handler()._checkpoint_markers(shell, len(shell.messages_history))
    assert markers == {1: [1]}


def test_history_prints_checkpoint_marker_before_item(capsys):
    """A numbered marker line is rendered before the item each checkpoint
    precedes."""
    shell = _shell()
    shell.messages_history = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
        {"role": "user", "content": "again"},
        {"role": "assistant", "content": "ok"},
    ]
    shell.history_checkpoints = [1, 3]
    _history_handler()._print_history(shell)
    out = capsys.readouterr().out
    assert "◉ checkpoint 1" in out
    assert "◉ checkpoint 2" in out
    # The marker for the first turn appears before the first user message.
    assert out.index("◉ checkpoint 1") < out.index("hello")
    # The marker for the second turn appears before the second user message.
    assert out.rindex("◉ checkpoint 2") < out.rindex("again")
