from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.i18n import tr
from janito.tools.loop_protection_decorator import protect_against_loops
from typing import Sequence


class ShowImageGridTool(ToolBase):
    """Display multiple images in a grid inline in the terminal using rich.

    Args:
        paths (list[str]): List of image file paths.
        columns (int, optional): Number of columns in the grid. Default: 2.
        width (int, optional): Max width for each image cell. Default: None (auto).
        height (int, optional): Max height for each image cell. Default: None (auto).
        preserve_aspect (bool, optional): Preserve aspect ratio. Default: True.

    Returns:
        str: Status string summarizing the grid display.
    """

    permissions = ToolPermissions(read=True)
    tool_name = "show_image_grid"

    @protect_against_loops(max_calls=5, time_window=10.0, key_field="paths")
    def run(
        self,
        paths: Sequence[str],
        columns: int = 2,
        width: int | None = None,
        height: int | None = None,
        preserve_aspect: bool = True,
    ) -> str:
        from janito.tools.path_utils import expand_path
        from janito.tools.tool_utils import display_path
        import os

        try:
            from rich.console import Console
            from rich.columns import Columns
            from PIL import Image as PILImage
            from rich.panel import Panel
        except Exception as e:
            msg = tr("⚠️ Missing dependency: PIL/Pillow ({error})", error=e)
            self.report_error(msg)
            return msg

        if not paths:
            return tr("No images provided")

        self.report_action(
            tr("🖼️ Show image grid ({n} images)", n=len(paths)), ReportAction.READ
        )

        console = Console()
        images = []
        shown = 0
        for p in paths:
            fp = expand_path(p)
            if not os.path.exists(fp):
                self.report_warning(tr("❗ not found: {p}", p=display_path(fp)))
                continue
            try:
                img = PILImage.open(fp)
                title = f"{display_path(fp)} ({img.width}x{img.height})"
                images.append(
                    Panel.fit(title, title=display_path(fp), border_style="dim")
                )
                shown += 1
            except Exception as e:
                self.report_warning(tr("⚠️ Skipped {p}: {e}", p=display_path(fp), e=e))

        if not images:
            return tr("No images could be displayed")

        # Render in columns (grid-like)
        console.print(Columns(images, equal=True, expand=True, columns=columns))
        self.report_success(tr("✅ Displayed {n} images", n=shown))
        return tr(
            "Displayed {shown}/{total} images in a {cols}x? grid",
            shown=shown,
            total=len(paths),
            cols=columns,
        )
