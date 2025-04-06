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

@app.route('/execute_stream', methods=['POST'])
def execute_stream():
    try:
        data = request.get_json()
        command = data.get('command', '').strip()
        if not command:
            return jsonify({'error': 'No command provided'}), 400

        command_id = str(uuid.uuid4())

        messages = []
        if agent.system_prompt:
            messages.append({"role": "system", "content": agent.system_prompt})
        messages.append({"role": "user", "content": command})

        def generate():
            try:
                def stream_event(payload_dict):
                    payload = json.dumps(payload_dict)
                    yield f"data: {payload}\n\n"

                def on_content(content):
                    yield from stream_event({
                        'command_id': command_id,
                        'type': 'content',
                        'content': content
                    })

                def on_tool_progress(progress_data):
                    yield from stream_event({
                        'command_id': command_id,
                        'type': 'tool_progress',
                        'progress': progress_data
                    })

                # patch tool handler to pass on_progress
                orig_handle_tool_call = agent.tool_handler.handle_tool_call

                def patched_handle_tool_call(tool_call, **kwargs):
                    return orig_handle_tool_call(tool_call, on_progress=lambda data: [
                        (_ for _ in ()).throw(StopIteration) if False else next(stream_event({
                            'command_id': command_id,
                            'type': 'tool_progress',
                            'progress': data
                        }), None)
                    ], **kwargs)

                agent.tool_handler.handle_tool_call = patched_handle_tool_call

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
                    return orig_handle_tool_call(tool_call, on_progress=enqueue_progress, **kwargs)

                agent.tool_handler.handle_tool_call = patched_handle_tool_call_q

                def on_content_q(content):
                    enqueue_content(content)

                import threading
                t = threading.Thread(target=agent.chat, args=(messages,), kwargs={'on_content': on_content_q})
                t.start()

                while t.is_alive() or not q.empty():
                    try:
                        event_type, data_obj = q.get(timeout=0.1)
                        if event_type == 'content':
                            yield from stream_event({
                                'command_id': command_id,
                                'type': 'content',
                                'content': data_obj
                            })
                        elif event_type == 'tool_progress':
                            yield from stream_event({
                                'command_id': command_id,
                                'type': 'tool_progress',
                                'progress': data_obj
                            })
                    except queue.Empty:
                        continue

            except Exception as e:
                error_payload = json.dumps({'command_id': command_id, 'error': str(e)})
                yield f"data: {error_payload}\n\n"

        return Response(generate(), mimetype='text/event-stream')

    except Exception as e:
        print(f"Error during streaming execution: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/favicon.ico')
def favicon():
    return make_response('', 204)

if __name__ == '__main__':
    app.run(debug=True)
