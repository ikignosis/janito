"""
In-memory memory tools for storing and retrieving reusable information during an agent session.
These tools allow the agent to remember and recall arbitrary key-value pairs for the duration of the process.
"""

from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool

# Simple in-memory store (process-local, not persistent)
_memory_store = {}


@register_tool(name="store_memory")
class StoreMemoryTool(ToolBase):
    """
    Store a value for later retrieval using a key. Use this tool to remember information that may be useful in future steps or requests.

    Args:
        key (str): The identifier for the value to store.
        value (str): The value to store for later retrieval.
    Returns:
        str: Status message indicating success or error. Example:
            - "✅ Stored value for key: 'foo'"
            - "❗ Error storing value: ..."
    """

    def call(self, key: str, value: str) -> str:
        self.report_info(f"Storing value for key: '{key}' ...")
        try:
            _memory_store[key] = value
            msg = f"✅ Stored value for key: '{key}'"
            self.report_success(msg)
            return msg
        except Exception as e:
            msg = f"❗ Error storing value: {e}"
            self.report_error(msg)
            return msg


@register_tool(name="retrieve_memory")
class RetrieveMemoryTool(ToolBase):
    """
    Retrieve a value previously stored using a key. Use this tool to recall information remembered earlier in the session.

    Args:
        key (str): The identifier for the value to retrieve.
    Returns:
        str: The stored value, or a warning message if not found. Example:
            - "🔎 Retrieved value for key: 'foo': bar"
            - "⚠️ No value found for key: 'notfound'"
    """

    def call(self, key: str) -> str:
        self.report_info(f"Retrieving value for key: '{key}' ...")
        try:
            if key in _memory_store:
                value = _memory_store[key]
                msg = f"🔎 Retrieved value for key: '{key}': {value}"
                self.report_success(msg)
                return msg
            else:
                msg = f"⚠️ No value found for key: '{key}'"
                self.report_warning(msg)
                return msg
        except Exception as e:
            msg = f"❗ Error retrieving value: {e}"
            self.report_error(msg)
            return msg
