"""Main CLI entry point for Janito."""

from janito.cli.arg_parser import create_parser
from janito.cli.config_commands import handle_config_commands
from janito.cli.logging_setup import setup_verbose_logging
from janito.cli.runner import run_cli


def main():
    """Entry point for the Janito CLI.

    Parses command-line arguments, handles config commands, sets up logging,
    and launches either the CLI chat shell or the web server.
    """

    parser = create_parser()
    args = parser.parse_args()

    from janito.agent.config import CONFIG_OPTIONS
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
        subprocess.run(['python', '-m', 'janito.web'])
    else:
        run_cli(args)
