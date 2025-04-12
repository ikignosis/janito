import os
from ._utils import home_shorten

def print_config_items(items, color_label=None):
    if not items:
        return
    if color_label:
        print(color_label)
    home = os.path.expanduser("~")
    for key, value in items.items():
        if key == "system_prompt" and isinstance(value, str):
            if value.startswith(home):
                print(f"{key} = {home_shorten(value)}")
            else:
                print(f"{key} = {value}")
        else:
            print(f"{key} = {value}")
    print()
