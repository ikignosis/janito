from flask import Flask, render_template, request, jsonify, make_response, Response
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

# (rest of the file remains unchanged)
