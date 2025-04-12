from janito.agent.config import local_config, global_config, CONFIG_OPTIONS
from janito.agent.config_defaults import CONFIG_DEFAULTS
from janito.agent.runtime_config import unified_config, runtime_config
from janito.cli._print_config import print_config_items
from rich import print
import sys

def handle_config_shell(console, *args, **kwargs):
    """
    /config show
    /config set local key=value
    /config set global key=value
    """
    if not args or args[0] not in ("show", "set"):
        console.print("[bold red]Usage:[/bold red] /config show | /config set local|global key=value")
        return

    if args[0] == "show":
        # Show config, unified with CLI
        from janito.cli._print_config import print_full_config
        print_full_config(local_config, global_config, unified_config, CONFIG_DEFAULTS, console=console)
        return

    if args[0] == "set":
        if len(args) < 3 or args[1] not in ("local", "global"):
            console.print("[bold red]Usage:[/bold red] /config set local|global key=value")
            return
        scope = args[1]
        try:
            key, val = args[2].split("=", 1)
        except ValueError:
            console.print("[bold red]Invalid format, expected key=val[/bold red]")
            return
        key = key.strip()
        if key not in CONFIG_OPTIONS:
            console.print(f"[bold red]Invalid config key: '{key}'. Supported keys are: {', '.join(CONFIG_OPTIONS.keys())}")
            return
        val = val.strip()
        if scope == "local":
            local_config.set(key, val)
            local_config.save()
            runtime_config.set(key, val)
            console.print(f"[green]Local config updated:[/green] {key} = {val}")
        elif scope == "global":
            global_config.set(key, val)
            global_config.save()
            runtime_config.set(key, val)
            console.print(f"[green]Global config updated:[/green] {key} = {val}")
        return
