from .session_manager import (
    load_last_conversation,
    load_input_history,
    save_conversation,
    save_input_history,
)
from prompt_toolkit.history import InMemoryHistory


def load_chat_state(continue_session: bool):
    messages = []
    last_usage_info = None
    last_elapsed = None
    history_list = load_input_history()
    mem_history = InMemoryHistory()
    for item in history_list:
        mem_history.append_string(item)
    if continue_session:
        msgs, prompts, usage = load_last_conversation()
        messages = msgs
        last_usage_info = usage
        mem_history = InMemoryHistory()
        for item in prompts:
            mem_history.append_string(item)
    state = {
        "messages": messages,
        "mem_history": mem_history,
        "history_list": history_list,
        "last_usage_info": last_usage_info,
        "last_elapsed": last_elapsed,
    }
    return state


def save_chat_state(messages, mem_history, last_usage_info):
    prompts = [h for h in mem_history.get_strings()]
    save_conversation(messages, prompts, last_usage_info)
    save_input_history(prompts)
