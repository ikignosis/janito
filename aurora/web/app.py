from flask import Flask, render_template, request, jsonify
import subprocess

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/execute', methods=['POST'])
def execute():
    data = request.get_json()
    command = data.get('command')
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        output = result.stdout + result.stderr
    except Exception as e:
        output = str(e)
    return jsonify({'output': output})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
