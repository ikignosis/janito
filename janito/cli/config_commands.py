import sys
from janito.agent.config import local_config, global_config
from janito.agent.runtime_config import runtime_config
from rich import print


def handle_config_commands(args):
    """Handle --set-local-config, --set-global-config, --show-config. Exit if any are used."""
    did_something = False

    if args.set_local_config:
        from janito.agent.config import CONFIG_OPTIONS
        try:
            key, val = args.set_local_config.split("=", 1)
        except ValueError:
            print("Invalid format for --set-local-config, expected key=val")
            sys.exit(1)
        key = key.strip()
        if key not in CONFIG_OPTIONS:
            print(f"Invalid config key: '{key}'. Supported keys are: {', '.join(CONFIG_OPTIONS.keys())}")
            sys.exit(1)
        local_config.set(key, val.strip())
        local_config.save()
        runtime_config.set(key, val.strip())
        print(f"Local config updated: {key} = {val.strip()}")
        did_something = True

    if args.set_global_config:
        from janito.agent.config import CONFIG_OPTIONS
        try:
            key, val = args.set_global_config.split("=", 1)
        except ValueError:
            print("Invalid format for --set-global-config, expected key=val")
            sys.exit(1)
        key = key.strip()
        if key not in CONFIG_OPTIONS:
            print(f"Invalid config key: '{key}'. Supported keys are: {', '.join(CONFIG_OPTIONS.keys())}")
            sys.exit(1)
        global_config.set(key, val.strip())
        global_config.save()
        runtime_config.set(key, val.strip())
        print(f"Global config updated: {key} = {val.strip()}")
        did_something = True

    if args.set_api_key:
        local_config.set("api_key", args.set_api_key.strip())
        local_config.save()
        runtime_config.set("api_key", args.set_api_key.strip())
        print("Local API key saved.")
        did_something = True

    if args.show_config:
        from janito.agent.runtime_config import unified_config, runtime_config
        local_items = {}
        global_items = {}

        # Collect and group keys
        from janito.agent.config_defaults import CONFIG_DEFAULTS
        local_keys = set(local_config.all().keys())
        global_keys = set(global_config.all().keys())
        all_keys = set(CONFIG_DEFAULTS.keys()) | global_keys | local_keys
        if not (local_keys or global_keys):
            print("No configuration found.")
        else:
            from janito.agent.config import get_api_key
            from janito.agent.runtime_config import unified_config
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

            # Print local config
            if local_items:
                print("[cyan]🏠 Local Configuration[/cyan]")
                for key, value in local_items.items():
                    print(f"{key} = {value}")
                print()

            # Print global config
            if global_items:
                print("[yellow]🌐 Global Configuration[/yellow]")
                for key, value in global_items.items():
                    print(f"{key} = {value}")
                print()

        # Show defaults for unset keys
        shown_keys = set(local_items.keys()) | set(global_items.keys())
        default_items = {k: v for k, v in CONFIG_DEFAULTS.items() if k not in shown_keys and k != 'api_key'}
        if default_items:
            print("[green]🟢 Defaults (not set in config files)[/green]")
            for key, value in default_items.items():
                # Special case for system_prompt: show template file if None
                if key == "system_prompt" and value is None:
                    from pathlib import Path
                    template_path = Path(__file__).parent.parent / "templates" / "system_instructions.j2"
                    print(f"{key} = file: {template_path}")
                else:
                    print(f"{key} = {value}")
            print()
        did_something = True

    if did_something:
        sys.exit(0)
