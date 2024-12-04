from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from pathlib import Path
from rich.console import Console
from janito.claude import ClaudeAPIAgent
from janito.prompts import build_request_analisys_prompt, SYSTEM_PROMPT
from janito.scan import collect_files_content
from janito.__main__ import handle_option_selection

def start_console_session(workdir: Path, include: list[Path] = None) -> None:
    """Start an interactive console session using prompt_toolkit"""
    console = Console()
    claude = ClaudeAPIAgent(system_prompt=SYSTEM_PROMPT)

    # Setup prompt session with history
    history_file = workdir / '.janito' / 'console_history'
    history_file.parent.mkdir(parents=True, exist_ok=True)
    session = PromptSession(history=FileHistory(str(history_file)))

    from importlib.metadata import version
    try:
        ver = version("janito")
    except:
        ver = "dev"

    console.print("\n[bold blue]╔═══════════════════════════════════════════╗[/bold blue]")
    console.print("[bold blue]║           Janito AI Assistant             ║[/bold blue]")
    console.print("[bold blue]║                v" + ver.ljust(8) + "                  ║[/bold blue]")
    console.print("[bold blue]╠═══════════════════════════════════════════╣[/bold blue]")
    console.print("[bold blue]║  Your AI-powered development companion    ║[/bold blue]")
    console.print("[bold blue]╚═══════════════════════════════════════════╝[/bold blue]")
    console.print("\n[cyan]Type your requests or 'exit' to quit[/cyan]\n")

    while True:
        try:
            request = session.prompt("janito> ")
            if request.lower() in ('exit', 'quit'):
                break

            if not request.strip():
                continue

            # Get current files content
            paths_to_scan = [workdir] if workdir else []
            if include:
                paths_to_scan.extend(include)
            files_content = collect_files_content(paths_to_scan, workdir)

            # Get initial analysis
            initial_prompt = build_request_analisys_prompt(files_content, request)
            initial_response = claude.send_message(initial_prompt)

            # Show response and handle options
            console.print(initial_response)
            handle_option_selection(claude, initial_response, request, False, workdir, include)

        except KeyboardInterrupt:
            continue
        except EOFError:
            break