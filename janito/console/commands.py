from pathlib import Path
from typing import List
from rich.console import Console
from rich.panel import Panel
from janito.agents import AIAgent
from janito.analysis import build_request_analysis_prompt
from janito.scan import collect_files_content
from janito.common import progress_send_message
from janito.__main__ import handle_option_selection
from .display import display_help

def process_command(command: str, args: str, workdir: Path, include: List[Path], agent: AIAgent) -> None:
    """Process console commands using CLI functions for consistent behavior"""
    console = Console()
    
    # Parse command options
    raw = False
    verbose = False
    debug = False
    test_cmd = None
    
    # Extract options from args
    words = args.split()
    filtered_args = []
    i = 0
    while i < len(words):
        if words[i] == '--raw':
            raw = True
        elif words[i] == '--verbose':
            verbose = True
        elif words[i] == '--debug':
            debug = True
        elif words[i] == '--test' and i + 1 < len(words):
            test_cmd = words[i + 1]
            i += 1
        else:
            filtered_args.append(words[i])
        i += 1
    
    args = ' '.join(filtered_args)
    
    # Update config with command options
    from janito.config import config
    config.set_debug(debug)
    config.set_verbose(verbose)
    config.set_test_cmd(test_cmd)
    
    # Remove leading slash if present
    command = command.lstrip('/')
    
    # Handle command aliases
    command_aliases = {
        'h': 'help',
        'a': 'ask',
        'r': 'request',
        'q': 'quit',
        'exit': 'quit'
    }
    command = command_aliases.get(command, command)
    
    if command == "help":
        display_help()
        return
        
    if command == "quit":
        raise EOFError()
        
    if command == "ask":
        if not args:
            console.print(Panel(
                "[red]Ask command requires a question[/red]",
                title="Error",
                border_style="red"
            ))
            return
            
        # Use CLI question processing function
        from janito.__main__ import process_question
        process_question(args, workdir, include, raw, claude)
        return
        
    if command == "request":
        if not args:
            console.print(Panel(
                "[red]Request command requires a description[/red]",
                title="Error",
                border_style="red"
            ))
            return
            
        paths_to_scan = [workdir] if workdir else []
        if include:
            paths_to_scan.extend(include)
        files_content = collect_files_content(paths_to_scan, workdir)

        # Use CLI request processing functions
        initial_prompt = build_request_analysis_prompt(files_content, args)
        initial_response = progress_send_message(initial_prompt)
        
        from janito.__main__ import save_to_file
        save_to_file(initial_response, 'analysis', workdir)
        
        from janito.analysis import format_analysis
        format_analysis(initial_response, raw)
        handle_option_selection(initial_response, args, raw, workdir, include)
        return
        
    console.print(Panel(
        f"[red]Unknown command: /{command}[/red]\nType '/help' for available commands",
        title="Error",
        border_style="red"
    ))
