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

def extract_code_blocks(text: str) -> Dict[str, List[str]]:
    """Extract code blocks by language from markdown text"""
    pattern = r'```(\w+)?\n(.*?)```'
    blocks = {}
    
    for match in re.finditer(pattern, text, re.DOTALL):
        lang = match.group(1) or 'text'
        code = match.group(2).strip()
        if lang not in blocks:
            blocks[lang] = []
        blocks[lang].append(code)
    
    return blocks

def format_code_blocks(text: str) -> str:
    """Format code blocks with syntax highlighting"""
    def replace_block(match):
        lang = match.group(1) or 'text'
        code = match.group(2).strip()
        syntax = Syntax(code, lang, theme="monokai", line_numbers=True)
        return f"\n{syntax}\n"
    
    pattern = r'```(\w+)?\n(.*?)```'
    return re.sub(pattern, replace_block, text, flags=re.DOTALL)

def ask_question(question: str, files_content: str, claude: ClaudeAPIAgent) -> str:
    """Process a question about the codebase and return the answer"""
    prompt = QA_PROMPT.format(
        question=question,
        files_content=files_content
    )
    return progress_send_message(claude, prompt)

def display_answer(answer: str, raw: bool = False) -> None:
    """Display the answer with enhanced formatting"""
    console = Console()
    
    if raw:
        console.print(answer)
        return
    
    # Extract and format code blocks
    code_blocks = extract_code_blocks(answer)
    formatted_answer = format_code_blocks(answer)
    
    # Create summary if multiple code blocks exist
    if len(code_blocks) > 0:
        summary = Table(title="Code Blocks Summary", box=None)
        summary.add_column("Language", style="cyan")
        summary.add_column("Count", style="green")
        
        for lang, blocks in code_blocks.items():
            summary.add_row(lang, str(len(blocks)))
        
        console.print("\n")
        console.print(summary)
    
    # Display formatted answer in a panel
    answer_panel = Panel(
        Markdown(formatted_answer),
        title="Answer",
        border_style="blue",
        padding=(1, 2)
    )
    
    console.print("\n")
    console.print(answer_panel)
    console.print("\n")