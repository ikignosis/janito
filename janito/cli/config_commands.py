import sys
from janito.agent.config import local_config, global_config, CONFIG_OPTIONS
from janito.agent.runtime_config import unified_config, runtime_config
from janito.agent.config_defaults import CONFIG_DEFAULTS
from rich import print
from ._utils import home_shorten
import os
from pathlib import Path


def handle_run_config(args):
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
        return True
    return False


def handle_set_local_config(args):
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
        return True
    return False


def handle_set_global_config(args):
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
            return True
        else:
            global_config.set(key, val.strip())
            global_config.save()
            runtime_config.set(key, val.strip())
            print(f"Global config updated: {key} = {val.strip()}")
            return True
    return False


def handle_set_api_key(args):
    if args.set_api_key:
        existing = dict(global_config.all())
        existing["api_key"] = args.set_api_key.strip()
        global_config._data = existing
        global_config.save()
        runtime_config.set("api_key", args.set_api_key.strip())
        print("Global API key saved.")
        return True
    return False


def handle_show_config(args):
    if args.show_config:
        local_items = _collect_config_items(local_config, unified_config, True)
        global_items = _collect_config_items(
            global_config, unified_config, False, set(local_items.keys())
        )
        _mask_api_keys(local_items)
        _mask_api_keys(global_items)
        _print_config_items(local_items, global_items)
        _print_default_items(local_items, global_items)
        return True
    return False


def _collect_config_items(config, unified_config, is_local, exclude_keys=None):
    items = {}
    keys = set(config.all().keys())
    if exclude_keys:
        keys = keys - set(exclude_keys)
    for key in sorted(keys):
        if key == "template":
            template_dict = config.get("template", {})
            if template_dict:
                items["template"] = f"({len(template_dict)} keys set)"
                for tkey, tval in template_dict.items():
                    items[f"  template.{tkey}"] = tval
            continue
        if key.startswith("template."):
            continue
        if key == "api_key":
            value = config.get("api_key")
            value = (
                value[:4] + "..." + value[-4:]
                if value and len(value) > 8
                else ("***" if value else None)
            )
        else:
            value = unified_config.get(key)
        items[key] = value
    return items


def _mask_api_keys(cfg):
    if "api_key" in cfg and cfg["api_key"]:
        val = cfg["api_key"]
        cfg["api_key"] = val[:4] + "..." + val[-4:] if len(val) > 8 else "***"


def _print_config_items(local_items, global_items):
    from ._print_config import print_config_items

    print_config_items(local_items, color_label="[cyan]🏠 Local Configuration[/cyan]")
    print_config_items(
        global_items, color_label="[yellow]🌐 Global Configuration[/yellow]"
    )


def _print_default_items(local_items, global_items):
    shown_keys = set(local_items.keys()) | set(global_items.keys())
    default_items = {
        k: v
        for k, v in CONFIG_DEFAULTS.items()
        if k not in shown_keys and k != "api_key"
    }
    if default_items:
        print("[green]🟢 Defaults (not set in config files)[/green]")
        for key, value in default_items.items():
            if key == "system_prompt" and value is None:
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


def handle_config_reset_local(args):
    if getattr(args, "config_reset_local", False):
        local_path = Path(".janito/config.json")
        if local_path.exists():
            os.remove(local_path)
            print(f"Removed local config file: {local_path}")
        else:
            print(f"Local config file does not exist: {local_path}")
        sys.exit(0)


def handle_config_reset_global(args):
    if getattr(args, "config_reset_global", False):
        global_path = Path.home() / ".janito/config.json"
        if global_path.exists():
            os.remove(global_path)
            print(f"Removed global config file: {global_path}")
        else:
            print(f"Global config file does not exist: {global_path}")
        sys.exit(0)


def handle_config_commands(args):
    did_something = False
    did_something |= handle_run_config(args)
    did_something |= handle_set_local_config(args)
    did_something |= handle_set_global_config(args)
    did_something |= handle_set_api_key(args)
    did_something |= handle_show_config(args)
    handle_config_reset_local(args)
    handle_config_reset_global(args)
    if did_something:
        sys.exit(0)
