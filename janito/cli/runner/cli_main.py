import sys
from janito.agent.profile_manager import AgentProfileManager
from janito.agent.runtime_config import unified_config, runtime_config
from janito.agent.config import get_api_key
from janito import __version__
from .config import get_system_prompt_template
from janito.agent.conversation_exceptions import (
    MaxRoundsExceededError,
    EmptyResponseError,
    ProviderError,
)


def run_cli(args):
    if args.version:
        print(f"janito version {__version__}")
        sys.exit(0)

    # --configure: exploratory workflow to detect core technologies
    if getattr(args, "configure", False):
        import os
        from rich.console import Console

        console = Console()
        prompt_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "agent",
                "templates",
                "detect_tech_prompt.j2",
            )
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            detect_prompt = f.read()
        api_key = get_api_key()
        model = unified_config.get("model")
        base_url = unified_config.get("base_url", "https://openrouter.ai/api/v1")
        azure_openai_api_version = unified_config.get(
            "azure_openai_api_version", "2023-05-15"
        )
        use_azure_openai = unified_config.get("use_azure_openai", False)
        profile_manager = AgentProfileManager(
            api_key=api_key,
            model=model,
            role=unified_config.get("role", "software engineer"),
            profile=unified_config.get("profile", "default"),
            interaction_mode="prompt",
            verbose_tools=True,
            base_url=base_url,
            azure_openai_api_version=azure_openai_api_version,
            use_azure_openai=use_azure_openai,
        )
        agent = profile_manager.agent
        from janito.agent.rich_message_handler import RichMessageHandler

        message_handler = RichMessageHandler()
        messages = [{"role": "system", "content": detect_prompt}]
        console.print(
            ":mag: [bold]Configuring project: discovering core technologies...[/bold]"
        )
        result = agent.chat(
            messages,
            message_handler=message_handler,
            spinner=True,
            max_rounds=50,
            verbose_response=False,
            verbose_events=False,
            stream=False,
        )
        os.makedirs(".janito", exist_ok=True)
        tech_txt = os.path.join(".janito", "tech.txt")
        with open(tech_txt, "w", encoding="utf-8") as f:
            f.write(result["content"].strip() + "\n")
        console.print(
            f"[green]:white_check_mark: Core technologies detected and saved to [bold]{tech_txt}[/bold]"
        )
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

    # Set trust-tools mode if enabled
    if getattr(args, "trust_tools", False):
        runtime_config.set("trust_tools", True)

    # Get system prompt template (instructions/config logic)
    system_prompt_template = get_system_prompt_template(args, role)

    if args.show_system:
        api_key = get_api_key()
        model = unified_config.get("model")
        print(" Model:", model)
        print("Parameters: {}")
        print(
            "System Prompt Template:",
            system_prompt_template or "(default system prompt template not provided)",
        )
        sys.exit(0)

    api_key = get_api_key()
    model = unified_config.get("model")
    base_url = unified_config.get("base_url", "https://openrouter.ai/api/v1")
    azure_openai_api_version = unified_config.get(
        "azure_openai_api_version", "2023-05-15"
    )
    # Handle vanilla mode
    vanilla_mode = getattr(args, "vanilla", False)
    if vanilla_mode:
        runtime_config.set("vanilla_mode", True)
        system_prompt_template = None
        runtime_config.set("system_prompt_template", None)
        if args.temperature is None:
            runtime_config.set("temperature", None)
    else:
        runtime_config.set("vanilla_mode", False)

    profile = getattr(args, "profile", None) or unified_config.get("profile", "default")

    if not getattr(args, "prompt", None):
        interaction_mode = "chat"
    else:
        interaction_mode = "prompt"

    profile_manager = AgentProfileManager(
        api_key=api_key,
        model=model,
        role=role,
        profile=profile,
        interaction_mode=interaction_mode,
        verbose_tools=args.verbose_tools,
        base_url=base_url,
        azure_openai_api_version=azure_openai_api_version,
        use_azure_openai=unified_config.get("use_azure_openai", False),
    )
    profile_manager.refresh_prompt()

    if args.max_tokens is not None:
        runtime_config.set("max_tokens", args.max_tokens)

    if not getattr(args, "prompt", None):
        from janito.cli_chat_shell.chat_loop import start_chat_shell

        start_chat_shell(
            profile_manager, continue_session=getattr(args, "continue_session", False)
        )
        sys.exit(0)

    prompt = args.prompt
    console = Console()
    from janito.agent.rich_message_handler import RichMessageHandler

    message_handler = RichMessageHandler()
    messages = []
    if profile_manager.system_prompt_template:
        messages.append(
            {"role": "system", "content": profile_manager.system_prompt_template}
        )
    messages.append({"role": "user", "content": prompt})
    try:
        try:
            max_rounds = 50
            profile_manager.agent.chat(
                messages,
                message_handler=message_handler,
                spinner=True,
                max_rounds=max_rounds,
                verbose_response=getattr(args, "verbose_response", False),
                verbose_events=getattr(args, "verbose_events", False),
                stream=getattr(args, "stream", False),
            )
        except MaxRoundsExceededError:
            console.print("[red]Max conversation rounds exceeded.[/red]")
        except ProviderError as e:
            console.print(f"[red]Provider error:[/red] {e}")
        except EmptyResponseError as e:
            console.print(f"[red]Error:[/red] {e}")
    except KeyboardInterrupt:
        console.print("[yellow]Interrupted by user.[/yellow]")
