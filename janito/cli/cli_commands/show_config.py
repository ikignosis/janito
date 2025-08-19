from rich.console import Console
from rich.pretty import Pretty

from janito.config import config
from janito.cli.config import CONFIG_OPTIONS


def resolve_effective_model(provider_name):
    # Try provider-specific model, then global model, then provider default
    provider_cfg = config.get_provider_config(provider_name)
    model = provider_cfg.get("model") if provider_cfg else None
    if not model:
        model = config.get("model")
    if not model:
        try:
            from janito.provider_registry import ProviderRegistry

            provider_class = ProviderRegistry().get_provider(provider_name)
            model = getattr(provider_class, "DEFAULT_MODEL", None)
        except Exception:
            model = None
    return model


def handle_show_config(args):
    console = Console()
    provider = config.get("provider")
    model = config.get("model")
    # Show all providers with their effective model
    from janito.provider_registry import ProviderRegistry

    provider_names = []
    try:
        provider_names = ProviderRegistry()._get_provider_names()
    except Exception:
        pass
    from janito.provider_config import get_config_path

    config_path = get_config_path()
    console.print("[bold green]Current configuration:[/bold green]")
    console.print(f"[bold yellow]Config file:[/bold yellow] {config_path}")
    console.print(f"[bold yellow]Current provider:[/bold yellow] {provider!r}\n")
    if model is not None:
        console.print(f"[bold yellow]Global model:[/bold yellow] {model!r}\n")

    # Show all configuration values
    console.print("[bold green]Configuration values:[/bold green]")
    all_config = config.all()
    if all_config:
        for key, value in sorted(all_config.items()):
            # Hide sensitive values like API keys
            if "api_key" in key.lower() and value:
                masked_value = (
                    value[:8] + "***" + value[-4:] if len(value) > 12 else "***"
                )
                console.print(f"  {key}: {masked_value!r}")
            elif key == "providers" and isinstance(value, dict):
                # Handle nested provider configs with API keys
                masked_providers = {}
                for provider_name, provider_config in value.items():
                    masked_config = dict(provider_config)
                    if "api_key" in masked_config and masked_config["api_key"]:
                        api_key = masked_config["api_key"]
                        masked_config["api_key"] = (
                            api_key[:8] + "***" + api_key[-4:]
                            if len(api_key) > 12
                            else "***"
                        )
                    masked_providers[provider_name] = masked_config
                console.print(f"  {key}: {masked_providers!r}")
            else:
                console.print(f"  {key}: {value!r}")
    else:
        console.print("  (no configuration values set)")

    # Show disabled tools
    from janito.tools.disabled_tools import load_disabled_tools_from_config

    disabled_tools = load_disabled_tools_from_config()
    if disabled_tools:
        console.print(
            f"\n[bold red]Disabled tools:[/bold red] {', '.join(sorted(disabled_tools))}"
        )
    else:
        console.print("\n[bold green]No tools are disabled[/bold green]")
    return
