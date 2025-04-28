from janito.i18n import tr


class QueuedMessageHandler:
    def __init__(self, queue, *args, **kwargs):
        self._queue = queue

    def handle_message(self, msg, msg_type=None):
        # Unified: send content (agent/LLM) messages to the frontend via queue
        if not isinstance(msg, dict):
            raise TypeError(
                tr(
                    "QueuedMessageHandler.handle_message expects a dict with 'type' and 'message', got {msg_type}: {msg!r}",
                    msg_type=type(msg),
                    msg=msg,
                )
            )
        msg_type = msg.get("type", "info")
        # For tool_call and tool_result, print and forward the full dict
        if msg_type in ("tool_call", "tool_result"):
            print(
                tr(
                    "[QueuedMessageHandler] {msg_type}: {msg}",
                    msg_type=msg_type,
                    msg=msg,
                )
            )
            self._queue.put(msg)
            return
        message = msg.get("message", "")
        # For normal agent/user/info messages, emit type 'content' for frontend compatibility
        print(
            tr(
                "[QueuedMessageHandler] {msg_type}: {message}",
                msg_type=msg_type,
                message=message,
            )
        )
        if msg_type == "content":
            self._queue.put({"type": "content", "content": message})
        elif msg_type == "info":
            out = {"type": "info", "message": message}
            if "tool" in msg:
                out["tool"] = msg["tool"]
            self._queue.put(out)
        else:
            out = {"type": msg_type, "message": message}
            if "tool" in msg:
                out["tool"] = msg["tool"]
            self._queue.put(out)
