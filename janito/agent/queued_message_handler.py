class QueuedMessageHandler:
    def __init__(self, queue, *args, **kwargs):
        self._queue = queue

    def handle_message(self, msg, msg_type=None):
        # Unified: send content (agent/LLM) messages to the frontend via queue
        if isinstance(msg, dict):
            msg_type = msg.get('type', 'info')
            # For tool_call and tool_result, print and forward the full dict
            if msg_type in ("tool_call", "tool_result"):
                print(f"[QueuedMessageHandler] {msg_type}: {msg}")
                self._queue.put(msg)
                return
            message = msg.get('message', '')
        else:
            message = msg
            msg_type = msg_type or 'info'
        # For normal agent/user/info messages, emit type 'content' for frontend compatibility
        print(f"[QueuedMessageHandler] {msg_type}: {message}")
        if msg_type == "content":
            self._queue.put({"type": "content", "content": message})
        elif msg_type == "info":
            out = {"type": "info", "message": message}
            if 'tool' in msg:
                out["tool"] = msg["tool"]
            self._queue.put(out)
        else:
            out = {"type": msg_type, "message": message}
            if 'tool' in msg:
                out["tool"] = msg["tool"]
            self._queue.put(out)

