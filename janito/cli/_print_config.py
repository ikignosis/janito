import os
from janito.rich_utils import RichPrinter

_rich_printer = RichPrinter()
from ._utils import home_shorten


def print_config_items(items, color_label=None):
    if not items:
        return
    if color_label:
        _rich_printer.print_info(color_label)
    home = os.path.expanduser("~")
    for key, value in items.items():
        if key == "system_prompt_template" and isinstance(value, str):
            if value.startswith(home):
                print(f"{key} = {home_shorten(value)}")
            else:
                _rich_printer.print_info(f"{key} = {value}")
        else:
            _rich_printer.print_info(f"{key} = {value}")
    _rich_printer.print_info("")


def _mask_api_key(value):
    if value and len(value) > 8:
        return value[:4] + "..." + value[-4:]
    elif value:
        return "***"
    return None


def _collect_config_items(config, unified_config, keys):
    items = {}
    for key in sorted(keys):
        if key == "api_key":
            value = config.get("api_key")
            value = _mask_api_key(value)
        else:
            value = unified_config.get(key)
        items[key] = value
    return items


def _print_defaults(config_defaults, shown_keys):
    default_items = {
        k: v
        for k, v in config_defaults.items()
        if k not in shown_keys and k != "api_key"
    }
    if default_items:
        _rich_printer.print_magenta(
            "[green]\U0001f7e2 Defaults (not set in config files)[/green]"
        )
        from pathlib import Path

        template_path = (
            Path(__file__).parent
            / "agent"
            / "templates"
            / "system_prompt_template_default.j2"
        )
        for key, value in default_items.items():
            if key == "system_prompt_template" and value is None:
                _rich_printer.print_info(
                    f"{key} = (default template path: {home_shorten(str(template_path))})"
                )
            else:
                _rich_printer.print_info(f"{key} = {value}")
        _rich_printer.print_info("")


def print_full_config(
    local_config, global_config, unified_config, config_defaults, console=None
):
    """
    Print local, global, and default config values in a unified way.
    Handles masking API keys and showing the template file for system_prompt_template if not set.
    """
    local_keys = set(local_config.all().keys())
    global_keys = set(global_config.all().keys())
    if not (local_keys or global_keys):
        _rich_printer.print_warning("No configuration found.")
    else:
        local_items = _collect_config_items(local_config, unified_config, local_keys)
        global_items = _collect_config_items(
            global_config, unified_config, global_keys - local_keys
        )
        print_config_items(
            local_items, color_label="[cyan]\U0001f3e0 Local Configuration[/cyan]"
        )
        print_config_items(
            global_items, color_label="[yellow]\U0001f310 Global Configuration[/yellow]"
        )
        shown_keys = set(local_items.keys()) | set(global_items.keys())
        _print_defaults(config_defaults, shown_keys)
