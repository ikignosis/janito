import sys
import os
from rich.console import Console
from rich.markdown import Markdown
from janito.render_prompt import render_system_prompt
from janito.agent.agent import Agent
from janito.agent.conversation import MaxRoundsExceededError, EmptyResponseError, ProviderError
from janito.agent.runtime_config import unified_config, runtime_config
from janito.agent.config import get_api_key
from janito import __version__
from rich.rule import Rule


def format_tokens(n):
    if n is None:
        return "?"
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}m"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def run_cli(args):
    if args.version:
        print(f"janito version {__version__}")
        sys.exit(0)

    role = args.role or unified_config.get("role", "software engineer")
    # Ensure runtime_config is updated so chat shell sees the role
    if args.role:
        runtime_config.set('role', args.role)
    # if args.role:
    #     runtime_config.set('role', args.role)
    system_prompt = args.system_prompt or unified_config.get("system_prompt")
    if system_prompt is None:
        system_prompt = render_system_prompt(role)

    if args.show_system:
        api_key = get_api_key()
        model = unified_config.get('model')
        agent = Agent(api_key=api_key, model=model)
        print("Model:", agent.model)
        print("Parameters: {}")
        import json
        print("System Prompt:", system_prompt or "(default system prompt not provided)")
        sys.exit(0)

    api_key = get_api_key()

    model = unified_config.get('model')
    base_url = unified_config.get('base_url', 'https://openrouter.ai/api/v1')
    agent = Agent(api_key=api_key, model=model, system_prompt=system_prompt, verbose_tools=args.verbose_tools, base_url=base_url)

    # Save runtime max_tokens override if provided
    if args.max_tokens is not None:
        runtime_config.set('max_tokens', args.max_tokens)

    # If no prompt is provided, enter shell loop mode
    if not getattr(args, 'prompt', None):
        from janito.cli_chat_shell.chat_loop import start_chat_shell
        start_chat_shell(agent, continue_session=getattr(args, 'continue_session', False))
        sys.exit(0)

    prompt = args.prompt

    console = Console()

    def on_content(data):
        content = data.get("content", "")
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
                spinner=True,
            )
            if args.verbose_response:
                import json
                console.print_json(json.dumps(response))
        except MaxRoundsExceededError:
            print("[red]Max conversation rounds exceeded.[/red]")
        except ProviderError as e:
            print(f"[red]Provider error:[/red] {e}")
        except EmptyResponseError as e:
            print(f"[red]Error:[/red] {e}")
    except KeyboardInterrupt:
        print("[yellow]Interrupted by user.[/yellow]")
