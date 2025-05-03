import os
import json
from datetime import datetime
from typing import List, Any, Dict


class UserInputHistory:
    """
    Handles loading, saving, and appending of user input history for the shell.
    Each day's history is stored in a line-delimited JSON file (.json.log) under .janito/input_history/.
    Each line is a JSON dict, e.g., {"input": ..., "ts": ...}
    """

    def __init__(self, history_dir=None):
        self.history_dir = history_dir or os.path.join(".janito", "input_history")
        os.makedirs(self.history_dir, exist_ok=True)

    def _get_today_file(self):
        today_str = datetime.now().strftime("%y%m%d")
        return os.path.join(self.history_dir, f"{today_str}.json.log")

    def load(self) -> List[Dict[str, Any]]:
        """Load today's input history as a list of dicts."""
        history_file = self._get_today_file()
        history = []
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        history.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass
        return history

    def sanitize_surrogates(self, s):
        if isinstance(s, str):
            return s.encode("utf-8", errors="replace").decode("utf-8")
        return s

    def append(self, input_str: str):
        """Append a new input as a JSON dict to today's history file."""
        history_file = self._get_today_file()
        input_str = self.sanitize_surrogates(input_str)
        entry = {"input": input_str, "ts": datetime.now().isoformat()}
        with open(history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def save(self, history_list: List[Any]):
        """Overwrite today's history file with the given list (for compatibility)."""
        history_file = self._get_today_file()
        with open(history_file, "w", encoding="utf-8") as f:
            for item in history_list:
                if isinstance(item, dict):
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
                else:
                    entry = {"input": str(item), "ts": datetime.now().isoformat()}
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
