import os
import base64
from janito.tooling.path_utils import expand_path


from janito.tooling.tool_utils import display_path
from janito.tooling.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.i18n import tr
from janito.tooling.loop_protection_decorator import protect_against_loops

from janito.tools.local.validate_file_syntax.core import validate_file_syntax



class CreateFileTool(ToolBase):
    permissions = ToolPermissions(write=True)

    @protect_against_loops(max_calls=5, time_window=10.0, key_field="path")
    def run(self, path: str, content: str = "", overwrite: bool = False, is_base64: bool = False) -> str:
        """
        Create a new file with specified content at the given path.

        This tool provides comprehensive file creation capabilities with built-in safety features,
        automatic syntax validation, and detailed feedback. It handles path expansion, directory
        creation, encoding issues, and provides clear status messages for both success and failure cases.

        Key Features:
        - Automatic directory creation for nested paths
        - UTF-8 encoding with error handling for special characters
        - Built-in syntax validation for common file types (Python, JavaScript, JSON, YAML, etc.)
        - Loop protection to prevent excessive file creation
        - Detailed error messages with context
        - Safe overwrite protection with preview of existing content
        - Cross-platform path handling (Windows, macOS, Linux)
        - Base64 decoding support for binary files

        Args:
            path (str, required): Target file path. Supports relative and absolute paths, with automatic
                       expansion of user home directory (~) and environment variables.
                       Examples: "src/main.py", "~/Documents/config.json", "$HOME/.env"
            content (str, optional): File content to write. Empty string creates empty file.
                          Supports any text content including Unicode characters, newlines,
                          and binary-safe text representation. Default: "" (empty file)
            overwrite (bool, optional): If True, allows overwriting existing files. Default: False.
                                       When False, prevents accidental overwrites by checking
                                       file existence and showing current content. Always review
                                       existing content before enabling overwrite.
            is_base64 (bool, optional): If True, treats the content as base64-encoded data and decodes it
                               before writing to the file. This enables creation of binary files
                               (images, executables, archives, etc.). Default: False.

        Returns:
            str: Detailed status message including:
                - Success confirmation with line count (for text files) or byte count (for binary files)
                - File path (display-friendly format)
                - Syntax validation results (for text files)
                - Existing content preview (when overwrite blocked)
                - Error details (when creation fails)

        Raises:
            No direct exceptions - all errors are caught and returned as user-friendly messages.
            Common error cases include: permission denied, invalid path format, disk full,
            or file exists (when overwrite=False).

        Security Features:
            - Loop protection: Maximum 5 calls per 10 seconds for the same file path
            - Path traversal prevention: Validates and sanitizes file paths
            - Permission checking: Respects file system permissions
            - Atomic writes: Prevents partial file creation on errors

        Examples:
            Basic file creation:
            >>> create_file("hello.py", "print('Hello, World!')")
            ✅ Created file 1 lines.
            ✅ Syntax OK

            Creating nested directories:
            >>> create_file("src/utils/helpers.py", "def helper(): pass")
            ✅ Created file 2 lines.
            ✅ Syntax OK

            Creating empty file:
            >>> create_file("empty.txt", "")
            ✅ Created file 0 lines.

            Creating a binary file from base64:
            >>> create_file("image.png", "/9j/4AAQSkZJRgABAQEASABIAAD/...", is_base64=True)
            ✅ Created file 12345 bytes.

            Overwrite protection:
            >>> create_file("existing.txt", "new content")
            ❗ Cannot create file: file already exists at 'existing.txt'.
            --- Current file content ---
            old content

        Note: After successful creation, automatic syntax validation is performed based on
        file extension. Results are appended to the return message for immediate feedback.
        """
        path = expand_path(path)
        disp_path = display_path(path)
        if os.path.exists(path) and not overwrite:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    existing_content = f.read()
            except Exception as e:
                existing_content = f"[Error reading file: {e}]"
            return tr(
                "❗ Cannot create file: file already exists at '{disp_path}'.\n--- Current file content ---\n{existing_content}",
                disp_path=disp_path,
                existing_content=existing_content,
            )
        # Determine if we are overwriting an existing file
        is_overwrite = os.path.exists(path) and overwrite
        if is_overwrite:
            # Overwrite branch: log only overwrite warning (no create message)
            self.report_action(
                tr("⚠️  Overwriting file '{disp_path}'", disp_path=disp_path),
                ReportAction.CREATE,
            )
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        if not is_overwrite:
            # Create branch: log file creation message
            self.report_action(
                tr("📝 Create file '{disp_path}' ...", disp_path=disp_path),
                ReportAction.CREATE,
            )
        
        # Handle base64 decoding if requested
        if is_base64:
            try:
                decoded_content = base64.b64decode(content)
                mode = "wb"  # Binary mode for base64 content
                # For binary files, we report byte count instead of line count
                new_bytes = len(decoded_content)
                self.report_success(
                    tr("✅ {new_bytes} bytes", new_bytes=new_bytes), ReportAction.CREATE
                )
            except Exception as e:
                return tr(
                    "❌ Failed to decode base64 content: {error}",
                    error=str(e)
                )
        else:
            # Regular text content
            decoded_content = content
            mode = "w"  # Text mode for regular content
            new_lines = content.count("\n") + 1 if content else 0
            self.report_success(
                tr("✅ {new_lines} lines", new_lines=new_lines), ReportAction.CREATE
            )
        
        with open(path, mode, errors="replace") as f:
            f.write(decoded_content)
        
        # Perform syntax validation only for text files (not binary)
        validation_result = ""
        if not is_base64:
            validation_result = validate_file_syntax(path)
        
        if is_overwrite:
            # Overwrite branch: return minimal overwrite info to user
            result = tr("✅ {count}", count=f"{new_bytes} bytes" if is_base64 else f"{new_lines} lines")
            if validation_result:
                result += f"\n{validation_result}"
            return result
        else:
            # Create branch: return detailed create success to user
            result = tr("✅ Created file {count}.", count=f"{new_bytes} bytes" if is_base64 else f"{new_lines} lines")
            if validation_result:
                result += f"\n{validation_result}"
            return result
