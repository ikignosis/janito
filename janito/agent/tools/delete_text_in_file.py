from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.i18n import tr


@register_tool(name="delete_text_in_file")
class DeleteTextInFileTool(ToolBase):
    """
    Delete all occurrences of text between start_marker and end_marker (inclusive) in a file, using exact string markers.

    Args:
        file_path (str): Path to the file to modify.
        start_marker (str): The starting delimiter string.
        end_marker (str): The ending delimiter string.
        backup (bool, optional): If True, create a backup (.bak) before deleting. Defaults to False.
    Returns:
        str: Status message indicating the result.
    """

    def run(
        self,
        file_path: str,
        start_marker: str,
        end_marker: str,
        backup: bool = False,
    ) -> str:
        import shutil
        from janito.agent.tools_utils.utils import display_path

        disp_path = display_path(file_path)
        backup_path = file_path + ".bak"
        backup_msg = ""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            self.report_error(tr(" ❌ Error reading file: {error}", error=e))
            return tr("Error reading file: {error}", error=e)

        start_count = content.count(start_marker)
        if start_count > 1:
            self.report_error("Need more context for start_marker")
            return (
                f"Error: start_marker is not unique in {disp_path}. "
                "Try including the next line(s) for more context."
            )

        end_count = content.count(end_marker)
        if end_count > 1:
            self.report_error("Need more context for end_marker")
            return (
                f"Error: end_marker is not unique in {disp_path}. "
                "Try including the previous line(s) for more context."
            )

        count = 0
        new_content = content
        while True:
            start_idx = new_content.find(start_marker)
            if start_idx == -1:
                break
            end_idx = new_content.find(end_marker, start_idx + len(start_marker))
            if end_idx == -1:
                break
            # Remove from start_marker to end_marker (inclusive)
            new_content = (
                new_content[:start_idx] + new_content[end_idx + len(end_marker) :]
            )
            count += 1

        if count == 0:
            self.report_warning(
                tr(
                    "No blocks found between markers in {disp_path}.",
                    disp_path=disp_path,
                )
            )
            return tr(
                "No blocks found between markers in {file_path}.", file_path=file_path
            )

        if backup:
            shutil.copy2(file_path, backup_path)
            backup_msg = f" (A backup was saved to {backup_path})"
        with open(file_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(new_content)

        self.report_success(
            tr(
                "Deleted {count} block(s) between markers in {disp_path}.",
                count=count,
                disp_path=disp_path,
            )
        )
        return (
            tr(
                "Deleted {count} block(s) between markers in {file_path}.",
                count=count,
                file_path=file_path,
            )
            + backup_msg
        )
