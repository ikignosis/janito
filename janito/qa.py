from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from janito.claude import ClaudeAPIAgent
from janito.common import progress_send_message
from typing import Dict, List
import re

QA_PROMPT = """Please provide a clear and concise answer to the following question about the codebase:

Question: {question}

Current files:
<files>
{files_content}
</files>

Focus on providing factual information and explanations. Do not suggest code changes.
Format your response using markdown with appropriate headers and code blocks.
"""

def ask_question(question: str, files_content: str, claude: ClaudeAPIAgent) -> str:
    """Process a question about the codebase and return the answer"""
    prompt = QA_PROMPT.format(
        question=question,
        files_content=files_content
    )
    return progress_send_message(claude, prompt)

def display_answer(answer: str, raw: bool = False) -> None:
    """Display the answer as markdown"""
    console = Console()
    
    if raw:
        console.print(answer)
        return
    
    # Display markdown answer in a panel
    answer_panel = Panel(
        Markdown(answer),
        title="Answer",
        border_style="blue",
        padding=(1, 2)
    )
    
    console.print("\n")
    console.print(answer_panel)
    console.print("\n")