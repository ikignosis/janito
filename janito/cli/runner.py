import sys
import os
from rich.console import Console
from rich.markdown import Markdown
from janito.render_prompt import render_system_prompt
from janito.agent.agent import Agent
from janito.agent.conversation import MaxRoundsExceededError, EmptyResponseError, ProviderError
from janito.agent.config import effective_config, get_api_key
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

    role = args.role or effective_config.get("role", "software engineer")
    if args.role:
        runtime_config.set('role', args.role)

    system_prompt = args.system_prompt or effective_config.get("system_prompt")
    if system_prompt is None:
        system_prompt = render_system_prompt(role)

    if args.show_system:
        api_key = get_api_key()
        agent = Agent(api_key=api_key)
        print("Model:", agent.model)
        print("Parameters: {}")
        import json
        print("System Prompt:", system_prompt or "(default system prompt not provided)")
        sys.exit(0)

    api_key = get_api_key()

    model = effective_config.get('model')
    base_url = effective_config.get('base_url', 'https://openrouter.ai/api/v1')
    agent = Agent(api_key=api_key, model=model if model else 'openrouter/optimus-alpha', system_prompt=system_prompt, verbose_tools=args.verbose_tools, base_url=base_url)

    # Save runtime max_tokens override if provided
    if args.max_tokens is not None:
        runtime_config.set('max_tokens', args.max_tokens)

    if not args.prompt:
        console = Console()

        if not getattr(args, 'continue_session', False):
            save_path = os.path.join('.janito', 'last_conversation.json')
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
                        console.print(Rule(f"Token usage - Prompt: {format_tokens(prompt_tokens)}, Completion: {format_tokens(completion_tokens)}, Total: {format_tokens(total_tokens)}"))

                    console.print("You can resume it anytime by typing [bold]/continue[/bold].")
                except Exception:
                    pass  # Fail silently if file is corrupt or unreadable

        from janito.cli_chat_shell.chat_loop import start_chat_shell
        start_chat_shell(agent, continue_session=getattr(args, 'continue_session', False))
        sys.exit(0)

    prompt = args.prompt

    console = Console()

    waiting_displayed = [True]

    def on_content(data):
        content = data.get("content", "")
        if waiting_displayed[0]:
            # Clear the waiting message
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
                spinner=True,
            )
            if args.verbose_response:
                import json
                console.print_json(json.dumps(response))

            usage = response.get('usage')
            if usage:
                prompt_tokens = usage.get('prompt_tokens')
                completion_tokens = usage.get('completion_tokens')
                total_tokens = usage.get('total_tokens')
                console.print(Rule(f"Token usage - Prompt: {format_tokens(prompt_tokens)}, Completion: {format_tokens(completion_tokens)}, Total: {format_tokens(total_tokens)}"))
        except MaxRoundsExceededError:
            print("[Error] Conversation exceeded maximum rounds.")
            sys.exit(1)
        except ProviderError as e:
            print(f"[Error] Provider error: {e}")
            sys.exit(1)
        except EmptyResponseError as e:
            print(f"[Error] {e}")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n[Interrupted by user]")
        sys.exit(1)
