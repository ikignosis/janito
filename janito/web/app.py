from flask import (
    Flask,
    request,
    send_from_directory,
    jsonify,
    render_template,
)
import json
from janito.agent.profile_manager import AgentProfileManager
import os

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
