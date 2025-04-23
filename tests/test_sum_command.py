import types
from janito.cli_chat_shell.commands.sum import handle_sum


class DummyConsole:
    def __init__(self):
        self.outputs = []

    def print(self, msg):
        self.outputs.append(msg)


class DummyAgent:
    def chat(self, messages, **kwargs):
        # Always return a fixed summary for testing
        return {"content": "This is a summary of the conversation."}


def test_handle_sum_basic():
    console = DummyConsole()
    agent = DummyAgent()
    profile_manager = types.SimpleNamespace()
    state = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi! How can I help you?"},
            {"role": "user", "content": "Summarize this chat."},
        ]
    }
    handle_sum(console, state, profile_manager, agent)
    assert len(state["messages"]) == 2
    assert state["messages"][0]["role"] == "system"
    assert state["messages"][1]["role"] == "assistant"
    assert "summary" in state["messages"][1]["content"].lower()
    assert any("summarized" in o.lower() for o in console.outputs[-1:])


def test_handle_sum_not_enough():
    console = DummyConsole()
    agent = DummyAgent()
    profile_manager = types.SimpleNamespace()
    state = {"messages": [{"role": "user", "content": "Hi"}]}
    handle_sum(console, state, profile_manager, agent)
    assert len(state["messages"]) == 1
    assert any("not enough" in o.lower() for o in console.outputs)
