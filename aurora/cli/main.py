"""Main CLI entry point for Aurora."""

from aurora.cli.arg_parser import create_parser
from aurora.cli.config_commands import handle_config_commands
from aurora.cli.logging_setup import setup_verbose_logging
from aurora.cli.runner import run_cli


def main():
    """Entry point for the Aurora CLI.

    Parses command-line arguments, handles config commands, sets up logging,
    and launches either the CLI chat shell or the web server.
    """

    parser = create_parser()
    args = parser.parse_args()

    from aurora.agent.config import CONFIG_OPTIONS
    import sys
    if getattr(args, "help_config", False):
        print("Available configuration options:\n")
        for key, desc in CONFIG_OPTIONS.items():
            print(f"{key:15} {desc}")
        sys.exit(0)

    handle_config_commands(args)
    setup_verbose_logging(args)
    if getattr(args, 'web', False):
        import subprocess
        subprocess.run(['python', '-m', 'aurora.web'])
    else:
        run_cli(args)
