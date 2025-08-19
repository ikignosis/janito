import time
import threading
from typing import Dict, List, Tuple
from janito.tools.tool_use_tracker import normalize_path


class LoopProtection:
    """
    Provides loop protection for tool calls by tracking repeated operations
    on the same resources within a short time period.

    This class monitors file operations and prevents excessive reads on the same
    file within a configurable time window. It helps prevent infinite loops or
    excessive resource consumption when tools repeatedly access the same files.

    The default configuration allows up to 5 operations on the same file within
    a 10-second window. Operations outside this window are automatically cleaned
    up to prevent memory accumulation.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_protection()
        return cls._instance

    def _init_protection(self):
        # Track file operations: {normalized_path: [(timestamp, operation_type), ...]}
        self._file_operations: Dict[str, List[Tuple[float, str]]] = {}
        # Time window for detecting loops (in seconds)
        self._time_window = 10.0
        # Maximum allowed operations on the same file within time window
        self._max_operations = 5

        """
        Configuration parameters:
        
        _time_window: Time window in seconds for detecting excessive operations.
                     Default is 10.0 seconds.
                     
        _max_operations: Maximum number of operations allowed on the same file
                        within the time window. Default is 5 operations.
        """

    def check_file_operation_limit(self, path: str, operation_type: str) -> bool:
        """
        Check if performing an operation on a file would exceed the limit.

        This method tracks file operations and prevents excessive reads on the same
        file within a configurable time window (default 10 seconds). It helps prevent
        infinite loops or excessive resource consumption when tools repeatedly access
        the same files.

        Args:
            path: The file path being operated on
            operation_type: Type of operation (e.g., "view_file", "read_files")

        Returns:
            bool: True if operation is allowed, False if it would exceed the limit

        Example:
            >>> loop_protection = LoopProtection.instance()
            >>> if loop_protection.check_file_operation_limit("/path/to/file.txt", "view_file"):
            ...     # Safe to proceed with file operation
            ...     content = read_file("/path/to/file.txt")
            ... else:
            ...     # Would exceed limit - potential loop detected
            ...     raise RuntimeError("Too many operations on the same file")
        """
        norm_path = normalize_path(path)
        current_time = time.time()

        # Clean up old operations outside the time window
        if norm_path in self._file_operations:
            self._file_operations[norm_path] = [
                (timestamp, op_type)
                for timestamp, op_type in self._file_operations[norm_path]
                if current_time - timestamp <= self._time_window
            ]

        # Check if we're exceeding the limit
        if norm_path in self._file_operations:
            operations = self._file_operations[norm_path]
            if len(operations) >= self._max_operations:
                # Check if all recent operations are within the time window
                if all(
                    current_time - timestamp <= self._time_window
                    for timestamp, _ in operations
                ):
                    return False  # Would exceed limit - potential loop

        # Record this operation
        if norm_path not in self._file_operations:
            self._file_operations[norm_path] = []
        self._file_operations[norm_path].append((current_time, operation_type))

        return True  # Operation allowed

    def reset_tracking(self):
        """
        Reset all tracking data.

        This method clears all recorded file operations, effectively resetting
        the loop protection state. This can be useful in testing scenarios or
        when you want to explicitly clear the tracking history.
        """
        with self._lock:
            self._file_operations.clear()

    @classmethod
    def instance(cls):
        return cls()
