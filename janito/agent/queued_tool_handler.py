from janito.agent.tool_handler import ToolHandler

class QueuedToolHandler(ToolHandler):
    def __init__(self, queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._queue = queue

    def handle_tool_call(self, tool_call, on_progress=None):
        def enqueue_progress(data):
            
            self._queue.put(('tool_progress', data))

        if on_progress is None:
            on_progress = enqueue_progress

        return super().handle_tool_call(tool_call, on_progress=on_progress)
