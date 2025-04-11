import sys
from janito.agent.config import local_config, global_config
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
        print(f"Global config updated: {key} = {val.strip()}")
        did_something = True

    if args.set_api_key:
        local_config.set("api_key", args.set_api_key.strip())
        local_config.save()
        print("Local API key saved.")
        did_something = True

    if args.show_config:
        from janito.agent.config import effective_config
        local_items = {}
        global_items = {}

        # Collect and group keys
        keys = set(global_config.all().keys()) | set(local_config.all().keys())
        if not keys:
            print("No configuration found.")
        else:
            for key in sorted(keys):
                if key in local_config.all():
                    source = "local"
                    value = local_config.get(key)
                    local_items[key] = value
                else:
                    source = "global"
                    value = global_config.get(key)
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

        did_something = True

    if did_something:
        sys.exit(0)
