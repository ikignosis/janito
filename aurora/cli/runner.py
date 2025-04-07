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
        console = Console()

        if not getattr(args, 'continue_session', False):
            save_path = os.path.join('.aurora', 'last_conversation.json')
            if os.path.exists(save_path):
                try:
                    with open(save_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    messages = data.get('messages', [])
                    num_messages = len(messages)
                    console.print(f"[bold yellow]A previous conversation with {num_messages} messages was found.[/bold yellow]")

                    last_usage_info = data.get('last_usage_info')
                    if last_usage_info:
                        prompt_tokens = last_usage_info.get('prompt_tokens', 0)
                        completion_tokens = last_usage_info.get('completion_tokens', 0)
                        total_tokens = prompt_tokens + completion_tokens
                        def fmt(n):
                            if n >= 1_000_000:
                                return f"{n/1_000_000:.1f}m"
                            if n >= 1_000:
                                return f"{n/1_000:.1f}k"
                            return str(n)
                        console.print(f"Token usage - Prompt: {fmt(prompt_tokens)}, Completion: {fmt(completion_tokens)}, Total: {fmt(total_tokens)}")

                    console.print("You can resume it anytime by typing [bold]/continue[/bold].")
                except Exception:
                    pass  # Fail silently if file is corrupt or unreadable

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
