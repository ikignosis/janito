from rich.console import Console
from rich.markdown import Markdown
from janito.claude import ClaudeAPIAgent
from janito.common import progress_send_message

QA_PROMPT = """Please provide a clear and concise answer to the following question about the codebase:

Question: {question}

Current files:
<files>
{files_content}
</files>

Focus on providing factual information and explanations. Do not suggest code changes.
"""

def ask_question(question: str, files_content: str, claude: ClaudeAPIAgent) -> str:
    """Process a question about the codebase and return the answer"""
    prompt = QA_PROMPT.format(
        question=question,
        files_content=files_content
    )
    return progress_send_message(claude, prompt)

def display_answer(answer: str, raw: bool = False) -> None:
    """Display the answer in markdown or raw format"""
    console = Console()
    if raw:
        console.print(answer)
    else:
        md = Markdown(answer)
        console.print(md)