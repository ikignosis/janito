from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from janito.common import progress_send_message
from janito.workspace import workset


QA_PROMPT = """Please provide a clear and concise answer to the following question about the workset you received above.

Question: {question}

Focus on providing factual information and explanations. Do not suggest code changes.
Format your response using markdown with appropriate headers and code blocks.
"""

def ask_question(question: str) -> str:
    """Process a question about the codebase and return the answer

    Args:
        question: The question to ask about the codebase
    """
    # Ensure content is refreshed and analyzed
    from janito.workspace import workset
    workset.show()

    prompt = QA_PROMPT.format(
        question=question,
    )
    return progress_send_message(prompt)


def display_answer(answer: str, raw: bool = False) -> None:
    """Display the answer as markdown"""
    console = Console()

    if raw:
        console.print(answer)
        return

    # Display markdown answer in a panel
    answer_panel = Panel(
        Markdown(answer),
        title="[bold]Answer[/bold]",
        title_align="center",
        padding=(1, 2)
    )

    console.print("\n")
    console.print(answer_panel)
    console.print("\n")
