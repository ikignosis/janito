from flask import Flask, render_template, request, jsonify, make_response, Response
import os
import json
import uuid
from queue import Queue
from aurora.agent.agent import Agent
from aurora.agent.queued_tool_handler import QueuedToolHandler

app = Flask(__name__)

# Initialize Aurora agent
api_key = os.getenv('OPENROUTER_API_KEY')
if not api_key:
    raise RuntimeError('OPENROUTER_API_KEY environment variable not set')

agent = Agent(api_key=api_key)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/execute', methods=['POST'])
def execute():
    # Your existing logic
    pass

@app.route('/execute_stream', methods=['POST'])
def execute_stream():
    data = request.get_json()
    messages = data.get('messages', [])

    q = Queue()
    # Replace the tool handler with queued version
    agent.tool_handler = QueuedToolHandler(q, verbose=True)

    def enqueue_content(content):
        q.put(('content', content))

    def on_content_q(content):
        enqueue_content(content)

    import threading
    t = threading.Thread(target=agent.chat, args=(messages,), kwargs={'on_content': on_content_q})
    t.start()

    def generate():
        while t.is_alive() or not q.empty():
            try:
                event_type, payload = q.get(timeout=0.1)
                if event_type == 'content':
                    yield f"data: {json.dumps({'type': 'content', 'payload': payload})}\n\n"
                elif event_type == 'tool_progress':
                    yield f"data: {json.dumps({'type': 'tool_progress', 'payload': payload})}\n\n"
            except Exception:
                continue

    return Response(generate(), mimetype='text/event-stream')

@app.route('/favicon.ico')
def favicon():
    return '', 204
