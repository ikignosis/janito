class MessageHandler:
    def __init__(self, queue, *args, **kwargs):
        self._queue = queue

    def handle_tool_call(self, tool_call):
        # All output is routed through the unified message handler and queue
        return super().handle_tool_call(tool_call)

    def handle_message(self, msg, msg_type=None):
        # Unified: send content (agent/LLM) messages to the frontend
        if isinstance(msg, dict):
            msg_type = msg.get("type", "info")
            message = msg.get("message", "")
        else:
            message = msg
            msg_type = msg_type or "info"
        self._queue.put(("message", message, msg_type))
