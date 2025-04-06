from flask import Flask, render_template, request, jsonify
import os
from aurora.agent.agent import Agent

app = Flask(__name__)

# Initialize Aurora agent
api_key = os.getenv('AURORA_API_KEY')
if not api_key:
    raise RuntimeError('AURORA_API_KEY environment variable not set')

agent = Agent(api_key=api_key)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/execute', methods=['POST'])
def execute():
    data = request.get_json()
    command = data.get('command')
    try:
        # Send the command as a message to the agent
        messages = [
            {"role": "user", "content": command}
        ]
        response = agent.chat(messages)
        # response can be a generator or dict, handle accordingly
        if hasattr(response, '__iter__') and not isinstance(response, dict):
            output = ''.join([chunk for chunk in response])
        else:
            output = response.get('content', str(response))
    except Exception as e:
        output = str(e)
    return jsonify({'output': output})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
