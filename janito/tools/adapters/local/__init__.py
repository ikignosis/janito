from .adapter import LocalToolsAdapter

from .ask_user import AskUserTool
from .copy_file import CopyFileTool
from .create_directory import CreateDirectoryTool
from .create_file import CreateFileTool
from .fetch_url import FetchUrlTool
from .find_files import FindFilesTool
from .view_file import ViewFileTool
from .read_files import ReadFilesTool
from .move_file import MoveFileTool
from .open_url import OpenUrlTool
from .open_html_in_browser import OpenHtmlInBrowserTool
from .python_code_run import PythonCodeRunTool
from .python_command_run import PythonCommandRunTool
from .python_file_run import PythonFileRunTool
from .remove_directory import RemoveDirectoryTool
from .remove_file import RemoveFileTool
from .replace_text_in_file import ReplaceTextInFileTool
from .run_bash_command import RunBashCommandTool
from .run_powershell_command import RunPowershellCommandTool
from .get_file_outline.core import GetFileOutlineTool
from .get_file_outline.search_outline import SearchOutlineTool
from .search_text.core import SearchTextTool
from .validate_file_syntax.core import ValidateFileSyntaxTool
from .read_chart import ReadChartTool

from janito.tools.tool_base import ToolPermissions
import os
from janito.tools.permissions import get_global_allowed_permissions

# Singleton tools adapter with all standard tools registered
local_tools_adapter = LocalToolsAdapter(workdir=os.getcwd())


def get_local_tools_adapter(workdir=None):
    return LocalToolsAdapter(workdir=workdir or os.getcwd())


# Register tools
for tool_class in [
    AskUserTool,
    CopyFileTool,
    CreateDirectoryTool,
    CreateFileTool,
    FetchUrlTool,
    FindFilesTool,
    ViewFileTool,
    ReadFilesTool,
    MoveFileTool,
    OpenUrlTool,
    OpenHtmlInBrowserTool,
    PythonCodeRunTool,
    PythonCommandRunTool,
    PythonFileRunTool,
    RemoveDirectoryTool,
    RemoveFileTool,
    ReplaceTextInFileTool,
    RunBashCommandTool,
    RunPowershellCommandTool,
    GetFileOutlineTool,
    SearchOutlineTool,
    SearchTextTool,
    ValidateFileSyntaxTool,
    ReadChartTool,
]:
    local_tools_adapter.register_tool(tool_class)

# DEBUG: Print registered tools at startup
