from flask import Flask, render_template, request, jsonify, Response
import os
import json
import uuid
from queue import Queue
from aurora.agent.agent import Agent
from aurora.agent.queued_tool_handler import QueuedToolHandler
from aurora.agent.tool_handler import ToolHandler
from aurora.render_prompt import render_system_prompt

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


def generate_sse(agent_response_generator):
    """Helper generator to yield server-sent events from agent response."""
    for chunk in agent_response_generator:
        data = json.dumps({"content": chunk})
        yield f"data: {data}\n\n"


@app.route('/execute_stream', methods=['POST'])
def execute_stream():
    data = request.get_json()
    user_input = data.get('input', '')

    def agent_response():
        yield from agent.chat(user_input, stream=True)

    return Response(generate_sse(agent_response()), mimetype='text/event-stream')
