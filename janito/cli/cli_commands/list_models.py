"""
CLI Command: List models for the specified/current provider
"""

import sys
from janito.cli.cli_commands.model_utils import _print_models_table

_provider_instance = None


def get_provider_instance():
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = setup_provider()
    return _provider_instance


def handle_list_models(args, provider_instance):
    provider_name = getattr(provider_instance, "name", None)
    if not provider_name:
        print(
            "Error: Provider must be specified with --provider or set as default before listing models."
        )
        sys.exit(1)
    try:
        models = list(provider_instance.get_model_info().values())
        if models and isinstance(models[0], dict):
            _print_models_table(models, provider_name)
        else:
            # Fallback for simple string model lists
            from rich.table import Table
            from janito.cli.console import shared_console

            table = Table(title=f"Supported models for provider '{provider_name}'")
            table.add_column("Model Name", style="cyan")

            for m in models:
                table.add_row(str(m))
            if sys.stdout.isatty():
                shared_console.print(table)
            else:
                print(f"Supported models for provider '{provider_name}':")
                for m in models:
                    print(f"- {m}")
    except Exception as e:
        print(f"Error listing models for provider '{provider_name}': {e}")
    return
