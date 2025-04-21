from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.agent.tools.tools_utils import pluralize


@register_tool(name="replace_text_in_file")
class ReplaceTextInFileTool(ToolBase):
    """
    Replace exact occurrences of a given text in a file.

    Args:
        file_path (str): Path to the file to modify.
        search_text (str): The exact text to search for (including indentation).
        replacement_text (str): The text to replace with (including indentation).
        replace_all (bool): If True, replace all occurrences; otherwise, only the first occurrence.
        backup (bool, optional): If True, create a backup (.bak) before replacing. Recommend using backup=True only in the first call to avoid redundant backups. Defaults to False.
    Returns:
        str: Status message. Example:
            - "Text replaced in /path/to/file (backup at /path/to/file.bak)"
            - "No changes made. [Warning: Search text not found in file] Please review the original file."
            - "Error replacing text: <error message>"
    """

    def call(
        self,
        file_path: str,
        search_text: str,
        replacement_text: str,
        replace_all: bool = False,
        backup: bool = False,
    ) -> str:
        from janito.agent.tools.tools_utils import display_path

        disp_path = display_path(file_path)
        action = "all occurrences" if replace_all else None
        # Show only concise info (lengths, not full content)
        search_preview = (
            (search_text[:20] + "...") if len(search_text) > 20 else search_text
        )
        replace_preview = (
            (replacement_text[:20] + "...")
            if len(replacement_text) > 20
            else replacement_text
        )
        search_lines = len(search_text.splitlines())
        replace_lines = len(replacement_text.splitlines())
        info_msg = f"\U0001f4dd Replacing in {disp_path}: {search_lines}\u2192{replace_lines} lines"
        if action:
            info_msg += f" ({action})"
        self.report_info(info_msg)

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            if replace_all:
                replaced_count = content.count(search_text)
                new_content = content.replace(search_text, replacement_text)
            else:
                occurrences = content.count(search_text)
                if occurrences > 1:
                    self.report_warning("\u26a0\ufe0f Search text is not unique.")
                    warning_detail = "The search text is not unique. Expand your search context with surrounding lines to ensure uniqueness."
                    return f"No changes made. {warning_detail}"
                replaced_count = 1 if occurrences == 1 else 0
                new_content = content.replace(search_text, replacement_text, 1)
            import shutil

            backup_path = file_path + ".bak"
            if backup and new_content != content:
                # Create a .bak backup before writing changes
                shutil.copy2(file_path, backup_path)
            if new_content != content:
                with open(file_path, "w", encoding="utf-8", errors="replace") as f:
                    f.write(new_content)
                file_changed = True
            else:
                file_changed = False
            warning = ""
            if replaced_count == 0:
                warning = " [Warning: Search text not found in file]"
            if not file_changed:
                self.report_warning(" \u2139\ufe0f No changes made.")
                concise_warning = "The search text was not found. Expand your search context with surrounding lines if needed."
                return f"No changes made. {concise_warning}"

            self.report_success(
                f" \u2705 {replaced_count} {pluralize('block', replaced_count)} replaced"
            )

            # Indentation check for agent warning
            def leading_ws(line):
                import re

                m = re.match(r"^\s*", line)
                return m.group(0) if m else ""

            search_indent = (
                leading_ws(search_text.splitlines()[0])
                if search_text.splitlines()
                else ""
            )
            replace_indent = (
                leading_ws(replacement_text.splitlines()[0])
                if replacement_text.splitlines()
                else ""
            )
            indent_warning = ""
            if search_indent != replace_indent:
                indent_warning = f" [Warning: Indentation mismatch between search and replacement text: '{search_indent}' vs '{replace_indent}']"
            if "warning_detail" in locals():
                return f"Text replaced in {file_path}{warning}{indent_warning} (backup at {backup_path})\n{warning_detail}"
            return f"Text replaced in {file_path}{warning}{indent_warning} (backup at {backup_path})"

        except Exception as e:
            self.report_error(" \u274c Error")
            return f"Error replacing text: {e}"
