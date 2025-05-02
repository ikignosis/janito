"""Main CLI entry point for Janito."""

from janito.cli.arg_parser import create_parser
from janito.cli.config_commands import handle_config_commands
from janito.cli.logging_setup import setup_verbose_logging
from janito.cli.cli_main import run_cli
from janito.agent.runtime_config import unified_config
from janito.cli.livereload_starter import start_livereload

# Ensure all tools are registered at startup
import janito.agent.tools  # noqa: F401
from janito.i18n import tr


def main():
    """Unified entry point for the Janito CLI and web server."""
    import sys

    from janito.agent.config import local_config, global_config
    import janito.i18n as i18n
    from janito.agent.runtime_config import runtime_config

    local_config.load()
    global_config.load()

    parser = create_parser()
    args = parser.parse_args()

    # Handle --set-provider-config <name> <key> <value>
    if getattr(args, "set_provider_config", None) is not None:
        import os
        import json

        name, key, value = args.set_provider_config
        config_dir = os.path.expanduser("~/.janito")
        os.makedirs(config_dir, exist_ok=True)
        providers_path = os.path.join(config_dir, "providers.json")

        # Load or initialize providers config
        if os.path.exists(providers_path):
            with open(providers_path, "r", encoding="utf-8") as f:
                try:
                    providers = json.load(f)
                except Exception:
                    providers = {}
        else:
            providers = {}

        if name not in providers or not isinstance(providers[name], dict):
            providers[name] = {}
        providers[name][key] = value

        with open(providers_path, "w", encoding="utf-8") as f:
            json.dump(providers, f, indent=2)

        print(f"Set {key} for provider '{name}' in {providers_path}.")
        sys.exit(0)

    # Handle --list [n] before anything else
    if getattr(args, "list", None) is not None:
        import os
        import glob

        n = args.list if args.list is not None else 10
        history_dir = os.path.join(os.path.expanduser(".janito"), "chat_history")
        if not os.path.exists(history_dir):
            print("No session history found.")
            sys.exit(0)
        files = glob.glob(os.path.join(history_dir, "*.json"))
        files = sorted(files, key=os.path.getmtime, reverse=True)
        print(f"Last {n} sessions:")
        for f in files[:n]:
            session_id = os.path.splitext(os.path.basename(f))[0]
            print(session_id)
        sys.exit(0)

    # Handle --view <id> to print conversation history
    if getattr(args, "view", None) is not None:
        import os
        import json

        history_dir = os.path.join(os.path.expanduser(".janito"), "chat_history")
        session_file = os.path.join(history_dir, f"{args.view}.json")
        if not os.path.exists(session_file):
            print(f"Session '{args.view}' not found.")
            sys.exit(1)
        with open(session_file, "r", encoding="utf-8") as f:
            try:
                messages = json.load(f)
            except Exception as e:
                print(f"Failed to load session: {e}")
                sys.exit(1)
        print(f"Conversation history for session '{args.view}':\n")
        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "?")
            content = msg.get("content", "")
            print(f"[{i}] {role}: {content}\n")
        sys.exit(0)

    # Seleção de idioma: prioridade --lang > config.json > padrão
    lang = getattr(args, "lang", None) or unified_config.get("lang", None) or "en"
    runtime_config.set("lang", lang)
    i18n.set_locale(lang)

    from janito.agent.config import CONFIG_OPTIONS
    from janito.agent.config_defaults import CONFIG_DEFAULTS

    if getattr(args, "help_config", False):
        print(tr("Available configuration options:\n"))
        for key, desc in CONFIG_OPTIONS.items():
            default = CONFIG_DEFAULTS.get(key, None)
            print(
                tr(
                    "{key:15} {desc} (default: {default})",
                    key=key,
                    desc=desc,
                    default=default,
                )
            )
        sys.exit(0)

    if getattr(args, "list_tools", False):
        from janito.agent.tool_registry import get_tool_schemas
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(
            title="Ferramentas Registradas", show_lines=True, style="bold magenta"
        )
        table.add_column("Gnome", style="cyan", no_wrap=True)
        table.add_column("Descrição", style="green")
        table.add_column("Parâmetros", style="yellow")
        for schema in get_tool_schemas():
            fn = schema["function"]
            params = "\n".join(
                [
                    f"[bold]{k}[/]: {v['type']}"
                    for k, v in fn["parameters"].get("properties", {}).items()
                ]
            )
            table.add_row(f"[b]{fn['name']}[/b]", fn["description"], params or "-")
        console.print(table)
        sys.exit(0)

    if getattr(args, "info", False):
        # Compact, colored, single-line info output using rich
        from janito import __version__
        from rich.console import Console
        from rich.text import Text
        from janito.agent.runtime_config import runtime_config

        model = unified_config.get("model")
        temperature = unified_config.get("temperature")
        max_tokens = unified_config.get("max_tokens")
        system_prompt_val = None
        if getattr(args, "system_file", None):
            try:
                with open(args.system_file, "r", encoding="utf-8") as f:
                    system_prompt_val = f.read().strip()
                runtime_config.set("system_prompt_template", system_prompt_val)
            except Exception as e:
                system_prompt_val = f"(error reading system-file: {e})"
        elif getattr(args, "system", None):
            system_prompt_val = args.system
            runtime_config.set("system_prompt_template", system_prompt_val)
        else:
            system_prompt_val = runtime_config.get("system_prompt_template")
            # if system_prompt_val:
            #     origem = "runtime_config"
        if not system_prompt_val:
            try:
                from janito.agent.profile_manager import AgentProfileManager
                from janito.agent.config import get_api_key

                role = args.role or unified_config.get("role", "software engineer")
                interaction_mode = (
                    "chat" if not getattr(args, "prompt", None) else "prompt"
                )
                profile = "base"
                profile_manager = AgentProfileManager(
                    api_key=get_api_key(),
                    model=unified_config.get("model"),
                )
                system_prompt_val = profile_manager.get_system_prompt(
                    role, interaction_mode, profile
                )
            except Exception as e:
                system_prompt_val = f"(error: {e})"

        console = Console()
        info_text = Text()
        info_text.append(f"Janito v{__version__}", style="bold cyan")
        info_text.append(" | model: ", style="white")
        info_text.append(str(model), style="green")
        info_text.append(" | temp: ", style="white")
        info_text.append(str(temperature), style="yellow")
        info_text.append(" | max_tokens: ", style="white")
        info_text.append(str(max_tokens), style="magenta")
        info_text.append(" | system: ", style="white")
        info_text.append(str(system_prompt_val), style="bold blue")
        console.print(info_text, style="dim")
        # Previously: sys.exit(0) would exit after showing info. Now, program continues after displaying info.

    # ... resto do main ...
    handle_config_commands(args)
    setup_verbose_logging(args)
    if getattr(args, "web", False):
        import subprocess  # Only needed if launching web

        subprocess.run([sys.executable, "-m", "janito.web"])
    elif getattr(args, "live", False):
        port = 35729  # Default livereload port
        livereload_proc, started, livereload_stdout_path, livereload_stderr_path = (
            start_livereload(port)
        )
        try:
            run_cli(args)
        finally:
            if livereload_proc:
                livereload_proc.terminate()
                livereload_proc.wait()
    else:
        run_cli(args)
