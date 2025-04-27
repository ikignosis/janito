from flask import (
    Flask,
    request,
    Response,
    send_from_directory,
    jsonify,
    render_template,
)
from queue import Queue
import json
from janito.agent.queued_message_handler import QueuedMessageHandler
from janito.agent.profile_manager import AgentProfileManager
import os
import threading
import traceback
import sys

from janito.agent.runtime_config import unified_config, runtime_config

# Render system prompt from config
role = unified_config.get("role", "software engineer")
system_prompt_template_override = unified_config.get("system_prompt_template")
if system_prompt_template_override:
    system_prompt_template = system_prompt_template_override
else:
    profile_manager = AgentProfileManager(
        api_key=unified_config.get("api_key"),
        model=unified_config.get("model"),
        role=role,
        profile_name="base",
        interaction_mode=unified_config.get("interaction_mode", "prompt"),
        verbose_tools=runtime_config.get("verbose_tools", False),
        base_url=unified_config.get("base_url", None),
        azure_openai_api_version=unified_config.get(
            "azure_openai_api_version", "2023-05-15"
        ),
        use_azure_openai=unified_config.get("use_azure_openai", False),
    )
system_prompt_template = profile_manager.system_prompt_template

app = Flask(
    __name__,
    static_url_path="/static",
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)

# Secret key for session management
app.secret_key = "replace_with_a_secure_random_secret_key"

# Path for persistent conversation storage
conversation_file = os.path.expanduser("~/.janito/last_conversation_web.json")

# Initially no conversation loaded
conversation = None


# Global event queue for streaming
stream_queue = Queue()

# Create a QueuedMessageHandler with the queue
message_handler = QueuedMessageHandler(stream_queue)

# Instantiate the Agent with config-driven parameters (no tool_handler)
agent = profile_manager.agent


@app.route("/get_config")
def get_config():
    # Expose full config for the web app: defaults, effective, runtime (mask api_key)
    from janito.agent.runtime_config import (
        unified_config,
    )  # Kept here: avoids circular import at module level
    from janito.agent.config_defaults import CONFIG_DEFAULTS

    # Start with defaults
    config = dict(CONFIG_DEFAULTS)
    # Overlay effective config
    config.update(unified_config.effective_cfg.all())
    # Overlay runtime config (highest priority)
    config.update(unified_config.runtime_cfg.all())
    api_key = config.get("api_key")
    if api_key:
        config["api_key"] = (
            api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
        )
    return jsonify(config)


@app.route("/set_config", methods=["POST"])
def set_config():
    from janito.agent.runtime_config import runtime_config
    from janito.agent.config import CONFIG_OPTIONS
    from janito.agent.config_defaults import CONFIG_DEFAULTS

    data = request.get_json()
    key = data.get("key")
    value = data.get("value")
    if key not in CONFIG_OPTIONS:
        return (
            jsonify({"status": "error", "message": f"Invalid config key: {key}"}),
            400,
        )
    # Type coercion based on defaults
    default = CONFIG_DEFAULTS.get(key)
    if default is not None and value is not None:
        try:
            if isinstance(default, bool):
                value = bool(value)
            elif isinstance(default, int):
                value = int(value)
            elif isinstance(default, float):
                value = float(value)
            # else: leave as string or None
        except Exception as e:
            return (
                jsonify(
                    {"status": "error", "message": f"Invalid value type for {key}: {e}"}
                ),
                400,
            )
    runtime_config.set(key, value)
    # Mask api_key in response
    resp_value = value
    if key == "api_key" and value:
        resp_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
    return jsonify({"status": "ok", "key": key, "value": resp_value})


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/load_conversation")
def load_conversation():
    global conversation
    try:
        with open(conversation_file, "r", encoding="utf-8") as f:
            conversation = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        conversation = []
    return jsonify({"status": "ok", "conversation": conversation})


@app.route("/new_conversation", methods=["POST"])
def new_conversation():
    global conversation
    conversation = []
    return jsonify({"status": "ok"})


@app.route("/execute_stream", methods=["POST"])
def execute_stream():
    data = request.get_json()
    user_input = data.get("input", "")

    global conversation
    if conversation is None:
        # If no conversation loaded, start a new one
        conversation = []

    # Always start with the system prompt as the first message
    if not conversation or conversation[0]["role"] != "system":
        conversation.insert(0, {"role": "system", "content": system_prompt_template})

    # Append the new user message
    conversation.append({"role": "user", "content": user_input})

    def run_agent():
        try:
            response = agent.chat(conversation, message_handler=message_handler)
            if response and "content" in response:
                conversation.append(
                    {"role": "assistant", "content": response["content"]}
                )
            try:
                os.makedirs(os.path.dirname(conversation_file), exist_ok=True)
                with open(conversation_file, "w", encoding="utf-8") as f:
                    json.dump(conversation, f, indent=2)
            except Exception as e:
                print(f"Error saving conversation: {e}")
        except Exception as e:
            tb = traceback.format_exc()
            stream_queue.put({"type": "error", "error": str(e), "traceback": tb})
        finally:
            stream_queue.put(None)

    threading.Thread(target=run_agent, daemon=True).start()

    def generate():
        while True:
            content = stream_queue.get()
            if content is None:
                break
            if isinstance(content, tuple) and content[0] == "tool_progress":
                message = json.dumps({"type": "tool_progress", "data": content[1]})
            else:
                message = json.dumps(content)
            yield f"data: {message}\n\n"
            sys.stdout.flush()

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
        },
    )
