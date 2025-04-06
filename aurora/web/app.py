    data = request.get_json()
    user_input = data.get('input', '')

    event_queue = Queue()

    # Replace tool handler with queued version for this request
    queued_handler = QueuedToolHandler(event_queue)
    queued_handler.tools = agent.tool_handler.tools  # copy registered tools
    agent.tool_handler = queued_handler

    def on_content(content):
