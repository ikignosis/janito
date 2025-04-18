class QueuedMessageHandler:
    def __init__(self, queue, *args, **kwargs):
        self._queue = queue

    def handle_message(self, msg, msg_type=None):
        # Unified: send content (assistant/LLM) messages to the frontend via queue
        if isinstance(msg, dict):
            msg_type = msg.get('type', 'info')
            message = msg.get('message', '')
        else:
            message = msg
            msg_type = msg_type or 'info'
        # For normal assistant/user/info messages, emit type 'content' for frontend compatibility
        if msg_type in ("info", "content"):
            self._queue.put({"type": "content", "content": message})
        else:
            self._queue.put({"type": msg_type, "message": message})

