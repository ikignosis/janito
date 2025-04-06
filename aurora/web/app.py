from flask import Flask, render_template, request, jsonify, make_response, Response
import os
import json
import uuid
from aurora.agent.agent import Agent

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

def some_function():  # placeholder for context
    # ... previous code ...

    # workaround: accumulate content and yield immediately
    def content_callback(content):
        for ev in stream_event({
            'command_id': command_id,
            'type': 'content',
            'content': content
        }):
            yield ev

    # since callbacks can't yield, we use a queue
    import queue
    q = queue.Queue()

    def enqueue_content(content):
        q.put(('content', content))

    def enqueue_progress(data):
        q.put(('tool_progress', data))

    # patch again with queue
    def patched_handle_tool_call_q(tool_call, **kwargs):
        if 'on_progress' not in kwargs:
            kwargs['on_progress'] = enqueue_progress
        return orig_handle_tool_call(tool_call, **kwargs)

    agent.tool_handler.handle_tool_call = patched_handle_tool_call_q

    def on_content_q(content):
        enqueue_content(content)

    import threading
    t = threading.Thread(target=agent.chat, args=(messages,), kwargs={'on_content': on_content_q})
    t.start()

    while t.is_alive() or not q.empty():
        pass  # placeholder for queue processing logic

# ... rest of the file ...
