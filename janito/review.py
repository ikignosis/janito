from rich.console import Console
from rich.markdown import Markdown
from janito.common import progress_send_message
from janito.agents import AIAgent

def review_text(text: str, raw: bool = False) -> None:
    """Review the provided text using Claude"""
    console = Console()
    response = progress_send_message(f"Please review this text and provide feedback:\n\n{text}")
    if raw:
        console.print(response)
    else:
        console.print(Markdown(response))
