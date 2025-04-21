import sys
from janito.agent.config import local_config, global_config, CONFIG_OPTIONS
from janito.agent.runtime_config import unified_config, runtime_config
from janito.agent.config_defaults import CONFIG_DEFAULTS
from rich import print
from ._utils import home_shorten


def handle_config_commands(args):
    """Handle --set-local-config, --set-global-config, --show-config. Exit if any are used."""
    did_something = False

    if args.run_config:
        for run_item in args.run_config:
            try:
                key, val = run_item.split("=", 1)
            except ValueError:
                print("Invalid format for --run-config, expected key=val")
                sys.exit(1)
            key = key.strip()
            if key not in CONFIG_OPTIONS:
                print(
                    f"Invalid config key: '{key}'. Supported keys are: {', '.join(CONFIG_OPTIONS.keys())}"
                )
                sys.exit(1)
            runtime_config.set(key, val.strip())
    if args.set_local_config:
        try:
            key, val = args.set_local_config.split("=", 1)
        except ValueError:
            print("Invalid format for --set-local-config, expected key=val")
            sys.exit(1)
        key = key.strip()
        if key not in CONFIG_OPTIONS:
            print(
                f"Invalid config key: '{key}'. Supported keys are: {', '.join(CONFIG_OPTIONS.keys())}"
            )
            sys.exit(1)
        local_config.set(key, val.strip())
        local_config.save()
        runtime_config.set(key, val.strip())
        print(f"Local config updated: {key} = {val.strip()}")
        did_something = True

    if args.set_global_config:
        try:
            key, val = args.set_global_config.split("=", 1)
        except ValueError:
            print("Invalid format for --set-global-config, expected key=val")
            sys.exit(1)
        key = key.strip()
        if key not in CONFIG_OPTIONS and not key.startswith("template."):
            print(
                f"Invalid config key: '{key}'. Supported keys are: {', '.join(CONFIG_OPTIONS.keys())}"
            )
            sys.exit(1)
        if key.startswith("template."):
            subkey = key[len("template.") :]
            template_dict = global_config.get("template", {})
            template_dict[subkey] = val.strip()
            global_config.set("template", template_dict)
            global_config.save()
            # Remove legacy flat key if present
            if key in global_config._data:
                del global_config._data[key]
            runtime_config.set("template", template_dict)
            print(f"Global config updated: template.{subkey} = {val.strip()}")
            did_something = True
        else:
            global_config.set(key, val.strip())
            global_config.save()
            runtime_config.set(key, val.strip())
            print(f"Global config updated: {key} = {val.strip()}")
            did_something = True

    if args.set_api_key:
        # Merge: load full config, update api_key, save all
        existing = dict(global_config.all())
        existing["api_key"] = args.set_api_key.strip()
        global_config._data = existing
        global_config.save()
        runtime_config.set("api_key", args.set_api_key.strip())
        print("Global API key saved.")
        did_something = True

    if args.show_config:
        local_items = {}
        global_items = {}

        # Collect and group keys
        local_keys = set(local_config.all().keys())
        global_keys = set(global_config.all().keys())
        if not (local_keys or global_keys):
            print("No configuration found.")
        else:
            # Imports previously inside block to avoid circular import at module level
            # Handle template as nested dict
            for key in sorted(local_keys):
                if key == "template":
                    template_dict = local_config.get("template", {})
                    if template_dict:
                        local_items["template"] = f"({len(template_dict)} keys set)"
                        for tkey, tval in template_dict.items():
                            local_items[f"  template.{tkey}"] = tval
                    continue
                if key.startswith("template."):
                    # Skip legacy flat keys
                    continue
                if key == "api_key":
                    value = local_config.get("api_key")
                    value = (
                        value[:4] + "..." + value[-4:]
                        if value and len(value) > 8
                        else ("***" if value else None)
                    )
                else:
                    value = unified_config.get(key)
                local_items[key] = value
            for key in sorted(global_keys - local_keys):
                if key == "template":
                    template_dict = global_config.get("template", {})
                    if template_dict:
                        global_items["template"] = f"({len(template_dict)} keys set)"
                        for tkey, tval in template_dict.items():
                            global_items[f"  template.{tkey}"] = tval
                    continue
                if key.startswith("template."):
                    continue
                if key == "api_key":
                    value = global_config.get("api_key")
                    value = (
                        value[:4] + "..." + value[-4:]
                        if value and len(value) > 8
                        else ("***" if value else None)
                    )
                else:
                    value = unified_config.get(key)
                global_items[key] = value

            # Mask API key
            for cfg in (local_items, global_items):
                if "api_key" in cfg and cfg["api_key"]:
                    val = cfg["api_key"]
                    cfg["api_key"] = (
                        val[:4] + "..." + val[-4:] if len(val) > 8 else "***"
                    )

            # Print local config
            from ._print_config import print_config_items

            print_config_items(
                local_items, color_label="[cyan]🏠 Local Configuration[/cyan]"
            )

            # Print global config
            print_config_items(
                global_items, color_label="[yellow]🌐 Global Configuration[/yellow]"
            )

        # Show defaults for unset keys
        shown_keys = set(local_items.keys()) | set(global_items.keys())
        default_items = {
            k: v
            for k, v in CONFIG_DEFAULTS.items()
            if k not in shown_keys and k != "api_key"
        }
        if default_items:
            print("[green]🟢 Defaults (not set in config files)[/green]")
            for key, value in default_items.items():
                # Special case for system_prompt: show template file if None
                if key == "system_prompt" and value is None:
                    from pathlib import Path

                    template_path = (
                        Path(__file__).parent
                        / "agent"
                        / "templates"
                        / "system_prompt_template_default.j2"
                    )
                    print(
                        f"{key} = (default template path: {home_shorten(str(template_path))})"
                    )
                else:
                    print(f"{key} = {value}")
            print()
        did_something = True

    import os
    from pathlib import Path

    if getattr(args, "config_reset_local", False):
        local_path = Path(".janito/config.json")
        if local_path.exists():
            os.remove(local_path)
            print(f"Removed local config file: {local_path}")
        else:
            print(f"Local config file does not exist: {local_path}")
        sys.exit(0)
    if getattr(args, "config_reset_global", False):
        global_path = Path.home() / ".janito/config.json"
        if global_path.exists():
            os.remove(global_path)
            print(f"Removed global config file: {global_path}")
        else:
            print(f"Global config file does not exist: {global_path}")
        sys.exit(0)
    if did_something:
        sys.exit(0)
