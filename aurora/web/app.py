from flask import Flask, request, render_template, Response
from queue import Queue
import json
from aurora.agent.queued_tool_handler import QueuedToolHandler
from aurora.agent.agent import Agent
from aurora.agent.config import get_api_key
import os
import threading

app = Flask(
    __name__,
    static_url_path='/static',
    static_folder=os.path.join(os.path.dirname(__file__), 'static')
)

# Global event queue for streaming
stream_queue = Queue()

# Create a QueuedToolHandler with the queue
queued_handler = QueuedToolHandler(stream_queue)

# Instantiate the Agent with the custom tool handler
agent = Agent(
    api_key=get_api_key(),
    tool_handler=queued_handler
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/execute_stream', methods=['POST'])
def execute_stream():
    data = request.get_json()
    user_input = data.get('input', '')

    def run_agent():
        agent.chat(
            [{"role": "user", "content": user_input}],
            on_content=lambda data: stream_queue.put({"type": "content", "content": data.get("content")})
        )
        # Signal end of stream
        stream_queue.put(None)

    threading.Thread(target=run_agent, daemon=True).start()

    def generate():
        while True:
            content = stream_queue.get()
            if content is None:
                break
            if isinstance(content, tuple) and content[0] == 'tool_progress':
                message = json.dumps({"type": "tool_progress", "data": content[1]})
            else:
                message = json.dumps(content)
            yield f"data: {message}\n\n"

    return Response(generate(), mimetype='text/event-stream')
