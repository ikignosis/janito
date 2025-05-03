from janito.agent.tool_registry import register_tool
from .python_outline import parse_python_outline
from .markdown_outline import parse_markdown_outline
from janito.agent.tools_utils.formatting import (
    format_outline_table,
    format_markdown_outline_table,
)
import os
from janito.agent.tool_base import ToolBase
from janito.agent.tools_utils.action_type import ActionType
from janito.agent.tools_utils.utils import display_path, pluralize
from janito.i18n import tr


@register_tool(name="get_file_outline")
class GetFileOutlineTool(ToolBase):
    """
    Get an outline of a file's structure. Supports Python and Markdown files.

    Args:
        file_path (str): Path to the file to outline.
    """

    def run(self, file_path: str) -> str:
        try:
            self.report_info(
                ActionType.READ,
                tr(
                    "📄 Outlining file '{disp_path}' ...",
                    disp_path=display_path(file_path),
                ),
            )
            ext = os.path.splitext(file_path)[1].lower()
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            if ext == ".py":
                outline_items = parse_python_outline(lines)
                outline_type = "python"
                table = format_outline_table(outline_items)
                self.report_success(
                    tr(
                        "✅ Outlined {count} {item_word}",
                        count=len(outline_items),
                        item_word=pluralize("item", len(outline_items)),
                    )
                )
                return (
                    tr(
                        "Outline: {count} items ({outline_type})\n",
                        count=len(outline_items),
                        outline_type=outline_type,
                    )
                    + table
                )
            elif ext == ".md":
                outline_items = parse_markdown_outline(lines)
                outline_type = "markdown"
                table = format_markdown_outline_table(outline_items)
                self.report_success(
                    tr(
                        "✅ Outlined {count} {item_word}",
                        count=len(outline_items),
                        item_word=pluralize("item", len(outline_items)),
                    )
                )
                return (
                    tr(
                        "Outline: {count} items ({outline_type})\n",
                        count=len(outline_items),
                        outline_type=outline_type,
                    )
                    + table
                )
            else:
                outline_type = "default"
                self.report_success(tr("✅ Outlined {count} items", count=len(lines)))
                return tr(
                    "Outline: {count} lines ({outline_type})\nFile has {count} lines.",
                    count=len(lines),
                    outline_type=outline_type,
                )
        except Exception as e:
            self.report_error(tr("❌ Error reading file: {error}", error=e))
            return tr("Error reading file: {error}", error=e)
