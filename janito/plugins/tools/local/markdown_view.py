from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.plugins.tools.local.adapter import register_local_tool
from janito.tools.tool_utils import display_path
from janito.i18n import tr
from janito.tools.loop_protection_decorator import protect_against_loops


@register_local_tool
class MarkdownViewTool(ToolBase):
    """
    Display markdown content in the terminal using rich markdown rendering.

    Args:
        path (str): Path to the markdown file to display.
        width (int, optional): Display width. Defaults to 80.
        theme (str, optional): Markdown theme. Defaults to "github".

    Returns:
        str: Status message indicating the result of the markdown display.
    """

    permissions = ToolPermissions(read=True)
    tool_name = "markdown_view"

    @protect_against_loops(max_calls=5, time_window=10.0, key_field="path")
    def run(self, path: str, width: int = 80, theme: str = "github") -> str:
        import os
        from janito.tools.path_utils import expand_path

        path = expand_path(path)
        disp_path = display_path(path)
        
        self.report_action(
            tr("📖 View markdown '{disp_path}'", disp_path=disp_path),
            ReportAction.READ,
        )
        
        try:
            if not os.path.exists(path):
                return f"❌ Error: File not found at '{path}'"
                
            if not path.lower().endswith(('.md', '.markdown')):
                return f"⚠️ Warning: File '{path}' does not appear to be a markdown file"

            # Read the markdown file
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                markdown_content = f.read()

            if not markdown_content.strip():
                return f"⚠️ Warning: Markdown file '{path}' is empty"

            # Import rich components for markdown rendering
            try:
                from rich.console import Console
                from rich.markdown import Markdown
                from rich.panel import Panel
                from rich.text import Text
            except ImportError:
                return "❌ Error: rich library not available for markdown rendering"

            # Create console with specified width
            console = Console(width=width)
            
            # Create markdown object
            markdown = Markdown(markdown_content)
            
            # Display the markdown with a header
            console.print(f"\n[bold cyan]📄 Markdown: {disp_path}[/bold cyan]")
            console.print("=" * min(len(disp_path) + 15, width))
            console.print()
            
            # Render the markdown content
            console.print(markdown)
            console.print()
            
            self.report_success(
                tr(" ✅ Markdown displayed: {disp_path}", disp_path=disp_path)
            )
            
            return f"✅ Markdown displayed: {disp_path}"

        except FileNotFoundError:
            self.report_warning(tr("❗ not found"))
            return f"❌ Error: File not found at '{path}'"
        except PermissionError:
            self.report_error(tr(" ❌ Permission denied: {path}", path=disp_path))
            return f"❌ Error: Permission denied reading '{path}'"
        except UnicodeDecodeError as e:
            self.report_error(tr(" ❌ Encoding error: {error}", error=e))
            return f"❌ Error: Unable to decode file '{path}' - {e}"
        except Exception as e:
            self.report_error(tr(" ❌ Error: {error}", error=e))
            return f"❌ Error displaying markdown: {e}"