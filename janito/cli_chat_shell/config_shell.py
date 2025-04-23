from janito.agent.config import local_config, global_config, CONFIG_OPTIONS
from janito.agent.config_defaults import CONFIG_DEFAULTS
from janito.agent.runtime_config import unified_config, runtime_config


def handle_config_shell(console, *args, **kwargs):
    """
    /config show
    /config set local key=value
    /config set global key=value
    /config reset local
    /config reset global
    """
    if not args or args[0] not in ("show", "set", "reset"):
        console.print(
            "[bold red]Usage:[/bold red] /config show | /config set local|global key=value | /config reset local|global"
        )
        return

    if args[0] == "show":
        # Show config, unified with CLI
        from janito.cli._print_config import print_full_config

        print_full_config(
            local_config,
            global_config,
            unified_config,
            CONFIG_DEFAULTS,
            console=console,
        )
        return

    if args[0] == "reset":
        if len(args) < 2 or args[1] not in ("local", "global"):
            console.print("[bold red]Usage:[/bold red] /config reset local|global")
            return
        import os
        from pathlib import Path

        scope = args[1]
        if scope == "local":
            local_path = Path(".janito/config.json")
            if local_path.exists():
                os.remove(local_path)
                console.print(f"[green]Removed local config file:[/green] {local_path}")
            else:
                console.print(
                    f"[yellow]Local config file does not exist:[/yellow] {local_path}"
                )
        elif scope == "global":
            global_path = Path.home() / ".janito/config.json"
            if global_path.exists():
                os.remove(global_path)
                console.print(
                    f"[green]Removed global config file:[/green] {global_path}"
                )
            else:
                console.print(
                    f"[yellow]Global config file does not exist:[/yellow] {global_path}"
                )
        console.print(
            "[bold yellow]Please use /restart for changes to take full effect.[/bold yellow]"
        )
        return

    if args[0] == "set":
        if len(args) < 3 or args[1] not in ("local", "global"):
            console.print(
                "[bold red]Usage:[/bold red] /config set local|global key=value"
            )
            return
        scope = args[1]
        try:
            key, val = args[2].split("=", 1)
        except ValueError:
            console.print("[bold red]Invalid format, expected key=val[/bold red]")
            return
        key = key.strip()
        if key not in CONFIG_OPTIONS and not key.startswith("template."):
            console.print(
                f"[bold red]Invalid config key: '{key}'. Supported keys are: {', '.join(CONFIG_OPTIONS.keys())}"
            )
            return
        val = val.strip()
        if scope == "local":
            local_config.set(key, val)
            local_config.save()
            runtime_config.set(key, val)
            console.print(f"[green]Local config updated:[/green] {key} = {val}")
            console.print(
                "[bold yellow]Please use /restart for changes to take full effect.[/bold yellow]"
            )
        elif scope == "global":
            global_config.set(key, val)
            global_config.save()
            runtime_config.set(key, val)
            console.print(f"[green]Global config updated:[/green] {key} = {val}")
            console.print(
                "[bold yellow]Please use /restart for changes to take full effect.[/bold yellow]"
            )
        return
