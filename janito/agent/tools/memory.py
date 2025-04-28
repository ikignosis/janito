from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.i18n import tr


@register_tool(name="memory")
class MemoryTool(ToolBase):
    """
    Simple in-memory key-value store for demonstration purposes.
    """

    def __init__(self):
        super().__init__()
        self.memory = {}

    def run(self, action: str, key: str, value: str = None) -> str:
        if action == "set":
            self.report_info(tr("ℹ️ Storing value for key: '{key}' ...", key=key))
            self.memory[key] = value
            msg = tr("Value stored for key: '{key}'.", key=key)
            self.report_success(msg)
            return msg
        elif action == "get":
            self.report_info(tr("ℹ️ Retrieving value for key: '{key}' ...", key=key))
            if key in self.memory:
                msg = tr(
                    "Value for key '{key}': {value}", key=key, value=self.memory[key]
                )
                self.report_success(msg)
                return msg
            else:
                msg = tr("Key '{key}' not found.", key=key)
                self.report_warning(msg)
                return msg
        elif action == "delete":
            if key in self.memory:
                del self.memory[key]
                msg = tr("Key '{key}' deleted.", key=key)
                self.report_success(msg)
                return msg
            else:
                msg = tr("Key '{key}' not found.", key=key)
                self.report_error(msg)
                return msg
        else:
            msg = tr("Unknown action: {action}", action=action)
            self.report_error(msg)
            return msg
