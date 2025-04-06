from flask import Flask, request, render_template, Response
from queue import Queue
from aurora.agent.queued_tool_handler import QueuedToolHandler
from aurora.agent.agent import Agent
from aurora.agent.config import get_api_key

app = Flask(__name__)

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

    def generate():
        # Use agent.chat() instead of deprecated agent.run()
        agent.chat(
            [{"role": "user", "content": user_input}],
            on_content=lambda content: stream_queue.put(content)
        )
        while True:
            content = stream_queue.get()
            if content is None:
                break
            yield f"data: {content}\n\n"

    return Response(generate(), mimetype='text/event-stream')
