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
        self._queue.put(('message', message, msg_type))
