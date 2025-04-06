from flask import Flask, render_template, request, jsonify
import os
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
def execute():
    try:
        data = request.get_json()
        command = data.get('command', '').strip()
        if not command:
            return jsonify({'output': 'Error: No command provided'}), 400

        messages = []
        if agent.system_prompt:
            messages.append({"role": "system", "content": agent.system_prompt})
        messages.append({"role": "user", "content": command})

        result = agent.chat(messages)
        return jsonify({'output': result})
    except Exception as e:
        print(f"Error during execution: {e}")
        return jsonify({'output': f"Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
