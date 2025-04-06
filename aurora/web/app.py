from flask import Flask, render_template, request, jsonify, Response
import os
import json
import uuid
from queue import Queue, Empty
from threading import Thread
from aurora.agent.agent import Agent
from aurora.agent.queued_tool_handler import QueuedToolHandler
from aurora.agent.tool_handler import ToolHandler
from aurora.render_prompt import render_system_prompt
import time

app = Flask(__name__)

# Initialize Aurora agent
api_key = os.getenv('OPENROUTER_API_KEY')
if not api_key:
    raise RuntimeError('OPENROUTER_API_KEY environment variable not set')

role = None  # Default role, can customize later
system_prompt = render_system_prompt(role)

agent = Agent(api_key=api_key, system_prompt=system_prompt)

# Register all known tools with the agent's tool handler
for tool_entry in ToolHandler._tool_registry.values():
    agent.tool_handler.register(tool_entry['function'])


@app.route('/')
def index():
    return render_template('index.html')


def stream_events(queue):
    """Generator yielding SSE events from a queue until 'DONE' sentinel received."""
    while True:
        try:
            event = queue.get(timeout=0.1)
            if event == 'DONE':
                break
            data = json.dumps(event)
            yield f"data: {data}\n\n"
        except Empty:
            continue


@app.route('/execute_stream', methods=['POST'])
def execute_stream():
    data = request.get_json()
    user_input = data.get('input', '')

    event_queue = Queue()

    # Replace tool handler with queued version for this request
    queued_handler = QueuedToolHandler(event_queue)
    queued_handler._tools = agent.tool_handler._tools  # copy registered tools
    agent.tool_handler = queued_handler

    def on_content(content):
        event_queue.put({"type": "content", "data": content})

    def run_agent():
        try:
            agent.chat(user_input, on_content=on_content, on_tool_progress=None)
        finally:
            event_queue.put('DONE')

    # Run agent in background thread
    Thread(target=run_agent, daemon=True).start()

    return Response(stream_events(event_queue), mimetype='text/event-stream')
