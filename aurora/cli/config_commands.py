import sys
from aurora.agent.config import local_config, global_config


def handle_config_commands(args):
    """Handle --set-local-config, --set-global-config, --show-config. Exit if any are used."""
    did_something = False

    if args.set_local_config:
        try:
            key, val = args.set_local_config.split("=", 1)
        except ValueError:
            print("Invalid format for --set-local-config, expected key=val")
            sys.exit(1)
        local_config.set(key.strip(), val.strip())
        local_config.save()
        print(f"Local config updated: {key.strip()} = {val.strip()}")
        did_something = True

    if args.set_global_config:
        try:
            key, val = args.set_global_config.split("=", 1)
        except ValueError:
            print("Invalid format for --set-global-config, expected key=val")
            sys.exit(1)
        global_config.set(key.strip(), val.strip())
        global_config.save()
        print(f"Global config updated: {key.strip()} = {val.strip()}")
        did_something = True

    if args.set_api_key:
        local_config.set("api_key", args.set_api_key.strip())
        local_config.save()
        print("Local API key saved.")
        did_something = True

    if args.show_config:
        from aurora.agent.config import effective_config
        keys = set(global_config.all().keys()) | set(local_config.all().keys())
        if not keys:
            print("No configuration found.")
        else:
            print("Effective configuration:")
            for key in sorted(keys):
                if key in local_config.all():
                    source = "local"
                    value = local_config.get(key)
                else:
                    source = "global"
                    value = global_config.get(key)
                print(f"{key} = {value}    (source: {source})")
        did_something = True

    if did_something:
        sys.exit(0)
