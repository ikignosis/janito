from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Header, Footer, Static
from rich.panel import Panel
from rich.text import Text
from rich import box
from pathlib import Path
from typing import Dict, List

class ContentFlow(Screen):
    """Screen for content viewing flow with unified display format"""
    CSS = """
    ScrollableContainer {
        width: 100%;
        height: 100%;
        border: solid green;
        background: $surface;
        color: $text;
        padding: 1;
    }

    Container.panel {
        margin: 1;
        padding: 1;
        border: solid $primary;
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit"),
        Binding("up", "previous", "Previous"),
        Binding("down", "next", "Next"),
    ]

    def __init__(self, content: str):
        super().__init__()
        self.content = content
        self.files_by_type = self._organize_content()

    def _organize_content(self) -> Dict[str, List[str]]:
        """Organize content into file groups"""
        files = {
            'Modified': [],
            'New': [],
            'Deleted': []
        }

        # Parse content to extract file information
        for line in self.content.split('\n'):
            if line.strip().startswith('- '):
                file_path = line[2:].strip()
                if '(new)' in file_path:
                    files['New'].append(file_path)
                elif '(removed)' in file_path:
                    files['Deleted'].append(file_path)
                else:
                    files['Modified'].append(file_path)

        return files

    def _format_files_group(self, group_name: str, files: List[str], style: str) -> Text:
        """Format a group of files with consistent styling"""
        content = Text()
        if files:
            content.append(Text(f"\n─── {group_name} ───\n", style="cyan"))

            # Group files by directory
            files_by_dir = {}
            for file_path in files:
                clean_path = file_path.split(' (')[0]
                path = Path(clean_path)
                dir_path = str(path.parent)
                if dir_path not in files_by_dir:
                    files_by_dir[dir_path] = []
                files_by_dir[dir_path].append(path)

            # Display files by directory
            for dir_path, paths in sorted(files_by_dir.items()):
                first_in_dir = True
                for path in sorted(paths):
                    if first_in_dir:
                        display_path = dir_path
                    else:
                        pad_left = (len(dir_path) - 3) // 2
                        pad_right = len(dir_path) - 3 - pad_left
                        display_path = " " * pad_left + "..." + " " * pad_right

                    content.append(Text(f"• {display_path}/{path.name}\n", style=style))
                    first_in_dir = False

        return content

    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
            # Format content with consistent styling
            content = Text()

            # Add each file group with appropriate styling
            content.append(self._format_files_group("Modified", self.files_by_type['Modified'], "yellow"))
            content.append(self._format_files_group("New", self.files_by_type['New'], "green"))
            content.append(self._format_files_group("Deleted", self.files_by_type['Deleted'], "red"))

            # Create panel with formatted content
            panel = Panel(
                content,
                box=box.ROUNDED,
                border_style="cyan",
                title="Content Changes",
                title_align="center",
                padding=(1, 2)
            )

            yield Static(panel)
        yield Footer()

    def action_quit(self):
        self.app.exit()

    def action_previous(self):
        self.scroll_up()

    def action_next(self):
        self.scroll_down()