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

    # Set runtime_config['model'] if --model is provided (highest priority, session only)
    if getattr(args, 'model', None):
        runtime_config.set('model', args.model)

    # New logic for --system-file
    system_prompt = None
    if getattr(args, 'system_file', None):
        try:
            with open(args.system_file, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
            runtime_config.set('system_prompt_file', args.system_file)
        except Exception as e:
            print(f"[red]Failed to read system prompt file:[/red] {e}")
            sys.exit(1)
    else:
        system_prompt = args.system_prompt or unified_config.get("system_prompt")
        if args.system_prompt:
            runtime_config.set('system_prompt', system_prompt)
        if system_prompt is None:
            # Pass full merged config (runtime overrides effective)

            system_prompt = render_system_prompt(role)

    if args.show_system:
        api_key = get_api_key()
        # Always get model from unified_config (which checks runtime_config first)
        model = unified_config.get('model')
        agent = Agent(api_key=api_key, model=model)
        print("Model:", agent.model)
        print("Parameters: {}")
        import json
        print("System Prompt:", system_prompt or "(default system prompt not provided)")
        sys.exit(0)

    api_key = get_api_key()

    # Always get model from unified_config (which checks runtime_config first)
    model = unified_config.get('model')
    base_url = unified_config.get('base_url', 'https://openrouter.ai/api/v1')
    # Handle --enable-tools flag
    from janito.agent.tool_handler import ToolHandler
    tool_handler = ToolHandler(verbose=args.verbose_tools, enable_tools=not getattr(args, 'disable_tools', False))
    agent = Agent(api_key=api_key, model=model, system_prompt=system_prompt, verbose_tools=args.verbose_tools, base_url=base_url, tool_handler=tool_handler)

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
            max_rounds = runtime_config.get('max_rounds', 50)
            response = agent.chat(
                messages,
                on_content=on_content,
                spinner=True,
                max_rounds=max_rounds,
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
        console.print("[yellow]Interrupted by user.[/yellow]")
