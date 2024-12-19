from pathlib import Path
from typing import Optional
from rich.console import Console
from janito.config import config
from janito.qa import ask_question, display_answer
from janito.workspace import workset  # Changed import
from ..base import BaseCLIHandler

class AskHandler(BaseCLIHandler):
    def handle(self, question: str):
        """Process a question about the codebase"""
        workset.refresh()
        
        if config.tui:
            answer = ask_question(question, workset._workspace.content)
            from janito.tui import TuiApp
            app = TuiApp(content=answer)
            app.run()
        else:
            answer = ask_question(question, workset._workspace.content)
            display_answer(answer)