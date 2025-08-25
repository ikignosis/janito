from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.i18n import tr
from janito.tools.loop_protection_decorator import protect_against_loops


class ShowImageTool(ToolBase):
    """Display an image inline in the terminal using the rich library.

    Args:
        path (str): Path to the image file.
        width (int, optional): Target width in terminal cells. If unset, auto-fit.
        height (int, optional): Target height in terminal rows. If unset, auto-fit.
        preserve_aspect (bool, optional): Preserve aspect ratio. Default: True.

    Returns:
        str: Status message indicating display result or error details.
    """

    permissions = ToolPermissions(read=True)
    tool_name = "show_image"

    @protect_against_loops(max_calls=5, time_window=10.0, key_field="path")
    def run(
        self,
        path: str,
        width: int | None = None,
        height: int | None = None,
        preserve_aspect: bool = True,
    ) -> str:
        from janito.tools.tool_utils import display_path
        from janito.tools.path_utils import expand_path
        import os

        # Defer heavy imports to runtime
        try:
            from rich.console import Console
            from PIL import Image as PILImage
        except Exception as e:
            msg = tr("⚠️ Missing dependency: PIL/Pillow ({error})", error=e)
            self.report_error(msg)
            return msg

        path = expand_path(path)
        disp_path = display_path(path)
        self.report_action(
            tr("🖼️ Show image '{disp_path}'", disp_path=disp_path), ReportAction.READ
        )

        if not os.path.exists(path):
            msg = tr("❗ not found")
            self.report_warning(msg)
            return tr("Error: file not found: {path}", path=disp_path)

        try:
            console = Console()
            # rich.image.Image handles inline terminal display of common formats
            from rich.console import Console
            from rich.text import Text

            console = Console()
            img = PILImage.open(path)
            console.print(
                Text(
                    f"Image: {disp_path} ({img.width}x{img.height})", style="bold green"
                )
            )
            console.print(img)
            self.report_success(tr("✅ Displayed"))
            details = []
            if width:
                details.append(f"width={width}")
            if height:
                details.append(f"height={height}")
            if not preserve_aspect:
                details.append("preserve_aspect=False")
            info = ("; ".join(details)) if details else "auto-fit"
            return tr(
                "Image displayed: {disp_path} ({info})", disp_path=disp_path, info=info
            )
        except Exception as e:
            self.report_error(tr(" ❌ Error: {error}", error=e))
            return tr("Error displaying image: {error}", error=e)
