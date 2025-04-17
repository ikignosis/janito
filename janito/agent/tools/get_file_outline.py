from janito.agent.tools.tool_base import ToolBase
import os
import re
from janito.agent.tools.rich_utils import print_info, print_success

class GetFileOutlineTool(ToolBase):
    """Get an outline of the file structure for any file type. For Python, Markdown, and HTML files, provides a structured outline; for .txt files, returns a summary with the number of lines and words; for other file types, shows basic info such as the total number of lines."""
    def call(self, path: str) -> str:
        print_info(f"\U0001F4D1 Getting file outline for: '{path}' ...")
        if not os.path.isfile(path):
            msg = f"\u274c File not found: {path}"
            print_success(msg)
            return msg
        ext = os.path.splitext(path)[1].lower()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            msg = f"\u274c Could not read file: {e}"
            print_success(msg)
            return msg
        if ext == '.py':
            outline = self._outline_python(lines)
            outline_type = 'Python classes/functions'
            items_count = outline.count('\n') + 1 if outline.strip() else 0
        elif ext in ('.md', '.markdown'):
            outline = self._outline_markdown(lines)
            outline_type = 'Markdown headers'
            items_count = outline.count('\n') + 1 if outline.strip() else 0
        elif ext == '.html':
            outline = self._outline_html(lines)
            outline_type = 'HTML tags'
            items_count = outline.count('\n') + 1 if outline.strip() else 0
        elif ext == '.txt':
            num_lines = len(lines)
            num_words = sum(len(line.split()) for line in lines)
            outline = f"Text file summary: {num_lines} lines, {num_words} words."
            outline_type = 'Text file summary'
            items_count = num_lines
        else:
            outline = f"\u26a0\ufe0f Outline not supported for file type: {ext}"
            outline_type = 'Unsupported file type'
            items_count = 0
        summary_line = f"\u2705 File outline ({outline_type}) | {items_count} items found in '{os.path.basename(path)}'"
        print_success(summary_line)
        # Compose output: summary line, then outline/summary (if any)
        if outline.strip():
            return f"{summary_line}\n{outline}"
        else:
            return summary_line

    def _outline_python(self, lines):
        outline = []
        class_or_func = re.compile(r'^(\s*)(class|def) (\w+)')
        for idx, line in enumerate(lines, 1):
            m = class_or_func.match(line)
            if m:
                indent, kind, name = m.groups()
                prefix = '  ' * (len(indent) // 2)
                outline.append(f"{idx}: {prefix}{kind} {name}")
        return '\n'.join(outline) if outline else "No classes or functions found."

    def _outline_markdown(self, lines):
        outline = []
        header = re.compile(r'^(#+) (.+)')
        for idx, line in enumerate(lines, 1):
            m = header.match(line)
            if m:
                hashes, title = m.groups()
                level = len(hashes)
                outline.append(f"{idx}: {'  ' * (level-1)}Header level {level}: {title}")
        return '\n'.join(outline) if outline else "No headers found."

    def _outline_html(self, lines):
        outline = []
        tag = re.compile(r'<([a-zA-Z0-9]+)')
        for idx, line in enumerate(lines, 1):
            for m in tag.finditer(line):
                outline.append(f"{idx}: Tag <{m.group(1)}>")
        return '\n'.join(outline) if outline else "No HTML tags found."
