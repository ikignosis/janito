"""Main CLI entry point for Janito."""

from janito.cli.arg_parser import create_parser
from janito.cli.config_commands import handle_config_commands
from janito.cli.logging_setup import setup_verbose_logging
from janito.cli.runner.cli_main import run_cli
from janito.agent.runtime_config import unified_config

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
        # (mantém bloco info)

        print("Janito - Agente CLI de automação")
        print(f"Modelo: {unified_config.get('model')}")
        print(f"Temperatura: {unified_config.get('temperature')}")
        print(f"Max tokens: {unified_config.get('max_tokens')}")
        # System prompt real via AgentProfileManager
        # Prioridade: --system-file > --system > AgentProfileManager
        from janito.agent.runtime_config import runtime_config

        system_prompt_val = None
        origem = None
        if getattr(args, "system_file", None):
            try:
                with open(args.system_file, "r", encoding="utf-8") as f:
                    system_prompt_val = f.read().strip()
                runtime_config.set("system_prompt_template", system_prompt_val)
                origem = "--system-file"
            except Exception as e:
                print(f"System prompt: (error reading system-file: {e})")
        elif getattr(args, "system", None):
            system_prompt_val = args.system
            runtime_config.set("system_prompt_template", system_prompt_val)
            origem = "--system"
        else:
            system_prompt_val = runtime_config.get("system_prompt_template")
            if system_prompt_val:
                origem = "runtime_config"
        if system_prompt_val:
            print(f"System prompt ({origem or 'runtime_config'}): {system_prompt_val}")
        else:
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
                print(f"System prompt (profile_manager): {system_prompt_val}")
            except Exception as e:
                print(f"System prompt: (error obtaining from profile_manager: {e})")
        sys.exit(0)

    # ... resto do main ...
    handle_config_commands(args)
    setup_verbose_logging(args)
    if getattr(args, "web", False):
        import subprocess  # Only needed if launching web

        subprocess.run([sys.executable, "-m", "janito.web"])
    else:
        run_cli(args)
