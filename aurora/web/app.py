from flask import Flask, request, render_template, Response, send_from_directory, session, jsonify
from queue import Queue
import json
from aurora.agent.queued_tool_handler import QueuedToolHandler
from aurora.agent.agent import Agent
from aurora.agent.config import get_api_key
from aurora.render_prompt import render_system_prompt
import os
import threading

# Render system prompt once
system_prompt = render_system_prompt("software engineer")

app = Flask(
    __name__,
    static_url_path='/static',
    static_folder=os.path.join(os.path.dirname(__file__), 'static')
)

# Secret key for session management
app.secret_key = 'replace_with_a_secure_random_secret_key'

# Path for persistent conversation storage
conversation_file = os.path.expanduser('~/.aurora/last_conversation_web.json')

# Initially no conversation loaded
conversation = None


# Global event queue for streaming
stream_queue = Queue()

# Create a QueuedToolHandler with the queue
queued_handler = QueuedToolHandler(stream_queue)

# Instantiate the Agent with the custom tool handler
agent = Agent(
    api_key=get_api_key(),
    tool_handler=queued_handler
)

@app.route('/get_model_name')
def get_model_name():
    return jsonify({"model": agent.model})


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/load_conversation')
def load_conversation():
    global conversation
    try:
        with open(conversation_file, 'r') as f:
            conversation = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        conversation = []
    return jsonify({'status': 'ok', 'conversation': conversation})

@app.route('/new_conversation', methods=['POST'])
def new_conversation():
    global conversation
    conversation = []
    return jsonify({'status': 'ok'})

@app.route('/execute_stream', methods=['POST'])
def execute_stream():
    data = request.get_json()
    user_input = data.get('input', '')

    global conversation
    if conversation is None:
        # If no conversation loaded, start a new one
        conversation = []

    # Always start with the system prompt as the first message
    if not conversation or conversation[0]['role'] != 'system':
        conversation.insert(0, {"role": "system", "content": system_prompt})

    # Append the new user message
    conversation.append({"role": "user", "content": user_input})

    def run_agent():
        response = agent.chat(
            conversation,
            on_content=lambda data: stream_queue.put({"type": "content", "content": data.get("content")})
        )
        if response and 'content' in response:
            conversation.append({"role": "assistant", "content": response['content']})
        try:
            os.makedirs(os.path.dirname(conversation_file), exist_ok=True)
            with open(conversation_file, 'w') as f:
                json.dump(conversation, f, indent=2)
        except Exception as e:
            print(f"Error saving conversation: {e}")
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
            import sys
            sys.stdout.flush()

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
            'Transfer-Encoding': 'chunked'
        }
    )
