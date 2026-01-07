import threading
import os
from typing import Any, Dict, List


def normalize_path(path: str) -> str:
    if not isinstance(path, str):
        return path
    return os.path.normcase(os.path.abspath(path))


class ToolUseTracker:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._history = []
        return cls._instance

    def record(self, tool_name: str, params: Dict[str, Any], result: Any = None):
        # Normalize path in params if present
        norm_params = params.copy()
        if "path" in norm_params:
            norm_params["path"] = normalize_path(norm_params["path"])
        self._history.append(
            {"tool": tool_name, "params": norm_params, "result": result}
        )

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._history)

    def get_operations_on_file(self, path: str) -> List[Dict[str, Any]]:
        norm_path = normalize_path(path)
        ops = []
        for entry in self._history:
            params = entry["params"]
            # Normalize any string param values for comparison
            for v in params.values():
                if isinstance(v, str) and normalize_path(v) == norm_path:
                    ops.append(entry)
                    break
        return ops

    def file_fully_read(self, path: str) -> bool:
        norm_path = normalize_path(path)
        for entry in self._history:
            if entry["tool"] == "view_file":
                params = entry["params"]
                if "path" in params and normalize_path(params["path"]) == norm_path:
                    # If both from_line and to_line are None, full file was read
                    if (
                        params.get("from_line") is None
                        and params.get("to_line") is None
                    ):
                        return True
        return False

    def last_operation_is_full_read_or_replace(self, path: str) -> bool:
        ops = self.get_operations_on_file(path)
        if not ops:
            return False
        last = ops[-1]
        if last["tool"] == "view_file":
            params = last["params"]
            if params.get("from_line") is None and params.get("to_line") is None:
                return True
        return False

    def clear_history(self):
        self._history.clear()

    @classmethod
    def instance(cls):
        return cls()
