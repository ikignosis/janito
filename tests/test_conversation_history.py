from janito.agent.conversation_history import ConversationHistory


def test_add_and_get_messages():
    history = ConversationHistory()
    assert history.get_messages() == []
    history.add_message({"role": "user", "content": "hi"})
    history.add_message({"role": "assistant", "content": "hello"})
    msgs = history.get_messages()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"


def test_get_messages_by_role():
    history = ConversationHistory(
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
    )
    user_msgs = history.get_messages("user")
    assert len(user_msgs) == 1
    assert user_msgs[0]["content"] == "hi"
    assistant_msgs = history.get_messages("assistant")
    assert len(assistant_msgs) == 1
    assert assistant_msgs[0]["content"] == "hello"
    system_msgs = history.get_messages("system")
    assert len(system_msgs) == 1
    assert system_msgs[0]["content"] == "sys"


def test_clear():
    history = ConversationHistory(
        [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
    )
    history.clear()
    assert history.get_messages() == []


def test_set_system_message_replace_and_insert():
    # Replace existing
    history = ConversationHistory(
        [
            {"role": "system", "content": "old"},
            {"role": "user", "content": "hi"},
        ]
    )
    history.set_system_message("new")
    msgs = history.get_messages()
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "new"
    # Insert if not present
    history = ConversationHistory(
        [
            {"role": "user", "content": "hi"},
        ]
    )
    history.set_system_message("sys")
    msgs = history.get_messages()
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "sys"
    assert msgs[1]["role"] == "user"
