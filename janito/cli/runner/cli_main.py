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

    # Set vanilla mode if -V/--vanilla is passed
    if getattr(args, "vanilla", False):
        runtime_config.set("vanilla_mode", True)

    # Set no_tools_tracking if --ntt is passed
    if getattr(args, "ntt", False):
        runtime_config.set("no_tools_tracking", True)
    # Normalize all verbose flags into runtime_config
    for flag in [
        "verbose_http",
        "verbose_http_raw",
        "verbose_response",
        "verbose_reason",
        "verbose_tools",
        "verbose_events",
        "verbose_stream",
    ]:
        if hasattr(args, flag):
            runtime_config.set(flag, getattr(args, flag, False))

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
    profile = "base"
    # PATCH: Pass lang from args or runtime_config to AgentProfileManager
    lang = getattr(args, "lang", None) or runtime_config.get("lang", "en")
    profile_manager = AgentProfileManager(
        api_key=get_api_key(),
        model=unified_config.get("model"),
        role=role,
        profile_name=profile,
        interaction_mode=interaction_mode,
        verbose_tools=args.verbose_tools,
        base_url=unified_config.get("base_url", "https://openrouter.ai/api/v1"),
        azure_openai_api_version=unified_config.get(
            "azure_openai_api_version", "2023-05-15"
        ),
        use_azure_openai=unified_config.get("use_azure_openai", False),
        lang=lang,
    )
    profile_manager.refresh_prompt()
    if getattr(args, "show_system", False):
        print(profile_manager.render_prompt())
        sys.exit(0)
    if args.max_tokens is not None:
        runtime_config.set("max_tokens", args.max_tokens)
    if getattr(args, "verbose_reason", False):
        runtime_config.set("verbose_reason", True)

    # --- termweb integration ---
    termweb_proc = None
    selected_port = None
    if (
        not getattr(args, "no_termweb", False)
        and interaction_mode == "chat"
        and not runtime_config.get("vanilla_mode", False)
    ):
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
        livereload_stdout_path = None
        livereload_stderr_path = None
        if not getattr(args, "input_arg", None) or getattr(
            args, "continue_session", False
        ):
            from janito.cli_chat_shell.chat_loop import start_chat_shell

            # Determine continue_session and session_id
            _cont = getattr(args, "continue_session", False)
            if _cont:
                continue_session = True
                session_id = getattr(args, "input_arg", None)
            else:
                continue_session = False
                session_id = None
            start_chat_shell(
                profile_manager,
                continue_session=continue_session,
                session_id=session_id,
                termweb_stdout_path=(
                    termweb_stdout_path if "termweb_stdout_path" in locals() else None
                ),
                termweb_stderr_path=(
                    termweb_stderr_path if "termweb_stderr_path" in locals() else None
                ),
                livereload_stdout_path=(
                    livereload_stdout_path
                    if "livereload_stdout_path" in locals()
                    else None
                ),
                livereload_stderr_path=(
                    livereload_stderr_path
                    if "livereload_stderr_path" in locals()
                    else None
                ),
            )
            sys.exit(0)
        # --- Prompt mode ---
        prompt = getattr(args, "input_arg", None)
        from rich.console import Console
        from janito.agent.rich_message_handler import RichMessageHandler

        console = Console()
        message_handler = RichMessageHandler()
        messages = []
        system_prompt_override = runtime_config.get("system_prompt_template")
        if system_prompt_override:
            # Só adiciona system prompt se NÃO for vanilla, ou se foi explicitamente passado via --system
            if not runtime_config.get("vanilla_mode", False) or getattr(
                args, "system", None
            ):
                messages.append({"role": "system", "content": system_prompt_override})
        elif profile_manager.system_prompt_template and not runtime_config.get(
            "vanilla_mode", False
        ):
            messages.append(
                {"role": "system", "content": profile_manager.system_prompt_template}
            )
        messages.append({"role": "user", "content": prompt})
        try:
            max_rounds = 100
            profile_manager.agent.chat(
                messages,
                message_handler=message_handler,
                spinner=True,
                max_rounds=max_rounds,
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
