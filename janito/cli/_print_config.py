import os
from janito.rich_utils import print_info, print_warning, print_magenta
from ._utils import home_shorten


def print_config_items(items, color_label=None):
    if not items:
        return
    if color_label:
        print_info(color_label)
    home = os.path.expanduser("~")
    for key, value in items.items():
        if key == "system_prompt_template" and isinstance(value, str):
            if value.startswith(home):
                print(f"{key} = {home_shorten(value)}")
            else:
                print_info(f"{key} = {value}")
        else:
            print_info(f"{key} = {value}")
    print_info("")


def print_full_config(
    local_config, global_config, unified_config, config_defaults, console=None
):
    """
    Print local, global, and default config values in a unified way.
    Handles masking API keys and showing the template file for system_prompt_template if not set.
    """
    local_items = {}
    global_items = {}
    local_keys = set(local_config.all().keys())
    global_keys = set(global_config.all().keys())
    if not (local_keys or global_keys):
        print_warning("No configuration found.")
    else:
        for key in sorted(local_keys):
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
                cfg["api_key"] = val[:4] + "..." + val[-4:] if len(val) > 8 else "***"
        print_config_items(
            local_items, color_label="[cyan]🏠 Local Configuration[/cyan]"
        )
        print_config_items(
            global_items, color_label="[yellow]🌐 Global Configuration[/yellow]"
        )
        # Show defaults for unset keys
        shown_keys = set(local_items.keys()) | set(global_items.keys())
        default_items = {
            k: v
            for k, v in config_defaults.items()
            if k not in shown_keys and k != "api_key"
        }
        if default_items:
            print_magenta("[green]🟢 Defaults (not set in config files)[/green]")
            from pathlib import Path

            template_path = (
                Path(__file__).parent
                / "agent"
                / "templates"
                / "system_prompt_template_default.j2"
            )
            for key, value in default_items.items():
                if key == "system_prompt_template" and value is None:
                    print_info(
                        f"{key} = (default template path: {home_shorten(str(template_path))})"
                    )
                else:
                    print_info(f"{key} = {value}")
            print_info("")
