import os
import json
from datetime import datetime


def load_last_summary(path=".janito/last_conversation.json"):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def load_last_conversation(path=".janito/last_conversation.json"):
    if not os.path.exists(path):
        return [], [], None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    messages = data.get("messages", [])
    prompts = data.get("prompts", [])
    usage = data.get("last_usage_info")
    return messages, prompts, usage


def save_conversation(
    messages, prompts, usage_info=None, path=".janito/last_conversation.json"
):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {"messages": messages, "prompts": prompts, "last_usage_info": usage_info}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_input_history():
    history_dir = os.path.join(".janito", "input_history")
    os.makedirs(history_dir, exist_ok=True)
    today_str = datetime.now().strftime("%y%m%d")
    history_file = os.path.join(history_dir, f"{today_str}.json")
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_input_history(history_list):
    history_dir = os.path.join(".janito", "input_history")
    os.makedirs(history_dir, exist_ok=True)
    today_str = datetime.now().strftime("%y%m%d")
    history_file = os.path.join(history_dir, f"{today_str}.json")
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history_list, f, indent=2)


def last_conversation_exists(path=".janito/last_conversation.json"):
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        messages = data.get("messages", [])
        return bool(messages)
    except Exception:
        return False
