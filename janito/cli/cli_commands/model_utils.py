"""
Utilities for model-related CLI output
"""


def _print_models_table(models, provider_name):
    from rich.table import Table
    from janito.cli.console import shared_console

    table = Table(title=f"Supported models for provider '{provider_name}'")
    table.add_column("Model Name", style="cyan")
    table.add_column("Vendor", style="yellow", justify="center")
    table.add_column("Context", style="magenta", justify="center")
    table.add_column("Max Input", style="green", justify="center")
    table.add_column("CoT", style="blue", justify="center")
    table.add_column("Max Response", style="red", justify="center")
    table.add_column("Thinking", style="bright_black", justify="center")
    table.add_column("Driver", style="white")

    # Get default model for this provider
    from janito.providers.registry import LLMProviderRegistry

    try:
        provider_class = LLMProviderRegistry.get(provider_name)
        default_model = getattr(provider_class, "DEFAULT_MODEL", None)
    except:
        default_model = None

    for m in models:
        name = str(m.get("name", ""))

        # Highlight default model with different color
        if name == default_model:
            name = f"[bold green]⭐ {name}[/bold green]"

        vendor = (
            "Open" if m.get("open") is True or m.get("open") == "Open" else "Locked"
        )

        context = _format_context(m.get("context", ""))
        max_input = _format_k(m.get("max_input", ""))
        max_cot = _format_k(m.get("max_cot", ""))
        max_response = _format_k(m.get("max_response", ""))

        # Determine thinking indicators
        thinking_supported = (
            m.get("thinking_supported") is True or m.get("thinking_supported") == "True"
        )
        cot_value = m.get("max_cot", "")

        thinking_icon = "📖" if thinking_supported and m.get("thinking", False) else ""
        # Only show CoT value if it's a valid number and thinking is supported
        cot_display = ""
        if thinking_supported and cot_value and str(cot_value).lower() != "n/a":
            cot_display = _format_k(cot_value)

        driver = _format_driver(m.get("driver", ""))

        table.add_row(
            name,
            vendor,
            context,
            max_input,
            cot_display,
            max_response,
            thinking_icon,
            driver,
        )

    import sys

    if sys.stdout.isatty():
        shared_console.print(table)
    else:
        # ASCII-friendly fallback table when output is redirected
        print(f"Supported models for provider '{provider_name}'")
        print(
            "Model Name | Vendor | Context | Max Input | CoT | Max Response | Thinking | Driver"
        )

        # Get default model for fallback
        from janito.providers.registry import LLMProviderRegistry

        try:
            provider_class = LLMProviderRegistry.get(provider_name)
            default_model = getattr(provider_class, "DEFAULT_MODEL", None)
        except:
            default_model = None

        for m in models:
            name = str(m.get("name", ""))
            if name == default_model:
                name = f"⭐ {name} (default)"

            vendor = (
                "Open" if m.get("open") is True or m.get("open") == "Open" else "Locked"
            )
            context = _format_context(m.get("context", ""))
            max_input = _format_k(m.get("max_input", ""))
            max_cot = _format_k(m.get("max_cot", ""))
            max_response = _format_k(m.get("max_response", ""))
            thinking_supported = (
                m.get("thinking_supported") is True
                or m.get("thinking_supported") == "True"
            )
            cot_value = m.get("max_cot", "")

            thinking = "Y" if thinking_supported and m.get("thinking", False) else ""
            cot_display = ""
            if thinking_supported and cot_value and str(cot_value).lower() != "n/a":
                cot_display = _format_k(cot_value)

            driver = _format_driver(m.get("driver", ""))
            print(
                f"{name} | {vendor} | {context} | {max_input} | {cot_display} | {max_response} | {thinking} | {driver}"
            )


def _format_k(val):
    """Format numeric values with k suffix for thousands."""
    try:
        n = int(val)
        if n >= 1000:
            return f"{n // 1000}k"
        return str(n)
    except Exception:
        return str(val)


def _format_context(val):
    """Format context field which might be a single value or range."""
    if isinstance(val, (list, tuple)) and len(val) == 2:
        return f"{_format_k(val[0])} / {_format_k(val[1])}"
    return _format_k(val)


def _format_driver(val):
    """Format driver name by removing ModelDriver suffix."""
    if isinstance(val, (list, tuple)):
        return ", ".join(val)
    val_str = str(val)
    return val_str.removesuffix("ModelDriver").strip()
