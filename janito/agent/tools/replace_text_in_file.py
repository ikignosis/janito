from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_registry import register_tool

@register_tool(name="replace_text_in_file")


class ReplaceTextInFileTool(ToolBase):
    """Replace exact occurrences of a given text in a file.

This tool is designed to make minimal, targeted changes—preferably a small region modifications—rather than rewriting large sections or the entire file. Use it for precise, context-aware edits.

NOTE: Indentation (leading whitespace) must be included in both search_text and replacement_text. This tool does not automatically adjust or infer indentation; matches are exact, including whitespace.
"""
    def call(self, file_path: str, search_text: str, replacement_text: str, replace_all: bool = False) -> str:
        """
        Replace exact occurrences of a given text in a file.

        Args:
            file_path (str): Path to the file.
            search_text (str): Text to search for. Must include indentation (leading whitespace) if present in the file.
            replacement_text (str): Replacement text. Must include desired indentation (leading whitespace).
            replace_all (bool): If True, replace all occurrences; otherwise, only the first occurrence.
        Returns:
            str: Status message.
        """
        from janito.agent.tools.tools_utils import display_path
        disp_path = display_path(file_path)
        action = "all occurrences" if replace_all else None
        # Show only concise info (lengths, not full content)
        search_preview = (search_text[:20] + '...') if len(search_text) > 20 else search_text
        replace_preview = (replacement_text[:20] + '...') if len(replacement_text) > 20 else replacement_text
        search_lines = len(search_text.splitlines())
        replace_lines = len(replacement_text.splitlines())
        info_msg = f"📝 Replacing in {disp_path}: {search_lines}→{replace_lines} lines"
        if action:
            info_msg += f" ({action})"
        self.report_info(info_msg)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if replace_all:
                replaced_count = content.count(search_text)
                new_content = content.replace(search_text, replacement_text)
            else:
                occurrences = content.count(search_text)
                if occurrences > 1:
                    self.report_warning(f"⚠️ Search text is not unique.")
                    warning_detail = (
                        f"Strong Warning: Search text is not unique ({occurrences} occurrences found). No replacement was performed. "
                        f"To avoid incorrect replacements, ALWAYS read the entire file before making any assumptions or edits. "
                        f"Provide a more complete and unique search content based on the full file context."
                    )
                    return f"No changes made. {warning_detail}"
                replaced_count = 1 if occurrences == 1 else 0
                new_content = content.replace(search_text, replacement_text, 1)
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                file_changed = True
            else:
                file_changed = False
            warning = ''
            if replaced_count == 0:
                warning = " [Warning: Search text not found in file]"
            if not file_changed:
                self.report_warning(f" ℹ No changes made.")
                strong_warning = (" Strong Warning: No changes were made. "
                                  "To avoid incorrect assumptions or edits, ALWAYS read the entire file before proceeding. "
                                  "Ensure your search pattern is correct and present in the file.")
                return f"No changes made{warning}. Please review the original file.{strong_warning}"
            from janito.agent.tools.tools_utils import pluralize
            self.report_success(f" ✅ {replaced_count} {pluralize('block', replaced_count)} replaced")
            # Indentation check for agent warning
            def leading_ws(line):
                import re
                m = re.match(r"^\s*", line)
                return m.group(0) if m else ''
            search_indent = leading_ws(search_text.splitlines()[0]) if search_text.splitlines() else ''
            replace_indent = leading_ws(replacement_text.splitlines()[0]) if replacement_text.splitlines() else ''
            indent_warning = ''
            if search_indent != replace_indent:
                indent_warning = f" [Warning: Indentation mismatch between search and replacement text: '{search_indent}' vs '{replace_indent}']"
            if 'warning_detail' in locals():
                return f"Text replaced in {file_path}{warning}{indent_warning}\n{warning_detail}"
            return f"Text replaced in {file_path}{warning}{indent_warning}"

        except Exception as e:
            self.report_error(f" ❌ Error")
            return f"Error replacing text: {e}"

