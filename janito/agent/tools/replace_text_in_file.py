from janito.agent.tools.tool_base import ToolBase
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error, format_path

class ReplaceTextInFileTool(ToolBase):
    """Replace exact occurrences of a given text in a file.

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
        import os
        filename = os.path.basename(file_path)
        action = "all occurrences" if replace_all else "first occurrence"
        # Show only concise info (lengths, not full content)
        search_preview = (search_text[:20] + '...') if len(search_text) > 20 else search_text
        replace_preview = (replacement_text[:20] + '...') if len(replacement_text) > 20 else replacement_text
        print_info(f"📝 Replacing in {filename}: '{search_preview}'  '{replace_preview}' ({action})", end="")
        self.update_progress(f"Replacing text in {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if replace_all:
                replaced_count = content.count(search_text)
                new_content = content.replace(search_text, replacement_text)
            else:
                occurrences = content.count(search_text)
                if occurrences > 1:
                    print_error(f" ❌ Error: Search text is not unique ({occurrences} occurrences found). Provide more detailed context.")
                    return f"Error: Search text is not unique ({occurrences} occurrences found) in {file_path}. Provide more detailed context for unique replacement."
                replaced_count = 1 if occurrences == 1 else 0
                new_content = content.replace(search_text, replacement_text, 1)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            warning = ''
            if replaced_count == 0:
                warning = " [Warning: Search text not found in file]"
            print_success(f" ✅ {replaced_count} replaced{warning}")
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
            return f"Text replaced in {file_path}{warning}{indent_warning}"

        except Exception as e:
            print_error(f" ❌ Error: {e}")
            return f"Error replacing text: {e}"

ToolHandler.register_tool(ReplaceTextInFileTool, name="replace_text_in_file")
