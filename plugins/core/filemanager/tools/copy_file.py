import os
from janito.tools.path_utils import expand_path
import shutil
from typing import List, Union
from janito.tools.adapters.local.adapter import register_local_tool
from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.tools.tool_utils import display_path
from janito.report_events import ReportAction
from janito.i18n import tr


@register_local_tool
class CopyFileTool(ToolBase):
    """
    Copy one or more files to a target directory, or copy a single file to a new file.
    Args:
        sources (str): Space-separated path(s) to the file(s) to copy.
            For multiple sources, provide a single string with paths separated by spaces.
        target (str): Destination path. If copying multiple sources, this must be an existing directory.
        overwrite (bool, optional): Overwrite existing files. Default: False.
            Recommended only after reading the file to be overwritten.
    Returns:
        str: Status string for each copy operation.
    """

    permissions = ToolPermissions(read=True, write=True)
    tool_name = "copy_file"

    def run(self, sources: str, target: str, overwrite: bool = False) -> str:
        source_list = [expand_path(src) for src in sources.split() if src]
        target = expand_path(target)
        messages = []
        if len(source_list) > 1:
            if not os.path.isdir(target):
                return tr(
                    "❗ Target must be an existing directory when copying multiple files: '{target}'",
                    target=display_path(target),
                )
            for src in source_list:
                if not os.path.isfile(src):
                    messages.append(
                        tr(
                            "❗ Source file does not exist: '{src}'",
                            src=display_path(src),
                        )
                    )
                    continue
                dst = os.path.join(target, os.path.basename(src))
                messages.append(self._copy_one(src, dst, overwrite=overwrite))
        else:
            src = source_list[0]
            if os.path.isdir(target):
                dst = os.path.join(target, os.path.basename(src))
            else:
                dst = target
            messages.append(self._copy_one(src, dst, overwrite=overwrite))
        return "\n".join(messages)

    def _copy_one(self, src, dst, overwrite=False) -> str:
        disp_src = display_path(src)
        disp_dst = display_path(dst)
        if not os.path.isfile(src):
            return tr("❗ Source file does not exist: '{src}'", src=disp_src)
        if os.path.exists(dst) and not overwrite:
            return tr(
                "❗ Target already exists: '{dst}'. Set overwrite=True to replace.",
                dst=disp_dst,
            )
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            note = (
                "\n⚠️ Overwrote existing file. (recommended only after reading the file to be overwritten)"
                if (os.path.exists(dst) and overwrite)
                else ""
            )
            self.report_success(
                tr("✅ Copied '{src}' to '{dst}'", src=disp_src, dst=disp_dst)
            )
            return tr("✅ Copied '{src}' to '{dst}'", src=disp_src, dst=disp_dst) + note
        except Exception as e:
            return tr(
                "❗ Copy failed from '{src}' to '{dst}': {err}",
                src=disp_src,
                dst=disp_dst,
                err=str(e),
            )
