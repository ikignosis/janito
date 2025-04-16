from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error
import os

@ToolHandler.register_tool
def edit_file(
    TargetFile: str,
    CodeMarkdownLanguage: str,
    Instruction: str,
    ReplacementChunks: list,
    TargetLintErrorIds: list = None
) -> str:
    """
    Edit an existing file by replacing specific chunks of code.
    Parameters:
      - TargetFile (string): File to modify. This should be the first parameter specified.
      - CodeMarkdownLanguage (string): Language for syntax highlighting.
      - Instruction (string): Description of the change.
      - ReplacementChunks (list of object): Each chunk specifies a replacement:
          - AllowMultiple (bool): If true, replace all occurrences of TargetContent.
          - TargetContent (string): Exact code/text to search for (must match exactly, including whitespace).
          - ReplacementContent (string): New code/text to replace TargetContent.
      - TargetLintErrorIds (list of string, optional): Lint error IDs to fix. Leave empty if unrelated.
    """
    print_info(f"📝 edit_file | File: {TargetFile} | Language: {CodeMarkdownLanguage} | Instruction: {Instruction}")
    if not os.path.isfile(TargetFile):
        print_error(f"! File not found")
        return f"Error: File not found: {TargetFile}"
    # Backup original file
    backup_file = TargetFile + ".bak"
    import shutil
    shutil.copy2(TargetFile, backup_file)
    print_info(f"🔒 Backup saved as {backup_file}")
    with open(TargetFile, "r", encoding="utf-8") as f:
        content = f.read()
    for chunk in ReplacementChunks:
        allow_multiple = chunk.get("AllowMultiple", False)
        target = chunk.get("TargetContent", "")
        replacement = chunk.get("ReplacementContent", "")
        if allow_multiple:
            if target not in content:
                print_error(f"! TargetContent not found for AllowMultiple")
                return f"Error: TargetContent not found for AllowMultiple: {target}"
            content = content.replace(target, replacement)
        else:
            if content.count(target) == 0:
                print_error(f"! TargetContent not found")
                return f"Error: TargetContent not found: {target}"
            if content.count(target) > 1:
                print_error(f"! TargetContent is not unique")
                return f"Error: TargetContent is not unique: {target}"
            content = content.replace(target, replacement, 1)
    with open(TargetFile, "w", encoding="utf-8") as f:
        f.write(content)
    print_success(f"✅ Updated {TargetFile}")
    return f"Updated {TargetFile} as instructed. Backup saved as {backup_file}"
