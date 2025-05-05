from typing import List, Dict, Optional
import json
import sys
import traceback


class LLMConversationHistory:
    """
    Manages the message history for a conversation, supporting OpenAI-style roles.
    Intended to be used by ConversationHandler and chat loop for all history operations.
    """

    def __init__(self, messages: Optional[List[Dict]] = None):
        self._messages = messages.copy() if messages else []

    def add_message(self, message: Dict):
        """Append a message dict to the history."""
        content = message.get("content")
        if isinstance(content, str) and any(
            0xD800 <= ord(ch) <= 0xDFFF for ch in content
        ):
            print(
                f"Surrogate code point detected in message content: {content!r}\nStack trace:\n{''.join(traceback.format_stack())}",
                file=sys.stderr,
            )
        self._messages.append(message)

    def get_messages(self, role: Optional[str] = None) -> List[Dict]:
        """
        Return all messages, or only those matching a given role/type (e.g., 'assistant', 'user', 'tool').
        If role is None, returns all messages.
        """
        if role is None:
            return self._messages.copy()
        return [msg for msg in self._messages if msg.get("role") == role]

    def clear(self):
        """Remove all messages from history."""
        self._messages.clear()

    def set_system_message(self, content: str):
        """
        Replace the first system prompt message, or insert if not present.
        """
        system_idx = next(
            (i for i, m in enumerate(self._messages) if m.get("role") == "system"), None
        )
        system_msg = {"role": "system", "content": content}
        if isinstance(content, str) and any(
            0xD800 <= ord(ch) <= 0xDFFF for ch in content
        ):
            print(
                f"Surrogate code point detected in system message content: {content!r}\nStack trace:\n{''.join(traceback.format_stack())}",
                file=sys.stderr,
            )
        if system_idx is not None:
            self._messages[system_idx] = system_msg
        else:
            self._messages.insert(0, system_msg)

    def to_json_file(self, path: str):
        """Save the conversation history as a JSON file to the given path."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.get_messages(), f, indent=2, ensure_ascii=False)

    def __len__(self):
        return len(self._messages)

    def __getitem__(self, idx):
        return self._messages[idx]
