from janito.agent.runtime_config import runtime_config


def handle_verbose(console, shell_state=None, **kwargs):
    """
    /verbose [on|off]
    Shows or sets verbose mode for the current shell session.
    """
    args = kwargs.get("args", [])
    verbose = runtime_config.get("verbose", False)
    if not args:
        status = "ON" if verbose else "OFF"
        console.print(
            f"[bold green]/verbose:[/bold green] Verbose mode is currently [bold]{status}[/bold]."
        )
        return
    arg = args[0].lower()
    if arg == "on":
        runtime_config["verbose"] = True
        console.print(
            "[bold green]/verbose:[/bold green] Verbose mode is now [bold]ON[/bold]."
        )
    elif arg == "off":
        runtime_config["verbose"] = False
        console.print(
            "[bold green]/verbose:[/bold green] Verbose mode is now [bold]OFF[/bold]."
        )
    else:
        console.print("[bold red]Usage:[/bold red] /verbose [on|off]")
