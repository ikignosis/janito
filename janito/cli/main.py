"""Main CLI entry point for Janito."""

from janito.cli.arg_parser import create_parser
from janito.cli.config_commands import handle_config_commands
from janito.cli.logging_setup import setup_verbose_logging
from janito.cli.runner import run_cli

# Ensure all tools are registered at startup
import janito.agent.tools  # noqa: F401


def main():
    """Entry point for the Janito CLI.

    Parses command-line arguments, handles config commands, sets up logging,
    and launches either the CLI chat shell or the web server.
    """
    # Ensure configs are loaded once at CLI startup
    from janito.agent.config import local_config, global_config

    local_config.load()
    global_config.load()

    parser = create_parser()
    args = parser.parse_args()

    from janito.agent.config import (
        CONFIG_OPTIONS,
    )  # Kept here: avoids circular import at module level
    from janito.agent.config_defaults import CONFIG_DEFAULTS
    import sys

    if getattr(args, "help_config", False):
        print("Available configuration options:\n")
        for key, desc in CONFIG_OPTIONS.items():
            default = CONFIG_DEFAULTS.get(key, None)
            print(f"{key:15} {desc} (default: {default})")
        sys.exit(0)

    handle_config_commands(args)
    setup_verbose_logging(args)
    if getattr(args, "web", False):
        import subprocess  # Only needed if launching web

        subprocess.run(["python", "-m", "janito.web"])
    else:
        run_cli(args)
