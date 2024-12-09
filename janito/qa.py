from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.rule import Rule
from janito.agents import AIAgent
from janito.common import progress_send_message
from janito.scan import show_content_stats

QA_PROMPT = """Please provide a clear and concise answer to the following question about the codebase:

Question: {question}

Current files:
<files>
{files_content}
</files>

Focus on providing factual information and explanations. Do not suggest code changes.
Format your response using markdown with appropriate headers and code blocks.
"""

def ask_question(question: str, files_content: str) -> str:
    """Process a question about the codebase and return the answer"""
    # Show content stats before processing
    show_content_stats(files_content)
    
    prompt = QA_PROMPT.format(
        question=question,
        files_content=files_content
    )
    return progress_send_message(prompt)


def display_answer(answer: str, raw: bool = False) -> None:
    """Display the answer as markdown with consistent colors"""
    console = Console()
    
    # Define consistent colors
    COLORS = {
        'primary': '#729FCF',    # Soft blue for primary elements
        'secondary': '#8AE234',  # Bright green for actions/success
        'accent': '#AD7FA8',     # Purple for accents
        'muted': '#7F9F7F',      # Muted green for less important text
    }
    
    if raw:
        console.print(answer)
        return
    
    # Display markdown answer in a panel with consistent styling
    answer_panel = Panel(
        Markdown(answer),
        title="[bold]Answer[/bold]",
        title_align="center",
        border_style=COLORS['primary'],
        padding=(1, 2)
    )
    
    console.print("\n")
    console.print(Rule(style=COLORS['accent']))
    console.print(answer_panel)
    console.print(Rule(style=COLORS['accent']))
    console.print("\n")