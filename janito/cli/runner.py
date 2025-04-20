import sys
from rich.console import Console
from janito.agent.profile_manager import AgentProfileManager

# Ensure all tools are registered at startup
import janito.agent.tools  # noqa: F401
from janito.agent.conversation import (
    MaxRoundsExceededError,
    EmptyResponseError,
    ProviderError,
)
from janito.agent.runtime_config import unified_config, runtime_config
from janito.agent.config import get_api_key
from janito import __version__


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
        runtime_config.set("role", args.role)

    # Set runtime_config['model'] if --model is provided (highest priority, session only)
    if getattr(args, "model", None):
        runtime_config.set("model", args.model)

    # Set runtime_config['max_tools'] if --max-tools is provided
    if getattr(args, "max_tools", None) is not None:
        runtime_config.set("max_tools", args.max_tools)

    # Set trust mode if enabled
    if getattr(args, "trust", False):
        runtime_config.set("trust", True)

    # New logic for --system-file
    system_prompt = None
    if getattr(args, "system_file", None):
        with open(args.system_file, "r", encoding="utf-8") as f:
            system_prompt = f.read()
        runtime_config.set("system_prompt_file", args.system_file)

    else:
        system_prompt = args.system or unified_config.get("system_prompt")
        if args.system:
            runtime_config.set("system_prompt", system_prompt)
        if system_prompt is None:
            # Pass full merged config (runtime overrides effective)

            from janito.render_prompt import render_system_prompt

            system_prompt = render_system_prompt(role)

    if args.show_system:
        api_key = get_api_key()
        # Always get model from unified_config (which checks runtime_config first)
        model = unified_config.get("model")
        print("Model:", model)
        print("Parameters: {}")
        import json

        print("System Prompt:", system_prompt or "(default system prompt not provided)")
        sys.exit(0)

    api_key = get_api_key()

    # Always get model from unified_config (which checks runtime_config first)
    model = unified_config.get("model")
    base_url = unified_config.get("base_url", "https://openrouter.ai/api/v1")
    azure_openai_api_version = unified_config.get(
        "azure_openai_api_version", "2023-05-15"
    )
    # Handle vanilla mode
    vanilla_mode = getattr(args, "vanilla", False)
    if vanilla_mode:
        runtime_config.set("vanilla_mode", True)
        system_prompt = None
        runtime_config.set("system_prompt", None)
        # Only set temperature if explicitly provided
        if args.temperature is None:
            runtime_config.set("temperature", None)
    else:
        runtime_config.set("vanilla_mode", False)
    interaction_style = getattr(args, "style", None) or unified_config.get(
        "interaction_style", "default"
    )
    profile_manager = AgentProfileManager(
        api_key=api_key,
        model=model,
        role=role,
        interaction_style=interaction_style,
        verbose_tools=args.verbose_tools,
        base_url=base_url,
        azure_openai_api_version=azure_openai_api_version,
        use_azure_openai=unified_config.get("use_azure_openai", False),
    )

    # Save runtime max_tokens override if provided
    if args.max_tokens is not None:
        runtime_config.set("max_tokens", args.max_tokens)

    # If no prompt is provided, enter shell loop mode
    if not getattr(args, "prompt", None):
        from janito.cli_chat_shell.chat_loop import start_chat_shell

        start_chat_shell(
            profile_manager, continue_session=getattr(args, "continue_session", False)
        )
        sys.exit(0)

    prompt = args.prompt

    console = Console()
    from janito.agent.rich_tool_handler import MessageHandler

    message_handler = MessageHandler()

    messages = []
    if profile_manager.system_prompt:
        messages.append({"role": "system", "content": profile_manager.system_prompt})

    messages.append({"role": "user", "content": prompt})

    try:
        try:
            max_rounds = runtime_config.get("max_rounds", 50)
            response = profile_manager.chat(
                messages,
                message_handler=message_handler,
                spinner=True,
                max_rounds=max_rounds,
                verbose_response=getattr(args, "verbose_response", False),
                verbose_events=getattr(args, "verbose_events", False),
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
