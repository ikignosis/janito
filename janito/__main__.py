import typer
from typing import Optional, List
from pathlib import Path
from rich.console import Console

from janito.claude import ClaudeAPIAgent
from janito.prompts import SYSTEM_PROMPT
from janito.config import config

from .cli.commands import (
    handle_version,
    handle_review,
    handle_ask,
    handle_scan,
    handle_play,
    handle_request
)

app = typer.Typer()

# Global options for all commands
class GlobalOptions:
    def __init__(
        self,
        workdir: Optional[Path] = typer.Option(None, "-w", "--workdir", help="Working directory", file_okay=False, dir_okay=True),
        include: Optional[List[Path]] = typer.Option(None, "-i", "--include", help="Additional paths to include"),
        raw: bool = typer.Option(False, "--raw", help="Print raw response"),
        verbose: bool = typer.Option(False, "-v", "--verbose", help="Show verbose output"),
        debug: bool = typer.Option(False, "-d", "--debug", help="Show debug information"),
        test: Optional[str] = typer.Option(None, "-t", "--test", help="Test command to run before changes"),
    ):
        self.workdir = workdir or Path.cwd()
        self.include = include
        self.raw = raw
        self.verbose = verbose
        self.debug = debug
        self.test = test

@app.callback()
def global_options(
    ctx: typer.Context,
    workdir: Optional[Path] = typer.Option(None, "-w", "--workdir", help="Working directory", file_okay=False, dir_okay=True),
    include: Optional[List[Path]] = typer.Option(None, "-i", "--include", help="Additional paths to include"),
    raw: bool = typer.Option(False, "--raw", help="Print raw response"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show verbose output"),
    debug: bool = typer.Option(False, "-d", "--debug", help="Show debug information"),
    test: Optional[str] = typer.Option(None, "-t", "--test", help="Test command to run before changes"),
):
    """Janito - AI-powered code modification assistant"""
    ctx.obj = GlobalOptions(workdir, include, raw, verbose, debug, test)
    config.set_debug(debug)
    config.set_verbose(verbose)
    config.set_test_cmd(test)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question about the codebase"),
    ctx: typer.Context = typer.Context
):
    """Ask a question about the codebase"""
    opts = ctx.obj
    claude = ClaudeAPIAgent(system_prompt=SYSTEM_PROMPT)
    handle_ask(question, opts.workdir, opts.include, opts.raw, claude)

@app.command()
def request(
    modification: str = typer.Argument(..., help="The modification request"),
    ctx: typer.Context = typer.Context
):
    """Process a modification request"""
    opts = ctx.obj
    claude = ClaudeAPIAgent(system_prompt=SYSTEM_PROMPT)
    handle_request(modification, opts.workdir, opts.include, opts.raw, claude)

@app.command()
def review(
    text: str = typer.Argument(..., help="Text to review"),
    ctx: typer.Context = typer.Context
):
    """Review the provided text"""
    opts = ctx.obj
    claude = ClaudeAPIAgent(system_prompt=SYSTEM_PROMPT)
    handle_review(text, claude, opts.raw)

@app.command()
def play(
    filepath: Path = typer.Argument(..., help="Saved prompt file to replay"),
    ctx: typer.Context = typer.Context
):
    """Replay a saved prompt file"""
    opts = ctx.obj
    claude = ClaudeAPIAgent(system_prompt=SYSTEM_PROMPT)
    handle_play(filepath, claude, opts.workdir, opts.raw)

@app.command()
def scan(ctx: typer.Context = typer.Context):
    """Preview files that would be analyzed"""
    opts = ctx.obj
    paths_to_scan = opts.include if opts.include else [opts.workdir]
    handle_scan(paths_to_scan, opts.workdir)

def main():
    app()

if __name__ == "__main__":
    main()
