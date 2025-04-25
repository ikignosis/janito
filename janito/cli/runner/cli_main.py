import sys
import socket
from janito.agent.profile_manager import AgentProfileManager
from janito.agent.runtime_config import unified_config, runtime_config
from janito.agent.config import get_api_key
from janito import __version__
from janito.agent.conversation_exceptions import (
    MaxRoundsExceededError,
    EmptyResponseError,
    ProviderError,
)


def is_port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) != 0


def run_cli(args):
    if args.version:
        print(f"janito version {__version__}")
        sys.exit(0)

    # --detect: exploratory workflow to detect core technologies
    if getattr(args, "detect", False):
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
    if args.role:
        runtime_config.set("role", args.role)
    if getattr(args, "model", None):
        runtime_config.set("model", args.model)
    if getattr(args, "max_tools", None) is not None:
        runtime_config.set("max_tools", args.max_tools)
    if getattr(args, "trust_tools", False):
        runtime_config.set("trust_tools", True)
    if not getattr(args, "prompt", None):
        interaction_mode = "chat"
    else:
        interaction_mode = "prompt"
    profile = getattr(args, "profile", None) or unified_config.get("profile", "default")
    profile_manager = AgentProfileManager(
        api_key=get_api_key(),
        model=unified_config.get("model"),
        role=role,
        profile=profile,
        interaction_mode=interaction_mode,
        verbose_tools=args.verbose_tools,
        base_url=unified_config.get("base_url", "https://openrouter.ai/api/v1"),
        azure_openai_api_version=unified_config.get(
            "azure_openai_api_version", "2023-05-15"
        ),
        use_azure_openai=unified_config.get("use_azure_openai", False),
    )
    profile_manager.refresh_prompt()
    if args.max_tokens is not None:
        runtime_config.set("max_tokens", args.max_tokens)

    # --- Liteweb integration ---
    termweb_proc = None
    selected_port = None
    if not getattr(args, "no_termweb", False) and interaction_mode == "chat":
        default_port = 8088
        max_port = 8100
        requested_port = args.termweb_port
        if requested_port == default_port:
            for port in range(default_port, max_port + 1):
                if is_port_free(port):
                    selected_port = port
                    break
            if selected_port is None:
                print(
                    f"[red]No free port found for termweb in range {default_port}-{max_port}.[/red]"
                )
                sys.exit(1)
        else:
            if not is_port_free(requested_port):
                print(f"[red]Port {requested_port} is not available for termweb.[/red]")
                sys.exit(1)
            selected_port = requested_port
        runtime_config.set("termweb_port", selected_port)
        from janito.cli.termweb_starter import start_termweb

        termweb_proc, started, termweb_stdout_path, termweb_stderr_path = start_termweb(
            selected_port
        )
        # Store last running port in .janito/config.json if started
        if started:
            from janito.agent.config import local_config

            local_config.set("termweb_last_running_port", selected_port)
            local_config.save()

    # --- End termweb integration ---
    try:
        if not getattr(args, "prompt", None):
            from janito.cli_chat_shell.chat_loop import start_chat_shell

            start_chat_shell(
                profile_manager,
                continue_session=getattr(args, "continue_session", False),
                termweb_stdout_path=(
                    termweb_stdout_path if "termweb_stdout_path" in locals() else None
                ),
                termweb_stderr_path=(
                    termweb_stderr_path if "termweb_stderr_path" in locals() else None
                ),
            )
            sys.exit(0)
        # --- Prompt mode ---
        prompt = args.prompt
        from rich.console import Console
        from janito.agent.rich_message_handler import RichMessageHandler

        console = Console()
        message_handler = RichMessageHandler()
        messages = []
        if profile_manager.system_prompt_template:
            messages.append(
                {"role": "system", "content": profile_manager.system_prompt_template}
            )
        messages.append({"role": "user", "content": prompt})
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
        from rich.console import Console

        console = Console()
        console.print("[yellow]Interrupted by user.[/yellow]")
    finally:
        if termweb_proc:
            termweb_proc.terminate()
            termweb_proc.wait()
