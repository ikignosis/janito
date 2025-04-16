from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error
import os

@ToolHandler.register_tool
def edit_file(
    TargetFile: str,
    CodeMarkdownLanguage: str,
    Instruction: str,
    StringReplacements: list,
    TargetLintErrorIds: list = None
) -> str:
    """
    Edit an existing file by replacing exact strings.
    Parameters:
      - TargetFile (string): File to modify. This should be the first parameter specified.
      - CodeMarkdownLanguage (string): Language for syntax highlighting.
      - Instruction (string): Description of the change.
      - StringReplacements (list of object): Each object specifies an exact string replacement:
          - allow_multiple (bool): If true, replace all occurrences of search_string.
          - search_string (string): Exact string to search for (must match exactly, including whitespace).
          - replacement_string (string): New string to replace search_string (must also be exact to preserve syntax alignment and formatting).
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
    for chunk in StringReplacements:
        allow_multiple = chunk.get("allow_multiple", False)
        target = chunk.get("search_string", "")
        replacement = chunk.get("replacement_string", "")
        if allow_multiple:
            if target not in content:
                print_info(f"! TargetContent not found for AllowMultiple")
                return f"Info: TargetContent not found for AllowMultiple: {target}"
            content = content.replace(target, replacement)
        else:
            if content.count(target) == 0:
                print_info(f"! TargetContent not found")
                return f"Info: TargetContent not found: {target}"
            if content.count(target) > 1:
                print_error(f"! TargetContent is not unique")
                return f"Error: TargetContent is not unique: {target}"
            content = content.replace(target, replacement, 1)
    with open(TargetFile, "w", encoding="utf-8") as f:
        f.write(content)
    print_success(f"✅ Updated {TargetFile}")
    return f"Updated {TargetFile} as instructed. Backup saved as {backup_file}"
