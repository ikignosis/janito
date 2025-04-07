import sys
import os
from rich.console import Console
from rich.markdown import Markdown
from aurora.render_prompt import render_system_prompt
from aurora.agent.agent import Agent
from aurora.agent.conversation import MaxRoundsExceededError
from aurora.agent.config import effective_config, get_api_key
from aurora import __version__


def run_cli(args):
    if args.version:
        print(f"aurora version {__version__}")
        sys.exit(0)

    role = args.role or effective_config.get("role", "software engineer")

    system_prompt = args.system_prompt or effective_config.get("system_prompt")
    if system_prompt is None:
        system_prompt = render_system_prompt(role)

    if args.show_system:
        api_key = get_api_key()
        agent = Agent(api_key=api_key)
        print("Model:", agent.model)
        print("Parameters: {}")
        import json as _json
        print("System Prompt:", system_prompt or "(default system prompt not provided)")
        print("Tool Definitions:")
        print(_json.dumps(agent.tool_handler.tools, indent=2))
        sys.exit(0)

    api_key = get_api_key()

    agent = Agent(api_key=api_key, system_prompt=system_prompt, verbose_tools=args.verbose_tools)

    if not args.prompt:
        from aurora.cli_chat_shell.chat_shell import chat_loop
        chat_loop(agent, continue_session=getattr(args, 'continue_session', False))
        sys.exit(0)

    prompt = args.prompt

    console = Console()

    waiting_displayed = [True]
    print("Waiting for AI response...", end="", flush=True)

    def on_content(data):
        content = data.get("content", "")
        if waiting_displayed[0]:
            # Clear the waiting message
            sys.stdout.write("\r" + " " * len("Waiting for AI response...") + "\r")
            sys.stdout.flush()
            waiting_displayed[0] = False
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
