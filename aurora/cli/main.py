from aurora.cli.arg_parser import create_parser
from aurora.cli.config_commands import handle_config_commands
from aurora.cli.logging_setup import setup_verbose_logging
from aurora.cli.runner import run_cli


def main():
    parser = create_parser()
    args = parser.parse_args()

    handle_config_commands(args)
    setup_verbose_logging(args)
    run_cli(args)
