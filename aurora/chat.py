import sys
from rich.console import Console
from rich.markdown import Markdown


def chat_loop(agent):
    console = Console()
    messages = []

    # Add system prompt if available
    if agent.system_prompt:
        messages.append({"role": "system", "content": agent.system_prompt})

    console.print("[bold green]Entering chat mode. Type /exit to quit.[/bold green]")

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in {"/exit", "/quit"}:
                print("Exiting chat mode.")
                break
            if not user_input:
                continue

            messages.append({"role": "user", "content": user_input})

            def on_content(content):
                console.print(Markdown(content))

            try:
                response = agent.chat(messages, on_content=on_content)
            except Exception as e:
                console.print(f"[red]Error during chat: {e}[/red]")
                continue

        except KeyboardInterrupt:
            print("\n[Interrupted by user]")
            sys.exit(0)
