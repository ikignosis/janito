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
        # Show config, similar to CLI
        local_items = {}
        global_items = {}
        local_keys = set(local_config.all().keys())
        global_keys = set(global_config.all().keys())
        all_keys = set(CONFIG_DEFAULTS.keys()) | global_keys | local_keys
        if not (local_keys or global_keys):
            console.print("No configuration found.")
        else:
            for key in sorted(local_keys):
                if key == "api_key":
                    value = local_config.get("api_key")
                    value = value[:4] + '...' + value[-4:] if value and len(value) > 8 else ('***' if value else None)
                else:
                    value = unified_config.get(key)
                local_items[key] = value
            for key in sorted(global_keys - local_keys):
                if key == "api_key":
                    value = global_config.get("api_key")
                    value = value[:4] + '...' + value[-4:] if value and len(value) > 8 else ('***' if value else None)
                else:
                    value = unified_config.get(key)
                global_items[key] = value
            # Mask API key
            for cfg in (local_items, global_items):
                if 'api_key' in cfg and cfg['api_key']:
                    val = cfg['api_key']
                    cfg['api_key'] = val[:4] + '...' + val[-4:] if len(val) > 8 else '***'
            print_config_items(local_items, color_label="[cyan]🏠 Local Configuration[/cyan]")
            print_config_items(global_items, color_label="[yellow]🌐 Global Configuration[/yellow]")
            # Show defaults for unset keys
            shown_keys = set(local_items.keys()) | set(global_items.keys())
            default_items = {k: v for k, v in CONFIG_DEFAULTS.items() if k not in shown_keys and k != 'api_key'}
            if default_items:
                print("[green]🟢 Defaults (not set in config files)[/green]")
                print_config_items(default_items)
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
