from janito.agent.message_handler_protocol import MessageHandlerProtocol


class QueueMessageHandler(MessageHandlerProtocol):
    def __init__(self, queue, *args, **kwargs):
        self._queue = queue

    def handle_tool_call(self, tool_call):
        # All output is routed through the unified message handler and queue
        return super().handle_tool_call(tool_call)

    def handle_message(self, msg, msg_type=None):
        # Unified: send content (agent/LLM) messages to the frontend
        if not isinstance(msg, dict):
            raise TypeError(
                f"QueueMessageHandler.handle_message expects a dict with 'type' and 'message', got {type(msg)}: {msg!r}"
            )
        msg_type = msg.get("type", "info")
        message = msg.get("message", "")
        self._queue.put(("message", message, msg_type))
