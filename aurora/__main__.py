import os
import sys
import importlib.resources
from aurora.render_prompt import render_system_prompt
import argparse
import logging
from rich.console import Console
from rich.markdown import Markdown
from aurora.agent.agent import Agent
from aurora.agent.conversation import MaxRoundsExceededError
from aurora.agent.config import local_config, global_config, effective_config, get_api_key
from aurora import __version__


def main():
    parser = argparse.ArgumentParser(description="OpenRouter API call using OpenAI Python SDK")
    parser.add_argument("prompt", type=str, nargs="?", help="Prompt to send to the model")
    parser.add_argument("-s", "--system-prompt", type=str, default=None, help="Optional system prompt")
    parser.add_argument("-r", "--role", type=str, default=None, help="Role description for the system prompt")
    parser.add_argument("--verbose-http", action="store_true", help="Enable verbose HTTP logging")
    parser.add_argument("--verbose-http-raw", action="store_true", help="Enable raw HTTP wire-level logging")
    parser.add_argument("--verbose-response", action="store_true", help="Pretty print the full response object")
    parser.add_argument("--show-system", action="store_true", help="Show model, parameters, system prompt, and tool definitions, then exit")
    parser.add_argument("--verbose-tools", action="store_true", help="Print tool call parameters and results")
    parser.add_argument("--set-local-config", type=str, default=None, help='Set a local config key-value pair, format "key=val"')
    parser.add_argument("--set-global-config", type=str, default=None, help='Set a global config key-value pair, format "key=val"')
    parser.add_argument("--show-config", action="store_true", help="Show effective configuration and exit")
    parser.add_argument("--version", action="store_true", help="Show program's version number and exit")
    parser.add_argument("--chat", action="store_true", help="Enter interactive chat mode")

    args = parser.parse_args()

    if args.version:
        print(f"aurora version {__version__}")
        sys.exit(0)

    # Handle config set commands early and exit
    if args.set_local_config or args.set_global_config:
        if args.set_local_config:
            try:
                key, val = args.set_local_config.split("=", 1)
            except ValueError:
                print("Invalid format for --set-local-config, expected key=val")
                sys.exit(1)
            local_config.set(key.strip(), val.strip())
            local_config.save()
            print(f"Local config updated: {key.strip()} = {val.strip()}")

        if args.set_global_config:
            try:
                key, val = args.set_global_config.split("=", 1)
            except ValueError:
                print("Invalid format for --set-global-config, expected key=val")
                sys.exit(1)
            global_config.set(key.strip(), val.strip())
            global_config.save()
            print(f"Global config updated: {key.strip()} = {val.strip()}")

        sys.exit(0)

    # Handle show-config early and exit
    if args.show_config:
        keys = set(global_config.all().keys()) | set(local_config.all().keys())
        if not keys:
            print("No configuration found.")
        else:
            print("Effective configuration:")
            for key in sorted(keys):
                if key in local_config.all():
                    source = "local"
                    value = local_config.get(key)
                else:
                    source = "global"
                    value = global_config.get(key)
                print(f"{key} = {value}    (source: {source})")
        sys.exit(0)

    # Determine effective role
    role = args.role or effective_config.get("role", "software engineer")

    # Determine effective system prompt
    system_prompt = args.system_prompt or effective_config.get("system_prompt")
    if system_prompt is None:
        system_prompt = render_system_prompt(role)

    if args.show_system:
        api_key = get_api_key()
        agent = Agent(api_key=api_key)
        print("Model:", agent.model)
        print("Parameters: {}")
        print("System Prompt:", system_prompt or "(default system prompt not provided)")
        import json as _json
        print("Tool Definitions:")
        print(_json.dumps(agent.tool_handler.tools, indent=2))
        sys.exit(0)

    if args.verbose_http or args.verbose_http_raw:
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        httpx_logger.addHandler(handler)

    if args.verbose_http_raw:
        os.environ["HTTPX_LOG_LEVEL"] = "trace"

        httpcore_logger = logging.getLogger("httpcore")
        httpcore_logger.setLevel(logging.DEBUG)
        handler_core = logging.StreamHandler()
        handler_core.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        httpcore_logger.addHandler(handler_core)

        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        httpx_logger.addHandler(handler)

    api_key = get_api_key()

    agent = Agent(api_key=api_key, system_prompt=system_prompt, verbose_tools=args.verbose_tools)

    if args.chat:
        from aurora.chat import chat_loop
        chat_loop(agent)
        sys.exit(0)

    if not args.prompt:
        if os.name == "nt":
            print("Enter your prompt. Press Ctrl+Z then Enter to finish:")
        else:
            print("Enter your prompt. Press Ctrl+D to finish:")
        prompt = sys.stdin.read().strip()
        if not prompt:
            print("Error: No prompt provided.")
            sys.exit(1)
    else:
        prompt = args.prompt

    console = Console()

    def on_content(content):
        if not isinstance(content, str):
            raise TypeError(f"on_content() expected a string, got {type(content)}")
        console.print(Markdown(content))

    messages = []
    if agent.system_prompt:
        messages.append({"role": "system", "content": agent.system_prompt})

    messages.append({"role": "user", "content": prompt})

    try:
        try:
            response = agent.chat(
                messages,
                on_content=on_content,
            )
            if args.verbose_response:
                import json
                console.print_json(json.dumps(response))
        except MaxRoundsExceededError:
            print("[Error] Conversation exceeded maximum rounds.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n[Interrupted by user]")
        sys.exit(1)


if __name__ == "__main__":
    main()
